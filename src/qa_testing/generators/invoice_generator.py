"""Invoice data generator for testing invoicing functionality."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import Invoice

fake = Faker()


class InvoiceGenerator:
    """
    Generator for creating Invoice test data.

    Usage:
        # Create a late fee invoice
        invoice = InvoiceGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            invoice_type="LATE_FEE",
            amount=Decimal("50.00"),
            description="Late fee for overdue balance",
            due_date=date.today() + timedelta(days=30),
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: UUID,
        member_id: UUID,
        invoice_type: str,
        amount: Decimal,
        description: str,
        due_date: date,
        invoice_date: Optional[date] = None,
        paid: bool = False,
        paid_date: Optional[date] = None,
        reference_id: Optional[UUID] = None,
    ) -> Invoice:
        """
        Create an Invoice.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_id: Member receiving the invoice
            invoice_type: Type of invoice (LATE_FEE, ASSESSMENT, VIOLATION_FINE, etc.)
            amount: Invoice amount
            description: Invoice description
            due_date: Payment due date
            invoice_date: Date invoice was created (defaults to today)
            paid: Whether invoice has been paid
            paid_date: Date invoice was paid (if applicable)
            reference_id: Reference to related entity (violation, assessment, etc.)

        Returns:
            Invoice instance with realistic data
        """
        # Default invoice date to today
        if invoice_date is None:
            invoice_date = date.today()

        # Ensure amount has exactly 2 decimal places
        amount = amount.quantize(Decimal("0.01"))

        return Invoice(
            tenant_id=tenant_id,
            member_id=member_id,
            invoice_type=invoice_type,
            amount=amount,
            description=description,
            due_date=due_date,
            invoice_date=invoice_date,
            paid=paid,
            paid_date=paid_date,
            reference_id=reference_id,
        )

    @staticmethod
    def create_late_fee_invoice(
        *,
        tenant_id: UUID,
        member_id: UUID,
        fee_amount: Decimal,
        due_date: Optional[date] = None,
        delinquency_id: Optional[UUID] = None,
    ) -> Invoice:
        """
        Create a late fee invoice.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_id: Member receiving the invoice
            fee_amount: Late fee amount
            due_date: Payment due date (defaults to 30 days from today)
            delinquency_id: Reference to delinquency record

        Returns:
            Invoice instance for late fee
        """
        if due_date is None:
            due_date = date.today() + timedelta(days=30)

        return InvoiceGenerator.create(
            tenant_id=tenant_id,
            member_id=member_id,
            invoice_type="LATE_FEE",
            amount=fee_amount,
            description="Late fee for overdue balance",
            due_date=due_date,
            reference_id=delinquency_id,
        )

    @staticmethod
    def create_assessment_invoice(
        *,
        tenant_id: UUID,
        member_id: UUID,
        assessment_amount: Decimal,
        assessment_name: str,
        due_date: Optional[date] = None,
        assessment_id: Optional[UUID] = None,
    ) -> Invoice:
        """
        Create a special assessment invoice.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_id: Member receiving the invoice
            assessment_amount: Assessment amount
            assessment_name: Name of the special assessment
            due_date: Payment due date (defaults to 30 days from today)
            assessment_id: Reference to assessment record

        Returns:
            Invoice instance for special assessment
        """
        if due_date is None:
            due_date = date.today() + timedelta(days=30)

        return InvoiceGenerator.create(
            tenant_id=tenant_id,
            member_id=member_id,
            invoice_type="ASSESSMENT",
            amount=assessment_amount,
            description=f"Special Assessment: {assessment_name}",
            due_date=due_date,
            reference_id=assessment_id,
        )

    @staticmethod
    def create_violation_fine_invoice(
        *,
        tenant_id: UUID,
        member_id: UUID,
        fine_amount: Decimal,
        violation_description: str,
        due_date: Optional[date] = None,
        violation_id: Optional[UUID] = None,
    ) -> Invoice:
        """
        Create a violation fine invoice.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_id: Member receiving the invoice
            fine_amount: Violation fine amount
            violation_description: Description of the violation
            due_date: Payment due date (defaults to 30 days from today)
            violation_id: Reference to violation record

        Returns:
            Invoice instance for violation fine
        """
        if due_date is None:
            due_date = date.today() + timedelta(days=30)

        return InvoiceGenerator.create(
            tenant_id=tenant_id,
            member_id=member_id,
            invoice_type="VIOLATION_FINE",
            amount=fine_amount,
            description=f"Violation Fine - {violation_description}",
            due_date=due_date,
            reference_id=violation_id,
        )

    @staticmethod
    def create_batch(
        *,
        tenant_id: UUID,
        member_ids: list[UUID],
        invoice_type: str = "LATE_FEE",
        amount_range: tuple[Decimal, Decimal] = (Decimal("25.00"), Decimal("100.00")),
    ) -> list[Invoice]:
        """
        Create multiple invoices.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_ids: List of member IDs to create invoices for
            invoice_type: Type of invoice
            amount_range: Range of invoice amounts (min, max)

        Returns:
            List of Invoice instances
        """
        invoices = []
        min_amount, max_amount = amount_range

        for member_id in member_ids:
            amount = Decimal(str(fake.random_int(
                min=int(min_amount),
                max=int(max_amount)
            ))).quantize(Decimal("0.01"))

            due_days = fake.random_int(min=15, max=45)
            due_date = date.today() + timedelta(days=due_days)

            invoice = InvoiceGenerator.create(
                tenant_id=tenant_id,
                member_id=member_id,
                invoice_type=invoice_type,
                amount=amount,
                description=f"{invoice_type.replace('_', ' ').title()} invoice",
                due_date=due_date,
            )
            invoices.append(invoice)

        return invoices
