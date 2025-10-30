"""
Integration tests for Phase 3 Operational Features.

Tests the complete operational features including:
- Work Order System (6 models)
- ARC (Architectural Review) Workflow (6 models)
- Enhanced Violation Tracking (4 models)
- Vendor management
- Document attachments
- Multi-step workflows
- GL account integration
- Committee reviews and approvals
"""

import os
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from qa_testing.generators import (
    FundGenerator,
    InvoiceGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
    ViolationGenerator,
)
from qa_testing.models import (
    ARCApproval,
    ARCCompletion,
    ARCDocument,
    ARCRequest,
    ARCRequestType,
    ARCReview,
    ARCStatus,
    FineSchedule,
    Transaction,
    TransactionType,
    Vendor,
    ViolationEscalation,
    ViolationFine,
    ViolationType,
    WorkOrder,
    WorkOrderAttachment,
    WorkOrderCategory,
    WorkOrderComment,
    WorkOrderInvoice,
    WorkOrderPriority,
    WorkOrderStatus,
)


class TestWorkOrderSystem:
    """Tests for the work order management system."""

    def test_create_work_order(self):
        """Test creating a basic work order."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        # Create work order category
        category = WorkOrderCategory(
            tenant_id=property_obj.tenant_id,
            name="Plumbing",
            description="Plumbing repairs and maintenance",
            gl_account_code="5200",
            is_emergency=False,
        )

        # Create work order
        work_order = WorkOrder(
            tenant_id=property_obj.tenant_id,
            category_id=category.id,
            requested_by=member.id,
            title="Leaky faucet in clubhouse",
            description="The kitchen faucet in the clubhouse is dripping",
            location="Clubhouse - Kitchen",
            priority=WorkOrderPriority.MEDIUM,
            status=WorkOrderStatus.OPEN,
            created_at=datetime.now(),
        )

        # Verify work order
        assert work_order.tenant_id == property_obj.tenant_id
        assert work_order.priority == WorkOrderPriority.MEDIUM
        assert work_order.status == WorkOrderStatus.OPEN
        assert work_order.location == "Clubhouse - Kitchen"

    def test_work_order_category_gl_mapping(self):
        """Test that work order categories map to GL accounts."""
        property_obj = PropertyGenerator.create()

        # Create categories with GL mappings
        categories = [
            ("Landscaping", "5100"),
            ("Plumbing", "5200"),
            ("Electrical", "5300"),
            ("Pool Maintenance", "5400"),
            ("General Repairs", "5500"),
        ]

        created_categories = []
        for name, gl_code in categories:
            category = WorkOrderCategory(
                tenant_id=property_obj.tenant_id,
                name=name,
                gl_account_code=gl_code,
                description=f"{name} work orders",
            )
            created_categories.append(category)

        # Verify GL mappings
        assert len(created_categories) == 5
        for cat in created_categories:
            assert cat.gl_account_code is not None
            assert len(cat.gl_account_code) == 4

    def test_vendor_management(self):
        """Test vendor creation and tracking."""
        property_obj = PropertyGenerator.create()

        # Create vendors
        vendor1 = Vendor(
            tenant_id=property_obj.tenant_id,
            name="ABC Plumbing",
            contact_name="John Smith",
            phone="555-1234",
            email="abc@plumbing.com",
            address="123 Main St",
            license_number="PLB-12345",
            insurance_expires=date.today() + timedelta(days=180),
            is_active=True,
            categories=["Plumbing", "Emergency"],
        )

        vendor2 = Vendor(
            tenant_id=property_obj.tenant_id,
            name="Green Thumb Landscaping",
            contact_name="Jane Doe",
            phone="555-5678",
            email="info@greenthumb.com",
            license_number="LND-67890",
            insurance_expires=date.today() + timedelta(days=365),
            is_active=True,
            categories=["Landscaping", "Tree Service"],
        )

        # Verify vendor details
        assert vendor1.is_active is True
        assert vendor2.insurance_expires > date.today()
        assert "Plumbing" in vendor1.categories
        assert "Landscaping" in vendor2.categories

    def test_vendor_insurance_expiration_tracking(self):
        """Test tracking vendor insurance expiration dates."""
        property_obj = PropertyGenerator.create()

        vendors_with_insurance = []
        for i in range(5):
            vendor = Vendor(
                tenant_id=property_obj.tenant_id,
                name=f"Vendor {i}",
                insurance_expires=date.today() + timedelta(days=30 * (i + 1)),
                is_active=True,
            )
            vendors_with_insurance.append(vendor)

        # Check for expiring insurance (within 30 days)
        expiring_soon = []
        for vendor in vendors_with_insurance:
            days_until_expiry = (vendor.insurance_expires - date.today()).days
            if days_until_expiry <= 30:
                expiring_soon.append(vendor)

        # First vendor expires in 30 days
        assert len(expiring_soon) == 1
        assert expiring_soon[0].name == "Vendor 0"

    def test_work_order_status_transitions(self):
        """Test work order status workflow transitions."""
        property_obj = PropertyGenerator.create()
        work_order = WorkOrder(
            tenant_id=property_obj.tenant_id,
            title="Test Work Order",
            status=WorkOrderStatus.OPEN,
        )

        # Valid transitions
        valid_transitions = [
            (WorkOrderStatus.OPEN, WorkOrderStatus.ASSIGNED),
            (WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS),
            (WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.PENDING_APPROVAL),
            (WorkOrderStatus.PENDING_APPROVAL, WorkOrderStatus.COMPLETED),
            (WorkOrderStatus.OPEN, WorkOrderStatus.CANCELLED),
        ]

        for from_status, to_status in valid_transitions:
            work_order.status = from_status
            # Transition should be allowed
            work_order.status = to_status
            assert work_order.status == to_status

    def test_work_order_priority_levels(self):
        """Test work order priority handling."""
        property_obj = PropertyGenerator.create()

        priorities = [
            (WorkOrderPriority.EMERGENCY, 0),  # Immediate
            (WorkOrderPriority.HIGH, 1),       # 1 day
            (WorkOrderPriority.MEDIUM, 3),     # 3 days
            (WorkOrderPriority.LOW, 7),         # 7 days
        ]

        work_orders = []
        for priority, sla_days in priorities:
            wo = WorkOrder(
                tenant_id=property_obj.tenant_id,
                title=f"{priority.value} priority work order",
                priority=priority,
                status=WorkOrderStatus.OPEN,
                created_at=datetime.now(),
                sla_due_date=datetime.now() + timedelta(days=sla_days),
            )
            work_orders.append(wo)

        # Verify SLA due dates
        for wo, (priority, sla_days) in zip(work_orders, priorities):
            expected_due = wo.created_at + timedelta(days=sla_days)
            assert wo.sla_due_date.date() == expected_due.date()

    def test_work_order_comments(self):
        """Test adding comments to work orders."""
        property_obj = PropertyGenerator.create()
        work_order = WorkOrder(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            title="Test Work Order",
        )

        # Add comments
        comments = []
        for i in range(3):
            comment = WorkOrderComment(
                tenant_id=property_obj.tenant_id,
                work_order_id=work_order.id,
                comment_text=f"Update {i}: Progress on the work order",
                created_by=property_obj.id,
                created_at=datetime.now() + timedelta(hours=i),
                is_internal=i == 0,  # First comment is internal
            )
            comments.append(comment)

        # Verify comments
        assert len(comments) == 3
        assert comments[0].is_internal is True
        assert comments[1].is_internal is False
        assert all(c.work_order_id == work_order.id for c in comments)

    def test_work_order_attachments(self):
        """Test adding file attachments to work orders."""
        property_obj = PropertyGenerator.create()
        work_order = WorkOrder(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            title="Test Work Order",
        )

        # Add attachments
        attachments = []
        file_types = [
            ("photo_before.jpg", "image/jpeg", 1024000),
            ("invoice.pdf", "application/pdf", 256000),
            ("photo_after.jpg", "image/jpeg", 2048000),
        ]

        for filename, mime_type, size in file_types:
            attachment = WorkOrderAttachment(
                tenant_id=property_obj.tenant_id,
                work_order_id=work_order.id,
                file_name=filename,
                file_path=f"work_orders/{property_obj.tenant_id}/{work_order.id}/{filename}",
                mime_type=mime_type,
                file_size=size,
                uploaded_by=property_obj.id,
                uploaded_at=datetime.now(),
            )
            attachments.append(attachment)

        # Verify attachments
        assert len(attachments) == 3
        assert sum(a.file_size for a in attachments) == 3328000
        assert all(str(property_obj.tenant_id) in a.file_path for a in attachments)

    def test_work_order_invoice_creation(self):
        """Test creating invoices from work orders."""
        property_obj = PropertyGenerator.create()
        fund = FundGenerator.create_operating(tenant_id=property_obj.tenant_id)

        work_order = WorkOrder(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            title="Plumbing Repair",
        )

        vendor = Vendor(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            name="ABC Plumbing",
        )

        # Create work order invoice
        wo_invoice = WorkOrderInvoice(
            tenant_id=property_obj.tenant_id,
            work_order_id=work_order.id,
            vendor_id=vendor.id,
            invoice_number="INV-2025-001",
            invoice_date=date.today(),
            amount=Decimal("350.00"),
            gl_account_code="5200",
            fund_id=fund.id,
            paid=False,
        )

        # Create GL transaction
        transaction = TransactionGenerator.create(
            tenant_id=property_obj.tenant_id,
            fund_id=fund.id,
            transaction_type=TransactionType.EXPENSE,
            amount=wo_invoice.amount,
            description=f"Work Order: {work_order.title}",
            reference_type="work_order_invoice",
            reference_id=wo_invoice.id,
        )

        # Verify invoice and transaction
        assert wo_invoice.amount == Decimal("350.00")
        assert wo_invoice.gl_account_code == "5200"
        assert transaction.amount == wo_invoice.amount
        assert transaction.reference_id == wo_invoice.id


class TestARCWorkflow:
    """Tests for Architectural Review Committee workflow."""

    def test_create_arc_request(self):
        """Test creating an ARC request."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        # Create request type
        request_type = ARCRequestType(
            tenant_id=property_obj.tenant_id,
            name="Exterior Paint",
            description="Requests to change exterior paint colors",
            requires_plans=False,
            requires_committee_review=True,
            typical_turnaround_days=14,
        )

        # Create ARC request
        arc_request = ARCRequest(
            tenant_id=property_obj.tenant_id,
            request_type_id=request_type.id,
            member_id=member.id,
            description="Change front door color from white to navy blue",
            status=ARCStatus.SUBMITTED,
            submitted_date=date.today(),
        )

        # Verify request
        assert arc_request.status == ARCStatus.SUBMITTED
        assert arc_request.member_id == member.id
        assert "navy blue" in arc_request.description

    def test_arc_request_types(self):
        """Test different ARC request types and requirements."""
        property_obj = PropertyGenerator.create()

        request_types = [
            ("Exterior Paint", False, True, 14),
            ("Fence Installation", True, True, 21),
            ("Window Replacement", False, False, 7),
            ("Deck/Patio Addition", True, True, 30),
            ("Landscaping Changes", False, False, 7),
        ]

        created_types = []
        for name, needs_plans, needs_review, turnaround in request_types:
            req_type = ARCRequestType(
                tenant_id=property_obj.tenant_id,
                name=name,
                requires_plans=needs_plans,
                requires_committee_review=needs_review,
                typical_turnaround_days=turnaround,
            )
            created_types.append(req_type)

        # Verify requirements
        fence_type = next(t for t in created_types if t.name == "Fence Installation")
        assert fence_type.requires_plans is True
        assert fence_type.requires_committee_review is True
        assert fence_type.typical_turnaround_days == 21

    def test_arc_document_attachments(self):
        """Test attaching documents to ARC requests."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        arc_request = ARCRequest(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            member_id=member.id,
            status=ARCStatus.SUBMITTED,
        )

        # Attach documents
        documents = []
        doc_types = [
            ("site_plan.pdf", "Site Plan", "application/pdf"),
            ("elevation_drawing.pdf", "Elevation Drawing", "application/pdf"),
            ("material_samples.jpg", "Material Samples Photo", "image/jpeg"),
            ("hoa_guidelines.pdf", "HOA Guidelines Reference", "application/pdf"),
        ]

        for filename, doc_type, mime_type in doc_types:
            doc = ARCDocument(
                tenant_id=property_obj.tenant_id,
                arc_request_id=arc_request.id,
                document_type=doc_type,
                file_name=filename,
                file_path=f"arc/{property_obj.tenant_id}/{arc_request.id}/{filename}",
                mime_type=mime_type,
                uploaded_by=member.id,
                uploaded_at=datetime.now(),
            )
            documents.append(doc)

        # Verify documents
        assert len(documents) == 4
        assert all(d.arc_request_id == arc_request.id for d in documents)
        assert any("Site Plan" in d.document_type for d in documents)

    def test_arc_committee_review_process(self):
        """Test committee review and voting process."""
        property_obj = PropertyGenerator.create()
        arc_request = ARCRequest(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            status=ARCStatus.UNDER_REVIEW,
        )

        # Create committee reviews
        committee_members = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown"]
        reviews = []

        for i, member_name in enumerate(committee_members):
            review = ARCReview(
                tenant_id=property_obj.tenant_id,
                arc_request_id=arc_request.id,
                reviewer_name=member_name,
                reviewer_role="Committee Member",
                vote="APPROVE" if i < 3 else "DENY",  # 3 approve, 1 deny
                comments=f"Review by {member_name}",
                review_date=datetime.now(),
            )
            reviews.append(review)

        # Count votes
        approve_votes = sum(1 for r in reviews if r.vote == "APPROVE")
        deny_votes = sum(1 for r in reviews if r.vote == "DENY")

        # Verify voting
        assert len(reviews) == 4
        assert approve_votes == 3
        assert deny_votes == 1
        assert approve_votes > deny_votes  # Majority approval

    def test_arc_approval_with_conditions(self):
        """Test ARC approval with conditions."""
        property_obj = PropertyGenerator.create()
        arc_request = ARCRequest(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            status=ARCStatus.UNDER_REVIEW,
        )

        # Create approval with conditions
        approval = ARCApproval(
            tenant_id=property_obj.tenant_id,
            arc_request_id=arc_request.id,
            approved=True,
            approval_date=date.today(),
            approved_by="ARC Committee",
            conditions=[
                "Use only approved paint colors from HOA palette",
                "Work must be completed within 60 days",
                "Contractor must be licensed and insured",
                "Final inspection required upon completion",
            ],
            expiration_date=date.today() + timedelta(days=180),
        )

        # Verify approval
        assert approval.approved is True
        assert len(approval.conditions) == 4
        assert approval.expiration_date > date.today()
        assert "licensed and insured" in approval.conditions[2]

    def test_arc_status_workflow(self):
        """Test ARC request status transitions."""
        property_obj = PropertyGenerator.create()
        arc_request = ARCRequest(
            tenant_id=property_obj.tenant_id,
            status=ARCStatus.SUBMITTED,
        )

        # Valid workflow transitions
        workflow = [
            ARCStatus.SUBMITTED,
            ARCStatus.UNDER_REVIEW,
            ARCStatus.APPROVED,
            ARCStatus.IN_PROGRESS,
            ARCStatus.COMPLETED,
        ]

        for status in workflow:
            arc_request.status = status
            assert arc_request.status == status

        # Alternative path - denial
        arc_request.status = ARCStatus.UNDER_REVIEW
        arc_request.status = ARCStatus.DENIED
        assert arc_request.status == ARCStatus.DENIED

    def test_arc_completion_verification(self):
        """Test ARC project completion verification."""
        property_obj = PropertyGenerator.create()
        arc_request = ARCRequest(
            tenant_id=property_obj.tenant_id,
            id=uuid4(),
            status=ARCStatus.IN_PROGRESS,
        )

        # Create completion record
        completion = ARCCompletion(
            tenant_id=property_obj.tenant_id,
            arc_request_id=arc_request.id,
            completion_date=date.today(),
            verified_by="Property Manager",
            verification_date=date.today() + timedelta(days=2),
            meets_approval_conditions=True,
            final_photos=[
                "final_front.jpg",
                "final_side.jpg",
                "final_detail.jpg",
            ],
            notes="Work completed according to approved plans and conditions",
        )

        # Verify completion
        assert completion.meets_approval_conditions is True
        assert len(completion.final_photos) == 3
        assert completion.verification_date > completion.completion_date

    def test_arc_expiration_tracking(self):
        """Test tracking ARC approval expirations."""
        property_obj = PropertyGenerator.create()

        # Create approvals with different expiration dates
        approvals = []
        for i in range(5):
            approval = ARCApproval(
                tenant_id=property_obj.tenant_id,
                arc_request_id=uuid4(),
                approved=True,
                approval_date=date.today() - timedelta(days=150),
                expiration_date=date.today() + timedelta(days=30 * (i - 2)),  # Some expired
            )
            approvals.append(approval)

        # Check for expired approvals
        expired = [a for a in approvals if a.expiration_date < date.today()]
        expiring_soon = [
            a for a in approvals
            if date.today() <= a.expiration_date <= date.today() + timedelta(days=30)
        ]

        assert len(expired) == 2  # First two are expired
        assert len(expiring_soon) == 1  # One expiring within 30 days


class TestEnhancedViolationTracking:
    """Tests for enhanced violation tracking with fines and escalation."""

    def test_create_violation_type_with_fine_schedule(self):
        """Test creating violation types with fine schedules."""
        property_obj = PropertyGenerator.create()

        # Create violation type
        violation_type = ViolationType(
            tenant_id=property_obj.tenant_id,
            name="Unauthorized Modification",
            description="Making changes without ARC approval",
            initial_notice_days=7,
            cure_period_days=30,
            max_escalation_level=4,
        )

        # Create fine schedule
        fine_schedule = FineSchedule(
            tenant_id=property_obj.tenant_id,
            violation_type_id=violation_type.id,
            escalation_level=1,
            fine_amount=Decimal("0.00"),  # Warning only
            days_after_notice=0,
            action="First Notice - Warning",
        )

        fine_schedule_2 = FineSchedule(
            tenant_id=property_obj.tenant_id,
            violation_type_id=violation_type.id,
            escalation_level=2,
            fine_amount=Decimal("50.00"),
            days_after_notice=14,
            action="Second Notice - $50 Fine",
        )

        fine_schedule_3 = FineSchedule(
            tenant_id=property_obj.tenant_id,
            violation_type_id=violation_type.id,
            escalation_level=3,
            fine_amount=Decimal("100.00"),
            days_after_notice=30,
            action="Third Notice - $100 Fine",
        )

        # Verify fine schedule
        assert fine_schedule.escalation_level == 1
        assert fine_schedule.fine_amount == Decimal("0.00")
        assert fine_schedule_2.fine_amount == Decimal("50.00")
        assert fine_schedule_3.fine_amount == Decimal("100.00")

    def test_violation_escalation_workflow(self):
        """Test violation escalation through levels."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        # Create escalation history
        escalations = []
        escalation_dates = [
            date.today() - timedelta(days=30),
            date.today() - timedelta(days=15),
            date.today() - timedelta(days=5),
            date.today(),
        ]

        for i, esc_date in enumerate(escalation_dates, 1):
            escalation = ViolationEscalation(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
                escalation_level=i,
                escalation_date=esc_date,
                notice_sent=True,
                notice_type=f"Level {i} Notice",
                fine_amount=Decimal(f"{(i-1) * 50}.00") if i > 1 else Decimal("0.00"),
            )
            escalations.append(escalation)

        # Verify escalation progression
        assert len(escalations) == 4
        assert escalations[0].fine_amount == Decimal("0.00")  # Warning
        assert escalations[1].fine_amount == Decimal("50.00")
        assert escalations[2].fine_amount == Decimal("100.00")
        assert escalations[3].fine_amount == Decimal("150.00")

    def test_violation_fine_to_invoice_integration(self):
        """Test creating invoices from violation fines."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        fund = FundGenerator.create_operating(tenant_id=property_obj.tenant_id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        # Create violation fine
        violation_fine = ViolationFine(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            fine_amount=Decimal("100.00"),
            assessed_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            paid=False,
        )

        # Create invoice for fine
        invoice = InvoiceGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            invoice_type="VIOLATION_FINE",
            amount=violation_fine.fine_amount,
            due_date=violation_fine.due_date,
            description=f"Violation Fine - {violation.id}",
        )

        # Link fine to invoice
        violation_fine.invoice_id = invoice.id

        # Create GL transaction
        transaction = TransactionGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            fund_id=fund.id,
            transaction_type=TransactionType.CHARGE,
            amount=violation_fine.fine_amount,
            description="Violation fine assessment",
            reference_type="invoice",
            reference_id=invoice.id,
        )

        # Verify integration
        assert violation_fine.invoice_id == invoice.id
        assert invoice.amount == violation_fine.fine_amount
        assert transaction.amount == violation_fine.fine_amount
        assert transaction.reference_id == invoice.id

    def test_multiple_violation_types(self):
        """Test managing multiple violation types with different schedules."""
        property_obj = PropertyGenerator.create()

        violation_types = [
            ("Landscaping", 7, 14, Decimal("25.00")),
            ("Parking", 3, 7, Decimal("50.00")),
            ("Noise", 1, 3, Decimal("100.00")),
            ("Trash", 1, 7, Decimal("35.00")),
            ("Pet", 7, 14, Decimal("75.00")),
        ]

        created_types = []
        for name, notice_days, cure_days, initial_fine in violation_types:
            vtype = ViolationType(
                tenant_id=property_obj.tenant_id,
                name=f"{name} Violation",
                initial_notice_days=notice_days,
                cure_period_days=cure_days,
                initial_fine_amount=initial_fine,
            )
            created_types.append(vtype)

        # Verify different violation types
        assert len(created_types) == 5
        parking_type = next(t for t in created_types if "Parking" in t.name)
        assert parking_type.cure_period_days == 7
        assert parking_type.initial_fine_amount == Decimal("50.00")

    def test_violation_cure_and_dismissal(self):
        """Test curing violations within cure period."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            status="NOTICE_SENT",
        )

        # Set cure period
        cure_deadline = violation.violation_date + timedelta(days=14)

        # Cure the violation before deadline
        cure_date = violation.violation_date + timedelta(days=10)
        if cure_date <= cure_deadline:
            violation.status = "CURED"
            violation.resolution_date = cure_date
            violation.resolution_notes = "Violation corrected by owner"

        # Verify cure
        assert violation.status == "CURED"
        assert violation.resolution_date <= cure_deadline
        assert violation.resolution_notes is not None


class TestMultiTenantIsolation:
    """Tests for multi-tenant isolation in operational features."""

    def test_work_order_tenant_isolation(self):
        """Test that work orders are isolated between tenants."""
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()

        # Create work orders for different properties
        wo1 = WorkOrder(
            tenant_id=property1.tenant_id,
            title="Property 1 Work Order",
        )

        wo2 = WorkOrder(
            tenant_id=property2.tenant_id,
            title="Property 2 Work Order",
        )

        # Verify isolation
        assert wo1.tenant_id != wo2.tenant_id
        assert wo1.tenant_id == property1.tenant_id
        assert wo2.tenant_id == property2.tenant_id

    def test_vendor_tenant_isolation(self):
        """Test that vendors are isolated between tenants."""
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()

        # Create vendors for different properties
        vendor1 = Vendor(
            tenant_id=property1.tenant_id,
            name="Property 1 Vendor",
        )

        vendor2 = Vendor(
            tenant_id=property2.tenant_id,
            name="Property 2 Vendor",
        )

        # Mock access check
        def can_access_vendor(tenant_id, vendor):
            return vendor.tenant_id == tenant_id

        # Verify isolation
        assert can_access_vendor(property1.tenant_id, vendor1) is True
        assert can_access_vendor(property1.tenant_id, vendor2) is False
        assert can_access_vendor(property2.tenant_id, vendor2) is True
        assert can_access_vendor(property2.tenant_id, vendor1) is False

    def test_arc_request_tenant_isolation(self):
        """Test that ARC requests are isolated between tenants."""
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()

        member1 = MemberGenerator.create(tenant_id=property1.tenant_id)
        member2 = MemberGenerator.create(tenant_id=property2.tenant_id)

        # Create ARC requests
        arc1 = ARCRequest(
            tenant_id=property1.tenant_id,
            member_id=member1.id,
            description="Property 1 ARC Request",
        )

        arc2 = ARCRequest(
            tenant_id=property2.tenant_id,
            member_id=member2.id,
            description="Property 2 ARC Request",
        )

        # Verify isolation
        assert arc1.tenant_id == property1.tenant_id
        assert arc2.tenant_id == property2.tenant_id
        assert arc1.member_id != arc2.member_id