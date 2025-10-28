"""
Data type consistency tests.

These tests ensure that all financial data uses correct types:
- Decimal for money (never float)
- date for accounting dates (never datetime/TIMESTAMP)
- Exactly 2 decimal places for currency
- No floating-point arithmetic errors
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from qa_testing.generators import (
    FundGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
)
from qa_testing.validators import DataTypeError, DataTypeValidator


class TestMoneyAmountValidation:
    """Tests for money amount type validation."""

    def test_decimal_amount_passes_validation(self):
        """Test that Decimal amounts with 2 decimals pass validation."""
        valid_amounts = [
            Decimal("100.00"),
            Decimal("0.01"),
            Decimal("999999.99"),
            Decimal("1234.56"),
        ]

        for amount in valid_amounts:
            assert DataTypeValidator.validate_money_amount(amount)

    def test_float_amount_fails_validation(self):
        """Test that float amounts fail validation."""
        float_amount = 123.45  # WRONG! Should be Decimal

        with pytest.raises(DataTypeError, match="is float"):
            DataTypeValidator.validate_money_amount(float_amount)

    def test_wrong_precision_fails_validation(self):
        """Test that amounts with wrong decimal places fail."""
        # 3 decimal places
        wrong_precision = Decimal("123.456")

        with pytest.raises(DataTypeError, match="decimal places"):
            DataTypeValidator.validate_money_amount(wrong_precision)

    def test_integer_decimal_fails_validation(self):
        """Test that Decimal without decimals fails (must have .00)."""
        integer_decimal = Decimal("100")  # Should be Decimal("100.00")

        with pytest.raises(DataTypeError, match="decimal places"):
            DataTypeValidator.validate_money_amount(integer_decimal)

    def test_amount_exceeding_max_fails(self):
        """Test that amount exceeding NUMERIC(15,2) max fails."""
        too_large = Decimal("10000000000000.00")  # 10 trillion

        with pytest.raises(DataTypeError, match="exceeds NUMERIC"):
            DataTypeValidator.validate_money_amount(too_large)

    @pytest.mark.property
    @given(st.decimals(min_value=0, max_value=9999999999999, places=2))
    def test_all_valid_decimals_pass(self, amount):
        """Property: All Decimals with 2 places in range pass validation."""
        # Ensure exactly 2 decimal places
        amount = amount.quantize(Decimal("0.01"))

        assert DataTypeValidator.validate_money_amount(amount)


class TestAccountingDateValidation:
    """Tests for accounting date type validation."""

    def test_date_passes_validation(self):
        """Test that date values pass validation."""
        valid_dates = [
            date(2024, 1, 1),
            date.today(),
            date(2025, 12, 31),
        ]

        for date_value in valid_dates:
            assert DataTypeValidator.validate_accounting_date(date_value)

    def test_datetime_fails_validation(self):
        """Test that datetime (TIMESTAMP) fails validation."""
        timestamp = datetime.now()  # WRONG! Should be date

        with pytest.raises(DataTypeError, match="is TIMESTAMP"):
            DataTypeValidator.validate_accounting_date(timestamp)

    def test_string_date_fails_validation(self):
        """Test that string dates fail validation."""
        string_date = "2024-01-01"  # WRONG! Should be date

        with pytest.raises(DataTypeError, match="must be date"):
            DataTypeValidator.validate_accounting_date(string_date)


class TestFloatingPointErrors:
    """Tests for floating-point arithmetic errors."""

    def test_float_arithmetic_has_errors(self):
        """Test that float arithmetic has rounding errors."""
        # Float arithmetic (WRONG)
        float_sum = 0.1 + 0.2

        # This is the problem with floats!
        assert float_sum != 0.3
        assert float_sum == 0.30000000000000004

    def test_decimal_arithmetic_exact(self):
        """Test that Decimal arithmetic is exact."""
        # Decimal arithmetic (CORRECT)
        decimal_sum = Decimal("0.1") + Decimal("0.2")

        # Exact result
        assert decimal_sum == Decimal("0.3")

    def test_detect_floating_point_errors(self):
        """Test floating-point error detection."""
        results = DataTypeValidator.detect_floating_point_errors()

        # Float has errors
        assert results["float_error"] is True
        assert results["float_sum"] != results["float_expected"]

        # Decimal is correct
        assert results["decimal_correct"] is True
        assert results["decimal_sum"] == results["decimal_expected"]

    def test_money_calculations_with_decimal(self):
        """Test that money calculations with Decimal are exact."""
        # Calculate 3 payments of $100.33
        payments = [Decimal("100.33")] * 3
        total = sum(payments)

        assert total == Decimal("300.99")  # Exact

        # With floats (WRONG), this could be off
        float_payments = [100.33] * 3
        float_total = sum(float_payments)

        # Floats may have rounding errors
        assert isinstance(float_total, float)  # Not Decimal!


class TestCurrencyRounding:
    """Tests for currency rounding validation."""

    def test_properly_rounded_amount_passes(self):
        """Test that properly rounded amounts pass validation."""
        amounts = [
            Decimal("100.00"),
            Decimal("123.45"),
            Decimal("0.01"),
            Decimal("999.99"),
        ]

        for amount in amounts:
            assert DataTypeValidator.validate_currency_rounding(amount)

    def test_unrounded_amount_fails(self):
        """Test that unrounded amounts fail validation."""
        unrounded = Decimal("123.456")  # 3 decimals

        with pytest.raises(DataTypeError, match="not rounded to 2 decimals"):
            DataTypeValidator.validate_currency_rounding(unrounded)

    def test_division_results_must_be_rounded(self):
        """Test that division results must be rounded to 2 decimals."""
        # Divide $100 among 3 people
        total = Decimal("100.00")
        num_people = 3

        # Without rounding (WRONG)
        per_person_unrounded = total / Decimal(num_people)
        # Result: 33.33333333333333333333333333

        # This will fail validation
        with pytest.raises(DataTypeError):
            DataTypeValidator.validate_currency_rounding(per_person_unrounded)

        # With rounding (CORRECT)
        per_person_rounded = (total / Decimal(num_people)).quantize(Decimal("0.01"))
        # Result: 33.33

        assert DataTypeValidator.validate_currency_rounding(per_person_rounded)
        assert per_person_rounded == Decimal("33.33")


class TestModelTypeValidation:
    """Tests for validating model field types."""

    def test_transaction_has_correct_types(self):
        """Test that Transaction model uses correct types."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(property_id=property.id)

        # Validate field types
        assert DataTypeValidator.validate_model_types(
            transaction,
            {
                "amount": Decimal,
                "transaction_date": date,
            }
        )

    def test_member_has_correct_types(self):
        """Test that Member model uses correct types."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Validate field types
        assert DataTypeValidator.validate_model_types(
            member,
            {
                "current_balance": Decimal,
                "total_paid": Decimal,
                "total_owed": Decimal,
                "move_in_date": date,
            }
        )

    def test_fund_has_correct_types(self):
        """Test that Fund model uses correct types."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Validate field types
        assert DataTypeValidator.validate_model_types(
            fund,
            {
                "current_balance": Decimal,
                "minimum_balance": Decimal,
            }
        )

    def test_wrong_type_fails_validation(self):
        """Test that wrong field types fail validation."""
        # Create a mock object with wrong types
        class BadTransaction:
            amount = 123.45  # float (WRONG!)
            transaction_date = datetime.now()  # datetime (WRONG!)

        bad_txn = BadTransaction()

        with pytest.raises(DataTypeError, match="type errors"):
            DataTypeValidator.validate_model_types(
                bad_txn,
                {
                    "amount": Decimal,
                    "transaction_date": date,
                }
            )


class TestFloatScanning:
    """Tests for scanning data structures for floats."""

    def test_scan_dict_for_floats(self):
        """Test scanning dictionary for float values."""
        data = {
            "amount": 123.45,  # float (WRONG!)
            "name": "Test",
            "count": 5,
        }

        floats = DataTypeValidator.scan_for_floats(data)

        assert len(floats) == 1
        assert floats[0]["path"] == "root.amount"
        assert floats[0]["value"] == 123.45
        assert floats[0]["type"] == "float"

    def test_scan_nested_structure(self):
        """Test scanning nested data structures."""
        data = {
            "transactions": [
                {"amount": 100.00, "id": 1},  # float
                {"amount": 200.00, "id": 2},  # float
            ]
        }

        floats = DataTypeValidator.scan_for_floats(data)

        assert len(floats) == 2
        assert floats[0]["path"] == "root.transactions[0].amount"
        assert floats[1]["path"] == "root.transactions[1].amount"

    def test_scan_object_for_floats(self):
        """Test scanning object attributes for floats."""
        class Transaction:
            def __init__(self):
                self.amount = 123.45  # float (WRONG!)

        txn = Transaction()
        floats = DataTypeValidator.scan_for_floats(txn)

        assert len(floats) == 1
        assert "amount" in floats[0]["path"]


class TestGeneratedDataTypes:
    """Tests that generated test data uses correct types."""

    def test_generated_transactions_use_decimal(self):
        """Test that generated transactions use Decimal for amounts."""
        property = PropertyGenerator.create()
        transactions = TransactionGenerator.create_batch(100, property_id=property.id)

        for txn in transactions:
            # Must be Decimal
            assert isinstance(txn.amount, Decimal)

            # Must have exactly 2 decimal places
            assert DataTypeValidator.validate_money_amount(txn.amount)

            # Must not be float
            assert not isinstance(txn.amount, float)

    def test_generated_transactions_use_date(self):
        """Test that generated transactions use date for dates."""
        property = PropertyGenerator.create()
        transactions = TransactionGenerator.create_batch(100, property_id=property.id)

        for txn in transactions:
            # Must be date
            assert isinstance(txn.transaction_date, date)

            # Must not be datetime (TIMESTAMP)
            assert not isinstance(txn.transaction_date, datetime)

            # Validate
            assert DataTypeValidator.validate_accounting_date(txn.transaction_date)

    def test_generated_members_use_decimal(self):
        """Test that generated members use Decimal for balances."""
        property = PropertyGenerator.create()
        members = MemberGenerator.create_batch(100, property_id=property.id)

        for member in members:
            assert isinstance(member.current_balance, Decimal)
            assert isinstance(member.total_paid, Decimal)
            assert isinstance(member.total_owed, Decimal)

            # All should have 2 decimal places
            assert DataTypeValidator.validate_money_amount(member.current_balance)
            assert DataTypeValidator.validate_money_amount(member.total_paid)
            assert DataTypeValidator.validate_money_amount(member.total_owed)

    def test_no_floats_in_generated_data(self):
        """Test that generated data contains no float values."""
        property = PropertyGenerator.create()
        transactions = TransactionGenerator.create_batch(10, property_id=property.id)

        for txn in transactions:
            floats = DataTypeValidator.scan_for_floats(txn)

            # Should be no floats
            assert len(floats) == 0, f"Found floats in transaction: {floats}"
