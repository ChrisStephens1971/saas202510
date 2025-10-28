"""Immutability verification for ledger entries.

This module verifies that ledger entries follow the INSERT-only pattern
required for financial compliance. Ledger entries must NEVER be updated
or deleted - all corrections must use reversing entries.

Key compliance requirements:
- INSERT only (no UPDATE or DELETE)
- Corrections via reversing entries
- Complete audit trail preservation
- Tamper detection
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from ..models.base import BaseTestModel
from ..models.transaction import LedgerEntry


class ImmutabilityReport(BaseTestModel):
    """
    Report verifying ledger immutability.

    This report is used for:
    - Audit compliance verification
    - Detecting tampering or unauthorized changes
    - Proving financial records haven't been modified
    """

    # Report metadata
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")
    report_date: datetime = Field(
        default_factory=datetime.now,
        description="When report was generated"
    )

    # Counts
    total_entries: int = Field(..., description="Total ledger entries examined")
    entries_with_updates: int = Field(
        default=0,
        description="Number of entries that appear updated (violation)"
    )
    entries_deleted: int = Field(
        default=0,
        description="Number of entries deleted (violation)"
    )
    reversing_entries: int = Field(
        default=0,
        description="Number of reversing entries (corrections)"
    )

    # Validation results
    is_immutable: bool = Field(
        ...,
        description="True if ledger is immutable (no updates or deletes)"
    )
    violations: list[str] = Field(
        default_factory=list,
        description="List of immutability violations found"
    )

    # Statistics
    oldest_entry_date: Optional[datetime] = Field(
        None,
        description="Date of oldest entry in ledger"
    )
    newest_entry_date: Optional[datetime] = Field(
        None,
        description="Date of newest entry in ledger"
    )


class ImmutabilityValidator:
    """
    Verify ledger entries follow INSERT-only pattern.

    This validator ensures financial records comply with immutability
    requirements:
    1. Ledger entries are never updated after creation
    2. Ledger entries are never deleted
    3. Corrections use reversing entries (not modifications)

    All methods are static for easy testing and reuse.
    """

    @staticmethod
    def verify_no_updates(ledger_entries: list[LedgerEntry]) -> bool:
        """
        Verify no ledger entries have been updated after creation.

        In a real database implementation, this would check:
        - created_at vs updated_at timestamps
        - Version numbers
        - Checksum/hash values

        For testing, we assume entries with matching created_at/updated_at
        have not been modified.

        Args:
            ledger_entries: List of ledger entries to check

        Returns:
            bool: True if no updates detected, False otherwise

        Example:
            >>> entries = [LedgerEntry(...), LedgerEntry(...)]
            >>> is_valid = ImmutabilityValidator.verify_no_updates(entries)
            >>> assert is_valid, "Ledger entries have been modified!"
        """
        # For testing purposes, we check if entries have internal consistency
        # In production, this would check database timestamps and audit trails

        for entry in ledger_entries:
            # Check if entry has been modified (simplified check)
            # In production, would compare created_at vs updated_at timestamps
            if hasattr(entry, "updated_at") and hasattr(entry, "created_at"):
                if entry.updated_at > entry.created_at:
                    return False

        return True

    @staticmethod
    def verify_no_deletes(
        expected_entry_ids: list[UUID],
        actual_entries: list[LedgerEntry],
    ) -> bool:
        """
        Verify no ledger entries have been deleted.

        Args:
            expected_entry_ids: List of entry IDs that should exist
            actual_entries: List of actual ledger entries found

        Returns:
            bool: True if no deletes detected, False otherwise

        Example:
            >>> expected_ids = [entry1.id, entry2.id, entry3.id]
            >>> actual_entries = [entry1, entry2, entry3]
            >>> is_valid = ImmutabilityValidator.verify_no_deletes(
            ...     expected_ids, actual_entries
            ... )
            >>> assert is_valid, "Ledger entries have been deleted!"
        """
        # Get actual entry IDs
        actual_entry_ids = {entry.id for entry in actual_entries}

        # Check if all expected IDs exist
        for expected_id in expected_entry_ids:
            if expected_id not in actual_entry_ids:
                return False  # Entry was deleted

        return True

    @staticmethod
    def verify_correction_pattern(
        original_entry: LedgerEntry,
        correction_entries: list[LedgerEntry],
    ) -> bool:
        """
        Verify corrections follow reversing entry pattern.

        Proper correction pattern:
        1. Original entry remains unchanged
        2. Reversing entry created with opposite debit/credit
        3. Reversing entry has same amount as original
        4. Reversing entry references original via reverses_entry_id
        5. New correct entry created

        Args:
            original_entry: Original (incorrect) entry
            correction_entries: List of correction entries (reversing + new)

        Returns:
            bool: True if correction pattern is valid, False otherwise

        Example:
            >>> # Original entry (incorrect)
            >>> original = LedgerEntry(amount=Decimal("100.00"), is_debit=True, ...)
            >>>
            >>> # Reversing entry
            >>> reversing = LedgerEntry(
            ...     amount=Decimal("100.00"),
            ...     is_debit=False,  # Opposite of original
            ...     is_reversing=True,
            ...     reverses_entry_id=original.id,
            ...     ...
            ... )
            >>>
            >>> # New correct entry
            >>> correct = LedgerEntry(amount=Decimal("150.00"), is_debit=True, ...)
            >>>
            >>> is_valid = ImmutabilityValidator.verify_correction_pattern(
            ...     original, [reversing, correct]
            ... )
        """
        if not correction_entries:
            return False

        # Find reversing entry (should reference original)
        reversing_entry = None
        for entry in correction_entries:
            if (
                entry.is_reversing
                and entry.reverses_entry_id == original_entry.id
            ):
                reversing_entry = entry
                break

        if not reversing_entry:
            return False  # No reversing entry found

        # Verify reversing entry has same amount
        if reversing_entry.amount != original_entry.amount:
            return False

        # Verify reversing entry has opposite debit/credit
        if reversing_entry.is_debit == original_entry.is_debit:
            return False

        # Verify reversing entry is in same fund
        if reversing_entry.fund_id != original_entry.fund_id:
            return False

        # Pattern is valid
        return True

    @staticmethod
    def generate_immutability_report(
        tenant_id: UUID,
        ledger_entries: list[LedgerEntry],
        expected_entry_ids: Optional[list[UUID]] = None,
    ) -> ImmutabilityReport:
        """
        Generate report verifying ledger immutability.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            ledger_entries: List of ledger entries to verify
            expected_entry_ids: Optional list of expected entry IDs

        Returns:
            ImmutabilityReport: Report with validation results

        Example:
            >>> report = ImmutabilityValidator.generate_immutability_report(
            ...     tenant_id=tenant_id,
            ...     ledger_entries=all_entries,
            ...     expected_entry_ids=expected_ids,
            ... )
            >>>
            >>> if not report.is_immutable:
            ...     print("VIOLATION: Ledger has been tampered with!")
            ...     for violation in report.violations:
            ...         print(f"  - {violation}")
        """
        violations = []

        # Check for updates
        if not ImmutabilityValidator.verify_no_updates(ledger_entries):
            violations.append("Ledger entries have been updated after creation")

        # Check for deletes (if expected IDs provided)
        entries_deleted = 0
        if expected_entry_ids:
            if not ImmutabilityValidator.verify_no_deletes(
                expected_entry_ids, ledger_entries
            ):
                # Count how many were deleted
                actual_ids = {e.id for e in ledger_entries}
                deleted_ids = set(expected_entry_ids) - actual_ids
                entries_deleted = len(deleted_ids)
                violations.append(
                    f"{entries_deleted} ledger entries have been deleted"
                )

        # Count reversing entries
        reversing_entries = sum(
            1 for entry in ledger_entries if entry.is_reversing
        )

        # Determine if immutable (no violations)
        is_immutable = len(violations) == 0

        # Get date range
        oldest_date = None
        newest_date = None
        if ledger_entries:
            # Use created_at if available, else entry_date
            dates = [
                getattr(entry, "created_at", entry.entry_date)
                for entry in ledger_entries
            ]
            # Convert dates to datetime for comparison
            datetime_dates = []
            for d in dates:
                if isinstance(d, datetime):
                    datetime_dates.append(d)
                else:
                    # Convert date to datetime
                    datetime_dates.append(
                        datetime.combine(d, datetime.min.time())
                    )

            oldest_date = min(datetime_dates) if datetime_dates else None
            newest_date = max(datetime_dates) if datetime_dates else None

        return ImmutabilityReport(
            tenant_id=tenant_id,
            total_entries=len(ledger_entries),
            entries_with_updates=len(violations) if "updated" in str(violations) else 0,
            entries_deleted=entries_deleted,
            reversing_entries=reversing_entries,
            is_immutable=is_immutable,
            violations=violations,
            oldest_entry_date=oldest_date,
            newest_entry_date=newest_date,
        )
