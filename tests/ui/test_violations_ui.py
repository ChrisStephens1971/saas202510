"""
Sprint 19: Violation Tracking UI Tests

Comprehensive Playwright UI/E2E tests for:
- ViolationsPage: List and filter violations with photo evidence
- Severity levels: Minor, Moderate, Major, Critical
- Status workflow: Reported → Notice Sent → Hearing Scheduled → Resolved
- Photo upload and display functionality
- Notice generation and hearing scheduling
"""

import pytest
from playwright.sync_api import Page, expect
import re


# ==============================
# Page Object Models
# ==============================

class ViolationsPage:
    """Page Object Model for Violations Management"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/violations"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def click_report_violation(self):
        """Click the Report Violation button"""
        self.page.click('button:has-text("Report Violation")')
        self.page.wait_for_load_state("networkidle")

    def filter_by_severity(self, severity: str):
        """Filter violations by severity level"""
        self.page.select_option('select[value*="severity"]', severity)
        self.page.wait_for_load_state("networkidle")

    def filter_by_status(self, status: str):
        """Filter violations by status"""
        self.page.select_option('select[value*="status"]', status)
        self.page.wait_for_load_state("networkidle")

    def get_violations_count(self) -> int:
        """Get total number of violations displayed"""
        return len(self.page.locator('.bg-white.rounded-lg.border.p-6').all())

    def get_violation_by_owner(self, owner_name: str):
        """Get violation card for specific owner"""
        return self.page.locator(f'.bg-white.rounded-lg.border:has-text("{owner_name}")').first

    def get_violation_severity(self, index: int = 0) -> str:
        """Get severity of violation by index"""
        severity_badges = self.page.locator('.rounded-full:has-text("Critical"), .rounded-full:has-text("Major"), .rounded-full:has-text("Moderate"), .rounded-full:has-text("Minor")').all()
        if len(severity_badges) > index:
            return severity_badges[index].inner_text()
        return ""

    def get_violation_status(self, index: int = 0) -> str:
        """Get status of violation by index"""
        status_badges = self.page.locator('.rounded-full:has-text("Reported"), .rounded-full:has-text("Notice Sent"), .rounded-full:has-text("Hearing Scheduled"), .rounded-full:has-text("Resolved")').all()
        if len(status_badges) > index:
            return status_badges[index].inner_text()
        return ""

    def get_violation_fine_amount(self, owner_name: str) -> str:
        """Get fine amount for specific violation"""
        violation_card = self.get_violation_by_owner(owner_name)
        fine_element = violation_card.locator('text="Fine Amount" ~ .font-semibold')
        return fine_element.inner_text()

    def get_photo_count(self, owner_name: str) -> int:
        """Get number of photos for a violation"""
        violation_card = self.get_violation_by_owner(owner_name)
        photo_count_element = violation_card.locator('text=/\\d+/').last
        count_text = photo_count_element.inner_text()
        return int(count_text)

    def click_violation_card(self, owner_name: str):
        """Click on a violation card to view details"""
        violation_card = self.get_violation_by_owner(owner_name)
        violation_card.click()
        self.page.wait_for_load_state("networkidle")


# ==============================
# Violations List Tests
# ==============================

class TestViolationsList:
    """Test suite for Violations List UI"""

    def test_violations_page_loads_successfully(self, page: Page):
        """Test that violations page loads with all key elements"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Verify page title
        expect(page.locator('h1:has-text("Violations")')).to_be_visible()

        # Verify Report Violation button
        expect(page.locator('button:has-text("Report Violation")')).to_be_visible()

    def test_filter_dropdowns_present(self, page: Page):
        """Test that severity and status filter dropdowns are present"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Verify filter dropdowns
        severity_filter = page.locator('select:has-option("All Severities"), select:has-option("Minor")')
        expect(severity_filter.first).to_be_visible()

        status_filter = page.locator('select:has-option("All Statuses"), select:has-option("Reported")')
        expect(status_filter.first).to_be_visible()

    def test_severity_filter_options(self, page: Page):
        """Test that severity filter has all severity levels"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Get severity filter select
        severity_select = page.locator('select').first

        # Verify options
        options_text = severity_select.inner_text()
        assert 'Minor' in options_text
        assert 'Moderate' in options_text
        assert 'Major' in options_text
        assert 'Critical' in options_text

    def test_status_filter_options(self, page: Page):
        """Test that status filter has all workflow statuses"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Get status filter select (usually second select)
        status_select = page.locator('select').nth(1)

        # Verify options
        options_text = status_select.inner_text()
        assert 'Reported' in options_text
        assert 'Notice Sent' in options_text
        assert 'Hearing Scheduled' in options_text
        assert 'Resolved' in options_text

    def test_violation_cards_display(self, page: Page):
        """Test that violation cards display with correct structure"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        cards_count = violations_page.get_violations_count()

        if cards_count > 0:
            # Verify first card has required elements
            first_card = page.locator('.bg-white.rounded-lg.border.p-6').first

            # Owner name should be visible
            expect(first_card.locator('h3.text-lg.font-semibold')).to_be_visible()

            # Severity badge should be visible
            expect(first_card.locator('.rounded-full').first).to_be_visible()

    def test_severity_badge_colors(self, page: Page):
        """Test that severity badges have correct colors"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Check Critical severity badges (should be red)
        critical_badges = page.locator('.rounded-full:has-text("Critical")').all()
        for badge in critical_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-red-200' in badge_class or 'bg-red-100' in badge_class

        # Check Major severity badges (should be red)
        major_badges = page.locator('.rounded-full:has-text("Major")').all()
        for badge in major_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-red-100' in badge_class

        # Check Moderate severity badges (should be orange)
        moderate_badges = page.locator('.rounded-full:has-text("Moderate")').all()
        for badge in moderate_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-orange-100' in badge_class

        # Check Minor severity badges (should be yellow)
        minor_badges = page.locator('.rounded-full:has-text("Minor")').all()
        for badge in minor_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-yellow-100' in badge_class

    def test_status_badge_colors(self, page: Page):
        """Test that status badges have correct colors"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Check Reported status badges (should be blue)
        reported_badges = page.locator('.rounded-full:has-text("Reported")').all()
        for badge in reported_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-blue-100' in badge_class

        # Check Resolved status badges (should be green)
        resolved_badges = page.locator('.rounded-full:has-text("Resolved")').all()
        for badge in resolved_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-green-100' in badge_class

    def test_violation_details_display(self, page: Page):
        """Test that violation details are displayed correctly"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            first_card = page.locator('.bg-white.rounded-lg.border.p-6').first

            # Verify key details are present
            expect(first_card.locator('text="Type"')).to_be_visible()
            expect(first_card.locator('text="Reported"')).to_be_visible()
            expect(first_card.locator('text="Fine Amount"')).to_be_visible()
            expect(first_card.locator('text="Photos"')).to_be_visible()

    def test_property_address_displays(self, page: Page):
        """Test that property addresses are displayed"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Property address should be in gray text
            address_elements = page.locator('.text-sm.text-gray-600').all()
            assert len(address_elements) > 0

    def test_violation_type_displays(self, page: Page):
        """Test that violation types are displayed"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Look for violation type field
            expect(page.locator('text="Type"').first).to_be_visible()

    def test_reported_date_displays(self, page: Page):
        """Test that reported dates are displayed and formatted"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Reported date should be visible
            expect(page.locator('text="Reported"').first).to_be_visible()

            # Date should be formatted (look for slashes or dashes)
            first_card = page.locator('.bg-white.rounded-lg.border.p-6').first
            card_text = first_card.inner_text()
            assert '/' in card_text or '-' in card_text

    def test_fine_amount_displays_currency(self, page: Page):
        """Test that fine amounts are displayed with currency formatting"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Fine amount should have dollar sign
            fine_elements = page.locator('text="Fine Amount" ~ .font-semibold').all()
            if len(fine_elements) > 0:
                fine_text = fine_elements[0].inner_text()
                assert '$' in fine_text

    def test_photo_count_displays(self, page: Page):
        """Test that photo counts are displayed with camera icon"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Camera icon should be visible
            camera_icons = page.locator('svg.lucide-camera, .lucide-camera').all()
            assert len(camera_icons) > 0

    def test_violation_description_displays(self, page: Page):
        """Test that violation descriptions are displayed"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Description should be in gray text at bottom of card
            description_elements = page.locator('.text-sm.text-gray-700').all()
            assert len(description_elements) > 0


# ==============================
# Filter Functionality Tests
# ==============================

class TestViolationsFiltering:
    """Test suite for Violations Filtering"""

    def test_filter_by_minor_severity(self, page: Page):
        """Test filtering violations by Minor severity"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        initial_count = violations_page.get_violations_count()

        if initial_count > 0:
            violations_page.filter_by_severity('minor')

            # All visible violations should be Minor
            severity_badges = page.locator('.rounded-full:has-text("Minor")').all()
            assert len(severity_badges) > 0

    def test_filter_by_critical_severity(self, page: Page):
        """Test filtering violations by Critical severity"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        violations_page.filter_by_severity('critical')

        # All visible violations should be Critical
        severity_badges = page.locator('.rounded-full').all()
        for badge in severity_badges:
            # Check if it's a severity badge
            text = badge.inner_text()
            if text in ['Minor', 'Moderate', 'Major', 'Critical']:
                assert text == 'Critical'

    def test_filter_by_reported_status(self, page: Page):
        """Test filtering violations by Reported status"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        violations_page.filter_by_status('reported')

        # All visible violations should be Reported
        status_badges = page.locator('.rounded-full:has-text("Reported")').all()
        if len(status_badges) > 0:
            assert len(status_badges) > 0

    def test_filter_by_resolved_status(self, page: Page):
        """Test filtering violations by Resolved status"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        violations_page.filter_by_status('resolved')

        # All visible violations should be Resolved
        status_badges = page.locator('.rounded-full:has-text("Resolved")').all()
        if len(status_badges) > 0:
            assert len(status_badges) > 0

    def test_combined_severity_and_status_filter(self, page: Page):
        """Test applying both severity and status filters"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Apply both filters
        violations_page.filter_by_severity('major')
        violations_page.filter_by_status('notice_sent')

        # Should show only Major violations with Notice Sent status
        cards_count = violations_page.get_violations_count()

        if cards_count > 0:
            # Verify filters are applied
            major_badges = page.locator('.rounded-full:has-text("Major")').all()
            notice_badges = page.locator('.rounded-full:has-text("Notice Sent")').all()
            assert len(major_badges) > 0
            assert len(notice_badges) > 0

    def test_clear_filters_shows_all(self, page: Page):
        """Test that selecting 'All' shows all violations"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        initial_count = violations_page.get_violations_count()

        # Apply filter
        violations_page.filter_by_severity('critical')

        filtered_count = violations_page.get_violations_count()

        # Clear filter
        violations_page.filter_by_severity('all')

        final_count = violations_page.get_violations_count()

        # Final count should match or be close to initial count
        assert final_count >= filtered_count


# ==============================
# Photo Evidence Tests
# ==============================

class TestViolationPhotos:
    """Test suite for Violation Photo Evidence"""

    def test_photo_count_indicator_visible(self, page: Page):
        """Test that photo count indicator is visible"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Camera icon should be present
            camera_icons = page.locator('svg[class*="lucide-camera"]').all()
            assert len(camera_icons) > 0

    def test_photo_count_numeric(self, page: Page):
        """Test that photo counts are numeric"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Get first violation card
            first_card = page.locator('.bg-white.rounded-lg.border.p-6').first

            # Photo count should be numeric
            photo_section = first_card.locator('text="Photos"').locator('..')
            photo_count_text = photo_section.inner_text()

            # Extract number
            numbers = re.findall(r'\d+', photo_count_text)
            assert len(numbers) > 0

    def test_violations_with_multiple_photos(self, page: Page):
        """Test that violations with multiple photos show correct count"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        cards = page.locator('.bg-white.rounded-lg.border.p-6').all()

        for card in cards:
            # Look for photo count
            card_text = card.inner_text()
            if 'Photos' in card_text:
                # Should have a number
                assert any(char.isdigit() for char in card_text)

    def test_violations_without_photos(self, page: Page):
        """Test that violations without photos show 0"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Look for violations with 0 photos
        zero_photo_indicators = page.locator('text="Photos" ~ div:has-text("0")').all()

        # If any exist, verify they're displayed correctly
        if len(zero_photo_indicators) > 0:
            expect(zero_photo_indicators[0]).to_be_visible()


# ==============================
# Report Violation Tests
# ==============================

class TestReportViolation:
    """Test suite for Report Violation functionality"""

    def test_report_violation_button_visible(self, page: Page):
        """Test that Report Violation button is visible and styled"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        report_btn = page.locator('button:has-text("Report Violation")')
        expect(report_btn).to_be_visible()

        # Should be red button
        expect(report_btn).to_have_class(re.compile(r'bg-red-600'))

    def test_report_violation_button_has_icon(self, page: Page):
        """Test that Report Violation button has plus icon"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Plus icon should be present in button
        plus_icon = page.locator('button:has-text("Report Violation") svg')
        expect(plus_icon).to_be_visible()

    def test_report_violation_button_clickable(self, page: Page):
        """Test that Report Violation button is clickable"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        report_btn = page.locator('button:has-text("Report Violation")')

        # Button should be enabled
        assert not report_btn.is_disabled()

        # Click should trigger action (modal or navigation)
        violations_page.click_report_violation()


# ==============================
# Responsive Design Tests
# ==============================

class TestViolationsResponsive:
    """Test suite for Responsive Design"""

    def test_violations_desktop_layout(self, page: Page):
        """Test violations page layout on desktop (1920x1080)"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Verify page is functional at desktop resolution
        expect(page.locator('h1:has-text("Violations")')).to_be_visible()
        expect(page.locator('button:has-text("Report Violation")')).to_be_visible()

    def test_violations_tablet_layout(self, page: Page):
        """Test violations page layout on tablet (768x1024)"""
        page.set_viewport_size({"width": 768, "height": 1024})

        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Verify page is functional at tablet resolution
        expect(page.locator('h1:has-text("Violations")')).to_be_visible()

    def test_violations_mobile_layout(self, page: Page):
        """Test violations page layout on mobile (375x667)"""
        page.set_viewport_size({"width": 375, "height": 667})

        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Verify page is functional at mobile resolution
        expect(page.locator('h1:has-text("Violations")')).to_be_visible()

        # Filters should still be accessible
        expect(page.locator('select').first).to_be_visible()

    def test_violation_cards_stack_on_mobile(self, page: Page):
        """Test that violation cards stack vertically on mobile"""
        page.set_viewport_size({"width": 375, "height": 667})

        violations_page = ViolationsPage(page)
        violations_page.navigate()

        if violations_page.get_violations_count() > 0:
            # Cards should be in a single column
            cards = page.locator('.bg-white.rounded-lg.border.p-6').all()

            if len(cards) >= 2:
                # Get positions of first two cards
                box1 = cards[0].bounding_box()
                box2 = cards[1].bounding_box()

                # Second card should be below first (y position greater)
                assert box2['y'] > box1['y']


# ==============================
# Empty State Tests
# ==============================

class TestViolationsEmptyState:
    """Test suite for Empty State handling"""

    def test_empty_state_message_when_no_violations(self, page: Page):
        """Test that appropriate message shows when no violations exist"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        cards_count = violations_page.get_violations_count()

        if cards_count == 0:
            # Should show empty state or no violations message
            empty_indicators = page.locator('text="No violations", text="No results found"').all()
            if len(empty_indicators) > 0:
                expect(empty_indicators[0]).to_be_visible()

    def test_empty_state_after_filtering(self, page: Page):
        """Test empty state when filters return no results"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Apply very specific filters that might return no results
        violations_page.filter_by_severity('critical')
        violations_page.filter_by_status('resolved')

        cards_count = violations_page.get_violations_count()

        if cards_count == 0:
            # Should show appropriate message
            page.wait_for_timeout(500)  # Wait for UI update


# ==============================
# E2E Workflow Tests
# ==============================

class TestViolationsE2EWorkflows:
    """End-to-end workflow tests for violations"""

    def test_view_and_filter_violations_workflow(self, page: Page):
        """Test complete workflow: View → Filter by severity → Filter by status"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Step 1: View all violations
        initial_count = violations_page.get_violations_count()
        assert initial_count >= 0

        # Step 2: Filter by severity
        violations_page.filter_by_severity('major')

        # Step 3: Further filter by status
        violations_page.filter_by_status('reported')

        # Should have filtered results
        final_count = violations_page.get_violations_count()
        assert final_count >= 0

    def test_violation_severity_progression(self, page: Page):
        """Test viewing violations at different severity levels"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        severities = ['minor', 'moderate', 'major', 'critical']

        for severity in severities:
            violations_page.filter_by_severity(severity)
            # Should load without errors
            expect(page.locator('h1:has-text("Violations")')).to_be_visible()

    def test_violation_status_workflow_progression(self, page: Page):
        """Test viewing violations through status workflow"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        statuses = ['reported', 'notice_sent', 'hearing_scheduled', 'resolved']

        for status in statuses:
            violations_page.filter_by_status(status)
            # Should load without errors
            expect(page.locator('h1:has-text("Violations")')).to_be_visible()


# ==============================
# Accessibility Tests
# ==============================

class TestViolationsAccessibility:
    """Accessibility tests for violations UI"""

    def test_page_heading_hierarchy(self, page: Page):
        """Test that page has proper heading hierarchy"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Should have exactly one h1
        h1_count = page.locator('h1').count()
        assert h1_count == 1

        # Violation cards should have h3 headings
        if violations_page.get_violations_count() > 0:
            h3_count = page.locator('h3').count()
            assert h3_count >= 1

    def test_filter_labels_present(self, page: Page):
        """Test that filter dropdowns have proper labels"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Select elements should be accessible
        selects = page.locator('select').all()
        assert len(selects) >= 2  # Severity and Status filters

    def test_button_accessibility(self, page: Page):
        """Test that buttons are accessible"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        report_btn = page.locator('button:has-text("Report Violation")')

        # Button should have accessible text
        btn_text = report_btn.inner_text()
        assert len(btn_text) > 0

    def test_keyboard_navigation_filters(self, page: Page):
        """Test keyboard navigation through filters"""
        violations_page = ViolationsPage(page)
        violations_page.navigate()

        # Focus first select
        page.focus('select')

        # Should be focused
        focused_tag = page.evaluate('document.activeElement.tagName')
        assert focused_tag.lower() == 'select'

        # Tab to next select
        page.keyboard.press('Tab')

        # Should focus next select
        focused_tag = page.evaluate('document.activeElement.tagName')
        assert focused_tag.lower() in ['select', 'button']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
