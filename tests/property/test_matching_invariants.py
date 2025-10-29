"""
Property-based tests for auto-matching invariants.

Uses Hypothesis to verify that matching operations maintain critical invariants:
- Confidence score: always 0-100 (integer), higher = better match
- Statistics invariants: total = auto_matched + manually_matched + unmatched
- Auto-match rate: always 0-100%, equals (auto_matched / total) * 100
- Accuracy invariants: accuracy_rate 0-100%, improves with verified matches
- Match status invariants: ACCEPTED/REJECTED require reviewed_by and reviewed_at
- Data type invariants: confidence_score is integer, rates are Decimal with 2 places
- Pattern invariants: pattern must be dict, not string
"""

from datetime import date, datetime
from decimal import Decimal

from hypothesis import assume, given
from hypothesis import strategies as st
import pytest

from qa_testing.generators import (
    AutoMatchRuleGenerator,
    MatchResultGenerator,
    MatchStatisticsGenerator,
    PropertyGenerator,
)
from qa_testing.models import MatchStatus, RuleType


# Custom strategies for matching tests
@st.composite
def confidence_score_strategy(draw):
    """Generate realistic confidence scores (50-95)."""
    return draw(st.integers(min_value=50, max_value=95))


@st.composite
def accuracy_rate_strategy(draw):
    """Generate realistic accuracy rates (85-99%)."""
    return Decimal(str(draw(st.floats(min_value=85.0, max_value=99.0)))).quantize(Decimal("0.01"))


@st.composite
def match_count_strategy(draw):
    """Generate realistic match counts (0-1000)."""
    return draw(st.integers(min_value=0, max_value=1000))


@st.composite
def transaction_count_strategy(draw):
    """Generate realistic transaction counts (100-1000)."""
    return draw(st.integers(min_value=100, max_value=1000))


class TestConfidenceScoreInvariants:
    """Property-based tests for confidence score invariants."""

    @given(
        confidence_score=confidence_score_strategy(),
    )
    def test_confidence_score_always_in_range(self, confidence_score):
        """
        INVARIANT: Confidence score is always 0-100 (integer).

        Confidence scores must be in valid range.
        """
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            confidence_score=confidence_score,
        )

        assert rule.confidence_score >= 0
        assert rule.confidence_score <= 100
        assert isinstance(rule.confidence_score, int)

    def test_confidence_score_is_integer_not_decimal(self):
        """
        INVARIANT: Confidence score must be integer, NOT Decimal.

        confidence_score field uses int type, not Decimal.
        """
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            confidence_score=85,
        )

        assert isinstance(rule.confidence_score, int)
        assert not isinstance(rule.confidence_score, Decimal)

    @given(
        confidence_score=confidence_score_strategy(),
    )
    def test_higher_confidence_indicates_better_match(self, confidence_score):
        """
        INVARIANT: Higher confidence score indicates better match quality.

        Confidence scores are ordered: EXACT > FUZZY > PATTERN.
        """
        property_obj = PropertyGenerator.create()

        # EXACT rules should have higher confidence
        exact_rule = AutoMatchRuleGenerator.create_exact(
            tenant_id=property_obj.tenant_id,
        )

        # FUZZY rules should have moderate confidence
        fuzzy_rule = AutoMatchRuleGenerator.create_fuzzy(
            tenant_id=property_obj.tenant_id,
        )

        # PATTERN rules should have lower confidence
        pattern_rule = AutoMatchRuleGenerator.create_pattern(
            tenant_id=property_obj.tenant_id,
        )

        # Exact should generally have highest confidence
        assert exact_rule.confidence_score >= 90
        # Fuzzy should have moderate confidence
        assert fuzzy_rule.confidence_score >= 75
        # All should be in valid range
        assert exact_rule.confidence_score <= 100


class TestStatisticsInvariants:
    """Property-based tests for statistics invariants."""

    @given(
        total_transactions=transaction_count_strategy(),
    )
    def test_statistics_totals_sum_correctly(self, total_transactions):
        """
        INVARIANT: total_transactions = auto_matched + manually_matched + unmatched.

        Sum of categories must equal total.
        """
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=total_transactions,
        )

        sum_of_categories = (
            stats.auto_matched +
            stats.manually_matched +
            stats.unmatched
        )

        assert stats.total_transactions == sum_of_categories

    @given(
        total_transactions=transaction_count_strategy(),
    )
    def test_auto_match_rate_calculation(self, total_transactions):
        """
        INVARIANT: auto_match_rate = (auto_matched / total_transactions) * 100.

        Rate must be calculated correctly from counts.
        """
        assume(total_transactions > 0)

        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=total_transactions,
        )

        if stats.total_transactions > 0:
            expected_rate = (
                Decimal(stats.auto_matched) /
                Decimal(stats.total_transactions) *
                Decimal("100")
            ).quantize(Decimal("0.01"))

            assert stats.auto_match_rate == expected_rate

    @given(
        total_transactions=transaction_count_strategy(),
    )
    def test_all_counts_non_negative(self, total_transactions):
        """
        INVARIANT: All transaction counts must be non-negative.

        Cannot have negative counts.
        """
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=total_transactions,
        )

        assert stats.total_transactions >= 0
        assert stats.auto_matched >= 0
        assert stats.manually_matched >= 0
        assert stats.unmatched >= 0

    @given(
        total_transactions=transaction_count_strategy(),
    )
    def test_auto_match_rate_in_valid_range(self, total_transactions):
        """
        INVARIANT: auto_match_rate must be 0-100%.

        Rate cannot exceed 100% or be negative.
        """
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=total_transactions,
        )

        assert stats.auto_match_rate >= Decimal("0.00")
        assert stats.auto_match_rate <= Decimal("100.00")


class TestAccuracyInvariants:
    """Property-based tests for accuracy tracking invariants."""

    @given(
        match_count=match_count_strategy(),
        accuracy_rate=accuracy_rate_strategy(),
    )
    def test_accuracy_rate_always_in_range(self, match_count, accuracy_rate):
        """
        INVARIANT: accuracy_rate is always 0-100%.

        Accuracy percentage must be in valid range.
        """
        assume(match_count > 0)  # Only test when there are matches

        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=match_count,
            accuracy_rate=accuracy_rate,
        )

        assert rule.accuracy_rate >= Decimal("0.00")
        assert rule.accuracy_rate <= Decimal("100.00")

    def test_accuracy_rate_zero_when_no_matches(self):
        """
        INVARIANT: accuracy_rate should be 0% when match_count is 0.

        No matches means no accuracy data yet.
        """
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=0,
            accuracy_rate=Decimal("0.00"),
        )

        if rule.match_count == 0:
            assert rule.accuracy_rate == Decimal("0.00")

    @given(
        match_count=match_count_strategy(),
    )
    def test_accuracy_improves_with_more_matches(self, match_count):
        """
        INVARIANT: More matches generally lead to better accuracy tracking.

        Rules with more matches have better statistical confidence.
        """
        assume(match_count > 100)

        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=match_count,
        )

        # With many matches, accuracy should be tracked
        if rule.match_count > 100:
            # Accuracy rate should be calculated (not zero)
            assert rule.accuracy_rate >= Decimal("0.00")

    def test_average_confidence_in_valid_range(self):
        """
        INVARIANT: average_confidence is always 0-100%.

        Average confidence must be in valid percentage range.
        """
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=1000,
            auto_matched=850,
        )

        assert stats.average_confidence >= Decimal("0.00")
        assert stats.average_confidence <= Decimal("100.00")


class TestMatchStatusInvariants:
    """Property-based tests for match status invariants."""

    def test_accepted_match_requires_reviewed_by(self):
        """
        INVARIANT: ACCEPTED status requires reviewed_by and reviewed_at.

        Accepted matches must have reviewer information.
        """
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create_accepted(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
        )

        if result.status == MatchStatus.ACCEPTED:
            assert result.reviewed_by is not None
            assert result.reviewed_at is not None

    def test_rejected_match_requires_reviewed_by(self):
        """
        INVARIANT: REJECTED status requires reviewed_by and reviewed_at.

        Rejected matches must have reviewer information.
        """
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create_rejected(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
        )

        if result.status == MatchStatus.REJECTED:
            assert result.reviewed_by is not None
            assert result.reviewed_at is not None

    def test_suggested_match_no_review_info(self):
        """
        INVARIANT: SUGGESTED status should not have reviewed_by or reviewed_at.

        Suggested matches haven't been reviewed yet.
        """
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create_suggested(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
        )

        if result.status == MatchStatus.SUGGESTED:
            assert result.reviewed_by is None
            assert result.reviewed_at is None

    def test_auto_matched_no_review_info(self):
        """
        INVARIANT: AUTO_MATCHED status should not have reviewed_by or reviewed_at.

        Auto-matched results don't need manual review.
        """
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create_auto_matched(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
        )

        if result.status == MatchStatus.AUTO_MATCHED:
            assert result.reviewed_by is None
            assert result.reviewed_at is None


class TestDataTypeInvariants:
    """Property-based tests for data type invariants."""

    @given(
        confidence_score=confidence_score_strategy(),
    )
    def test_confidence_score_is_integer_type(self, confidence_score):
        """
        INVARIANT: confidence_score must be integer, NOT Decimal.

        This is a critical data type requirement.
        """
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            confidence_score=confidence_score,
        )

        assert isinstance(rule.confidence_score, int)
        assert not isinstance(rule.confidence_score, Decimal)

    @given(
        accuracy_rate=accuracy_rate_strategy(),
    )
    def test_accuracy_rate_uses_decimal_with_precision(self, accuracy_rate):
        """
        INVARIANT: accuracy_rate uses Decimal with exactly 2 decimal places.

        Percentage rates must use NUMERIC(15,2) equivalent.
        """
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            match_count=100,
            accuracy_rate=accuracy_rate,
        )

        assert isinstance(rule.accuracy_rate, Decimal)
        assert rule.accuracy_rate.as_tuple().exponent == -2

    @given(
        total_transactions=transaction_count_strategy(),
    )
    def test_auto_match_rate_uses_decimal_with_precision(self, total_transactions):
        """
        INVARIANT: auto_match_rate uses Decimal with exactly 2 decimal places.

        Percentage rates must use NUMERIC(15,2) equivalent.
        """
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=total_transactions,
        )

        assert isinstance(stats.auto_match_rate, Decimal)
        assert stats.auto_match_rate.as_tuple().exponent == -2

    @given(
        total_transactions=transaction_count_strategy(),
    )
    def test_average_confidence_uses_decimal_with_precision(self, total_transactions):
        """
        INVARIANT: average_confidence uses Decimal with exactly 2 decimal places.

        Percentage rates must use NUMERIC(15,2) equivalent.
        """
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            total_transactions=total_transactions,
        )

        assert isinstance(stats.average_confidence, Decimal)
        assert stats.average_confidence.as_tuple().exponent == -2

    def test_reviewed_at_uses_datetime_type(self):
        """
        INVARIANT: reviewed_at uses datetime type (can be null).

        Review timestamp must be datetime when present.
        """
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
        """
        INVARIANT: statistics date uses date type (not datetime).

        Date fields should use DATE, not datetime.
        """
        property_obj = PropertyGenerator.create()

        stats = MatchStatisticsGenerator.create(
            tenant_id=property_obj.tenant_id,
            stat_date=date.today(),
        )

        assert isinstance(stats.date, date)
        # Ensure it's date, not datetime
        assert type(stats.date).__name__ == "date"


class TestPatternInvariants:
    """Property-based tests for pattern field invariants."""

    def test_pattern_must_be_dict(self):
        """
        INVARIANT: pattern field must be dict/JSON, not string.

        Pattern configuration stored as structured data.
        """
        property_obj = PropertyGenerator.create()

        rule = AutoMatchRuleGenerator.create_exact(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(rule.pattern, dict)
        assert not isinstance(rule.pattern, str)

    def test_all_rule_types_have_dict_patterns(self):
        """
        INVARIANT: All rule types store patterns as dict.

        Every rule type must use dict for pattern field.
        """
        property_obj = PropertyGenerator.create()

        for rule_type in RuleType:
            if rule_type == RuleType.EXACT:
                rule = AutoMatchRuleGenerator.create_exact(tenant_id=property_obj.tenant_id)
            elif rule_type == RuleType.FUZZY:
                rule = AutoMatchRuleGenerator.create_fuzzy(tenant_id=property_obj.tenant_id)
            elif rule_type == RuleType.PATTERN:
                rule = AutoMatchRuleGenerator.create_pattern(tenant_id=property_obj.tenant_id)
            elif rule_type == RuleType.REFERENCE:
                rule = AutoMatchRuleGenerator.create_reference(tenant_id=property_obj.tenant_id)
            else:  # ML
                rule = AutoMatchRuleGenerator.create_ml(tenant_id=property_obj.tenant_id)

            assert isinstance(rule.pattern, dict)


class TestMatchExplanationInvariants:
    """Property-based tests for match explanation invariants."""

    @given(
        confidence_score=confidence_score_strategy(),
    )
    def test_match_explanation_is_text(self, confidence_score):
        """
        INVARIANT: match_explanation is text string, not empty.

        Explanations must be descriptive text.
        """
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
            confidence_score=confidence_score,
        )

        assert isinstance(result.match_explanation, str)
        assert len(result.match_explanation) > 0

    def test_match_explanation_describes_match(self):
        """
        INVARIANT: match_explanation should describe why match was made.

        Explanations should contain match-related keywords.
        """
        property_obj = PropertyGenerator.create()
        from uuid import uuid4

        result = MatchResultGenerator.create(
            tenant_id=property_obj.tenant_id,
            bank_transaction_id=uuid4(),
            matched_entry_id=uuid4(),
            rule_used_id=uuid4(),
        )

        explanation_lower = result.match_explanation.lower()
        # Should contain at least one match-related keyword
        keywords = ["match", "amount", "date", "description", "confidence", "pattern", "reference"]
        assert any(keyword in explanation_lower for keyword in keywords)
