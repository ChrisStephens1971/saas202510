"""
Frontend/UI Tests for Auditor Export Feature (Sprint 21)

Tests the complete frontend experience for auditor exports including:
- UI components and user interactions
- Form validation and date range selection
- Export generation progress tracking
- Download functionality
- Integrity verification display
- Error handling and user feedback
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import json

from qa_testing.ui_testing import (
    UITestRunner, FormValidator, ComponentTester,
    PageObject, ElementLocator, InteractionSimulator
)
from qa_testing.models import AuditorExport, AuditorExportStatus
from qa_testing.generators import AuditorExportGenerator


class TestAuditorExportPage:
    """Test the Auditor Export page UI components"""

    def test_page_loads_correctly(self):
        """Test that the auditor export page loads with all components"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')

        # Act
        page.load()
        components = page.get_all_components()

        # Assert
        assert page.is_loaded()
        assert page.title == "Auditor Exports"

        # Verify required components
        required_components = [
            'export-list-table',
            'create-export-button',
            'date-range-picker',
            'export-format-selector',
            'evidence-toggle'
        ]

        for component_id in required_components:
            assert page.has_component(component_id)
            assert page.get_component(component_id).is_visible()

    def test_export_list_display(self):
        """Test the display of existing exports in the list"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')

        # Create mock exports
        exports = [
            AuditorExportGenerator.create_mock_export(
                id='exp_001',
                status=AuditorExportStatus.COMPLETED,
                created_date=datetime(2025, 10, 15, 10, 30),
                file_size=2500000
            ),
            AuditorExportGenerator.create_mock_export(
                id='exp_002',
                status=AuditorExportStatus.GENERATING,
                created_date=datetime(2025, 10, 14, 14, 20),
                file_size=None
            ),
            AuditorExportGenerator.create_mock_export(
                id='exp_003',
                status=AuditorExportStatus.FAILED,
                created_date=datetime(2025, 10, 13, 9, 15),
                file_size=None
            )
        ]

        # Act
        page.load()
        export_table = page.get_component('export-list-table')
        export_table.set_data(exports)

        # Assert
        assert export_table.row_count == 3

        # Verify first export (completed)
        row1 = export_table.get_row(0)
        assert row1['status'] == 'Completed'
        assert row1['date'] == '10/15/2025 10:30 AM'
        assert row1['size'] == '2.5 MB'
        assert row1.has_action('download')
        assert row1.has_action('verify')

        # Verify second export (generating)
        row2 = export_table.get_row(1)
        assert row2['status'] == 'Generating...'
        assert row2.has_spinner()
        assert not row2.has_action('download')

        # Verify third export (failed)
        row3 = export_table.get_row(2)
        assert row3['status'] == 'Failed'
        assert row3.has_error_indicator()
        assert row3.has_action('retry')

    def test_create_export_form(self):
        """Test the create export form functionality"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        # Act
        create_button = page.get_component('create-export-button')
        create_button.click()

        form = page.get_component('create-export-form')

        # Assert
        assert form.is_visible()
        assert form.has_field('start_date')
        assert form.has_field('end_date')
        assert form.has_field('export_format')
        assert form.has_field('include_evidence')
        assert form.has_field('email_notification')

        # Test form validation
        validation_errors = form.validate()
        assert 'start_date' in validation_errors  # Required field
        assert 'end_date' in validation_errors    # Required field

        # Fill form with valid data
        form.set_field('start_date', '2025-01-01')
        form.set_field('end_date', '2025-12-31')
        form.set_field('export_format', 'csv')
        form.set_field('include_evidence', True)

        validation_errors = form.validate()
        assert len(validation_errors) == 0

    def test_date_range_picker(self):
        """Test date range picker functionality"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        date_picker = page.get_component('date-range-picker')

        # Act - Test preset ranges
        presets = date_picker.get_preset_options()

        # Assert
        expected_presets = [
            'Current Month',
            'Last Month',
            'Current Quarter',
            'Last Quarter',
            'Current Year',
            'Last Year',
            'Custom Range'
        ]

        for preset in expected_presets:
            assert preset in presets

        # Test selecting preset
        date_picker.select_preset('Current Quarter')
        selected_range = date_picker.get_selected_range()

        # Verify Q4 2025 (Oct-Dec)
        assert selected_range['start'] == date(2025, 10, 1)
        assert selected_range['end'] == date(2025, 12, 31)

        # Test custom range
        date_picker.select_preset('Custom Range')
        date_picker.set_custom_range(
            start=date(2025, 7, 1),
            end=date(2025, 9, 30)
        )

        custom_range = date_picker.get_selected_range()
        assert custom_range['start'] == date(2025, 7, 1)
        assert custom_range['end'] == date(2025, 9, 30)

    def test_export_generation_progress(self):
        """Test export generation progress display"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        # Start export generation
        form = page.get_component('create-export-form')
        form.set_field('start_date', '2025-01-01')
        form.set_field('end_date', '2025-12-31')
        form.submit()

        # Act
        progress_modal = page.get_component('progress-modal')

        # Assert
        assert progress_modal.is_visible()
        assert progress_modal.has_progress_bar()
        assert progress_modal.has_cancel_button()

        # Simulate progress updates
        progress_updates = [
            (10, "Initializing export..."),
            (25, "Gathering journal entries..."),
            (50, "Processing transactions..."),
            (75, "Linking evidence documents..."),
            (90, "Generating CSV file..."),
            (100, "Export complete!")
        ]

        for percentage, message in progress_updates:
            progress_modal.update_progress(percentage, message)
            assert progress_modal.get_progress() == percentage
            assert progress_modal.get_message() == message

        # Verify completion
        assert progress_modal.is_complete()
        assert progress_modal.has_download_button()

    def test_download_functionality(self):
        """Test export download functionality"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        export = AuditorExportGenerator.create_mock_export(
            status=AuditorExportStatus.COMPLETED,
            file_url='https://s3.amazonaws.com/exports/export_123.csv',
            file_size=1500000
        )

        export_table = page.get_component('export-list-table')
        export_table.add_row(export)

        # Act
        download_button = export_table.get_action_button(export.id, 'download')
        download_result = download_button.click()

        # Assert
        assert download_result['initiated'] is True
        assert download_result['file_name'] == 'export_123.csv'
        assert download_result['file_size'] == 1500000

        # Verify download tracking
        assert export.download_count == 1
        assert export.last_downloaded_at is not None
        assert export.last_downloaded_by == 'current_user@hoa.com'

    def test_integrity_verification_display(self):
        """Test display of file integrity verification"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        export = AuditorExportGenerator.create_mock_export(
            status=AuditorExportStatus.COMPLETED,
            file_hash='a1b2c3d4e5f6...'  # Mock SHA-256
        )

        export_table = page.get_component('export-list-table')
        export_table.add_row(export)

        # Act
        verify_button = export_table.get_action_button(export.id, 'verify')
        verify_button.click()

        verification_modal = page.get_component('verification-modal')

        # Assert
        assert verification_modal.is_visible()
        assert verification_modal.get_title() == "File Integrity Verification"

        # Verify hash display
        displayed_hash = verification_modal.get_field('file_hash')
        assert displayed_hash == 'a1b2c3d4e5f6...'

        # Simulate verification
        verification_modal.verify()
        result = verification_modal.get_result()

        assert result['status'] == 'Verified'
        assert result['icon'] == 'checkmark'
        assert result['message'] == 'File integrity verified successfully'

    def test_error_handling_display(self):
        """Test error handling and user feedback"""
        error_scenarios = [
            {
                'error': 'date_range_invalid',
                'message': 'End date must be after start date',
                'field': 'end_date'
            },
            {
                'error': 'date_range_too_large',
                'message': 'Date range cannot exceed 366 days',
                'field': 'date_range'
            },
            {
                'error': 'generation_failed',
                'message': 'Export generation failed. Please try again.',
                'type': 'alert'
            },
            {
                'error': 'download_failed',
                'message': 'Download failed. Please check your connection.',
                'type': 'toast'
            }
        ]

        for scenario in error_scenarios:
            # Arrange
            page = PageObject('/accounting/auditor-exports')
            page.load()

            # Act
            if 'field' in scenario:
                # Form validation error
                form = page.get_component('create-export-form')
                form.trigger_error(scenario['error'])
                error = form.get_field_error(scenario['field'])
            else:
                # Alert or toast error
                page.trigger_error(scenario['error'])
                if scenario['type'] == 'alert':
                    error = page.get_alert()
                else:
                    error = page.get_toast()

            # Assert
            assert error.is_visible()
            assert scenario['message'] in error.get_text()

    def test_export_filtering_and_search(self):
        """Test export list filtering and search functionality"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        # Create diverse exports
        exports = [
            AuditorExportGenerator.create_mock_export(
                status=AuditorExportStatus.COMPLETED,
                date_range='Q1 2025',
                requested_by='auditor@firm1.com'
            ),
            AuditorExportGenerator.create_mock_export(
                status=AuditorExportStatus.COMPLETED,
                date_range='Q2 2025',
                requested_by='cpa@firm2.com'
            ),
            AuditorExportGenerator.create_mock_export(
                status=AuditorExportStatus.GENERATING,
                date_range='Q3 2025',
                requested_by='auditor@firm1.com'
            )
        ]

        export_table = page.get_component('export-list-table')
        export_table.set_data(exports)

        # Act - Test status filter
        status_filter = page.get_component('status-filter')
        status_filter.select('Completed')

        filtered_rows = export_table.get_visible_rows()

        # Assert
        assert len(filtered_rows) == 2
        for row in filtered_rows:
            assert row['status'] == 'Completed'

        # Test search
        search_box = page.get_component('search-box')
        search_box.enter_text('Q2 2025')

        search_results = export_table.get_visible_rows()
        assert len(search_results) == 1
        assert search_results[0]['date_range'] == 'Q2 2025'

    def test_bulk_actions(self):
        """Test bulk actions on multiple exports"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        # Create multiple exports
        exports = [
            AuditorExportGenerator.create_mock_export(id=f'exp_{i}')
            for i in range(5)
        ]

        export_table = page.get_component('export-list-table')
        export_table.set_data(exports)

        # Act - Select multiple exports
        export_table.select_rows([0, 2, 4])

        bulk_actions = page.get_component('bulk-actions')

        # Assert
        assert bulk_actions.is_visible()
        assert bulk_actions.get_selected_count() == 3

        available_actions = bulk_actions.get_available_actions()
        assert 'Download All' in available_actions
        assert 'Delete' in available_actions

        # Test bulk download
        bulk_actions.execute('Download All')
        download_modal = page.get_component('bulk-download-modal')

        assert download_modal.is_visible()
        assert download_modal.get_file_count() == 3
        assert download_modal.has_option('zip')
        assert download_modal.has_option('separate')

    def test_responsive_design(self):
        """Test UI responsiveness on different screen sizes"""
        screen_sizes = [
            ('mobile', 375, 667),
            ('tablet', 768, 1024),
            ('desktop', 1920, 1080)
        ]

        for device, width, height in screen_sizes:
            # Arrange
            page = PageObject('/accounting/auditor-exports')
            page.set_viewport(width, height)

            # Act
            page.load()

            # Assert
            assert page.is_loaded()

            if device == 'mobile':
                # Mobile specific layout
                assert page.has_component('mobile-menu-toggle')
                assert not page.get_component('export-list-table').is_visible()
                assert page.get_component('export-cards').is_visible()
            elif device == 'tablet':
                # Tablet layout
                assert page.get_component('export-list-table').is_visible()
                assert page.get_component('export-list-table').is_responsive()
            else:
                # Desktop layout
                assert page.get_component('export-list-table').is_visible()
                assert page.get_component('sidebar-filters').is_visible()

    def test_accessibility_features(self):
        """Test accessibility features of the UI"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        # Act
        accessibility_check = page.run_accessibility_audit()

        # Assert
        assert accessibility_check['score'] >= 95  # WCAG 2.1 AA compliance

        # Verify specific accessibility features
        assert page.has_aria_labels()
        assert page.has_keyboard_navigation()
        assert page.has_focus_indicators()
        assert page.has_screen_reader_support()

        # Test keyboard navigation
        keyboard = page.get_keyboard_simulator()
        keyboard.press('Tab')  # Focus create button
        assert page.get_focused_element()['id'] == 'create-export-button'

        keyboard.press('Enter')  # Open form
        assert page.get_component('create-export-form').is_visible()

        keyboard.press('Escape')  # Close form
        assert not page.get_component('create-export-form').is_visible()

    def test_real_time_updates(self):
        """Test real-time updates for export generation"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        # Mock WebSocket connection
        websocket = page.create_websocket_mock()

        # Act - Start export generation
        form = page.get_component('create-export-form')
        form.set_field('start_date', '2025-01-01')
        form.set_field('end_date', '2025-12-31')
        export_id = form.submit()

        # Simulate WebSocket updates
        updates = [
            {'export_id': export_id, 'status': 'generating', 'progress': 25},
            {'export_id': export_id, 'status': 'generating', 'progress': 50},
            {'export_id': export_id, 'status': 'generating', 'progress': 75},
            {'export_id': export_id, 'status': 'completed', 'progress': 100}
        ]

        for update in updates:
            websocket.send_message(update)

            # Assert - Verify UI updates
            export_row = page.get_component('export-list-table').get_row(export_id)

            if update['status'] == 'generating':
                assert export_row.has_progress_bar()
                assert export_row.get_progress() == update['progress']
            else:
                assert export_row['status'] == 'Completed'
                assert export_row.has_action('download')


class TestAuditorExportIntegration:
    """Integration tests for auditor export UI with backend"""

    @patch('qa_testing.api.AuditorExportAPI')
    def test_end_to_end_export_workflow(self, mock_api):
        """Test complete workflow from UI to backend"""
        # Arrange
        page = PageObject('/accounting/auditor-exports')
        page.load()

        mock_api.create_export.return_value = {
            'id': 'exp_new',
            'status': 'pending'
        }

        mock_api.generate_export.return_value = {
            'id': 'exp_new',
            'status': 'completed',
            'file_url': 'https://s3.amazonaws.com/exports/new.csv'
        }

        # Act
        # Step 1: Create export
        create_button = page.get_component('create-export-button')
        create_button.click()

        form = page.get_component('create-export-form')
        form.set_field('start_date', '2025-07-01')
        form.set_field('end_date', '2025-09-30')
        form.set_field('include_evidence', True)
        form.submit()

        # Step 2: Wait for generation
        page.wait_for_element('export-row-exp_new')

        # Step 3: Download
        export_row = page.get_component('export-list-table').get_row('exp_new')
        download_button = export_row.get_action('download')
        download_button.click()

        # Assert
        assert mock_api.create_export.called
        assert mock_api.generate_export.called

        call_args = mock_api.create_export.call_args[0][0]
        assert call_args['start_date'] == '2025-07-01'
        assert call_args['end_date'] == '2025-09-30'
        assert call_args['include_evidence'] is True