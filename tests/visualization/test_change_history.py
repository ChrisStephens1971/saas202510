"""
Tests for Change History Visualization

Covers:
- Timeline generation
- Diff calculation (added, removed, modified, unchanged)
- Correction flow tracking
- HTML export
- PDF export
- Edge cases
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import os
import tempfile

import pytest

from qa_testing.visualization import (
    ChangeHistoryVisualizer,
    ChangeTimeline,
    ChangeEvent,
    CorrectionFlow,
    Diff,
    DiffType,
)


@pytest.fixture
def tenant_id():
    """Create a test tenant ID."""
    return uuid4()


@pytest.fixture
def entity_id():
    """Create a test entity ID."""
    return uuid4()


@pytest.fixture
def sample_events(entity_id):
    """Create sample change events."""
    base_time = datetime.now()

    return [
        ChangeEvent(
            event_id=uuid4(),
            entity_id=entity_id,
            entity_type="LedgerEntry",
            event_type="created",
            timestamp=base_time,
            changed_by="admin",
            before_state=None,
            after_state={
                "amount": "100.00",
                "account": "1100",
                "description": "Initial entry"
            },
            diffs=[]
        ),
        ChangeEvent(
            event_id=uuid4(),
            entity_id=entity_id,
            entity_type="LedgerEntry",
            event_type="updated",
            timestamp=base_time + timedelta(hours=1),
            changed_by="admin",
            before_state={
                "amount": "100.00",
                "account": "1100",
                "description": "Initial entry"
            },
            after_state={
                "amount": "150.00",
                "account": "1100",
                "description": "Updated entry"
            },
            diffs=[]
        ),
        ChangeEvent(
            event_id=uuid4(),
            entity_id=entity_id,
            entity_type="LedgerEntry",
            event_type="updated",
            timestamp=base_time + timedelta(hours=2),
            changed_by="user",
            before_state={
                "amount": "150.00",
                "account": "1100",
                "description": "Updated entry"
            },
            after_state={
                "amount": "150.00",
                "account": "1200",
                "description": "Updated entry"
            },
            diffs=[]
        ),
    ]


@pytest.fixture
def sample_correction_flow(entity_id):
    """Create a sample correction flow."""
    base_time = datetime.now()

    return CorrectionFlow(
        flow_id=uuid4(),
        original_entry_id=entity_id,
        original_timestamp=base_time,
        original_state={
            "amount": "100.00",
            "is_debit": True,
            "account": "1100"
        },
        reversing_entry_id=uuid4(),
        reversing_timestamp=base_time + timedelta(hours=1),
        reversing_state={
            "amount": "100.00",
            "is_debit": False,
            "account": "1100",
            "reverses_entry_id": str(entity_id)
        },
        correction_entry_id=uuid4(),
        correction_timestamp=base_time + timedelta(hours=1, minutes=5),
        correction_state={
            "amount": "150.00",
            "is_debit": True,
            "account": "1100"
        },
        reason="Amount was incorrect",
        corrected_by="admin",
        is_complete=True
    )


# ==============================================================================
# Test Timeline Generation
# ==============================================================================

class TestTimelineGeneration:
    """Test generating change timelines."""

    def test_generate_basic_timeline(self, tenant_id, entity_id, sample_events):
        """Test generating a basic timeline."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events
        )

        assert timeline.entity_id == entity_id
        assert timeline.entity_type == "LedgerEntry"
        assert timeline.tenant_id == tenant_id
        assert len(timeline.events) == 3
        assert timeline.total_changes == 3

    def test_timeline_events_sorted_by_time(self, tenant_id, entity_id, sample_events):
        """Test that timeline events are sorted by timestamp."""
        # Shuffle events
        shuffled = [sample_events[2], sample_events[0], sample_events[1]]

        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=shuffled
        )

        # Verify events are sorted
        for i in range(len(timeline.events) - 1):
            assert timeline.events[i].timestamp <= timeline.events[i + 1].timestamp

    def test_timeline_with_corrections(
        self,
        tenant_id,
        entity_id,
        sample_events,
        sample_correction_flow
    ):
        """Test timeline with correction flows."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events,
            corrections=[sample_correction_flow]
        )

        assert len(timeline.corrections) == 1
        assert timeline.corrections[0].is_complete is True

    def test_timeline_created_and_modified_times(
        self,
        tenant_id,
        entity_id,
        sample_events
    ):
        """Test that created and last modified times are correct."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events
        )

        assert timeline.created_at == sample_events[0].timestamp
        assert timeline.last_modified == sample_events[2].timestamp

    def test_timeline_with_empty_events(self, tenant_id, entity_id):
        """Test timeline with no events."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=[]
        )

        assert timeline.total_changes == 0
        assert len(timeline.events) == 0


# ==============================================================================
# Test Diff Generation
# ==============================================================================

class TestDiffGeneration:
    """Test diff calculation between states."""

    def test_diff_with_added_field(self):
        """Test diff when field is added."""
        before = {"field1": "value1"}
        after = {"field1": "value1", "field2": "value2"}

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        added_diffs = [d for d in diffs if d.diff_type == DiffType.ADDED]
        assert len(added_diffs) == 1
        assert added_diffs[0].field == "field2"
        assert added_diffs[0].new_value == "value2"

    def test_diff_with_removed_field(self):
        """Test diff when field is removed."""
        before = {"field1": "value1", "field2": "value2"}
        after = {"field1": "value1"}

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        removed_diffs = [d for d in diffs if d.diff_type == DiffType.REMOVED]
        assert len(removed_diffs) == 1
        assert removed_diffs[0].field == "field2"
        assert removed_diffs[0].old_value == "value2"

    def test_diff_with_modified_field(self):
        """Test diff when field is modified."""
        before = {"amount": "100.00"}
        after = {"amount": "150.00"}

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        modified_diffs = [d for d in diffs if d.diff_type == DiffType.MODIFIED]
        assert len(modified_diffs) == 1
        assert modified_diffs[0].field == "amount"
        assert modified_diffs[0].old_value == "100.00"
        assert modified_diffs[0].new_value == "150.00"

    def test_diff_calculates_percentage_change(self):
        """Test diff calculates percentage change for numeric fields."""
        before = {"amount": 100}
        after = {"amount": 150}

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        modified_diffs = [d for d in diffs if d.diff_type == DiffType.MODIFIED]
        assert len(modified_diffs) == 1
        assert modified_diffs[0].change_percentage == Decimal("50.0")

    def test_diff_with_unchanged_fields_excluded(self):
        """Test that unchanged fields are excluded by default."""
        before = {"field1": "value1", "field2": "value2"}
        after = {"field1": "value1", "field2": "value2"}

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        assert len(diffs) == 0

    def test_diff_with_unchanged_fields_included(self):
        """Test including unchanged fields."""
        before = {"field1": "value1"}
        after = {"field1": "value1"}

        diffs = ChangeHistoryVisualizer.generate_diff(before, after, include_unchanged=True)

        unchanged_diffs = [d for d in diffs if d.diff_type == DiffType.UNCHANGED]
        assert len(unchanged_diffs) == 1
        assert unchanged_diffs[0].field == "field1"

    def test_diff_skips_internal_fields(self):
        """Test that internal fields are skipped."""
        before = {
            "amount": "100.00",
            "id": "123",
            "_internal": "value",
            "created_at": "2024-01-01"
        }
        after = {
            "amount": "150.00",
            "id": "123",
            "_internal": "new_value",
            "created_at": "2024-01-02"
        }

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        # Should only have diff for amount
        assert len(diffs) == 1
        assert diffs[0].field == "amount"

    def test_diff_with_multiple_changes(self):
        """Test diff with multiple types of changes."""
        before = {
            "amount": "100.00",
            "account": "1100",
            "removed_field": "value"
        }
        after = {
            "amount": "150.00",
            "account": "1100",
            "new_field": "new_value"
        }

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        added = [d for d in diffs if d.diff_type == DiffType.ADDED]
        removed = [d for d in diffs if d.diff_type == DiffType.REMOVED]
        modified = [d for d in diffs if d.diff_type == DiffType.MODIFIED]

        assert len(added) == 1
        assert len(removed) == 1
        assert len(modified) == 1


# ==============================================================================
# Test Correction Flow Tracking
# ==============================================================================

class TestCorrectionFlowTracking:
    """Test tracking correction flows."""

    def test_trace_basic_correction_flow(self, entity_id):
        """Test tracing a basic correction flow."""
        base_time = datetime.now()

        events = [
            ChangeEvent(
                event_id=uuid4(),
                entity_id=entity_id,
                entity_type="LedgerEntry",
                event_type="created",
                timestamp=base_time,
                changed_by="admin",
                before_state=None,
                after_state={"amount": "100.00"}
            )
        ]

        flow = ChangeHistoryVisualizer.trace_corrections(
            entry_id=entity_id,
            all_events=events
        )

        assert flow.original_entry_id == entity_id
        assert flow.original_timestamp == base_time
        assert flow.original_state == {"amount": "100.00"}

    def test_trace_correction_with_reversal(self, entity_id):
        """Test tracing correction with reversal entry."""
        base_time = datetime.now()
        reversing_id = uuid4()

        events = [
            ChangeEvent(
                event_id=uuid4(),
                entity_id=entity_id,
                entity_type="LedgerEntry",
                event_type="created",
                timestamp=base_time,
                changed_by="admin",
                before_state=None,
                after_state={"amount": "100.00"}
            ),
            ChangeEvent(
                event_id=uuid4(),
                entity_id=reversing_id,
                entity_type="LedgerEntry",
                event_type="created",
                timestamp=base_time + timedelta(hours=1),
                changed_by="admin",
                before_state=None,
                after_state={
                    "amount": "100.00",
                    "reverses_entry_id": str(entity_id)
                }
            )
        ]

        ledger_entries = [
            {"id": reversing_id, "reverses_entry_id": entity_id}
        ]

        flow = ChangeHistoryVisualizer.trace_corrections(
            entry_id=entity_id,
            all_events=events,
            ledger_entries=ledger_entries
        )

        assert flow.reversing_entry_id == reversing_id
        assert flow.reversing_timestamp is not None

    def test_trace_nonexistent_entry_raises_error(self):
        """Test that tracing nonexistent entry raises error."""
        fake_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            ChangeHistoryVisualizer.trace_corrections(
                entry_id=fake_id,
                all_events=[]
            )


# ==============================================================================
# Test HTML Export
# ==============================================================================

class TestHTMLExport:
    """Test HTML export functionality."""

    def test_export_to_html_basic(self, tenant_id, entity_id, sample_events):
        """Test basic HTML export."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events
        )

        html = ChangeHistoryVisualizer.export_to_html(timeline)

        assert "<!DOCTYPE html>" in html
        assert "Change History" in html
        assert str(entity_id) in html
        assert "LedgerEntry" in html

    def test_html_export_includes_events(self, tenant_id, entity_id, sample_events):
        """Test HTML export includes all events."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events
        )

        html = ChangeHistoryVisualizer.export_to_html(timeline)

        # Verify event types are in HTML
        assert "CREATED" in html
        assert "UPDATED" in html

    def test_html_export_includes_corrections(
        self,
        tenant_id,
        entity_id,
        sample_events,
        sample_correction_flow
    ):
        """Test HTML export includes correction flows."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events,
            corrections=[sample_correction_flow]
        )

        html = ChangeHistoryVisualizer.export_to_html(timeline, include_corrections=True)

        assert "Correction Flow" in html
        assert str(sample_correction_flow.original_entry_id) in html

    def test_html_export_with_diffs(self, tenant_id, entity_id):
        """Test HTML export includes diffs."""
        base_time = datetime.now()

        # Create event with diffs
        before = {"amount": "100.00"}
        after = {"amount": "150.00"}
        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        events = [
            ChangeEvent(
                event_id=uuid4(),
                entity_id=entity_id,
                entity_type="LedgerEntry",
                event_type="updated",
                timestamp=base_time,
                changed_by="admin",
                before_state=before,
                after_state=after,
                diffs=diffs
            )
        ]

        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=events
        )

        html = ChangeHistoryVisualizer.export_to_html(timeline)

        assert "amount" in html
        assert "100.00" in html
        assert "150.00" in html


# ==============================================================================
# Test PDF Export
# ==============================================================================

class TestPDFExport:
    """Test PDF export functionality."""

    def test_export_to_pdf_creates_file(self, tenant_id, entity_id, sample_events):
        """Test PDF export creates a file."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filepath = tmp.name

        try:
            ChangeHistoryVisualizer.export_to_pdf(timeline, filepath)

            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 0
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_pdf_export_with_corrections(
        self,
        tenant_id,
        entity_id,
        sample_events,
        sample_correction_flow
    ):
        """Test PDF export includes correction flows."""
        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=sample_events,
            corrections=[sample_correction_flow]
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filepath = tmp.name

        try:
            ChangeHistoryVisualizer.export_to_pdf(timeline, filepath, include_corrections=True)

            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_pdf_export_with_diffs(self, tenant_id, entity_id):
        """Test PDF export with diff information."""
        base_time = datetime.now()

        before = {"amount": "100.00", "account": "1100"}
        after = {"amount": "150.00", "account": "1200"}
        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        events = [
            ChangeEvent(
                event_id=uuid4(),
                entity_id=entity_id,
                entity_type="LedgerEntry",
                event_type="updated",
                timestamp=base_time,
                changed_by="admin",
                before_state=before,
                after_state=after,
                diffs=diffs
            )
        ]

        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=events
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filepath = tmp.name

        try:
            ChangeHistoryVisualizer.export_to_pdf(timeline, filepath)

            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


# ==============================================================================
# Test Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_diff_with_empty_states(self):
        """Test diff with empty states."""
        diffs = ChangeHistoryVisualizer.generate_diff({}, {})

        assert len(diffs) == 0

    def test_diff_with_none_values(self):
        """Test diff handles None values."""
        before = {"field1": None}
        after = {"field1": "value"}

        diffs = ChangeHistoryVisualizer.generate_diff(before, after)

        modified = [d for d in diffs if d.diff_type == DiffType.MODIFIED]
        assert len(modified) == 1

    def test_timeline_with_single_event(self, tenant_id, entity_id):
        """Test timeline with only one event."""
        base_time = datetime.now()

        events = [
            ChangeEvent(
                event_id=uuid4(),
                entity_id=entity_id,
                entity_type="LedgerEntry",
                event_type="created",
                timestamp=base_time,
                changed_by="admin",
                before_state=None,
                after_state={"amount": "100.00"}
            )
        ]

        timeline = ChangeHistoryVisualizer.generate_timeline(
            entity_id=entity_id,
            entity_type="LedgerEntry",
            tenant_id=tenant_id,
            events=events
        )

        assert timeline.total_changes == 1
        assert timeline.created_at == timeline.last_modified

    def test_correction_flow_incomplete(self, entity_id):
        """Test correction flow that is not complete."""
        base_time = datetime.now()

        flow = CorrectionFlow(
            flow_id=uuid4(),
            original_entry_id=entity_id,
            original_timestamp=base_time,
            original_state={"amount": "100.00"},
            reversing_entry_id=uuid4(),
            reversing_timestamp=base_time + timedelta(hours=1),
            reversing_state={"amount": "100.00"},
            is_complete=False
        )

        assert flow.is_complete is False
        assert flow.correction_entry_id is None
