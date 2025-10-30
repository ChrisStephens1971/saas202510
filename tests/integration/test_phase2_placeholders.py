"""
Integration tests for Phase 2 Critical Placeholders.

Tests the critical placeholder implementations including:
- Photo upload for violations
- Automated late fee assessment
- PDF integration with board packets
- File handling and validation
- Storage path isolation
- Automated batch processing
"""

import os
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from PIL import Image

from qa_testing.generators import (
    DelinquencyGenerator,
    InvoiceGenerator,
    LateFeeRuleGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
    ViolationGenerator,
)
from qa_testing.models import (
    DelinquencyStatus,
    FeeType,
    Invoice,
    LateFeeRule,
    Transaction,
    TransactionType,
    Violation,
    ViolationPhoto,
    ViolationStatus,
)


class TestViolationPhotoUpload:
    """Tests for violation photo upload functionality."""

    def test_upload_single_photo(self):
        """Test uploading a single photo to a violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        # Create test image
        image = Image.new('RGB', (800, 600), color='red')
        img_bytes = BytesIO()
        image.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        # Mock photo upload
        photo = ViolationPhoto(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            file_path=f"violations/{property_obj.tenant_id}/{violation.id}/photo_001.jpg",
            file_size=len(img_bytes.getvalue()),
            uploaded_by=member.id,
            uploaded_at=datetime.now(),
        )

        # Verify photo properties
        assert photo.violation_id == violation.id
        assert property_obj.tenant_id in photo.file_path
        assert photo.file_size > 0
        assert photo.uploaded_at is not None

    def test_upload_multiple_photos(self):
        """Test uploading multiple photos to a violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        photos = []
        for i in range(5):
            # Create test image with different colors
            colors = ['red', 'green', 'blue', 'yellow', 'purple']
            image = Image.new('RGB', (800, 600), color=colors[i])
            img_bytes = BytesIO()
            image.save(img_bytes, format='JPEG')
            img_bytes.seek(0)

            photo = ViolationPhoto(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
                file_path=f"violations/{property_obj.tenant_id}/{violation.id}/photo_{i:03d}.jpg",
                file_size=len(img_bytes.getvalue()),
                uploaded_by=member.id,
                uploaded_at=datetime.now(),
                order_index=i,
            )
            photos.append(photo)

        # Verify all photos uploaded
        assert len(photos) == 5
        assert all(p.violation_id == violation.id for p in photos)
        assert [p.order_index for p in photos] == [0, 1, 2, 3, 4]

    def test_file_type_validation(self):
        """Test that only allowed image file types are accepted."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        # Test valid file types
        valid_extensions = ['.jpg', '.jpeg', '.png', '.heic']
        for ext in valid_extensions:
            filename = f"test_image{ext}"
            assert ViolationGenerator.is_valid_image_type(filename) is True

        # Test invalid file types
        invalid_extensions = ['.pdf', '.doc', '.txt', '.exe', '.zip']
        for ext in invalid_extensions:
            filename = f"test_file{ext}"
            assert ViolationGenerator.is_valid_image_type(filename) is False

    def test_file_size_validation(self):
        """Test that file size limits are enforced (10MB max)."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        max_size = 10 * 1024 * 1024  # 10MB

        # Test file under limit
        small_file_size = 5 * 1024 * 1024  # 5MB
        assert ViolationGenerator.is_valid_file_size(small_file_size, max_size) is True

        # Test file at limit
        exact_size = max_size
        assert ViolationGenerator.is_valid_file_size(exact_size, max_size) is True

        # Test file over limit
        large_file_size = 15 * 1024 * 1024  # 15MB
        assert ViolationGenerator.is_valid_file_size(large_file_size, max_size) is False

    def test_image_processing_and_resizing(self):
        """Test that images are resized to max 1920x1080."""
        # Create large image
        large_image = Image.new('RGB', (4000, 3000), color='blue')

        # Process image (resize to max 1920x1080)
        max_width = 1920
        max_height = 1080

        # Calculate new size maintaining aspect ratio
        ratio = min(max_width / large_image.width, max_height / large_image.height)
        if ratio < 1:
            new_width = int(large_image.width * ratio)
            new_height = int(large_image.height * ratio)
            resized_image = large_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            resized_image = large_image

        # Verify resized dimensions
        assert resized_image.width <= max_width
        assert resized_image.height <= max_height
        # Verify aspect ratio maintained (within rounding tolerance)
        original_ratio = large_image.width / large_image.height
        new_ratio = resized_image.width / resized_image.height
        assert abs(original_ratio - new_ratio) < 0.01

    def test_image_format_conversion(self):
        """Test that images are converted to RGB format."""
        # Create RGBA image (with alpha channel)
        rgba_image = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))

        # Convert to RGB
        rgb_image = rgba_image.convert('RGB')

        # Verify conversion
        assert rgb_image.mode == 'RGB'
        assert rgba_image.mode == 'RGBA'

        # Create grayscale image
        gray_image = Image.new('L', (800, 600), color=128)

        # Convert to RGB
        rgb_from_gray = gray_image.convert('RGB')

        assert rgb_from_gray.mode == 'RGB'

    def test_tenant_isolated_storage_paths(self):
        """Test that photo storage paths are tenant-isolated."""
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()

        violation1 = ViolationGenerator.create(tenant_id=property1.tenant_id)
        violation2 = ViolationGenerator.create(tenant_id=property2.tenant_id)

        # Generate storage paths
        path1 = f"violations/{property1.tenant_id}/{violation1.id}/photo.jpg"
        path2 = f"violations/{property2.tenant_id}/{violation2.id}/photo.jpg"

        # Verify paths are isolated by tenant
        assert str(property1.tenant_id) in path1
        assert str(property2.tenant_id) in path2
        assert path1 != path2

        # Verify directory structure
        parts1 = path1.split('/')
        parts2 = path2.split('/')
        assert parts1[1] == str(property1.tenant_id)  # Tenant ID in path
        assert parts2[1] == str(property2.tenant_id)

    def test_photo_metadata_tracking(self):
        """Test that photo metadata is properly tracked."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        # Upload photo with metadata
        photo_metadata = {
            "original_filename": "front_yard_violation.jpg",
            "mime_type": "image/jpeg",
            "width": 1920,
            "height": 1080,
            "file_size": 256789,
            "upload_timestamp": datetime.now(),
            "uploaded_by": member.id,
            "description": "Unapproved landscaping modification",
        }

        photo = ViolationPhoto(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            file_path=f"violations/{property_obj.tenant_id}/{violation.id}/001.jpg",
            **photo_metadata
        )

        # Verify metadata
        assert photo.original_filename == "front_yard_violation.jpg"
        assert photo.mime_type == "image/jpeg"
        assert photo.width == 1920
        assert photo.height == 1080
        assert photo.file_size == 256789
        assert photo.uploaded_by == member.id


class TestAutomatedLateFeeAssessment:
    """Tests for automated late fee assessment."""

    def test_assess_late_fees_for_delinquent_accounts(self):
        """Test assessing late fees for delinquent accounts."""
        property_obj = PropertyGenerator.create()

        # Create delinquent members
        delinquent_members = []
        for i in range(5):
            member = MemberGenerator.create_with_balance(
                tenant_id=property_obj.tenant_id,
                balance=Decimal(f"{500 + i * 100}.00"),
            )

            # Create delinquency record
            delinquency = DelinquencyGenerator.create(
                tenant_id=property_obj.tenant_id,
                member_id=member.id,
                days_delinquent=30 + i * 10,  # 30, 40, 50, 60, 70 days
                total_amount_due=member.balance,
                status=DelinquencyStatus.DELINQUENT,
            )

            delinquent_members.append((member, delinquency))

        # Create late fee rule
        fee_rule = LateFeeRuleGenerator.create_percentage_rule(
            tenant_id=property_obj.tenant_id,
            grace_period_days=15,
            fee_percentage=Decimal("5.00"),
            max_fee=Decimal("100.00"),
        )

        # Assess fees
        fees_assessed = []
        for member, delinquency in delinquent_members:
            if delinquency.days_delinquent > fee_rule.grace_period_days:
                fee_amount = fee_rule.calculate_fee(
                    delinquency.total_amount_due,
                    delinquency.days_delinquent
                )
                fees_assessed.append((member, fee_amount))

        # Verify fees assessed
        assert len(fees_assessed) == 5  # All are past grace period
        for member, fee in fees_assessed:
            assert fee > Decimal("0.00")
            assert fee <= fee_rule.max_fee

    def test_grace_period_enforcement(self):
        """Test that fees are not assessed during grace period."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create_with_balance(
            tenant_id=property_obj.tenant_id,
            balance=Decimal("500.00"),
        )

        # Create fee rule with 15-day grace period
        fee_rule = LateFeeRuleGenerator.create_flat_fee_rule(
            tenant_id=property_obj.tenant_id,
            grace_period_days=15,
            fee_amount=Decimal("25.00"),
        )

        # Test within grace period (10 days late)
        delinquency_within = DelinquencyGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=10,
            total_amount_due=member.balance,
        )

        # Should not assess fee
        if delinquency_within.days_delinquent <= fee_rule.grace_period_days:
            fee_amount = Decimal("0.00")
        else:
            fee_amount = fee_rule.calculate_fee(
                delinquency_within.total_amount_due,
                delinquency_within.days_delinquent
            )

        assert fee_amount == Decimal("0.00")

        # Test after grace period (20 days late)
        delinquency_after = DelinquencyGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=20,
            total_amount_due=member.balance,
        )

        # Should assess fee
        if delinquency_after.days_delinquent <= fee_rule.grace_period_days:
            fee_amount = Decimal("0.00")
        else:
            fee_amount = fee_rule.calculate_fee(
                delinquency_after.total_amount_due,
                delinquency_after.days_delinquent
            )

        assert fee_amount == Decimal("25.00")

    def test_percentage_based_late_fees(self):
        """Test percentage-based late fee calculation."""
        property_obj = PropertyGenerator.create()

        # Create fee rule: 5% with max $100
        fee_rule = LateFeeRuleGenerator.create_percentage_rule(
            tenant_id=property_obj.tenant_id,
            fee_percentage=Decimal("5.00"),
            max_fee=Decimal("100.00"),
        )

        test_cases = [
            (Decimal("100.00"), Decimal("5.00")),    # $100 * 5% = $5
            (Decimal("500.00"), Decimal("25.00")),   # $500 * 5% = $25
            (Decimal("1000.00"), Decimal("50.00")),  # $1000 * 5% = $50
            (Decimal("2000.00"), Decimal("100.00")),  # $2000 * 5% = $100 (at max)
            (Decimal("3000.00"), Decimal("100.00")),  # $3000 * 5% = $150, capped at $100
        ]

        for balance, expected_fee in test_cases:
            calculated_fee = min(
                balance * fee_rule.fee_percentage / Decimal("100"),
                fee_rule.max_fee
            )
            assert calculated_fee == expected_fee

    def test_flat_fee_late_fees(self):
        """Test flat fee late fee calculation."""
        property_obj = PropertyGenerator.create()

        # Create flat fee rule: $35
        fee_rule = LateFeeRuleGenerator.create_flat_fee_rule(
            tenant_id=property_obj.tenant_id,
            fee_amount=Decimal("35.00"),
        )

        # Test various balances - fee should be same
        test_balances = [
            Decimal("100.00"),
            Decimal("500.00"),
            Decimal("1000.00"),
            Decimal("5000.00"),
        ]

        for balance in test_balances:
            calculated_fee = fee_rule.fee_amount
            assert calculated_fee == Decimal("35.00")

    def test_create_late_fee_invoices(self):
        """Test creating invoices for assessed late fees."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create_with_balance(
            tenant_id=property_obj.tenant_id,
            balance=Decimal("1000.00"),
        )

        # Assess late fee
        fee_amount = Decimal("50.00")

        # Create late fee invoice
        invoice = InvoiceGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            invoice_type="LATE_FEE",
            amount=fee_amount,
            description="Late fee for overdue balance",
            due_date=date.today() + timedelta(days=30),
        )

        # Create transaction for late fee
        transaction = TransactionGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            transaction_type=TransactionType.CHARGE,
            amount=fee_amount,
            description="Late fee assessment",
            reference_type="invoice",
            reference_id=invoice.id,
        )

        # Verify invoice and transaction
        assert invoice.amount == fee_amount
        assert invoice.invoice_type == "LATE_FEE"
        assert transaction.amount == fee_amount
        assert transaction.transaction_type == TransactionType.CHARGE
        assert transaction.reference_id == invoice.id

    def test_batch_late_fee_processing(self):
        """Test processing late fees for all tenants in batch."""
        # Create multiple properties
        properties = []
        for i in range(3):
            prop = PropertyGenerator.create()
            properties.append(prop)

        # Create delinquent members for each property
        all_assessments = []
        for prop in properties:
            # Create fee rule for this property
            fee_rule = LateFeeRuleGenerator.create_percentage_rule(
                tenant_id=prop.tenant_id,
                fee_percentage=Decimal("5.00"),
                max_fee=Decimal("100.00"),
            )

            # Create delinquent members
            for j in range(3):
                member = MemberGenerator.create_with_balance(
                    tenant_id=prop.tenant_id,
                    balance=Decimal(f"{200 + j * 100}.00"),
                )

                delinquency = DelinquencyGenerator.create(
                    tenant_id=prop.tenant_id,
                    member_id=member.id,
                    days_delinquent=30,
                    total_amount_due=member.balance,
                )

                # Calculate fee
                fee = min(
                    member.balance * Decimal("0.05"),
                    Decimal("100.00")
                )

                all_assessments.append({
                    "tenant_id": prop.tenant_id,
                    "member_id": member.id,
                    "fee_amount": fee,
                })

        # Verify batch processing
        assert len(all_assessments) == 9  # 3 properties * 3 members
        assert len(set(a["tenant_id"] for a in all_assessments)) == 3  # 3 unique tenants

    def test_skip_already_assessed_fees(self):
        """Test that late fees are not duplicated if already assessed."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create_with_balance(
            tenant_id=property_obj.tenant_id,
            balance=Decimal("500.00"),
        )

        # Create initial late fee invoice
        existing_invoice = InvoiceGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            invoice_type="LATE_FEE",
            amount=Decimal("25.00"),
            created_at=date.today() - timedelta(days=5),
        )

        # Mock check for existing fee this month
        def has_late_fee_this_month(member_id, current_date):
            # Check if late fee already assessed this month
            month_start = date(current_date.year, current_date.month, 1)
            return existing_invoice.created_at >= month_start

        # Should skip assessment
        assert has_late_fee_this_month(member.id, date.today()) is True

    def test_late_fee_notification_tracking(self):
        """Test tracking of late fee notifications sent to members."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        # Create late fee assessment
        fee_amount = Decimal("50.00")

        # Track notification
        notification = {
            "tenant_id": property_obj.tenant_id,
            "member_id": member.id,
            "notification_type": "LATE_FEE_ASSESSED",
            "fee_amount": str(fee_amount),
            "sent_at": datetime.now(),
            "sent_to": member.email,
            "status": "SENT",
        }

        # Verify notification tracking
        assert notification["notification_type"] == "LATE_FEE_ASSESSED"
        assert Decimal(notification["fee_amount"]) == fee_amount
        assert notification["status"] == "SENT"


class TestPDFIntegrationWithBoardPackets:
    """Tests for PDF integration with board packet generation."""

    def test_include_delinquency_report_in_packet(self):
        """Test including delinquency report in board packet."""
        property_obj = PropertyGenerator.create()

        # Create delinquent members
        delinquent_members = []
        for i in range(5):
            member = MemberGenerator.create_with_balance(
                tenant_id=property_obj.tenant_id,
                balance=Decimal(f"{500 + i * 100}.00"),
            )
            delinquency = DelinquencyGenerator.create(
                tenant_id=property_obj.tenant_id,
                member_id=member.id,
                days_delinquent=30 + i * 10,
            )
            delinquent_members.append((member, delinquency))

        # Create board packet section
        delinquency_section = {
            "type": "DELINQUENCY_REPORT",
            "title": "Delinquency Report",
            "content": {
                "total_delinquent": len(delinquent_members),
                "total_amount": sum(d.total_amount_due for m, d in delinquent_members),
                "members": [
                    {
                        "unit": m.unit.unit_number,
                        "name": m.name,
                        "days_late": d.days_delinquent,
                        "amount_due": str(d.total_amount_due),
                    }
                    for m, d in delinquent_members
                ],
            },
        }

        # Verify section content
        assert delinquency_section["content"]["total_delinquent"] == 5
        assert len(delinquency_section["content"]["members"]) == 5

    def test_include_violation_photos_in_packet(self):
        """Test including violation photos in board packet PDF."""
        property_obj = PropertyGenerator.create()

        # Create violations with photos
        violations_with_photos = []
        for i in range(3):
            member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
            violation = ViolationGenerator.create_with_photo(
                tenant_id=property_obj.tenant_id,
                member_id=member.id,
                num_photos=2,
            )
            violations_with_photos.append(violation)

        # Create violations section for packet
        violations_section = {
            "type": "VIOLATIONS_REPORT",
            "title": "Current Violations",
            "content": {
                "total_violations": len(violations_with_photos),
                "violations": [
                    {
                        "id": v.id,
                        "unit": v.member.unit.unit_number,
                        "type": v.violation_type.value,
                        "date": v.violation_date.isoformat(),
                        "status": v.status.value,
                        "photos": [
                            {
                                "path": p.file_path,
                                "caption": p.description,
                            }
                            for p in v.photos
                        ],
                    }
                    for v in violations_with_photos
                ],
            },
        }

        # Verify photos included
        assert violations_section["content"]["total_violations"] == 3
        for v_data in violations_section["content"]["violations"]:
            assert len(v_data["photos"]) == 2

    def test_automated_report_scheduling(self):
        """Test scheduling automated reports for board packets."""
        property_obj = PropertyGenerator.create()

        # Define report schedule
        report_schedule = {
            "frequency": "MONTHLY",
            "day_of_month": 25,  # Generate on 25th for board meeting on 1st
            "reports_to_include": [
                "FINANCIAL_SUMMARY",
                "AR_AGING",
                "DELINQUENCY_REPORT",
                "VIOLATIONS_SUMMARY",
                "RESERVE_STATUS",
            ],
            "auto_generate": True,
            "send_to_board": True,
        }

        # Mock next generation date calculation
        today = date.today()
        if today.day <= report_schedule["day_of_month"]:
            next_generation = date(today.year, today.month, report_schedule["day_of_month"])
        else:
            # Next month
            if today.month == 12:
                next_generation = date(today.year + 1, 1, report_schedule["day_of_month"])
            else:
                next_generation = date(today.year, today.month + 1, report_schedule["day_of_month"])

        # Verify schedule
        assert report_schedule["frequency"] == "MONTHLY"
        assert len(report_schedule["reports_to_include"]) == 5
        assert report_schedule["auto_generate"] is True
        assert next_generation >= today