"""Auto-matching data generator for realistic test data."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import (
    AutoMatchRule,
    MatchResult,
    MatchStatistics,
    MatchStatus,
    RuleType,
)

fake = Faker()


class AutoMatchRuleGenerator:
    """
    Generator for creating realistic AutoMatchRule test data.

    Usage:
        # Create an exact match rule
        rule = AutoMatchRuleGenerator.create_exact(
            tenant_id=tenant.id,
            confidence_score=95
        )

        # Create a fuzzy match rule
        rule = AutoMatchRuleGenerator.create_fuzzy(
            tenant_id=tenant.id,
            confidence_score=85
        )

        # Create a pattern match rule
        rule = AutoMatchRuleGenerator.create_pattern(
            tenant_id=tenant.id,
            confidence_score=80
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        name: Optional[str] = None,
        rule_type: Optional[RuleType] = None,
        pattern: Optional[dict] = None,
        target_account_id: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
        match_count: int = 0,
        accuracy_rate: Optional[Decimal] = None,
        is_active: bool = True,
    ) -> AutoMatchRule:
        """
        Create an auto-match rule with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            name: Rule name (generates if not provided)
            rule_type: Type of rule (random if not provided)
            pattern: Pattern configuration dict (generates based on type if not provided)
            target_account_id: Target account (optional)
            confidence_score: Minimum confidence (50-95 if not provided)
            match_count: Number of times used (0 by default)
            accuracy_rate: Success rate percentage (85-99% if not provided)
            is_active: Whether rule is active

        Returns:
            AutoMatchRule instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Select random rule type if not provided
        if rule_type is None:
            rule_type = fake.random.choice(list(RuleType))

        # Generate confidence score (typical: 50-95)
        if confidence_score is None:
            if rule_type == RuleType.EXACT:
                confidence_score = fake.random.randint(90, 95)
            elif rule_type == RuleType.FUZZY:
                confidence_score = fake.random.randint(80, 90)
            elif rule_type == RuleType.PATTERN:
                confidence_score = fake.random.randint(75, 85)
            elif rule_type == RuleType.REFERENCE:
                confidence_score = fake.random.randint(85, 92)
            else:  # ML
                confidence_score = fake.random.randint(70, 90)

        # Generate pattern based on rule type
        if pattern is None:
            if rule_type == RuleType.EXACT:
                pattern = {
                    "amount_tolerance": 0.0,
                    "date_range": 1,
                    "description_match": "exact",
                }
            elif rule_type == RuleType.FUZZY:
                pattern = {
                    "amount_tolerance": 0.01,
                    "date_range": 3,
                    "description_similarity": 0.85,
                }
            elif rule_type == RuleType.PATTERN:
                pattern = {
                    "amount_tolerance": 0.01,
                    "date_range": 5,
                    "description_regex": "ACH.*TRANSFER|WIRE.*|CHECK.*",
                }
            elif rule_type == RuleType.REFERENCE:
                pattern = {
                    "reference_field": "check_number",
                    "match_type": "exact",
                }
            else:  # ML
                pattern = {
                    "model": "random_forest",
                    "features": ["amount", "date", "description", "reference"],
                    "threshold": 0.75,
                }

        # Generate accuracy rate (typical: 85-99%)
        if accuracy_rate is None:
            if match_count > 0:
                accuracy_rate = Decimal(str(fake.random.uniform(85.0, 99.0))).quantize(Decimal("0.01"))
            else:
                accuracy_rate = Decimal("0.00")

        # Generate name
        if name is None:
            if rule_type == RuleType.EXACT:
                name = "Exact Match - Amount + Date + Description"
            elif rule_type == RuleType.FUZZY:
                name = "Fuzzy Match - Similar Amount/Description"
            elif rule_type == RuleType.PATTERN:
                name = f"Pattern Match - {pattern.get('description_regex', 'ACH/Wire/Check')}"
            elif rule_type == RuleType.REFERENCE:
                name = f"Reference Match - {pattern.get('reference_field', 'check_number')}"
            else:  # ML
                name = f"ML Match - {pattern.get('model', 'random_forest')}"

        return AutoMatchRule(
            tenant_id=tenant_id,
            name=name,
            rule_type=rule_type,
            pattern=pattern,
            target_account_id=target_account_id,
            confidence_score=confidence_score,
            match_count=match_count,
            accuracy_rate=accuracy_rate,
            is_active=is_active,
        )

    @staticmethod
    def create_exact(
        *,
        tenant_id: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
    ) -> AutoMatchRule:
        """Create an exact match rule."""
        return AutoMatchRuleGenerator.create(
            tenant_id=tenant_id,
            rule_type=RuleType.EXACT,
            confidence_score=confidence_score or 95,
        )

    @staticmethod
    def create_fuzzy(
        *,
        tenant_id: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
    ) -> AutoMatchRule:
        """Create a fuzzy match rule."""
        return AutoMatchRuleGenerator.create(
            tenant_id=tenant_id,
            rule_type=RuleType.FUZZY,
            confidence_score=confidence_score or 85,
        )

    @staticmethod
    def create_pattern(
        *,
        tenant_id: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
        pattern: Optional[dict] = None,
    ) -> AutoMatchRule:
        """Create a pattern match rule."""
        return AutoMatchRuleGenerator.create(
            tenant_id=tenant_id,
            rule_type=RuleType.PATTERN,
            confidence_score=confidence_score or 80,
            pattern=pattern,
        )

    @staticmethod
    def create_reference(
        *,
        tenant_id: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
        reference_field: str = "check_number",
    ) -> AutoMatchRule:
        """Create a reference match rule."""
        pattern = {
            "reference_field": reference_field,
            "match_type": "exact",
        }
        return AutoMatchRuleGenerator.create(
            tenant_id=tenant_id,
            rule_type=RuleType.REFERENCE,
            confidence_score=confidence_score or 90,
            pattern=pattern,
        )

    @staticmethod
    def create_ml(
        *,
        tenant_id: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
        model: str = "random_forest",
    ) -> AutoMatchRule:
        """Create an ML match rule."""
        pattern = {
            "model": model,
            "features": ["amount", "date", "description", "reference"],
            "threshold": 0.75,
        }
        return AutoMatchRuleGenerator.create(
            tenant_id=tenant_id,
            rule_type=RuleType.ML,
            confidence_score=confidence_score or 80,
            pattern=pattern,
        )


class MatchResultGenerator:
    """
    Generator for creating realistic MatchResult test data.

    Usage:
        # Create a suggested match
        result = MatchResultGenerator.create_suggested(
            tenant_id=tenant.id,
            bank_transaction_id=transaction.id,
            matched_entry_id=entry.id,
            rule_used_id=rule.id
        )

        # Create an accepted match
        result = MatchResultGenerator.create_accepted(
            tenant_id=tenant.id,
            bank_transaction_id=transaction.id,
            matched_entry_id=entry.id,
            rule_used_id=rule.id,
            reviewed_by=user.id
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        bank_transaction_id: UUID,
        matched_entry_id: UUID,
        rule_used_id: UUID,
        confidence_score: Optional[int] = None,
        match_explanation: Optional[str] = None,
        status: Optional[MatchStatus] = None,
        reviewed_by: Optional[UUID] = None,
        reviewed_at: Optional[datetime] = None,
    ) -> MatchResult:
        """
        Create a match result with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            bank_transaction_id: Bank transaction ID (required)
            matched_entry_id: GL entry ID (required)
            rule_used_id: Rule that generated match (required)
            confidence_score: Confidence score (50-95 if not provided)
            match_explanation: Explanation text (generates if not provided)
            status: Match status (SUGGESTED if not provided)
            reviewed_by: User who reviewed (for ACCEPTED/REJECTED)
            reviewed_at: Review timestamp (for ACCEPTED/REJECTED)

        Returns:
            MatchResult instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate confidence score (typical: 50-95)
        if confidence_score is None:
            confidence_score = fake.random.randint(50, 95)

        # Default status
        if status is None:
            status = MatchStatus.SUGGESTED

        # Generate match explanation
        if match_explanation is None:
            explanations = [
                f"Exact amount match ${fake.random.randint(100, 5000)}.{fake.random.randint(0, 99):02d}, date within 1 day",
                f"Fuzzy match: amount ${fake.random.randint(100, 5000)}.{fake.random.randint(0, 99):02d} ±$0.01, description similarity 87%",
                f"Pattern match: ACH TRANSFER detected, amount ${fake.random.randint(100, 5000)}.{fake.random.randint(0, 99):02d}",
                f"Reference match: check number #{fake.random.randint(1000, 9999)} exact match",
                f"ML prediction: confidence {confidence_score}%, features: amount + description + date",
            ]
            match_explanation = fake.random.choice(explanations)

        # Set reviewed_by and reviewed_at for ACCEPTED/REJECTED status
        if status in [MatchStatus.ACCEPTED, MatchStatus.REJECTED]:
            if reviewed_by is None:
                reviewed_by = uuid4()
            if reviewed_at is None:
                reviewed_at = datetime.now()

        return MatchResult(
            tenant_id=tenant_id,
            bank_transaction_id=bank_transaction_id,
            matched_entry_id=matched_entry_id,
            rule_used_id=rule_used_id,
            confidence_score=confidence_score,
            match_explanation=match_explanation,
            status=status,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
        )

    @staticmethod
    def create_suggested(
        *,
        tenant_id: Optional[UUID] = None,
        bank_transaction_id: UUID,
        matched_entry_id: UUID,
        rule_used_id: UUID,
        confidence_score: Optional[int] = None,
    ) -> MatchResult:
        """Create a suggested match (not yet reviewed)."""
        return MatchResultGenerator.create(
            tenant_id=tenant_id,
            bank_transaction_id=bank_transaction_id,
            matched_entry_id=matched_entry_id,
            rule_used_id=rule_used_id,
            confidence_score=confidence_score,
            status=MatchStatus.SUGGESTED,
        )

    @staticmethod
    def create_accepted(
        *,
        tenant_id: Optional[UUID] = None,
        bank_transaction_id: UUID,
        matched_entry_id: UUID,
        rule_used_id: UUID,
        reviewed_by: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
    ) -> MatchResult:
        """Create an accepted match."""
        return MatchResultGenerator.create(
            tenant_id=tenant_id,
            bank_transaction_id=bank_transaction_id,
            matched_entry_id=matched_entry_id,
            rule_used_id=rule_used_id,
            confidence_score=confidence_score or fake.random.randint(85, 95),
            status=MatchStatus.ACCEPTED,
            reviewed_by=reviewed_by or uuid4(),
            reviewed_at=datetime.now(),
        )

    @staticmethod
    def create_rejected(
        *,
        tenant_id: Optional[UUID] = None,
        bank_transaction_id: UUID,
        matched_entry_id: UUID,
        rule_used_id: UUID,
        reviewed_by: Optional[UUID] = None,
        confidence_score: Optional[int] = None,
    ) -> MatchResult:
        """Create a rejected match."""
        return MatchResultGenerator.create(
            tenant_id=tenant_id,
            bank_transaction_id=bank_transaction_id,
            matched_entry_id=matched_entry_id,
            rule_used_id=rule_used_id,
            confidence_score=confidence_score or fake.random.randint(50, 75),
            status=MatchStatus.REJECTED,
            reviewed_by=reviewed_by or uuid4(),
            reviewed_at=datetime.now(),
        )

    @staticmethod
    def create_auto_matched(
        *,
        tenant_id: Optional[UUID] = None,
        bank_transaction_id: UUID,
        matched_entry_id: UUID,
        rule_used_id: UUID,
        confidence_score: Optional[int] = None,
    ) -> MatchResult:
        """Create an auto-matched result (high confidence, no review needed)."""
        return MatchResultGenerator.create(
            tenant_id=tenant_id,
            bank_transaction_id=bank_transaction_id,
            matched_entry_id=matched_entry_id,
            rule_used_id=rule_used_id,
            confidence_score=confidence_score or fake.random.randint(90, 95),
            status=MatchStatus.AUTO_MATCHED,
        )


class MatchStatisticsGenerator:
    """
    Generator for creating realistic MatchStatistics test data.

    Usage:
        # Create daily statistics
        stats = MatchStatisticsGenerator.create(
            tenant_id=tenant.id,
            date=date.today(),
            total_transactions=500,
            auto_matched=450
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        stat_date: Optional[date] = None,
        total_transactions: Optional[int] = None,
        auto_matched: Optional[int] = None,
        manually_matched: Optional[int] = None,
        unmatched: Optional[int] = None,
        auto_match_rate: Optional[Decimal] = None,
        average_confidence: Optional[Decimal] = None,
    ) -> MatchStatistics:
        """
        Create daily match statistics with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            stat_date: Statistics date (today if not provided)
            total_transactions: Total bank transactions (100-1000 if not provided)
            auto_matched: Auto-matched count (70-90% of total if not provided)
            manually_matched: Manually matched count (5-20% if not provided)
            unmatched: Unmatched count (5-15% if not provided)
            auto_match_rate: Auto-match percentage (calculates if not provided)
            average_confidence: Average confidence score (calculates if not provided)

        Returns:
            MatchStatistics instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate date
        if stat_date is None:
            stat_date = date.today()

        # Generate total transactions (typical: 100-1000 per day)
        if total_transactions is None:
            total_transactions = fake.random.randint(100, 1000)

        # Generate auto_matched (goal: 70-90% of total)
        if auto_matched is None:
            auto_match_percent = fake.random.uniform(0.70, 0.90)
            auto_matched = int(total_transactions * auto_match_percent)

        # Generate manually_matched (typical: 5-20%)
        if manually_matched is None:
            remaining = total_transactions - auto_matched
            if remaining > 0:
                manual_percent = fake.random.uniform(0.5, 0.9)
                manually_matched = int(remaining * manual_percent)
            else:
                manually_matched = 0

        # Calculate unmatched (remainder)
        if unmatched is None:
            unmatched = total_transactions - auto_matched - manually_matched
            if unmatched < 0:
                unmatched = 0

        # Ensure totals match
        actual_total = auto_matched + manually_matched + unmatched
        if actual_total != total_transactions:
            # Adjust unmatched to make totals match
            unmatched = total_transactions - auto_matched - manually_matched

        # Calculate auto_match_rate
        if auto_match_rate is None:
            if total_transactions > 0:
                auto_match_rate = (Decimal(auto_matched) / Decimal(total_transactions) * Decimal("100")).quantize(Decimal("0.01"))
            else:
                auto_match_rate = Decimal("0.00")

        # Generate average confidence (typical: 80-92% for auto-matches)
        if average_confidence is None:
            if auto_matched > 0:
                average_confidence = Decimal(str(fake.random.uniform(80.0, 92.0))).quantize(Decimal("0.01"))
            else:
                average_confidence = Decimal("0.00")

        return MatchStatistics(
            tenant_id=tenant_id,
            date=stat_date,
            total_transactions=total_transactions,
            auto_matched=auto_matched,
            manually_matched=manually_matched,
            unmatched=unmatched,
            auto_match_rate=auto_match_rate,
            average_confidence=average_confidence,
        )
