"""
Integration Tests for Resale Disclosure Packages (Sprint 22, Phase 4)

Tests the complete resale disclosure workflow from saas202509 including:
- State-compliant PDF generation (CA, TX, FL, DEFAULT templates)
- 7-section disclosure structure
- Financial snapshot capture at point in time
- SHA-256 file integrity hashing
- Revenue tracking ($200-500 per package)
- Email delivery to buyers
- Invoice generation for HOA fees
- Multi-state compliance testing
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import hashlib
import json

from qa_testing.models import (
    Member, Property, Unit, Fund, Transaction, LedgerEntry,
    ResaleDisclosure, ResaleDisclosureStatus, DisclosureState,
    Invoice, EmailDelivery
)
from qa_testing.generators import (
    MemberGenerator, PropertyGenerator, TransactionGenerator,
    ResaleDisclosureGenerator, FinancialSnapshotGenerator,
    InvoiceGenerator, DocumentGenerator
)
from qa_testing.validators import (
    PDFValidator, FinancialValidator, ComplianceValidator,
    HashValidator, StateComplianceValidator
)


class TestResaleDisclosureGeneration:
    """Test resale disclosure package generation functionality"""

    def test_create_simple_resale_disclosure(self):
        """Test creating a simple resale disclosure package"""
        # Arrange
        property_data = PropertyGenerator.create_property("Resale HOA", 150)
        seller = MemberGenerator.create_member(property_data, unit_number="205")
        buyer_info = {
            'name': 'John Buyer',
            'email': 'buyer@email.com',
            'phone': '555-0123'
        }

        # Act
        disclosure = ResaleDisclosureGenerator.create_disclosure(
            property=property_data,
            seller=seller,
            buyer=buyer_info,
            unit_number="205",
            sale_date=date(2025, 12, 1),
            state='CA'  # California
        )

        pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)

        # Assert
        assert disclosure is not None
        assert disclosure.status == ResaleDisclosureStatus.DRAFT
        assert disclosure.state == 'CA'
        assert disclosure.unit_number == "205"
        assert len(pdf_bytes) > 10000  # Should be substantial PDF
        assert PDFValidator.is_valid_pdf(pdf_bytes)
        assert PDFValidator.get_page_count(pdf_bytes) >= 5

    def test_state_specific_templates(self):
        """Test generation with state-specific templates"""
        states_to_test = [
            ('CA', 'California Civil Code 5235'),  # California
            ('TX', 'Texas Property Code 207'),      # Texas
            ('FL', 'Florida Statute 720.303'),      # Florida
            ('DEFAULT', 'Standard Disclosure')       # Default template
        ]

        for state_code, state_requirement in states_to_test:
            # Arrange
            property_data = PropertyGenerator.create_property(f"{state_code} HOA", 100)
            seller = MemberGenerator.create_member(property_data, unit_number="101")

            # Act
            disclosure = ResaleDisclosureGenerator.create_disclosure(
                property=property_data,
                seller=seller,
                buyer={'name': 'Test Buyer', 'email': 'test@email.com'},
                unit_number="101",
                state=state_code
            )

            pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)

            # Assert
            assert disclosure.state == state_code
            assert PDFValidator.is_valid_pdf(pdf_bytes)
            assert PDFValidator.contains_text(pdf_bytes, state_requirement)

            # Verify state-specific sections
            if state_code == 'CA':
                assert PDFValidator.contains_text(pdf_bytes, 'Assessment Information')
                assert PDFValidator.contains_text(pdf_bytes, 'Reserve Study Summary')
            elif state_code == 'TX':
                assert PDFValidator.contains_text(pdf_bytes, 'Restrictive Covenants')
                assert PDFValidator.contains_text(pdf_bytes, 'Management Certificate')
            elif state_code == 'FL':
                assert PDFValidator.contains_text(pdf_bytes, 'Financial Report')
                assert PDFValidator.contains_text(pdf_bytes, 'Frequently Asked Questions')

    def test_seven_section_disclosure_structure(self):
        """Test that disclosure includes all 7 required sections"""
        # Arrange
        property_data = PropertyGenerator.create_property("Complete HOA", 200)
        seller = MemberGenerator.create_member(property_data, unit_number="301")

        # Create comprehensive financial data
        financial_snapshot = FinancialSnapshotGenerator.create_snapshot(
            property=property_data,
            as_of_date=date(2025, 11, 30),
            include_reserves=True,
            include_budget=True
        )

        # Act
        disclosure = ResaleDisclosureGenerator.create_comprehensive_disclosure(
            property=property_data,
            seller=seller,
            buyer={'name': 'Jane Buyer', 'email': 'jane@email.com'},
            unit_number="301",
            financial_snapshot=financial_snapshot,
            state='CA'
        )

        pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)
        sections = PDFValidator.extract_sections(pdf_bytes)

        # Assert - Verify all 7 sections
        required_sections = [
            'Cover Page',
            'HOA Information',
            'Financial Summary',
            'Assessment Information',
            'Account Status',
            'Governing Documents',
            'Additional Disclosures'
        ]

        for section in required_sections:
            assert section in sections
            assert PDFValidator.contains_text(pdf_bytes, section)

    def test_financial_snapshot_capture(self):
        """Test capturing financial snapshot at point in time"""
        # Arrange
        property_data = PropertyGenerator.create_property("Snapshot HOA", 125)
        seller = MemberGenerator.create_member(property_data, unit_number="215")

        # Create historical financial data
        transactions = []
        for month in range(1, 12):  # 11 months of data
            tx = TransactionGenerator.create_dues_payment(
                member=seller,
                amount=Decimal("350.00"),
                payment_date=date(2025, month, 1)
            )
            transactions.append(tx)

        # Add some delinquency
        delinquent_amount = Decimal("700.00")  # 2 months behind
        seller.account_balance = -delinquent_amount

        # Act
        disclosure = ResaleDisclosureGenerator.create_disclosure(
            property=property_data,
            seller=seller,
            buyer={'name': 'Buyer Name', 'email': 'buyer@test.com'},
            unit_number="215",
            capture_financials=True
        )

        # Assert
        assert disclosure.financial_snapshot is not None
        assert disclosure.financial_snapshot['account_balance'] == -delinquent_amount
        assert disclosure.financial_snapshot['monthly_assessment'] == Decimal("350.00")
        assert disclosure.financial_snapshot['special_assessments'] == Decimal("0.00")
        assert disclosure.financial_snapshot['reserve_balance'] > Decimal("0.00")
        assert disclosure.financial_snapshot['as_of_date'] == date.today()

        # Verify snapshot is immutable
        original_snapshot = disclosure.financial_snapshot.copy()
        seller.account_balance = Decimal("0.00")  # Change seller balance
        assert disclosure.financial_snapshot == original_snapshot  # Snapshot unchanged

    def test_pdf_integrity_hashing(self):
        """Test SHA-256 file integrity for generated PDFs"""
        # Arrange
        property_data = PropertyGenerator.create_property("Hash HOA", 90)
        seller = MemberGenerator.create_member(property_data, unit_number="405")

        disclosure = ResaleDisclosureGenerator.create_disclosure(
            property=property_data,
            seller=seller,
            buyer={'name': 'Test', 'email': 'test@test.com'},
            unit_number="405"
        )

        # Act
        pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        disclosure.file_hash = file_hash
        disclosure.save()

        # Verify integrity
        is_valid = HashValidator.verify_file_integrity(
            content=pdf_bytes,
            expected_hash=disclosure.file_hash
        )

        # Assert
        assert is_valid is True
        assert len(disclosure.file_hash) == 64  # SHA-256 produces 64 hex chars

        # Test tampering detection
        tampered_pdf = pdf_bytes + b"TAMPERED"
        is_tampered_valid = HashValidator.verify_file_integrity(
            content=tampered_pdf,
            expected_hash=disclosure.file_hash
        )
        assert is_tampered_valid is False

    def test_disclosure_api_workflow(self):
        """Test complete API workflow for resale disclosures"""
        # Arrange
        property_data = PropertyGenerator.create_property("API HOA", 110)
        seller = MemberGenerator.create_member(property_data, unit_number="505")

        # Simulate API request
        api_request = {
            'property_id': property_data.id,
            'seller_id': seller.id,
            'unit_number': '505',
            'buyer_name': 'API Buyer',
            'buyer_email': 'api@buyer.com',
            'buyer_phone': '555-9999',
            'sale_date': '2025-12-15',
            'state': 'TX'
        }

        # Act
        # Step 1: Create disclosure
        disclosure = ResaleDisclosureGenerator.create_from_api(api_request)
        assert disclosure.status == ResaleDisclosureStatus.DRAFT

        # Step 2: Generate PDF
        pdf_result = disclosure.generate_pdf()
        assert disclosure.status == ResaleDisclosureStatus.GENERATED
        assert pdf_result['pdf_url'] is not None
        assert pdf_result['file_size'] > 0

        # Step 3: Download PDF
        download_result = disclosure.download(
            downloaded_by='agent@realty.com',
            ip_address='192.168.1.50'
        )
        assert download_result['success'] is True
        assert disclosure.download_count == 1

        # Step 4: Deliver to buyer
        delivery_result = disclosure.deliver_to_buyer()
        assert disclosure.status == ResaleDisclosureStatus.DELIVERED
        assert delivery_result['email_sent'] is True
        assert delivery_result['delivered_at'] is not None

        # Step 5: Create invoice
        invoice_result = disclosure.create_invoice()
        assert invoice_result['invoice_number'] is not None
        assert invoice_result['amount'] >= Decimal("200.00")
        assert invoice_result['amount'] <= Decimal("500.00")
        assert disclosure.status == ResaleDisclosureStatus.BILLED

    def test_disclosure_fee_calculation(self):
        """Test fee calculation for resale disclosure packages"""
        # Standard fees by state
        state_fees = [
            ('CA', Decimal("395.00")),  # California standard
            ('TX', Decimal("375.00")),  # Texas standard
            ('FL', Decimal("250.00")),  # Florida standard
            ('DEFAULT', Decimal("200.00"))  # Default minimum
        ]

        for state, expected_fee in state_fees:
            # Arrange
            property_data = PropertyGenerator.create_property(f"Fee {state} HOA", 75)
            seller = MemberGenerator.create_member(property_data, unit_number="101")

            # Act
            disclosure = ResaleDisclosureGenerator.create_disclosure(
                property=property_data,
                seller=seller,
                buyer={'name': 'Buyer', 'email': 'buyer@test.com'},
                unit_number="101",
                state=state
            )

            fee = disclosure.calculate_fee()

            # Assert
            assert fee == expected_fee
            assert fee >= Decimal("200.00")  # Minimum fee
            assert fee <= Decimal("500.00")  # Maximum fee

    def test_disclosure_email_delivery(self):
        """Test email delivery of disclosure packages"""
        # Arrange
        property_data = PropertyGenerator.create_property("Email HOA", 85)
        seller = MemberGenerator.create_member(property_data, unit_number="605")

        disclosure = ResaleDisclosureGenerator.create_disclosure(
            property=property_data,
            seller=seller,
            buyer={
                'name': 'Email Buyer',
                'email': 'buyer@realestate.com',
                'phone': '555-1234'
            },
            unit_number="605"
        )

        # Generate PDF first
        pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)
        disclosure.pdf_url = 'https://s3.amazonaws.com/disclosures/disc_123.pdf'
        disclosure.status = ResaleDisclosureStatus.GENERATED

        # Act
        with patch('qa_testing.services.EmailService') as mock_email:
            mock_email.send_email.return_value = {'success': True, 'message_id': 'msg_123'}

            delivery_result = disclosure.deliver_to_buyer(
                cc_recipients=['agent@realty.com', 'escrow@titleco.com'],
                subject='HOA Resale Disclosure Package - Unit 605',
                body='Please find attached the HOA disclosure package for unit 605.'
            )

        # Assert
        assert delivery_result['success'] is True
        assert delivery_result['recipients'] == ['buyer@realestate.com']
        assert delivery_result['cc_recipients'] == ['agent@realty.com', 'escrow@titleco.com']
        assert disclosure.status == ResaleDisclosureStatus.DELIVERED
        assert disclosure.delivered_at is not None
        assert disclosure.delivered_to == 'buyer@realestate.com'

    def test_disclosure_performance(self):
        """Test performance of disclosure generation for large properties"""
        import time

        # Arrange
        property_data = PropertyGenerator.create_property("Large HOA", 1000)

        # Create complex property with lots of data
        members = MemberGenerator.create_bulk_members(property_data, 1000)

        # Generate extensive transaction history
        transactions = []
        for member in members[:100]:  # First 100 members
            for month in range(1, 13):  # 12 months
                tx = TransactionGenerator.create_dues_payment(
                    member=member,
                    amount=Decimal("300.00"),
                    payment_date=date(2025, month, 1)
                )
                transactions.append(tx)

        seller = members[50]  # Pick one seller

        # Act
        start_time = time.time()

        disclosure = ResaleDisclosureGenerator.create_comprehensive_disclosure(
            property=property_data,
            seller=seller,
            buyer={'name': 'Performance Buyer', 'email': 'perf@test.com'},
            unit_number=seller.unit_number,
            include_all_financials=True,
            include_all_documents=True
        )

        pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)
        generation_time = time.time() - start_time

        # Assert
        assert generation_time < 5.0  # Should complete in under 5 seconds
        assert len(pdf_bytes) > 50000  # Large comprehensive package
        assert PDFValidator.get_page_count(pdf_bytes) > 10

        # Verify quality despite size
        assert PDFValidator.is_valid_pdf(pdf_bytes)
        assert disclosure.file_hash is not None

    def test_disclosure_revenue_tracking(self):
        """Test revenue tracking from disclosure packages"""
        # Arrange
        property_data = PropertyGenerator.create_property("Revenue HOA", 150)

        # Create multiple disclosures over time
        disclosures = []
        total_expected_revenue = Decimal("0.00")

        for month in range(1, 13):  # 12 months
            for unit in range(1, 6):  # 5 units per month = 60 annual
                seller = MemberGenerator.create_member(
                    property_data,
                    unit_number=f"{month:02d}{unit:02d}"
                )

                disclosure = ResaleDisclosureGenerator.create_disclosure(
                    property=property_data,
                    seller=seller,
                    buyer={'name': f'Buyer {month}-{unit}', 'email': f'b{month}{unit}@test.com'},
                    unit_number=seller.unit_number,
                    state='CA',  # $395 fee
                    created_date=date(2025, month, 15)
                )

                disclosure.status = ResaleDisclosureStatus.BILLED
                disclosure.fee_amount = Decimal("395.00")
                disclosures.append(disclosure)
                total_expected_revenue += Decimal("395.00")

        # Act
        revenue_report = ResaleDisclosureGenerator.generate_revenue_report(
            property=property_data,
            year=2025,
            disclosures=disclosures
        )

        # Assert
        assert revenue_report['total_packages'] == 60
        assert revenue_report['total_revenue'] == total_expected_revenue
        assert revenue_report['average_fee'] == Decimal("395.00")
        assert revenue_report['monthly_average'] == total_expected_revenue / 12

        # Annual projection: $30K-72K range
        assert revenue_report['annual_projection'] >= Decimal("30000.00")
        assert revenue_report['annual_projection'] <= Decimal("72000.00")

    def test_disclosure_multi_state_compliance(self):
        """Test compliance with multiple state requirements"""
        # Arrange
        states = ['CA', 'TX', 'FL', 'AZ', 'NV', 'CO']
        property_data = PropertyGenerator.create_property("MultiState HOA", 200)

        for state in states:
            seller = MemberGenerator.create_member(
                property_data,
                unit_number=f"{state}01"
            )

            # Act
            disclosure = ResaleDisclosureGenerator.create_disclosure(
                property=property_data,
                seller=seller,
                buyer={'name': f'{state} Buyer', 'email': f'{state.lower()}@test.com'},
                unit_number=seller.unit_number,
                state=state
            )

            pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)

            # Assert
            compliance_check = StateComplianceValidator.validate_disclosure(
                pdf_content=pdf_bytes,
                state=state
            )

            assert compliance_check['is_compliant'] is True
            assert len(compliance_check['missing_sections']) == 0
            assert compliance_check['state'] == state

            # Verify state-specific requirements
            if state == 'CA':
                assert compliance_check['has_civil_code_reference'] is True
            elif state == 'TX':
                assert compliance_check['has_property_code_reference'] is True
            elif state == 'FL':
                assert compliance_check['has_statute_reference'] is True

    def test_disclosure_document_attachments(self):
        """Test attaching governing documents to disclosure"""
        # Arrange
        property_data = PropertyGenerator.create_property("Docs HOA", 95)
        seller = MemberGenerator.create_member(property_data, unit_number="705")

        # Create mock governing documents
        documents = [
            {
                'name': 'CC&Rs',
                'url': 'https://s3.amazonaws.com/docs/ccrs.pdf',
                'size': 2500000,  # 2.5MB
                'pages': 45
            },
            {
                'name': 'Bylaws',
                'url': 'https://s3.amazonaws.com/docs/bylaws.pdf',
                'size': 1200000,  # 1.2MB
                'pages': 20
            },
            {
                'name': 'Rules and Regulations',
                'url': 'https://s3.amazonaws.com/docs/rules.pdf',
                'size': 800000,  # 800KB
                'pages': 15
            },
            {
                'name': 'Budget 2025',
                'url': 'https://s3.amazonaws.com/docs/budget2025.pdf',
                'size': 500000,  # 500KB
                'pages': 8
            }
        ]

        # Act
        disclosure = ResaleDisclosureGenerator.create_disclosure_with_documents(
            property=property_data,
            seller=seller,
            buyer={'name': 'Doc Buyer', 'email': 'docs@buyer.com'},
            unit_number="705",
            attached_documents=documents
        )

        pdf_bytes = ResaleDisclosureGenerator.generate_pdf(disclosure)

        # Assert
        assert disclosure.attached_document_count == 4
        assert disclosure.total_document_size == 5000000  # 5MB total

        # Verify document references in PDF
        for doc in documents:
            assert PDFValidator.contains_text(pdf_bytes, doc['name'])
            assert PDFValidator.contains_url(pdf_bytes, doc['url'])

    def test_disclosure_status_workflow(self):
        """Test disclosure status transitions"""
        # Arrange
        property_data = PropertyGenerator.create_property("Status HOA", 80)
        seller = MemberGenerator.create_member(property_data, unit_number="805")

        disclosure = ResaleDisclosureGenerator.create_disclosure(
            property=property_data,
            seller=seller,
            buyer={'name': 'Status Buyer', 'email': 'status@test.com'},
            unit_number="805"
        )

        # Test status transitions
        assert disclosure.status == ResaleDisclosureStatus.DRAFT

        # Draft -> Generated
        disclosure.generate_pdf()
        assert disclosure.status == ResaleDisclosureStatus.GENERATED
        assert disclosure.generated_at is not None

        # Generated -> Delivered
        disclosure.deliver_to_buyer()
        assert disclosure.status == ResaleDisclosureStatus.DELIVERED
        assert disclosure.delivered_at is not None

        # Delivered -> Billed
        disclosure.create_invoice()
        assert disclosure.status == ResaleDisclosureStatus.BILLED
        assert disclosure.invoice_number is not None

        # Test invalid transitions
        with pytest.raises(ValueError, match="Cannot deliver draft disclosure"):
            draft_disclosure = ResaleDisclosureGenerator.create_disclosure(
                property=property_data,
                seller=seller,
                buyer={'name': 'Test', 'email': 'test@test.com'},
                unit_number="999"
            )
            draft_disclosure.deliver_to_buyer()

    def test_disclosure_error_handling(self):
        """Test error handling in disclosure generation"""
        # Test missing required data
        with pytest.raises(ValueError, match="Seller is required"):
            ResaleDisclosureGenerator.create_disclosure(
                property=PropertyGenerator.create_property("Test", 10),
                seller=None,
                buyer={'name': 'Test', 'email': 'test@test.com'},
                unit_number="101"
            )

        # Test invalid state code
        with pytest.raises(ValueError, match="Invalid state code"):
            ResaleDisclosureGenerator.create_disclosure(
                property=PropertyGenerator.create_property("Test", 10),
                seller=MemberGenerator.create_member(None, "101"),
                buyer={'name': 'Test', 'email': 'test@test.com'},
                unit_number="101",
                state="ZZ"  # Invalid state
            )

        # Test missing buyer information
        with pytest.raises(ValueError, match="Buyer email is required"):
            ResaleDisclosureGenerator.create_disclosure(
                property=PropertyGenerator.create_property("Test", 10),
                seller=MemberGenerator.create_member(None, "101"),
                buyer={'name': 'Test'},  # Missing email
                unit_number="101"
            )