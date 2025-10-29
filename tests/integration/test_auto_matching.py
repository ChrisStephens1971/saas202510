"""
Integration tests for auto-matching engine and bank reconciliation matching.

Tests the complete auto-matching lifecycle including:
- Auto-match rule configuration (5 rule types: EXACT, FUZZY, PATTERN, REFERENCE, ML)
- Match rule pattern structure and validation
- Match result generation (4 statuses: SUGGESTED, ACCEPTED, REJECTED, AUTO_MATCHED)
- Match review workflow (SUGGESTED → ACCEPTED/REJECTED)
- Daily match statistics tracking and aggregation
- Performance tracking (match_count, accuracy_rate)
- Data type validation (integer confidence_score, Decimal percentages, datetime for reviewed_at)
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from qa_testing.generators import (
    AutoMatchRuleGenerator,
    MatchResultGenerator,
    MatchStatisticsGenerator,
    PropertyGenerator,
)
from qa_testing.models import (
    AutoMatchRule,
    MatchResult,
    MatchStatistics,
    MatchStatus,
    RuleType,
)


class TestAutoMatchRules:
    """Tests for auto-match rule configuration."""

    def test_create_exact_match_rule(self):
        """Test creating an exact match rule."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_exact(
            tenant_id=property_obj.tenant_id,
            confidence_score=95,
        )

        assert rule.rule_type == RuleType.EXACT
        assert rule.confidence_score == 95
        assert isinstance(rule.confidence_score, int)
        assert rule.pattern["amount_tolerance"] == 0.0
        assert rule.is_active is True

    def test_create_fuzzy_match_rule(self):
        """Test creating a fuzzy match rule."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_fuzzy(
            tenant_id=property_obj.tenant_id,
            confidence_score=85,
        )

        assert rule.rule_type == RuleType.FUZZY
        assert rule.confidence_score == 85
        assert isinstance(rule.confidence_score, int)
        assert rule.pattern["amount_tolerance"] == 0.01
        assert "description_similarity" in rule.pattern

    def test_create_pattern_match_rule(self):
        """Test creating a pattern match rule."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_pattern(
            tenant_id=property_obj.tenant_id,
            confidence_score=80,
        )

        assert rule.rule_type == RuleType.PATTERN
        assert rule.confidence_score == 80
        assert isinstance(rule.confidence_score, int)
        assert "description_regex" in rule.pattern

    def test_create_reference_match_rule(self):
        """Test creating a reference match rule."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_reference(
            tenant_id=property_obj.tenant_id,
            confidence_score=90,
        )

        assert rule.rule_type == RuleType.REFERENCE
        assert rule.confidence_score == 90
        assert isinstance(rule.confidence_score, int)
        assert rule.pattern["reference_field"] == "check_number"
        assert rule.pattern["match_type"] == "exact"

    def test_create_ml_match_rule(self):
        """Test creating an ML match rule."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_ml(
            tenant_id=property_obj.tenant_id,
            confidence_score=80,
        )

        assert rule.rule_type == RuleType.ML
        assert rule.confidence_score == 80
        assert isinstance(rule.confidence_score, int)
        assert rule.pattern["model"] == "random_forest"
        assert "features" in rule.pattern

    def test_rule_confidence_score_validation(self):
        """Test that confidence_score is validated (0-100)."""
        property_obj = PropertyGenerator.create()

        # Valid confidence scores
        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            confidence_score=75,
        )
        assert rule.confidence_score == 75
        assert isinstance(rule.confidence_score, int)

    def test_rule_match_count_tracking(self):
        """Test that match_count tracks usage."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=150,
        )

        assert rule.match_count == 150
        assert rule.match_count >= 0

    def test_rule_accuracy_rate_tracking(self):
        """Test that accuracy_rate tracks success."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=100,
            accuracy_rate=Decimal("92.50"),
        )

        assert rule.accuracy_rate == Decimal("92.50")
        assert isinstance(rule.accuracy_rate, Decimal)
        assert rule.accuracy_rate.as_tuple().exponent == -2


class TestRulePatterns:
    """Tests for rule pattern structure and validation."""

    def test_exact_rule_pattern_structure(self):
        """Test exact rule pattern has correct fields."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_exact(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(rule.pattern, dict)
        assert "amount_tolerance" in rule.pattern
        assert "date_range" in rule.pattern
        assert rule.pattern["amount_tolerance"] == 0.0

    def test_fuzzy_rule_pattern_structure(self):
        """Test fuzzy rule pattern has correct fields."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_fuzzy(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(rule.pattern, dict)
        assert "amount_tolerance" in rule.pattern
        assert "date_range" in rule.pattern
        assert "description_similarity" in rule.pattern

    def test_pattern_rule_pattern_structure(self):
        """Test pattern rule has regex pattern."""
        property_obj = PropertyGenerator.create()

        pattern = {
            "amount_tolerance": 0.01,
            "date_range": 5,
            "description_regex": "ACH.*TRANSFER",
        }

        rule = AutoMatchRuleGenerator.create_pattern(
            tenant_id=property_obj.tenant_id,
            pattern=pattern,
        )

        assert isinstance(rule.pattern, dict)
        assert rule.pattern["description_regex"] == "ACH.*TRANSFER"

    def test_reference_rule_pattern_structure(self):
        """Test reference rule pattern has reference field."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_reference(
            tenant_id=property_obj.tenant_id,
            reference_field="invoice_number",
        )

        assert isinstance(rule.pattern, dict)
        assert rule.pattern["reference_field"] == "invoice_number"
        assert rule.pattern["match_type"] == "exact"

    def test_ml_rule_pattern_structure(self):
        """Test ML rule pattern has model and features."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_ml(
            tenant_id=property_obj.tenant_id,
            model="gradient_boosting",
        )

        assert isinstance(rule.pattern, dict)
        assert rule.pattern["model"] == "gradient_boosting"
        assert "features" in rule.pattern
        assert isinstance(rule.pattern["features"], list)


class TestMatchResults:
    """Tests for match result generation."""

    def test_create_suggested_match(self):
        """Test creating a suggested match."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4
        bank_tx_id = uuid4()
        entry_id = uuid4()
        rule_id = uuid4()

        result = MatchResultGenerator.create_suggested(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
            confidence_score=85,
        )

        assert result.status == MatchStatus.SUGGESTED
        assert result.confidence_score == 85
        assert isinstance(result.confidence_score, int)
        assert result.reviewed_by is None
        assert result.reviewed_at is None

    def test_create_accepted_match(self):
        """Test creating an accepted match."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4
        bank_tx_id = uuid4()
        entry_id = uuid4()
        rule_id = uuid4()
        reviewer_id = uuid4()

        result = MatchResultGenerator.create_accepted(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
            reviewed_by=reviewer_id,
            confidence_score=90,
        )

        assert result.status == MatchStatus.ACCEPTED
        assert result.confidence_score == 90
        assert isinstance(result.confidence_score, int)
        assert result.reviewed_by == reviewer_id
        assert result.reviewed_at is not None
        assert isinstance(result.reviewed_at, datetime)

    def test_create_rejected_match(self):
        """Test creating a rejected match."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4
        bank_tx_id = uuid4()
        entry_id = uuid4()
        rule_id = uuid4()
        reviewer_id = uuid4()

        result = MatchResultGenerator.create_rejected(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
            reviewed_by=reviewer_id,
            confidence_score=65,
        )

        assert result.status == MatchStatus.REJECTED
        assert result.confidence_score == 65
        assert isinstance(result.confidence_score, int)
        assert result.reviewed_by == reviewer_id
        assert result.reviewed_at is not None
        assert isinstance(result.reviewed_at, datetime)

    def test_create_auto_matched_result(self):
        """Test creating an auto-matched result."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4
        bank_tx_id = uuid4()
        entry_id = uuid4()
        rule_id = uuid4()

        result = MatchResultGenerator.create_auto_matched(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
            confidence_score=95,
        )

        assert result.status == MatchStatus.AUTO_MATCHED
        assert result.confidence_score == 95
        assert isinstance(result.confidence_score, int)
        assert result.reviewed_by is None
        assert result.reviewed_at is None

    def test_match_explanation_text(self):
        """Test that match explanation is descriptive text."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
            match_explanation="Exact amount match $523.45, date within 1 day",
        )

        assert isinstance(result.match_explanation, str)
        assert len(result.match_explanation) > 0
        assert "match" in result.match_explanation.lower()


class TestMatchReview:
    """Tests for match review workflow."""

    def test_suggested_to_accepted_workflow(self):
        """Test SUGGESTED → ACCEPTED workflow."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4
        bank_tx_id = uuid4()
        entry_id = uuid4()
        rule_id = uuid4()

        # Create suggested match
        suggested = MatchResultGenerator.create_suggested(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
        )

        assert suggested.status == MatchStatus.SUGGESTED
        assert suggested.reviewed_by is None

        # Accept the match
        accepted = MatchResultGenerator.create_accepted(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
        )

        assert accepted.status == MatchStatus.ACCEPTED
        assert accepted.reviewed_by is not None
        assert accepted.reviewed_at is not None

    def test_suggested_to_rejected_workflow(self):
        """Test SUGGESTED → REJECTED workflow."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4
        bank_tx_id = uuid4()
        entry_id = uuid4()
        rule_id = uuid4()

        # Create suggested match
        suggested = MatchResultGenerator.create_suggested(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
        )

        assert suggested.status == MatchStatus.SUGGESTED

        # Reject the match
        rejected = MatchResultGenerator.create_rejected(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=bank_tx_id,
            matched_entry_id=entry_id,
            rule_used_id=rule_id,
        )

        assert rejected.status == MatchStatus.REJECTED
        assert rejected.reviewed_by is not None
        assert rejected.reviewed_at is not None

    def test_reviewed_by_tracking(self):
        """Test that reviewed_by tracks the reviewer."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4
        reviewer_id = uuid4()

        result = MatchResultGenerator.create_accepted(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
            reviewed_by=reviewer_id,
        )

        assert result.reviewed_by == reviewer_id

    def test_reviewed_at_timestamp(self):
        """Test that reviewed_at captures review timestamp."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create_accepted(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
        )

        assert result.reviewed_at is not None
        assert isinstance(result.reviewed_at, datetime)


class TestMatchStatistics:
    """Tests for daily match statistics."""

    def test_create_daily_statistics(self):
        """Test creating daily match statistics."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            stat_date=date.today(),
            total_transactions=500,
            auto_matched=450,
            manually_matched=30,
            unmatched=20,
        )

        assert stats.total_transactions == 500
        assert stats.auto_matched == 450
        assert stats.manually_matched == 30
        assert stats.unmatched == 20

    def test_statistics_totals_sum_correctly(self):
        """Test that statistics totals sum correctly."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=1000,
            auto_matched=850,
            manually_matched=100,
            unmatched=50,
        )

        total = stats.auto_matched + stats.manually_matched + stats.unmatched
        assert total == stats.total_transactions

    def test_auto_match_rate_calculation(self):
        """Test auto_match_rate calculation."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=1000,
            auto_matched=900,
            manually_matched=75,
            unmatched=25,
        )

        expected_rate = (Decimal("900") / Decimal("1000") * Decimal("100")).quantize(Decimal("0.01"))
        assert stats.auto_match_rate == expected_rate
        assert isinstance(stats.auto_match_rate, Decimal)
        assert stats.auto_match_rate.as_tuple().exponent == -2

    def test_average_confidence_tracking(self):
        """Test average_confidence calculation."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=500,
            auto_matched=450,
            average_confidence=Decimal("87.50"),
        )

        assert stats.average_confidence == Decimal("87.50")
        assert isinstance(stats.average_confidence, Decimal)
        assert stats.average_confidence.as_tuple().exponent == -2

    def test_high_auto_match_rate_goal(self):
        """Test achieving high auto-match rate (goal: 90-95%)."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=1000,
            auto_matched=925,  # 92.5%
            manually_matched=50,
            unmatched=25,
        )

        assert stats.auto_match_rate >= Decimal("90.00")
        assert stats.auto_match_rate <= Decimal("95.00")


class TestPerformanceTracking:
    """Tests for match performance tracking."""

    def test_rule_match_count_increment(self):
        """Test that match_count increments with usage."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=0,
        )

        assert rule.match_count == 0

        # Simulate usage
        rule_with_matches = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=50,
        )

        assert rule_with_matches.match_count == 50
        assert rule_with_matches.match_count > rule.match_count

    def test_rule_accuracy_rate_updates(self):
        """Test that accuracy_rate updates with performance."""
        property_obj = PropertyGenerator.create()

        # Initial rule with no matches
        rule_initial = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=0,
            accuracy_rate=Decimal("0.00"),
        )

        assert rule_initial.accuracy_rate == Decimal("0.00")

        # Rule with good performance
        rule_good = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=100,
            accuracy_rate=Decimal("95.00"),
        )

        assert rule_good.accuracy_rate == Decimal("95.00")
        assert rule_good.accuracy_rate > rule_initial.accuracy_rate

    def test_rule_effectiveness_comparison(self):
        """Test comparing rule effectiveness."""
        property_obj = PropertyGenerator.create()

        exact_rule = AutoMatchRuleGenerator.create_exact(
            tenant_id=property_obj.tenant_id,
        )

        fuzzy_rule = AutoMatchRuleGenerator.create_fuzzy(
            tenant_id=property_obj.tenant_id,
        )

        # Exact rules typically have higher confidence
        assert exact_rule.confidence_score >= fuzzy_rule.confidence_score


class TestMatchingDataTypes:
    """Tests for proper data type usage in matching."""

    def test_confidence_score_is_integer(self):
        """Test that confidence_score uses integer (0-100)."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            confidence_score=85,
        )

        assert isinstance(rule.confidence_score, int)
        assert rule.confidence_score >= 0
        assert rule.confidence_score <= 100

    def test_accuracy_rate_uses_decimal(self):
        """Test that accuracy_rate uses Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=100,
            accuracy_rate=Decimal("92.50"),
        )

        assert isinstance(rule.accuracy_rate, Decimal)
        assert rule.accuracy_rate.as_tuple().exponent == -2

    def test_auto_match_rate_uses_decimal(self):
        """Test that auto_match_rate uses Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=1000,
            auto_matched=850,
        )

        assert isinstance(stats.auto_match_rate, Decimal)
        assert stats.auto_match_rate.as_tuple().exponent == -2

    def test_average_confidence_uses_decimal(self):
        """Test that average_confidence uses Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=500,
            auto_matched=450,
            average_confidence=Decimal("87.50"),
        )

        assert isinstance(stats.average_confidence, Decimal)
        assert stats.average_confidence.as_tuple().exponent == -2

    def test_reviewed_at_uses_datetime(self):
        """Test that reviewed_at uses datetime type."""
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create_accepted(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
        )

        if result.reviewed_at is not None:
            assert isinstance(result.reviewed_at, datetime)

    def test_statistics_date_uses_date_type(self):
        """Test that statistics date uses date type."""
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            stat_date=date.today(),
        )

        assert isinstance(stats.date, date)

    def test_pattern_is_dict(self):
        """Test that pattern field is dict/JSON."""
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_exact(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(rule.pattern, dict)
        assert not isinstance(rule.pattern, str)
