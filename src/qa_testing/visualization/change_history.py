"""
Change History Visualization

Provides tools for visualizing change history, corrections, and audit trails:
- Timeline view of all changes to an entity
- Before/after diff display
- Correction flow tracking (original → reversal → correction)
- Export to HTML and PDF
- Integration with audit trail
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT


class DiffType(str, Enum):
    """Types of differences between states."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class Diff(BaseModel):
    """Difference between two states."""
    field: str = Field(..., description="Field name")
    diff_type: DiffType = Field(..., description="Type of difference")
    old_value: Optional[Any] = Field(None, description="Previous value")
    new_value: Optional[Any] = Field(None, description="New value")
    change_percentage: Optional[Decimal] = Field(None, description="Percentage change for numeric fields")


class ChangeEvent(BaseModel):
    """A single change event in entity history."""
    event_id: UUID = Field(..., description="Unique event ID")
    entity_id: UUID = Field(..., description="Entity that changed")
    entity_type: str = Field(..., description="Type of entity (Transaction, LedgerEntry, etc.)")
    event_type: str = Field(..., description="Type of event (created, updated, etc.)")
    timestamp: datetime = Field(..., description="When change occurred")
    changed_by: Optional[str] = Field(None, description="User who made the change")
    before_state: Optional[dict[str, Any]] = Field(None, description="State before change")
    after_state: dict[str, Any] = Field(..., description="State after change")
    diffs: list[Diff] = Field(default_factory=list, description="Computed differences")
    audit_trail_id: Optional[UUID] = Field(None, description="Link to audit trail entry")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class CorrectionFlow(BaseModel):
    """Tracks a correction workflow from original through reversal to correction."""
    flow_id: UUID = Field(..., description="Unique flow ID")
    original_entry_id: UUID = Field(..., description="Original (incorrect) entry")
    original_timestamp: datetime = Field(..., description="When original was created")
    original_state: dict[str, Any] = Field(..., description="Original entry state")

    reversing_entry_id: Optional[UUID] = Field(None, description="Reversing entry ID")
    reversing_timestamp: Optional[datetime] = Field(None, description="When reversal was created")
    reversing_state: Optional[dict[str, Any]] = Field(None, description="Reversing entry state")

    correction_entry_id: Optional[UUID] = Field(None, description="Corrected entry ID")
    correction_timestamp: Optional[datetime] = Field(None, description="When correction was created")
    correction_state: Optional[dict[str, Any]] = Field(None, description="Corrected entry state")

    reason: Optional[str] = Field(None, description="Reason for correction")
    corrected_by: Optional[str] = Field(None, description="User who made correction")
    is_complete: bool = Field(False, description="Whether correction flow is complete")


class ChangeTimeline(BaseModel):
    """Timeline of all changes to an entity."""
    entity_id: UUID = Field(..., description="Entity being tracked")
    entity_type: str = Field(..., description="Type of entity")
    tenant_id: UUID = Field(..., description="Tenant ID for isolation")
    events: list[ChangeEvent] = Field(default_factory=list, description="All change events")
    corrections: list[CorrectionFlow] = Field(default_factory=list, description="Correction flows")
    created_at: datetime = Field(..., description="When entity was created")
    last_modified: datetime = Field(..., description="When entity was last modified")
    total_changes: int = Field(0, description="Total number of changes")


class ChangeHistoryVisualizer:
    """
    Visualizer for change history and correction flows.

    Features:
    - Timeline generation from change events
    - Diff calculation between states
    - Correction flow tracking
    - HTML and PDF export
    """

    @staticmethod
    def generate_timeline(
        entity_id: UUID,
        entity_type: str,
        tenant_id: UUID,
        events: list[ChangeEvent],
        corrections: Optional[list[CorrectionFlow]] = None
    ) -> ChangeTimeline:
        """
        Generate a timeline of changes for an entity.

        Args:
            entity_id: Entity to generate timeline for
            entity_type: Type of entity
            tenant_id: Tenant ID
            events: List of change events
            corrections: Optional list of correction flows

        Returns:
            ChangeTimeline with all events
        """
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Find creation and last modified times
        created_at = sorted_events[0].timestamp if sorted_events else datetime.now()
        last_modified = sorted_events[-1].timestamp if sorted_events else datetime.now()

        return ChangeTimeline(
            entity_id=entity_id,
            entity_type=entity_type,
            tenant_id=tenant_id,
            events=sorted_events,
            corrections=corrections or [],
            created_at=created_at,
            last_modified=last_modified,
            total_changes=len(sorted_events)
        )

    @staticmethod
    def generate_diff(
        before: dict[str, Any],
        after: dict[str, Any],
        include_unchanged: bool = False
    ) -> list[Diff]:
        """
        Generate diff between two states.

        Args:
            before: Previous state
            after: New state
            include_unchanged: Whether to include unchanged fields

        Returns:
            List of differences
        """
        diffs: list[Diff] = []

        # Get all keys from both states
        all_keys = set(before.keys()) | set(after.keys())

        for key in all_keys:
            before_value = before.get(key)
            after_value = after.get(key)

            # Skip internal/system fields
            if key.startswith('_') or key in ['id', 'created_at', 'updated_at']:
                continue

            # Determine diff type
            if key not in before:
                # Field added
                diffs.append(Diff(
                    field=key,
                    diff_type=DiffType.ADDED,
                    old_value=None,
                    new_value=after_value
                ))
            elif key not in after:
                # Field removed
                diffs.append(Diff(
                    field=key,
                    diff_type=DiffType.REMOVED,
                    old_value=before_value,
                    new_value=None
                ))
            elif before_value != after_value:
                # Field modified
                change_pct = None
                # Calculate percentage change for numeric values
                if isinstance(before_value, (int, float, Decimal)) and isinstance(after_value, (int, float, Decimal)):
                    if before_value != 0:
                        change_pct = ((Decimal(str(after_value)) - Decimal(str(before_value))) / Decimal(str(before_value))) * 100

                diffs.append(Diff(
                    field=key,
                    diff_type=DiffType.MODIFIED,
                    old_value=before_value,
                    new_value=after_value,
                    change_percentage=change_pct
                ))
            elif include_unchanged:
                # Field unchanged
                diffs.append(Diff(
                    field=key,
                    diff_type=DiffType.UNCHANGED,
                    old_value=before_value,
                    new_value=after_value
                ))

        return diffs

    @staticmethod
    def trace_corrections(
        entry_id: UUID,
        all_events: list[ChangeEvent],
        ledger_entries: Optional[list[dict[str, Any]]] = None
    ) -> CorrectionFlow:
        """
        Trace a correction flow from original through reversal to correction.

        Args:
            entry_id: ID of entry to trace
            all_events: All change events
            ledger_entries: Optional ledger entry data

        Returns:
            CorrectionFlow tracking the correction
        """
        # Find the original event
        original_event = next((e for e in all_events if e.entity_id == entry_id), None)
        if not original_event:
            raise ValueError(f"Entry {entry_id} not found in events")

        flow = CorrectionFlow(
            flow_id=original_event.event_id,
            original_entry_id=entry_id,
            original_timestamp=original_event.timestamp,
            original_state=original_event.after_state
        )

        # Look for reversing entry
        if ledger_entries:
            original_state = original_event.after_state

            # Find reversal (entry that reverses this one)
            for entry in ledger_entries:
                if entry.get('reverses_entry_id') == entry_id:
                    # Found the reversing entry
                    reversing_event = next((e for e in all_events if e.entity_id == entry.get('id')), None)
                    if reversing_event:
                        flow.reversing_entry_id = entry.get('id')
                        flow.reversing_timestamp = reversing_event.timestamp
                        flow.reversing_state = reversing_event.after_state

            # If there's a reversing entry, look for the correction
            if flow.reversing_entry_id:
                # Correction is typically created around the same time as reversal
                # and has similar characteristics but corrected values
                reversal_time = flow.reversing_timestamp
                if reversal_time:
                    # Look for entries created shortly after reversal
                    potential_corrections = [
                        e for e in all_events
                        if e.timestamp >= reversal_time
                        and e.entity_id != entry_id
                        and e.entity_id != flow.reversing_entry_id
                        and e.entity_type == original_event.entity_type
                    ]

                    # Take the first one as the correction
                    # (In practice, you might have more sophisticated logic)
                    if potential_corrections:
                        correction_event = potential_corrections[0]
                        flow.correction_entry_id = correction_event.entity_id
                        flow.correction_timestamp = correction_event.timestamp
                        flow.correction_state = correction_event.after_state
                        flow.is_complete = True

        return flow

    @staticmethod
    def export_to_html(
        timeline: ChangeTimeline,
        include_corrections: bool = True
    ) -> str:
        """
        Export timeline to HTML format.

        Args:
            timeline: Timeline to export
            include_corrections: Whether to include correction flows

        Returns:
            HTML string
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Change History - {timeline.entity_type} {timeline.entity_id}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #366092;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .timeline {{
            position: relative;
            padding-left: 40px;
        }}
        .event {{
            background: white;
            border-left: 3px solid #366092;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .event-header {{
            font-weight: bold;
            color: #366092;
            margin-bottom: 10px;
        }}
        .event-time {{
            color: #666;
            font-size: 0.9em;
        }}
        .diff {{
            margin-top: 10px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 3px;
        }}
        .diff-added {{ color: #28a745; }}
        .diff-removed {{ color: #dc3545; }}
        .diff-modified {{ color: #ffc107; }}
        .correction-flow {{
            background-color: #fff3cd;
            border-left: 3px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .correction-title {{
            font-weight: bold;
            color: #856404;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Change History</h1>
        <p><strong>Entity:</strong> {timeline.entity_type} ({timeline.entity_id})</p>
        <p><strong>Created:</strong> {timeline.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Last Modified:</strong> {timeline.last_modified.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Changes:</strong> {timeline.total_changes}</p>
    </div>
"""

        # Add correction flows if requested
        if include_corrections and timeline.corrections:
            html += "<h2>Correction Flows</h2>\n"
            for correction in timeline.corrections:
                html += f"""
    <div class="correction-flow">
        <div class="correction-title">Correction Flow</div>
        <p><strong>Original Entry:</strong> {correction.original_entry_id}</p>
        <p><strong>Created:</strong> {correction.original_timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
                if correction.reversing_entry_id:
                    html += f"""
        <p><strong>Reversed By:</strong> {correction.reversing_entry_id}</p>
        <p><strong>Reversed:</strong> {correction.reversing_timestamp.strftime('%Y-%m-%d %H:%M:%S') if correction.reversing_timestamp else 'N/A'}</p>
"""
                if correction.correction_entry_id:
                    html += f"""
        <p><strong>Corrected By:</strong> {correction.correction_entry_id}</p>
        <p><strong>Corrected:</strong> {correction.correction_timestamp.strftime('%Y-%m-%d %H:%M:%S') if correction.correction_timestamp else 'N/A'}</p>
"""
                html += f"""
        <p><strong>Status:</strong> {'Complete' if correction.is_complete else 'In Progress'}</p>
    </div>
"""

        # Add timeline
        html += "<h2>Timeline</h2>\n<div class=\"timeline\">\n"

        for event in timeline.events:
            html += f"""
    <div class="event">
        <div class="event-header">{event.event_type.upper()}</div>
        <div class="event-time">{event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</div>
"""
            if event.changed_by:
                html += f"        <p><strong>By:</strong> {event.changed_by}</p>\n"

            # Show diffs if available
            if event.diffs:
                html += "        <div class=\"diff\">\n"
                html += "            <strong>Changes:</strong><ul>\n"
                for diff in event.diffs:
                    css_class = f"diff-{diff.diff_type.value}"
                    if diff.diff_type == DiffType.ADDED:
                        html += f"            <li class=\"{css_class}\">{diff.field}: Added = {diff.new_value}</li>\n"
                    elif diff.diff_type == DiffType.REMOVED:
                        html += f"            <li class=\"{css_class}\">{diff.field}: Removed (was {diff.old_value})</li>\n"
                    elif diff.diff_type == DiffType.MODIFIED:
                        change_info = ""
                        if diff.change_percentage:
                            change_info = f" ({diff.change_percentage:+.1f}%)"
                        html += f"            <li class=\"{css_class}\">{diff.field}: {diff.old_value} → {diff.new_value}{change_info}</li>\n"
                html += "            </ul>\n        </div>\n"

            html += "    </div>\n"

        html += """
</div>
</body>
</html>
"""
        return html

    @staticmethod
    def export_to_pdf(
        timeline: ChangeTimeline,
        filepath: str,
        include_corrections: bool = True
    ) -> None:
        """
        Export timeline to PDF format.

        Args:
            timeline: Timeline to export
            filepath: Output file path
            include_corrections: Whether to include correction flows
        """
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#366092'),
            spaceAfter=12
        )
        elements.append(Paragraph("Change History", title_style))
        elements.append(Spacer(1, 0.2*inch))

        # Entity info
        info_style = styles['Normal']
        elements.append(Paragraph(f"<b>Entity:</b> {timeline.entity_type} ({timeline.entity_id})", info_style))
        elements.append(Paragraph(f"<b>Created:</b> {timeline.created_at.strftime('%Y-%m-%d %H:%M:%S')}", info_style))
        elements.append(Paragraph(f"<b>Last Modified:</b> {timeline.last_modified.strftime('%Y-%m-%d %H:%M:%S')}", info_style))
        elements.append(Paragraph(f"<b>Total Changes:</b> {timeline.total_changes}", info_style))
        elements.append(Spacer(1, 0.3*inch))

        # Correction flows
        if include_corrections and timeline.corrections:
            elements.append(Paragraph("<b>Correction Flows</b>", styles['Heading2']))
            elements.append(Spacer(1, 0.1*inch))

            for correction in timeline.corrections:
                correction_data = [
                    ["Original Entry", str(correction.original_entry_id)],
                    ["Created", correction.original_timestamp.strftime('%Y-%m-%d %H:%M:%S')],
                ]
                if correction.reversing_entry_id:
                    correction_data.append(["Reversed By", str(correction.reversing_entry_id)])
                    if correction.reversing_timestamp:
                        correction_data.append(["Reversed", correction.reversing_timestamp.strftime('%Y-%m-%d %H:%M:%S')])
                if correction.correction_entry_id:
                    correction_data.append(["Corrected By", str(correction.correction_entry_id)])
                    if correction.correction_timestamp:
                        correction_data.append(["Corrected", correction.correction_timestamp.strftime('%Y-%m-%d %H:%M:%S')])
                correction_data.append(["Status", "Complete" if correction.is_complete else "In Progress"])

                table = Table(correction_data, colWidths=[2*inch, 4.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFF3CD')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elements.append(table)
                elements.append(Spacer(1, 0.2*inch))

        # Timeline
        elements.append(Paragraph("<b>Timeline</b>", styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))

        for event in timeline.events:
            # Event header
            event_title = f"<b>{event.event_type.upper()}</b> - {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            if event.changed_by:
                event_title += f" by {event.changed_by}"
            elements.append(Paragraph(event_title, info_style))

            # Diffs
            if event.diffs:
                diff_data = [["Field", "Change"]]
                for diff in event.diffs:
                    if diff.diff_type == DiffType.ADDED:
                        change = f"Added: {diff.new_value}"
                    elif diff.diff_type == DiffType.REMOVED:
                        change = f"Removed (was {diff.old_value})"
                    elif diff.diff_type == DiffType.MODIFIED:
                        change_info = ""
                        if diff.change_percentage:
                            change_info = f" ({diff.change_percentage:+.1f}%)"
                        change = f"{diff.old_value} → {diff.new_value}{change_info}"
                    else:
                        continue

                    diff_data.append([diff.field, change])

                if len(diff_data) > 1:
                    diff_table = Table(diff_data, colWidths=[1.5*inch, 5*inch])
                    diff_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    elements.append(diff_table)

            elements.append(Spacer(1, 0.2*inch))

        # Build PDF
        doc.build(elements)
