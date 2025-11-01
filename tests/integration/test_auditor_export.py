"""
Integration Tests for Auditor Export Functionality (Sprint 21, Phase 4)

Tests the complete auditor export workflow from saas202509 including:
- CSV generation with full general ledger data
- Evidence linking for violations, work orders, ARC requests
- File integrity verification with SHA-256 hashing
- Balance validation (debits = credits)
- Running balance calculations per account
- Audit trail tracking for downloads
- Date range exports for external auditors
"""

import pytest
import csv
import hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
import uuid

from qa_testing.models import (
    Member, Property, Unit, Fund, Transaction, LedgerEntry,
    AuditorExport, AuditorExportStatus, JournalEntry,
    Violation, WorkOrder, ARCRequest
)
from qa_testing.generators import (
    MemberGenerator, PropertyGenerator, TransactionGenerator,
    LedgerGenerator, AuditorExportGenerator, EvidenceGenerator,
    ViolationGenerator, WorkOrderGenerator, ARCRequestGenerator
)
from qa_testing.validators import (
    CSVValidator, FinancialValidator, AuditValidator,
    HashValidator, BalanceValidator
)


class TestAuditorExportGeneration:
    """Test auditor export CSV generation functionality"""

    def test_create_simple_auditor_export(self):
        """Test creating a simple auditor export with basic transactions"""
        # Arrange
        property_data = PropertyGenerator.create_property("Audit HOA", 100)
        members = MemberGenerator.create_bulk_members(property_data, 20)

        # Generate sample transactions for Q3 2025
        start_date = date(2025, 7, 1)
        end_date = date(2025, 9, 30)

        transactions = []
        for member in members[:10]:
            tx = TransactionGenerator.create_dues_payment(
                member=member,
                amount=Decimal("275.00"),
                payment_date=date(2025, 8, 1)
            )
            transactions.append(tx)

        # Act
        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            export_type='general_ledger',
            requested_by='auditor@cpa-firm.com'
        )

        csv_content = AuditorExportGenerator.generate_csv(export)

        # Assert
        assert export is not None
        assert export.status == AuditorExportStatus.COMPLETED
        assert export.start_date == start_date
        assert export.end_date == end_date
        assert len(csv_content) > 1000  # Should have substantial content
        assert CSVValidator.is_valid_csv(csv_content)
        assert CSVValidator.has_required_columns(csv_content, [
            'date', 'journal_entry_id', 'account', 'description',
            'debit', 'credit', 'running_balance'
        ])

    def test_export_with_evidence_linking(self):
        """Test export includes evidence URLs for supporting documents"""
        # Arrange
        property_data = PropertyGenerator.create_property("Evidence HOA", 50)
        member = MemberGenerator.create_member(property_data, unit_number="101")

        # Create violation with evidence
        violation = ViolationGenerator.create_violation(
            property=property_data,
            member=member,
            violation_type='landscaping',
            evidence_urls=[
                'https://s3.amazonaws.com/evidence/violation_123_photo1.jpg',
                'https://s3.amazonaws.com/evidence/violation_123_photo2.jpg'
            ]
        )

        # Create work order with invoice
        work_order = WorkOrderGenerator.create_work_order(
            property=property_data,
            category='landscaping',
            vendor='ABC Landscaping',
            amount=Decimal("450.00"),
            invoice_url='https://s3.amazonaws.com/invoices/wo_456.pdf'
        )

        # Create ARC request with plans
        arc_request = ARCRequestGenerator.create_arc_request(
            property=property_data,
            member=member,
            request_type='fence',
            plans_url='https://s3.amazonaws.com/arc/request_789_plans.pdf'
        )

        # Act
        export = AuditorExportGenerator.create_export_with_evidence(
            property=property_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            violations=[violation],
            work_orders=[work_order],
            arc_requests=[arc_request]
        )

        csv_content = AuditorExportGenerator.generate_csv(export)

        # Assert
        assert export.has_evidence_links is True
        assert CSVValidator.contains_url(csv_content, 'violation_123_photo1.jpg')
        assert CSVValidator.contains_url(csv_content, 'wo_456.pdf')
        assert CSVValidator.contains_url(csv_content, 'request_789_plans.pdf')
        assert 'evidence_url' in csv_content.lower()

    def test_export_balance_validation(self):
        """Test that exports maintain debit/credit balance"""
        # Arrange
        property_data = PropertyGenerator.create_property("Balance HOA", 75)

        # Create balanced transactions
        journal_entries = []

        # Entry 1: Dues collection
        journal_entries.append(LedgerGenerator.create_journal_entry(
            property=property_data,
            date=date(2025, 10, 1),
            description='Monthly dues collection',
            debits=[
                {'account': '1100-Cash', 'amount': Decimal("5000.00")}
            ],
            credits=[
                {'account': '4100-Dues Income', 'amount': Decimal("5000.00")}
            ]
        ))

        # Entry 2: Vendor payment
        journal_entries.append(LedgerGenerator.create_journal_entry(
            property=property_data,
            date=date(2025, 10, 15),
            description='Landscaping payment',
            debits=[
                {'account': '6100-Landscaping', 'amount': Decimal("1500.00")}
            ],
            credits=[
                {'account': '1100-Cash', 'amount': Decimal("1500.00")}
            ]
        ))

        # Act
        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31),
            journal_entries=journal_entries
        )

        csv_content = AuditorExportGenerator.generate_csv(export)
        validation_result = BalanceValidator.validate_csv_balance(csv_content)

        # Assert
        assert validation_result['is_balanced'] is True
        assert validation_result['total_debits'] == Decimal("6500.00")
        assert validation_result['total_credits'] == Decimal("6500.00")
        assert validation_result['difference'] == Decimal("0.00")

    def test_export_running_balance_calculation(self):
        """Test running balance calculations per account"""
        # Arrange
        property_data = PropertyGenerator.create_property("Running HOA", 40)

        # Create sequential transactions for one account
        cash_transactions = []
        running_balance = Decimal("10000.00")  # Starting balance

        for day in range(1, 11):  # 10 days of transactions
            if day % 2 == 0:  # Even days: income
                amount = Decimal("500.00")
                cash_transactions.append({
                    'date': date(2025, 11, day),
                    'account': '1100-Cash',
                    'debit': amount,
                    'credit': Decimal("0.00"),
                    'expected_balance': running_balance + amount
                })
                running_balance += amount
            else:  # Odd days: expense
                amount = Decimal("200.00")
                cash_transactions.append({
                    'date': date(2025, 11, day),
                    'account': '1100-Cash',
                    'debit': Decimal("0.00"),
                    'credit': amount,
                    'expected_balance': running_balance - amount
                })
                running_balance -= amount

        # Act
        export = AuditorExportGenerator.create_export_with_transactions(
            property=property_data,
            transactions=cash_transactions
        )

        csv_content = AuditorExportGenerator.generate_csv(export)
        balances = CSVValidator.extract_running_balances(csv_content, '1100-Cash')

        # Assert
        assert len(balances) == 10
        for i, tx in enumerate(cash_transactions):
            assert balances[i] == tx['expected_balance']

        # Final balance should be: 10000 + (5 * 500) - (5 * 200) = 11500
        assert balances[-1] == Decimal("11500.00")

    def test_export_file_integrity(self):
        """Test SHA-256 file integrity verification"""
        # Arrange
        property_data = PropertyGenerator.create_property("Integrity HOA", 60)

        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31)
        )

        csv_content = AuditorExportGenerator.generate_csv(export)

        # Act
        # Calculate SHA-256 hash
        file_hash = hashlib.sha256(csv_content.encode()).hexdigest()
        export.file_hash = file_hash
        export.save()

        # Verify integrity
        is_valid = HashValidator.verify_file_integrity(
            content=csv_content,
            expected_hash=export.file_hash
        )

        # Assert
        assert is_valid is True
        assert len(export.file_hash) == 64  # SHA-256 produces 64 hex characters

        # Test tampering detection
        tampered_content = csv_content + "TAMPERED"
        is_tampered_valid = HashValidator.verify_file_integrity(
            content=tampered_content,
            expected_hash=export.file_hash
        )
        assert is_tampered_valid is False

    def test_export_api_workflow(self):
        """Test complete API workflow for auditor exports"""
        # Arrange
        property_data = PropertyGenerator.create_property("API HOA", 80)

        # Simulate API request
        api_request = {
            'property_id': property_data.id,
            'start_date': '2025-07-01',
            'end_date': '2025-09-30',
            'export_format': 'csv',
            'include_evidence': True,
            'requested_by': 'cpa@audit-firm.com'
        }

        # Act
        # Step 1: Create export
        export = AuditorExportGenerator.create_from_api_request(api_request)
        assert export.status == AuditorExportStatus.PENDING

        # Step 2: Generate CSV
        export.generate()
        assert export.status == AuditorExportStatus.GENERATING

        # Step 3: Complete generation
        csv_content = export.complete_generation()
        assert export.status == AuditorExportStatus.COMPLETED

        # Step 4: Download tracking
        download_record = export.track_download(
            downloaded_by='cpa@audit-firm.com',
            ip_address='192.168.1.100'
        )

        # Assert
        assert export.file_url is not None
        assert export.file_size_bytes > 0
        assert export.row_count > 0
        assert download_record.downloaded_at is not None
        assert export.download_count == 1

    def test_export_date_range_filtering(self):
        """Test exports correctly filter by date range"""
        # Arrange
        property_data = PropertyGenerator.create_property("DateRange HOA", 45)

        # Create transactions across multiple months
        all_transactions = []

        # Q1 2025 transactions
        for month in [1, 2, 3]:
            tx = TransactionGenerator.create_transaction(
                property=property_data,
                date=date(2025, month, 15),
                amount=Decimal("1000.00")
            )
            all_transactions.append(tx)

        # Q2 2025 transactions
        for month in [4, 5, 6]:
            tx = TransactionGenerator.create_transaction(
                property=property_data,
                date=date(2025, month, 15),
                amount=Decimal("1000.00")
            )
            all_transactions.append(tx)

        # Act
        # Export only Q1
        q1_export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            transactions=all_transactions
        )

        q1_csv = AuditorExportGenerator.generate_csv(q1_export)
        q1_row_count = CSVValidator.count_data_rows(q1_csv)

        # Export only Q2
        q2_export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 6, 30),
            transactions=all_transactions
        )

        q2_csv = AuditorExportGenerator.generate_csv(q2_export)
        q2_row_count = CSVValidator.count_data_rows(q2_csv)

        # Assert
        assert q1_row_count == 3  # Only Q1 transactions
        assert q2_row_count == 3  # Only Q2 transactions

        # Verify dates in exports
        q1_dates = CSVValidator.extract_dates(q1_csv)
        for dt in q1_dates:
            assert dt >= date(2025, 1, 1)
            assert dt <= date(2025, 3, 31)

        q2_dates = CSVValidator.extract_dates(q2_csv)
        for dt in q2_dates:
            assert dt >= date(2025, 4, 1)
            assert dt <= date(2025, 6, 30)

    def test_export_large_dataset_performance(self):
        """Test export performance with large datasets"""
        import time

        # Arrange
        property_data = PropertyGenerator.create_property("Large HOA", 500)

        # Generate 10,000 journal entries (full year of activity for large HOA)
        journal_entries = []
        for day in range(365):
            for entry_num in range(27):  # ~27 entries per day = ~10,000 total
                entry = LedgerGenerator.create_random_journal_entry(
                    property=property_data,
                    date=date(2025, 1, 1) + timedelta(days=day)
                )
                journal_entries.append(entry)

        # Act
        start_time = time.time()

        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            journal_entries=journal_entries
        )

        csv_content = AuditorExportGenerator.generate_csv(export)
        generation_time = time.time() - start_time

        # Assert
        assert generation_time < 10.0  # Should complete in under 10 seconds
        assert export.row_count >= 10000
        assert len(csv_content) > 500000  # Should be substantial size

        # Verify CSV is still valid and balanced
        assert CSVValidator.is_valid_csv(csv_content)
        validation = BalanceValidator.validate_csv_balance(csv_content)
        assert validation['is_balanced'] is True

    def test_export_error_handling(self):
        """Test error handling in export generation"""
        # Test missing required data
        with pytest.raises(ValueError, match="Property is required"):
            AuditorExportGenerator.create_export(
                property=None,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31)
            )

        # Test invalid date range
        with pytest.raises(ValueError, match="End date must be after start date"):
            AuditorExportGenerator.create_export(
                property=PropertyGenerator.create_property("Test", 10),
                start_date=date(2025, 12, 31),
                end_date=date(2025, 1, 1)
            )

        # Test future date range
        with pytest.raises(ValueError, match="Cannot export future dates"):
            AuditorExportGenerator.create_export(
                property=PropertyGenerator.create_property("Test", 10),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31)
            )

    def test_export_multi_fund_support(self):
        """Test exports handle multiple funds correctly"""
        # Arrange
        property_data = PropertyGenerator.create_property("MultiFund HOA", 100)

        # Create transactions for different funds
        operating_fund = Fund(id='operating', name='Operating Fund')
        reserve_fund = Fund(id='reserve', name='Reserve Fund')

        transactions = []

        # Operating fund transactions
        for i in range(5):
            tx = TransactionGenerator.create_fund_transaction(
                property=property_data,
                fund=operating_fund,
                amount=Decimal("1000.00"),
                date=date(2025, 10, i + 1)
            )
            transactions.append(tx)

        # Reserve fund transactions
        for i in range(5):
            tx = TransactionGenerator.create_fund_transaction(
                property=property_data,
                fund=reserve_fund,
                amount=Decimal("5000.00"),
                date=date(2025, 10, i + 1)
            )
            transactions.append(tx)

        # Act
        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31),
            transactions=transactions
        )

        csv_content = AuditorExportGenerator.generate_csv(export)

        # Assert
        assert CSVValidator.contains_text(csv_content, 'Operating Fund')
        assert CSVValidator.contains_text(csv_content, 'Reserve Fund')

        # Verify fund balances are tracked separately
        operating_balance = CSVValidator.get_fund_balance(csv_content, 'operating')
        reserve_balance = CSVValidator.get_fund_balance(csv_content, 'reserve')

        assert operating_balance == Decimal("5000.00")  # 5 * 1000
        assert reserve_balance == Decimal("25000.00")   # 5 * 5000


class TestAuditorExportCompliance:
    """Test auditor export compliance and audit requirements"""

    def test_export_immutability(self):
        """Test that completed exports cannot be modified"""
        # Arrange
        property_data = PropertyGenerator.create_property("Immutable HOA", 50)

        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31)
        )

        original_hash = export.file_hash
        original_content = export.csv_content

        # Act & Assert
        # Try to modify completed export
        with pytest.raises(ValueError, match="Cannot modify completed export"):
            export.csv_content = "Modified content"
            export.save()

        # Verify original content unchanged
        assert export.file_hash == original_hash
        assert export.csv_content == original_content

    def test_export_audit_trail(self):
        """Test audit trail for export access"""
        # Arrange
        property_data = PropertyGenerator.create_property("AuditTrail HOA", 70)

        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            requested_by='initial@auditor.com'
        )

        # Act
        # Multiple downloads by different users
        download1 = export.track_download(
            downloaded_by='partner@cpa-firm.com',
            ip_address='192.168.1.100'
        )

        download2 = export.track_download(
            downloaded_by='senior@cpa-firm.com',
            ip_address='192.168.1.101'
        )

        download3 = export.track_download(
            downloaded_by='manager@cpa-firm.com',
            ip_address='192.168.1.102'
        )

        audit_trail = export.get_audit_trail()

        # Assert
        assert export.download_count == 3
        assert len(audit_trail) == 4  # 1 creation + 3 downloads

        # Verify audit trail entries
        assert audit_trail[0]['action'] == 'created'
        assert audit_trail[0]['user'] == 'initial@auditor.com'

        assert audit_trail[1]['action'] == 'downloaded'
        assert audit_trail[1]['user'] == 'partner@cpa-firm.com'

        assert audit_trail[2]['action'] == 'downloaded'
        assert audit_trail[2]['user'] == 'senior@cpa-firm.com'

        assert audit_trail[3]['action'] == 'downloaded'
        assert audit_trail[3]['user'] == 'manager@cpa-firm.com'

    def test_export_retention_policy(self):
        """Test export retention and archival policies"""
        # Arrange
        property_data = PropertyGenerator.create_property("Retention HOA", 55)

        # Create exports with different ages
        current_export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31),
            created_at=datetime.now()
        )

        old_export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2018, 1, 1),
            end_date=date(2018, 12, 31),
            created_at=datetime.now() - timedelta(days=2555)  # 7 years old
        )

        # Act
        retention_check = AuditValidator.check_retention_requirements([
            current_export,
            old_export
        ])

        # Assert
        assert retention_check[current_export.id]['retain'] is True
        assert retention_check[current_export.id]['reason'] == 'Within retention period'

        assert retention_check[old_export.id]['retain'] is True
        assert retention_check[old_export.id]['reason'] == 'Required for 7-year audit retention'

    def test_export_completeness_verification(self):
        """Test verification of export completeness"""
        # Arrange
        property_data = PropertyGenerator.create_property("Complete HOA", 65)

        # Create comprehensive transaction set
        transactions = TransactionGenerator.create_complete_month_transactions(
            property=property_data,
            year=2025,
            month=10
        )

        export = AuditorExportGenerator.create_export(
            property=property_data,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31),
            transactions=transactions
        )

        csv_content = AuditorExportGenerator.generate_csv(export)

        # Act
        completeness_check = AuditValidator.verify_export_completeness(
            csv_content=csv_content,
            expected_transactions=transactions
        )

        # Assert
        assert completeness_check['is_complete'] is True
        assert completeness_check['missing_transactions'] == []
        assert completeness_check['transaction_count'] == len(transactions)
        assert completeness_check['has_all_required_fields'] is True