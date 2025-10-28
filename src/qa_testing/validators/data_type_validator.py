"""
Data type validators for financial data.

These validators ensure that financial data uses correct types:
- NUMERIC(15,2) for money amounts (never float)
- DATE for accounting dates (never TIMESTAMP)
- Exactly 2 decimal places for currency
- No floating-point arithmetic errors

CRITICAL: Financial calculations MUST use Decimal to avoid floating-point errors.
Example: 0.1 + 0.2 = 0.3 (not 0.30000000000000004)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .accounting_validators import ValidationError


class DataTypeError(ValidationError):
    """Raised when data type validation fails."""

    pass


class DataTypeValidator:
    """
    Validator for data type correctness.

    CRITICAL RULES:
    1. Money amounts MUST be Decimal, never float
    2. Money amounts MUST have exactly 2 decimal places
    3. Accounting dates MUST be DATE, never TIMESTAMP
    4. No floating-point arithmetic errors allowed
    """

    @staticmethod
    def validate_money_amount(amount: Any) -> bool:
        """
        Validate money amount uses NUMERIC(15,2).

        Args:
            amount: Amount to validate

        Returns:
            True if valid

        Raises:
            DataTypeError: If amount is not Decimal or has wrong precision
        """
        # Check if it's a float (WRONG!)
        if isinstance(amount, float):
            raise DataTypeError(
                f"Money amount is float ({amount})! Must use Decimal for financial calculations. "
                f"Floats cause rounding errors: 0.1 + 0.2 = {0.1 + 0.2} (not 0.3)"
            )

        # Must be Decimal
        if not isinstance(amount, Decimal):
            raise DataTypeError(
                f"Money amount is {type(amount).__name__} ({amount}), must be Decimal. "
                f"Use Decimal('123.45') or money_amount() function."
            )

        # Must have exactly 2 decimal places
        exponent = amount.as_tuple().exponent
        if exponent != -2:
            raise DataTypeError(
                f"Amount {amount} has {abs(exponent)} decimal places, must have exactly 2. "
                f"Use .quantize(Decimal('0.01')) to fix."
            )

        # Check if within NUMERIC(15,2) range
        # Maximum: 9,999,999,999,999.99 (13 digits + 2 decimals = 15 total)
        if abs(amount) >= Decimal("10000000000000"):  # 10 trillion
            raise DataTypeError(
                f"Amount {amount} exceeds NUMERIC(15,2) max (9,999,999,999,999.99)"
            )

        return True

    @staticmethod
    def validate_accounting_date(date_value: Any) -> bool:
        """
        Validate accounting date uses DATE, not TIMESTAMP.

        Args:
            date_value: Date to validate

        Returns:
            True if valid

        Raises:
            DataTypeError: If date is TIMESTAMP instead of DATE
        """
        # Check if it's a datetime (TIMESTAMP - WRONG!)
        if isinstance(date_value, datetime):
            raise DataTypeError(
                f"Accounting date is TIMESTAMP ({date_value})! Must use DATE. "
                f"Use date_value.date() to convert, or use date(YYYY, MM, DD)."
            )

        # Must be date
        if not isinstance(date_value, date):
            raise DataTypeError(
                f"Date is {type(date_value).__name__} ({date_value}), must be date. "
                f"Use date(YYYY, MM, DD) or date.today()."
            )

        return True

    @staticmethod
    def detect_floating_point_errors() -> dict:
        """
        Detect if floating-point arithmetic has errors.

        Returns:
            Dictionary with test results showing float errors

        Example:
            >>> results = DataTypeValidator.detect_floating_point_errors()
            >>> results['float_error']
            True  # 0.1 + 0.2 != 0.3
            >>> results['decimal_correct']
            True  # Decimal('0.1') + Decimal('0.2') == Decimal('0.3')
        """
        # Test float arithmetic (WRONG)
        float_sum = 0.1 + 0.2
        float_error = float_sum != 0.3

        # Test Decimal arithmetic (CORRECT)
        decimal_sum = Decimal("0.1") + Decimal("0.2")
        decimal_correct = decimal_sum == Decimal("0.3")

        return {
            "float_sum": float_sum,
            "float_expected": 0.3,
            "float_error": float_error,
            "float_error_message": f"0.1 + 0.2 = {float_sum} (not 0.3)" if float_error else None,
            "decimal_sum": decimal_sum,
            "decimal_expected": Decimal("0.3"),
            "decimal_correct": decimal_correct,
            "recommendation": "Always use Decimal for money calculations, never float"
        }

    @staticmethod
    def validate_currency_rounding(amount: Decimal) -> bool:
        """
        Validate that currency amount is properly rounded to 2 decimals.

        Args:
            amount: Decimal amount to validate

        Returns:
            True if properly rounded

        Raises:
            DataTypeError: If amount has wrong number of decimal places
        """
        if not isinstance(amount, Decimal):
            raise DataTypeError("Amount must be Decimal")

        # Check decimal places
        exponent = amount.as_tuple().exponent
        if exponent != -2:
            raise DataTypeError(
                f"Amount {amount} not rounded to 2 decimals (has {abs(exponent)} decimals). "
                f"Use amount.quantize(Decimal('0.01'))"
            )

        return True

    @staticmethod
    def validate_model_types(model: Any, expected_types: dict[str, type]) -> bool:
        """
        Validate model field types match expected types.

        Args:
            model: Model instance to validate
            expected_types: Dictionary mapping field names to expected types

        Returns:
            True if all fields match expected types

        Raises:
            DataTypeError: If any field has wrong type

        Example:
            >>> validate_model_types(
            ...     transaction,
            ...     {"amount": Decimal, "transaction_date": date}
            ... )
        """
        errors = []

        for field_name, expected_type in expected_types.items():
            if not hasattr(model, field_name):
                errors.append(f"Model lacks field '{field_name}'")
                continue

            field_value = getattr(model, field_name)

            # Allow None for optional fields
            if field_value is None:
                continue

            if not isinstance(field_value, expected_type):
                actual_type = type(field_value).__name__
                expected_type_name = expected_type.__name__
                errors.append(
                    f"Field '{field_name}' is {actual_type} ({field_value}), "
                    f"expected {expected_type_name}"
                )

        if errors:
            raise DataTypeError(
                f"Model {type(model).__name__} has type errors:\n" +
                "\n".join(f"  - {error}" for error in errors)
            )

        return True

    @staticmethod
    def scan_for_floats(data: Any, path: str = "root") -> list[dict]:
        """
        Recursively scan data structure for float values.

        This helps detect accidental float usage in nested structures.

        Args:
            data: Data to scan (dict, list, object, etc.)
            path: Current path in data structure

        Returns:
            List of dictionaries describing found floats

        Example:
            >>> floats = DataTypeValidator.scan_for_floats({"amount": 123.45})
            >>> floats[0]
            {"path": "root.amount", "value": 123.45, "type": "float"}
        """
        floats_found = []

        if isinstance(data, float):
            floats_found.append({
                "path": path,
                "value": data,
                "type": "float",
                "warning": "Float detected! Should use Decimal for money."
            })

        elif isinstance(data, dict):
            for key, value in data.items():
                floats_found.extend(
                    DataTypeValidator.scan_for_floats(value, f"{path}.{key}")
                )

        elif isinstance(data, (list, tuple)):
            for i, item in enumerate(data):
                floats_found.extend(
                    DataTypeValidator.scan_for_floats(item, f"{path}[{i}]")
                )

        elif hasattr(data, '__dict__'):
            # Scan object attributes
            for key, value in data.__dict__.items():
                floats_found.extend(
                    DataTypeValidator.scan_for_floats(value, f"{path}.{key}")
                )

        return floats_found
