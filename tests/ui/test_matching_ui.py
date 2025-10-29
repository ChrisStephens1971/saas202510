"""
Sprint 18: Auto-Matching Engine UI Tests

Comprehensive Playwright UI/E2E tests for:
- TransactionMatchingPage: Review AI match suggestions with confidence scores
- MatchRulesPage: Manage auto-match rules and accuracy tracking
- MatchStatisticsPage: Performance dashboard (auto-match rate, confidence)
"""

import pytest
from playwright.sync_api import Page, expect
import re


# ==============================
# Page Object Models
# ==============================

class TransactionMatchingPage:
    """Page Object Model for Transaction Matching Review"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/matching/transactions"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def get_pending_matches_count(self) -> int:
        """Get count of pending matches from summary card"""
        pending_text = self.page.locator('text="Pending Matches" ~ div').first.inner_text()
        return int(pending_text.strip())

    def get_accepted_matches_count(self) -> int:
        """Get count of accepted matches from summary card"""
        accepted_text = self.page.locator('text="Accepted" ~ div').first.inner_text()
        return int(accepted_text.strip())

    def accept_match(self, index: int = 0):
        """Accept a match by index (0-based)"""
        accept_buttons = self.page.locator('button[title="Accept Match"]').all()
        if len(accept_buttons) > index:
            accept_buttons[index].click()
            self.page.wait_for_load_state("networkidle")

    def reject_match(self, index: int = 0):
        """Reject a match by index (0-based)"""
        reject_buttons = self.page.locator('button[title="Reject Match"]').all()
        if len(reject_buttons) > index:
            reject_buttons[index].click()
            self.page.wait_for_load_state("networkidle")

    def get_match_confidence(self, index: int = 0) -> int:
        """Get confidence score for a match"""
        confidence_badges = self.page.locator('text=/\\d+% Confidence/').all()
        if len(confidence_badges) > index:
            text = confidence_badges[index].inner_text()
            return int(text.replace('% Confidence', ''))
        return 0

    def get_match_cards_count(self) -> int:
        """Get total number of match cards displayed"""
        return len(self.page.locator('.bg-white.rounded-lg.border.p-6').all())

    def get_match_explanation(self, index: int = 0) -> str:
        """Get explanation text for a match"""
        explanations = self.page.locator('.bg-gray-50.rounded .text-sm.text-gray-700').all()
        if len(explanations) > index:
            return explanations[index].inner_text()
        return ""

    def get_bank_transaction_description(self, index: int = 0) -> str:
        """Get bank transaction description for a match"""
        descriptions = self.page.locator('text="Bank Transaction" ~ .font-semibold').all()
        if len(descriptions) > index:
            return descriptions[index].inner_text()
        return ""

    def get_matched_entry_reference(self, index: int = 0) -> str:
        """Get matched entry reference for a match"""
        references = self.page.locator('text="Matched Entry" ~ .font-semibold').all()
        if len(references) > index:
            return references[index].inner_text()
        return ""


class MatchRulesPage:
    """Page Object Model for Match Rules Management"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/matching/rules"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def click_add_rule(self):
        """Click the Add Rule button"""
        self.page.click('button:has-text("Add Rule")')
        self.page.wait_for_load_state("networkidle")

    def get_rules_count(self) -> int:
        """Get total number of rules displayed"""
        rows = self.page.locator('tbody tr').all()
        # Filter out "no rules" message row
        return len([r for r in rows if 'No rules configured' not in r.inner_text()])

    def get_rule_accuracy(self, rule_name: str) -> str:
        """Get accuracy percentage for a specific rule"""
        row = self.page.locator(f'tr:has-text("{rule_name}")').first
        accuracy_cell = row.locator('td').nth(2)
        return accuracy_cell.inner_text()

    def toggle_rule_status(self, rule_name: str):
        """Toggle active/inactive status for a rule"""
        row = self.page.locator(f'tr:has-text("{rule_name}")').first
        toggle_button = row.locator('button:has-text("Toggle")')
        toggle_button.click()
        self.page.wait_for_load_state("networkidle")


class MatchStatisticsPage:
    """Page Object Model for Match Statistics Dashboard"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/matching/statistics"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def get_auto_match_rate(self) -> str:
        """Get the auto-match rate percentage"""
        return self.page.locator('text="Auto-Match Rate" ~ .text-2xl').inner_text()

    def get_avg_confidence(self) -> str:
        """Get the average confidence score"""
        return self.page.locator('text="Avg Confidence" ~ .text-2xl').inner_text()

    def get_total_matches(self) -> str:
        """Get total matches processed"""
        return self.page.locator('text="Total Matches" ~ .text-2xl').inner_text()

    def get_manual_reviews(self) -> str:
        """Get count of manual reviews needed"""
        return self.page.locator('text="Manual Reviews" ~ .text-2xl').inner_text()

    def select_time_period(self, period: str):
        """Select time period filter (last_7_days, last_30_days, etc.)"""
        self.page.select_option('select', period)
        self.page.wait_for_load_state("networkidle")


# ==============================
# Transaction Matching Tests
# ==============================

class TestTransactionMatching:
    """Test suite for Transaction Matching Review UI"""

    def test_matching_page_loads_successfully(self, page: Page):
        """Test that the matching page loads with all key elements"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        # Verify page title and icon
        expect(page.locator('h1:has-text("Transaction Matching")')).to_be_visible()
        expect(page.locator('p:has-text("Review AI-powered match suggestions")')).to_be_visible()

    def test_summary_cards_display(self, page: Page):
        """Test that summary cards show pending and accepted counts"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        # Verify summary cards are visible
        expect(page.locator('text="Pending Matches"')).to_be_visible()
        expect(page.locator('text="Accepted"')).to_be_visible()

        # Get counts (should be numeric)
        pending_count = matching_page.get_pending_matches_count()
        accepted_count = matching_page.get_accepted_matches_count()

        assert pending_count >= 0
        assert accepted_count >= 0

    def test_match_cards_display_correctly(self, page: Page):
        """Test that match cards show all required information"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        cards_count = matching_page.get_match_cards_count()

        if cards_count > 0:
            # Verify first card has all elements
            expect(page.locator('text=/\\d+% Confidence/').first).to_be_visible()
            expect(page.locator('text="Bank Transaction"').first).to_be_visible()
            expect(page.locator('text="Matched Entry"').first).to_be_visible()

    def test_confidence_score_badge_colors(self, page: Page):
        """Test that confidence score badges have correct colors based on score"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        confidence_badges = page.locator('text=/\\d+% Confidence/').all()

        for badge in confidence_badges:
            text = badge.inner_text()
            score = int(text.replace('% Confidence', ''))

            badge_class = badge.get_attribute('class')

            # High confidence (90+) should be green
            if score >= 90:
                assert 'bg-green-100' in badge_class
                assert 'text-green-800' in badge_class
            # Medium confidence (70-89) should be yellow
            elif score >= 70:
                assert 'bg-yellow-100' in badge_class
                assert 'text-yellow-800' in badge_class
            # Low confidence (<70) should be orange
            else:
                assert 'bg-orange-100' in badge_class
                assert 'text-orange-800' in badge_class

    def test_accept_match_functionality(self, page: Page):
        """Test accepting a match suggestion"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        pending_before = matching_page.get_pending_matches_count()
        accepted_before = matching_page.get_accepted_matches_count()

        if pending_before > 0:
            # Accept the first match
            matching_page.accept_match(0)

            # Verify counts updated
            pending_after = matching_page.get_pending_matches_count()
            accepted_after = matching_page.get_accepted_matches_count()

            assert pending_after == pending_before - 1
            assert accepted_after == accepted_before + 1

    def test_reject_match_functionality(self, page: Page):
        """Test rejecting a match suggestion"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        pending_before = matching_page.get_pending_matches_count()

        if pending_before > 0:
            # Reject the first match
            matching_page.reject_match(0)

            # Verify pending count decreased
            pending_after = matching_page.get_pending_matches_count()
            assert pending_after == pending_before - 1

    def test_match_explanation_displays(self, page: Page):
        """Test that match explanations are shown"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 0:
            explanation = matching_page.get_match_explanation(0)
            assert len(explanation) > 0
            assert explanation != ""

    def test_bank_transaction_details_display(self, page: Page):
        """Test that bank transaction details are displayed"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 0:
            bank_desc = matching_page.get_bank_transaction_description(0)
            assert len(bank_desc) > 0

    def test_matched_entry_details_display(self, page: Page):
        """Test that matched entry details are displayed"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 0:
            entry_ref = matching_page.get_matched_entry_reference(0)
            assert len(entry_ref) > 0

    def test_empty_state_displays(self, page: Page):
        """Test that empty state shows when no pending matches"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        pending_count = matching_page.get_pending_matches_count()

        if pending_count == 0:
            expect(page.locator('text="No pending matches"')).to_be_visible()
            expect(page.locator('text="All transactions have been reviewed!"')).to_be_visible()

    def test_action_buttons_visible_and_styled(self, page: Page):
        """Test that accept/reject buttons are visible and properly styled"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 0:
            # Accept button should be green
            accept_btn = page.locator('button[title="Accept Match"]').first
            expect(accept_btn).to_be_visible()
            expect(accept_btn).to_have_class(re.compile(r'bg-green-600'))

            # Reject button should be red
            reject_btn = page.locator('button[title="Reject Match"]').first
            expect(reject_btn).to_be_visible()
            expect(reject_btn).to_have_class(re.compile(r'bg-red-600'))

    def test_responsive_layout_desktop(self, page: Page):
        """Test matching page layout on desktop"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        # Verify page is functional at desktop resolution
        expect(page.locator('h1:has-text("Transaction Matching")')).to_be_visible()

    def test_responsive_layout_mobile(self, page: Page):
        """Test matching page layout on mobile"""
        page.set_viewport_size({"width": 375, "height": 667})

        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        # Verify page is functional at mobile resolution
        expect(page.locator('h1:has-text("Transaction Matching")')).to_be_visible()

    def test_match_cards_scrollable(self, page: Page):
        """Test that match cards are scrollable when many exist"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 5:
            # Page should be scrollable
            scroll_height = page.evaluate('document.documentElement.scrollHeight')
            viewport_height = page.evaluate('window.innerHeight')
            assert scroll_height > viewport_height

    def test_confidence_score_numerical_accuracy(self, page: Page):
        """Test that confidence scores are valid numbers (0-100)"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        cards_count = matching_page.get_match_cards_count()

        for i in range(cards_count):
            confidence = matching_page.get_match_confidence(i)
            assert 0 <= confidence <= 100

    def test_button_hover_states(self, page: Page):
        """Test that buttons show hover states"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 0:
            accept_btn = page.locator('button[title="Accept Match"]').first

            # Hover over button
            accept_btn.hover()

            # Check for hover class
            expect(accept_btn).to_have_class(re.compile(r'hover:bg-green-700'))


# ==============================
# Match Rules Tests
# ==============================

class TestMatchRules:
    """Test suite for Match Rules Management UI"""

    def test_match_rules_page_loads(self, page: Page):
        """Test that match rules page loads successfully"""
        rules_page = MatchRulesPage(page)
        rules_page.navigate()

        expect(page.locator('h1:has-text("Match Rules")')).to_be_visible()

    def test_add_rule_button_visible(self, page: Page):
        """Test that Add Rule button is visible"""
        rules_page = MatchRulesPage(page)
        rules_page.navigate()

        expect(page.locator('button:has-text("Add Rule")')).to_be_visible()

    def test_rules_table_displays(self, page: Page):
        """Test that rules table displays with correct columns"""
        rules_page = MatchRulesPage(page)
        rules_page.navigate()

        # Verify table headers
        expect(page.locator('th:has-text("Rule Name")')).to_be_visible()
        expect(page.locator('th:has-text("Type")')).to_be_visible()
        expect(page.locator('th:has-text("Accuracy")')).to_be_visible()
        expect(page.locator('th:has-text("Status")')).to_be_visible()

    def test_rule_accuracy_displays(self, page: Page):
        """Test that rule accuracy percentages display"""
        rules_page = MatchRulesPage(page)
        rules_page.navigate()

        rules_count = rules_page.get_rules_count()

        if rules_count > 0:
            # Check for accuracy percentages
            accuracy_cells = page.locator('td:has-text("%")').all()
            assert len(accuracy_cells) > 0

    def test_rule_status_badge_colors(self, page: Page):
        """Test that active/inactive status badges have correct colors"""
        rules_page = MatchRulesPage(page)
        rules_page.navigate()

        # Active badges should be green
        active_badges = page.locator('.rounded-full:has-text("Active")').all()
        for badge in active_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-green-100' in badge_class
            assert 'text-green-800' in badge_class

        # Inactive badges should be gray
        inactive_badges = page.locator('.rounded-full:has-text("Inactive")').all()
        for badge in inactive_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-gray-100' in badge_class

    def test_empty_state_message(self, page: Page):
        """Test that empty state shows when no rules exist"""
        rules_page = MatchRulesPage(page)
        rules_page.navigate()

        rules_count = rules_page.get_rules_count()

        if rules_count == 0:
            expect(page.locator('text="No rules configured"')).to_be_visible()

    def test_rule_types_display(self, page: Page):
        """Test that different rule types are displayed"""
        rules_page = MatchRulesPage(page)
        rules_page.navigate()

        # Common rule types
        rule_types = ['Amount Match', 'Date Range', 'Description Pattern', 'Exact Match']

        # At least one rule type should be visible if rules exist
        rules_count = rules_page.get_rules_count()
        if rules_count > 0:
            type_cells = page.locator('td').all()
            types_found = [cell.inner_text() for cell in type_cells]
            assert any(rtype in ' '.join(types_found) for rtype in rule_types)


# ==============================
# Match Statistics Tests
# ==============================

class TestMatchStatistics:
    """Test suite for Match Statistics Dashboard UI"""

    def test_statistics_page_loads(self, page: Page):
        """Test that statistics page loads successfully"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        expect(page.locator('h1:has-text("Match Statistics")')).to_be_visible()

    def test_summary_metrics_display(self, page: Page):
        """Test that all summary metrics are displayed"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        # Verify all metric cards
        expect(page.locator('text="Auto-Match Rate"')).to_be_visible()
        expect(page.locator('text="Avg Confidence"')).to_be_visible()
        expect(page.locator('text="Total Matches"')).to_be_visible()
        expect(page.locator('text="Manual Reviews"')).to_be_visible()

    def test_auto_match_rate_percentage(self, page: Page):
        """Test that auto-match rate shows valid percentage"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        rate = stats_page.get_auto_match_rate()

        # Should contain % sign or be numeric
        assert '%' in rate or rate.replace('.', '').isdigit()

    def test_avg_confidence_score(self, page: Page):
        """Test that average confidence score is displayed"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        confidence = stats_page.get_avg_confidence()

        # Should be numeric or contain %
        assert '%' in confidence or confidence.replace('.', '').isdigit()

    def test_total_matches_count(self, page: Page):
        """Test that total matches count is displayed"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        total = stats_page.get_total_matches()

        # Should be numeric
        assert total.replace(',', '').isdigit()

    def test_manual_reviews_count(self, page: Page):
        """Test that manual reviews count is displayed"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        reviews = stats_page.get_manual_reviews()

        # Should be numeric
        assert reviews.replace(',', '').isdigit()

    def test_time_period_filter(self, page: Page):
        """Test that time period filter works"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        # Verify filter dropdown exists
        expect(page.locator('select')).to_be_visible()

        # Change filter
        stats_page.select_time_period('last_30_days')

        # Page should reload with new data
        expect(page.locator('h1:has-text("Match Statistics")')).to_be_visible()

    def test_metric_card_icons(self, page: Page):
        """Test that metric cards have appropriate icons"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        # Check for icon containers
        icon_containers = page.locator('.rounded-lg.p-3').all()
        assert len(icon_containers) >= 4  # At least 4 metric cards

    def test_chart_displays_if_present(self, page: Page):
        """Test that charts/visualizations display if implemented"""
        stats_page = MatchStatisticsPage(page)
        stats_page.navigate()

        # Look for common chart containers
        chart_elements = page.locator('canvas, svg[class*="chart"]').all()

        # If charts exist, verify they're visible
        if len(chart_elements) > 0:
            expect(chart_elements[0]).to_be_visible()


# ==============================
# E2E Workflow Tests
# ==============================

class TestMatchingE2EWorkflows:
    """End-to-end workflow tests for matching system"""

    def test_complete_matching_workflow(self, page: Page):
        """Test complete workflow: Review matches → Statistics → Rules"""
        # Step 1: Review and accept a match
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()
        expect(page.locator('h1:has-text("Transaction Matching")')).to_be_visible()

        pending_before = matching_page.get_pending_matches_count()

        if pending_before > 0:
            matching_page.accept_match(0)

        # Step 2: View statistics
        page.goto("http://localhost:3010/matching/statistics")
        expect(page.locator('h1:has-text("Match Statistics")')).to_be_visible()

        # Step 3: Review rules
        page.goto("http://localhost:3010/matching/rules")
        expect(page.locator('h1:has-text("Match Rules")')).to_be_visible()

    def test_navigation_between_matching_pages(self, page: Page):
        """Test navigation between all matching-related pages"""
        # Navigate to matching
        page.goto("http://localhost:3010/matching/transactions")
        expect(page.locator('h1:has-text("Transaction Matching")')).to_be_visible()

        # Navigate to rules
        page.goto("http://localhost:3010/matching/rules")
        expect(page.locator('h1:has-text("Match Rules")')).to_be_visible()

        # Navigate to statistics
        page.goto("http://localhost:3010/matching/statistics")
        expect(page.locator('h1:has-text("Match Statistics")')).to_be_visible()

    def test_accept_multiple_matches_sequence(self, page: Page):
        """Test accepting multiple matches in sequence"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        pending_initial = matching_page.get_pending_matches_count()

        if pending_initial >= 3:
            # Accept 3 matches
            for i in range(3):
                matching_page.accept_match(0)  # Always accept first since list updates

            # Verify count decreased by 3
            pending_final = matching_page.get_pending_matches_count()
            assert pending_final == pending_initial - 3


# ==============================
# Accessibility Tests
# ==============================

class TestMatchingAccessibility:
    """Accessibility tests for matching UI"""

    def test_page_headings_hierarchy(self, page: Page):
        """Test that page headings follow proper hierarchy"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        # Should have exactly one h1
        h1_count = page.locator('h1').count()
        assert h1_count == 1

    def test_button_titles_present(self, page: Page):
        """Test that action buttons have title attributes"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 0:
            accept_btn = page.locator('button[title="Accept Match"]').first
            expect(accept_btn).to_have_attribute('title', 'Accept Match')

            reject_btn = page.locator('button[title="Reject Match"]').first
            expect(reject_btn).to_have_attribute('title', 'Reject Match')

    def test_keyboard_navigation_action_buttons(self, page: Page):
        """Test keyboard navigation between action buttons"""
        matching_page = TransactionMatchingPage(page)
        matching_page.navigate()

        if matching_page.get_match_cards_count() > 0:
            # Tab to first accept button
            page.keyboard.press('Tab')

            # Focus should be on a button
            focused_tag = page.evaluate('document.activeElement.tagName')
            assert focused_tag.lower() in ['button', 'a']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
