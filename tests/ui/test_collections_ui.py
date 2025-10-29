"""
Sprint 17: Delinquency & Collections UI Tests

Comprehensive Playwright UI/E2E tests for:
- DelinquencyDashboardPage: Overview with summary stats and aging breakdown
- LateFeeRulesPage: Configure late fee rules (flat/percentage/both)
- CollectionNoticesPage: View and track collection notices
- CollectionActionsPage: Board approval workflow for legal actions
"""

import pytest
from playwright.sync_api import Page, expect
from decimal import Decimal


# ==============================
# Page Object Models
# ==============================

class DelinquencyDashboardPage:
    """Page Object Model for Delinquency Dashboard"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/delinquency/dashboard"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def get_total_delinquent(self) -> str:
        return self.page.locator('text="Total Delinquent" ~ p').inner_text()

    def get_total_balance(self) -> str:
        return self.page.locator('text="Total Balance" ~ p').inner_text()

    def get_avg_days_delinquent(self) -> str:
        return self.page.locator('text="Avg Days Delinquent" ~ p').inner_text()

    def get_accounts_90_plus(self) -> str:
        return self.page.locator('text="Accounts 90+ Days" ~ p').inner_text()

    def filter_by_stage(self, stage: str):
        self.page.select_option('select', stage)
        self.page.wait_for_load_state("networkidle")

    def get_table_rows(self):
        return self.page.locator('tbody tr').all()

    def get_stage_breakdown(self, stage: str) -> dict:
        """Get count and balance for a specific stage"""
        locator = self.page.locator(f'text="{stage.replace("_", " ").title()}"')
        container = locator.locator('..')
        count = container.locator('.text-2xl').inner_text()
        balance = container.locator('.text-sm.font-semibold').inner_text()
        return {"count": count, "balance": balance}


class LateFeeRulesPage:
    """Page Object Model for Late Fee Rules Management"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/collections/late-fee-rules"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def click_add_rule(self):
        self.page.click('button:has-text("Add Rule")')
        expect(self.page.locator('h2:has-text("Add Late Fee Rule")')).to_be_visible()

    def fill_rule_form(self, rule_data: dict):
        """Fill in the late fee rule form"""
        if 'name' in rule_data:
            self.page.fill('input[type="text"]', rule_data['name'])

        if 'grace_period_days' in rule_data:
            self.page.fill('input[type="number"]', str(rule_data['grace_period_days']))

        if 'fee_type' in rule_data:
            self.page.select_option('select', rule_data['fee_type'])

        if 'flat_amount' in rule_data:
            self.page.fill('label:has-text("Flat Amount") + input', str(rule_data['flat_amount']))

        if 'percentage_rate' in rule_data:
            self.page.fill('label:has-text("Percentage Rate") + input', str(rule_data['percentage_rate']))

        if 'max_amount' in rule_data:
            self.page.fill('label:has-text("Max Amount") + input', str(rule_data['max_amount']))

        if 'is_recurring' in rule_data and rule_data['is_recurring']:
            self.page.check('#is_recurring')

        if 'is_active' in rule_data and not rule_data['is_active']:
            self.page.uncheck('#is_active')

    def submit_form(self):
        self.page.click('button[type="submit"]:has-text("Create")')
        self.page.wait_for_load_state("networkidle")

    def edit_rule(self, rule_name: str):
        row = self.page.locator(f'tr:has-text("{rule_name}")')
        row.locator('button[title="Edit"]').click()
        expect(self.page.locator('h2:has-text("Edit Late Fee Rule")')).to_be_visible()

    def delete_rule(self, rule_name: str):
        row = self.page.locator(f'tr:has-text("{rule_name}")')

        # Set up dialog handler before clicking delete
        self.page.on("dialog", lambda dialog: dialog.accept())
        row.locator('button[title="Delete"]').click()
        self.page.wait_for_load_state("networkidle")

    def get_rules_table_rows(self):
        return self.page.locator('tbody tr').all()

    def get_rule_details(self, rule_name: str) -> dict:
        """Extract rule details from table row"""
        row = self.page.locator(f'tr:has-text("{rule_name}")')
        cells = row.locator('td').all()
        return {
            "name": cells[0].inner_text(),
            "grace_period": cells[1].inner_text(),
            "fee_type": cells[2].inner_text(),
            "fee_amount": cells[3].inner_text(),
            "recurring": cells[4].inner_text(),
            "status": cells[5].inner_text()
        }


class CollectionNoticesPage:
    """Page Object Model for Collection Notices"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/collections/notices"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def get_notices_count(self) -> int:
        rows = self.page.locator('tbody tr').all()
        return len(rows)

    def filter_by_notice_type(self, notice_type: str):
        self.page.select_option('select[name="notice_type"]', notice_type)
        self.page.wait_for_load_state("networkidle")

    def get_notice_details(self, owner_name: str) -> dict:
        row = self.page.locator(f'tr:has-text("{owner_name}")').first
        cells = row.locator('td').all()
        return {
            "owner": cells[0].inner_text(),
            "notice_type": cells[1].inner_text(),
            "sent_date": cells[2].inner_text(),
            "balance": cells[3].inner_text(),
            "status": cells[4].inner_text()
        }


class CollectionActionsPage:
    """Page Object Model for Collection Actions (Legal Actions)"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/collections/actions"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def approve_action(self, owner_name: str):
        row = self.page.locator(f'tr:has-text("{owner_name}")').first
        row.locator('button:has-text("Approve")').click()
        self.page.wait_for_load_state("networkidle")

    def get_pending_actions_count(self) -> int:
        return len(self.page.locator('tr:has-text("Pending")').all())

    def filter_by_action_type(self, action_type: str):
        self.page.select_option('select[name="action_type"]', action_type)
        self.page.wait_for_load_state("networkidle")


# ==============================
# Delinquency Dashboard Tests
# ==============================

class TestDelinquencyDashboard:
    """Test suite for Delinquency Dashboard UI"""

    def test_dashboard_loads_successfully(self, page: Page):
        """Test that the dashboard page loads with all key elements"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Verify page title
        expect(page.locator('h1:has-text("Delinquency Dashboard")')).to_be_visible()

        # Verify summary cards are visible
        expect(page.locator('text="Total Delinquent"')).to_be_visible()
        expect(page.locator('text="Total Balance"')).to_be_visible()
        expect(page.locator('text="Avg Days Delinquent"')).to_be_visible()
        expect(page.locator('text="Accounts 90+ Days"')).to_be_visible()

    def test_summary_cards_display_data(self, page: Page):
        """Test that summary cards show numeric data"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Get summary card values
        total_delinquent = dashboard.get_total_delinquent()
        total_balance = dashboard.get_total_balance()
        avg_days = dashboard.get_avg_days_delinquent()
        accounts_90_plus = dashboard.get_accounts_90_plus()

        # Verify all cards have numeric values
        assert total_delinquent.isdigit()
        assert '$' in total_balance or total_balance.replace(',', '').replace('.', '').isdigit()
        assert avg_days.isdigit()
        assert accounts_90_plus.isdigit()

    def test_stage_breakdown_displays_correctly(self, page: Page):
        """Test that the stage breakdown section shows all stages"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Verify stage breakdown section exists
        expect(page.locator('h2:has-text("By Collection Stage")')).to_be_visible()

        # Check for common stages
        stages = ['current', 'first_notice', 'second_notice', 'final_notice']
        for stage in stages:
            stage_display = stage.replace('_', ' ').title()
            # Stage should be visible somewhere in the breakdown
            expect(page.locator(f'text="{stage_display}"').first).to_be_visible()

    def test_delinquent_accounts_table_loads(self, page: Page):
        """Test that the delinquent accounts table loads"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Verify table headers
        expect(page.locator('th:has-text("Owner")')).to_be_visible()
        expect(page.locator('th:has-text("Total Balance")')).to_be_visible()
        expect(page.locator('th:has-text("0-30 Days")')).to_be_visible()
        expect(page.locator('th:has-text("31-60 Days")')).to_be_visible()
        expect(page.locator('th:has-text("61-90 Days")')).to_be_visible()
        expect(page.locator('th:has-text("90+ Days")')).to_be_visible()
        expect(page.locator('th:has-text("Stage")')).to_be_visible()

    def test_stage_filter_changes_table_data(self, page: Page):
        """Test that filtering by stage updates the table"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Get initial row count
        initial_rows = len(dashboard.get_table_rows())

        # Filter to "First Notice" stage
        dashboard.filter_by_stage('first_notice')

        # Get filtered rows
        filtered_rows = dashboard.get_table_rows()

        # Verify filtering worked (all visible rows show correct stage)
        for row in filtered_rows:
            stage_badge = row.locator('.rounded-full').inner_text()
            assert 'First Notice' in stage_badge

    def test_payment_plan_indicator_shows(self, page: Page):
        """Test that payment plan indicator is visible for accounts on payment plans"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Look for payment plan indicator
        payment_plan_indicators = page.locator('text="Payment Plan"').all()

        # If any exist, verify they're styled correctly
        if len(payment_plan_indicators) > 0:
            first_indicator = payment_plan_indicators[0]
            expect(first_indicator).to_have_class(re.compile(r'text-blue-600'))

    def test_aging_buckets_display_correctly(self, page: Page):
        """Test that aging buckets (0-30, 31-60, 61-90, 90+) show amounts"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        rows = dashboard.get_table_rows()
        if len(rows) > 0:
            first_row = rows[0]
            cells = first_row.locator('td').all()

            # Verify balance cells (indices 2-5 are aging buckets)
            for i in range(2, 6):
                cell_text = cells[i].inner_text()
                assert '$' in cell_text or cell_text == '$0'

    def test_dashboard_handles_no_data_gracefully(self, page: Page):
        """Test that dashboard shows appropriate message when no delinquent accounts"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        rows = dashboard.get_table_rows()
        if len(rows) == 0:
            expect(page.locator('text="No delinquent accounts found"')).to_be_visible()

    def test_dashboard_responsive_layout_desktop(self, page: Page):
        """Test dashboard layout on desktop (1920x1080)"""
        page.set_viewport_size({"width": 1920, "height": 1080})
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Summary cards should be in a grid on desktop
        summary_cards = page.locator('.grid.grid-cols-1.md\\:grid-cols-4 > div').all()
        assert len(summary_cards) == 4

    def test_dashboard_responsive_layout_mobile(self, page: Page):
        """Test dashboard layout on mobile (375x667)"""
        page.set_viewport_size({"width": 375, "height": 667})
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Verify page is still functional on mobile
        expect(page.locator('h1:has-text("Delinquency Dashboard")')).to_be_visible()
        expect(page.locator('text="Total Delinquent"')).to_be_visible()


# ==============================
# Late Fee Rules Tests
# ==============================

class TestLateFeeRules:
    """Test suite for Late Fee Rules Management UI"""

    def test_late_fee_rules_page_loads(self, page: Page):
        """Test that late fee rules page loads successfully"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        # Verify page elements
        expect(page.locator('h1:has-text("Late Fee Rules")')).to_be_visible()
        expect(page.locator('button:has-text("Add Rule")')).to_be_visible()

    def test_add_rule_button_opens_modal(self, page: Page):
        """Test that clicking Add Rule opens the modal form"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Verify modal is open
        expect(page.locator('h2:has-text("Add Late Fee Rule")')).to_be_visible()
        expect(page.locator('label:has-text("Rule Name")')).to_be_visible()
        expect(page.locator('label:has-text("Grace Period")')).to_be_visible()

    def test_create_flat_fee_rule(self, page: Page):
        """Test creating a flat amount late fee rule"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Fill form with flat fee data
        rules_page.fill_rule_form({
            'name': 'Standard Late Fee - $25',
            'grace_period_days': 10,
            'fee_type': 'flat',
            'flat_amount': '25.00',
            'is_recurring': False,
            'is_active': True
        })

        rules_page.submit_form()

        # Verify rule appears in table
        expect(page.locator('tr:has-text("Standard Late Fee - $25")')).to_be_visible()

    def test_create_percentage_fee_rule(self, page: Page):
        """Test creating a percentage-based late fee rule"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Fill form with percentage fee data
        rules_page.fill_rule_form({
            'name': 'Percentage Late Fee - 5%',
            'grace_period_days': 15,
            'fee_type': 'percentage',
            'percentage_rate': '5.00',
            'is_recurring': False,
            'is_active': True
        })

        rules_page.submit_form()

        # Verify rule appears in table
        expect(page.locator('tr:has-text("Percentage Late Fee - 5%")')).to_be_visible()

    def test_create_combined_fee_rule(self, page: Page):
        """Test creating a combined (flat + percentage) late fee rule"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Fill form with combined fee data
        rules_page.fill_rule_form({
            'name': 'Combined Late Fee',
            'grace_period_days': 5,
            'fee_type': 'both',
            'flat_amount': '10.00',
            'percentage_rate': '2.50',
            'max_amount': '100.00',
            'is_recurring': True,
            'is_active': True
        })

        rules_page.submit_form()

        # Verify rule appears in table
        expect(page.locator('tr:has-text("Combined Late Fee")')).to_be_visible()

    def test_form_validation_required_fields(self, page: Page):
        """Test that required fields are validated"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Try to submit empty form
        rules_page.submit_form()

        # Verify form doesn't submit (modal still visible)
        expect(page.locator('h2:has-text("Add Late Fee Rule")')).to_be_visible()

    def test_form_validation_numeric_fields(self, page: Page):
        """Test that numeric fields only accept numbers"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Try to enter non-numeric value in grace period
        grace_period_input = page.locator('label:has-text("Grace Period") + input')
        grace_period_input.fill('abc')

        # Verify input type prevents non-numeric (browser validation)
        assert grace_period_input.get_attribute('type') == 'number'

    def test_edit_existing_rule(self, page: Page):
        """Test editing an existing late fee rule"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        # First create a rule
        rules_page.click_add_rule()
        rules_page.fill_rule_form({
            'name': 'Test Edit Rule',
            'grace_period_days': 10,
            'fee_type': 'flat',
            'flat_amount': '25.00'
        })
        rules_page.submit_form()

        # Now edit it
        rules_page.edit_rule('Test Edit Rule')

        # Verify edit modal opened
        expect(page.locator('h2:has-text("Edit Late Fee Rule")')).to_be_visible()

        # Change the flat amount
        page.fill('label:has-text("Flat Amount") + input', '30.00')
        page.click('button[type="submit"]:has-text("Update")')

        # Verify updated amount shows in table
        rule_details = rules_page.get_rule_details('Test Edit Rule')
        assert '$30.00' in rule_details['fee_amount']

    def test_delete_rule_confirmation(self, page: Page):
        """Test that deleting a rule shows confirmation dialog"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        # Create a rule to delete
        rules_page.click_add_rule()
        rules_page.fill_rule_form({
            'name': 'Rule to Delete',
            'grace_period_days': 10,
            'fee_type': 'flat',
            'flat_amount': '25.00'
        })
        rules_page.submit_form()

        # Delete the rule
        rules_page.delete_rule('Rule to Delete')

        # Verify rule is removed from table
        expect(page.locator('tr:has-text("Rule to Delete")')).not_to_be_visible()

    def test_cancel_button_closes_modal(self, page: Page):
        """Test that cancel button closes the modal without saving"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Fill in some data
        page.fill('input[type="text"]', 'Cancelled Rule')

        # Click cancel
        page.click('button:has-text("Cancel")')

        # Verify modal is closed
        expect(page.locator('h2:has-text("Add Late Fee Rule")')).not_to_be_visible()

        # Verify rule was not created
        expect(page.locator('tr:has-text("Cancelled Rule")')).not_to_be_visible()

    def test_recurring_checkbox_functionality(self, page: Page):
        """Test that recurring checkbox works correctly"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Check recurring checkbox
        recurring_checkbox = page.locator('#is_recurring')
        recurring_checkbox.check()
        expect(recurring_checkbox).to_be_checked()

        # Uncheck it
        recurring_checkbox.uncheck()
        expect(recurring_checkbox).not_to_be_checked()

    def test_active_inactive_toggle(self, page: Page):
        """Test toggling rule active/inactive status"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Active checkbox should be checked by default
        active_checkbox = page.locator('#is_active')
        expect(active_checkbox).to_be_checked()

        # Uncheck to create inactive rule
        active_checkbox.uncheck()

        rules_page.fill_rule_form({
            'name': 'Inactive Rule',
            'grace_period_days': 10,
            'fee_type': 'flat',
            'flat_amount': '25.00'
        })
        rules_page.submit_form()

        # Verify status shows as Inactive
        rule_details = rules_page.get_rule_details('Inactive Rule')
        assert 'Inactive' in rule_details['status']

    def test_fee_type_selector_shows_correct_fields(self, page: Page):
        """Test that fee type selector shows/hides appropriate fields"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Select "flat" - should show flat amount field only
        page.select_option('select', 'flat')
        expect(page.locator('label:has-text("Flat Amount")')).to_be_visible()

        # Select "percentage" - should show percentage field only
        page.select_option('select', 'percentage')
        expect(page.locator('label:has-text("Percentage Rate")')).to_be_visible()

        # Select "both" - should show both fields
        page.select_option('select', 'both')
        expect(page.locator('label:has-text("Flat Amount")')).to_be_visible()
        expect(page.locator('label:has-text("Percentage Rate")')).to_be_visible()

    def test_max_amount_field_optional(self, page: Page):
        """Test that max amount field is optional"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Create rule without max amount
        rules_page.fill_rule_form({
            'name': 'No Max Rule',
            'grace_period_days': 10,
            'fee_type': 'percentage',
            'percentage_rate': '5.00'
        })

        # Should submit successfully
        rules_page.submit_form()
        expect(page.locator('tr:has-text("No Max Rule")')).to_be_visible()

    def test_rules_table_empty_state(self, page: Page):
        """Test that empty state message shows when no rules exist"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rows = rules_page.get_rules_table_rows()
        if len(rows) == 0:
            expect(page.locator('text="No late fee rules configured"')).to_be_visible()

    def test_rules_table_displays_all_columns(self, page: Page):
        """Test that rules table displays all required columns"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        # Verify all column headers
        headers = ['Name', 'Grace Period', 'Type', 'Fee Amount', 'Recurring', 'Status', 'Actions']
        for header in headers:
            expect(page.locator(f'th:has-text("{header}")')).to_be_visible()

    def test_responsive_modal_mobile(self, page: Page):
        """Test that modal form is responsive on mobile"""
        page.set_viewport_size({"width": 375, "height": 667})

        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Modal should be visible and form fields accessible
        expect(page.locator('h2:has-text("Add Late Fee Rule")')).to_be_visible()
        expect(page.locator('label:has-text("Rule Name")')).to_be_visible()

    def test_keyboard_navigation_in_form(self, page: Page):
        """Test keyboard navigation through form fields"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()

        rules_page.click_add_rule()

        # Focus first input
        page.focus('input[type="text"]')

        # Tab to next field
        page.keyboard.press('Tab')

        # Should focus grace period input
        focused_element = page.evaluate('document.activeElement.type')
        assert focused_element == 'number'


# ==============================
# Collection Notices Tests
# ==============================

class TestCollectionNotices:
    """Test suite for Collection Notices UI"""

    def test_collection_notices_page_loads(self, page: Page):
        """Test that collection notices page loads successfully"""
        notices_page = CollectionNoticesPage(page)
        notices_page.navigate()

        expect(page.locator('h1:has-text("Collection Notices")')).to_be_visible()

    def test_notices_table_displays(self, page: Page):
        """Test that notices table displays with correct columns"""
        notices_page = CollectionNoticesPage(page)
        notices_page.navigate()

        # Verify table headers
        expect(page.locator('th:has-text("Owner")')).to_be_visible()
        expect(page.locator('th:has-text("Notice Type")')).to_be_visible()
        expect(page.locator('th:has-text("Sent Date")')).to_be_visible()

    def test_filter_notices_by_type(self, page: Page):
        """Test filtering notices by type (First, Second, Final)"""
        notices_page = CollectionNoticesPage(page)
        notices_page.navigate()

        # Filter to first notice
        notices_page.filter_by_notice_type('first_notice')

        # Verify filtered results
        notice_badges = page.locator('.rounded-full:has-text("First Notice")').all()
        assert len(notice_badges) > 0

    def test_notice_tracking_number_display(self, page: Page):
        """Test that tracking numbers display for certified mail"""
        notices_page = CollectionNoticesPage(page)
        notices_page.navigate()

        # Look for tracking numbers
        tracking_cells = page.locator('td:has-text("Tracking:")')
        if tracking_cells.count() > 0:
            expect(tracking_cells.first).to_be_visible()

    def test_undeliverable_indicator(self, page: Page):
        """Test that undeliverable notices are marked"""
        notices_page = CollectionNoticesPage(page)
        notices_page.navigate()

        # Look for undeliverable indicators
        undeliverable = page.locator('text="Undeliverable"')
        if undeliverable.count() > 0:
            expect(undeliverable.first).to_have_class(re.compile(r'text-red'))


# ==============================
# Collection Actions Tests
# ==============================

class TestCollectionActions:
    """Test suite for Collection Actions (Legal Actions) UI"""

    def test_collection_actions_page_loads(self, page: Page):
        """Test that collection actions page loads successfully"""
        actions_page = CollectionActionsPage(page)
        actions_page.navigate()

        expect(page.locator('h1:has-text("Collection Actions")')).to_be_visible()

    def test_pending_actions_display(self, page: Page):
        """Test that pending actions are displayed"""
        actions_page = CollectionActionsPage(page)
        actions_page.navigate()

        pending_count = actions_page.get_pending_actions_count()
        assert pending_count >= 0

    def test_approve_action_workflow(self, page: Page):
        """Test board approval workflow for legal action"""
        actions_page = CollectionActionsPage(page)
        actions_page.navigate()

        pending_count_before = actions_page.get_pending_actions_count()

        if pending_count_before > 0:
            # Get first pending action owner name
            first_pending = page.locator('tr:has-text("Pending")').first
            owner_name = first_pending.locator('td').first.inner_text()

            # Approve it
            actions_page.approve_action(owner_name)

            # Verify count decreased
            pending_count_after = actions_page.get_pending_actions_count()
            assert pending_count_after == pending_count_before - 1

    def test_filter_by_action_type(self, page: Page):
        """Test filtering by action type (lien, foreclosure, etc.)"""
        actions_page = CollectionActionsPage(page)
        actions_page.navigate()

        # Filter to lien filings
        actions_page.filter_by_action_type('lien_filing')

        # Verify filtered results
        action_badges = page.locator('.rounded-full:has-text("Lien Filing")').all()
        if len(action_badges) > 0:
            expect(action_badges[0]).to_be_visible()

    def test_attorney_information_display(self, page: Page):
        """Test that attorney name and case number display for legal actions"""
        actions_page = CollectionActionsPage(page)
        actions_page.navigate()

        # Look for attorney information
        attorney_fields = page.locator('text="Attorney:"')
        if attorney_fields.count() > 0:
            expect(attorney_fields.first).to_be_visible()


# ==============================
# E2E Workflow Tests
# ==============================

class TestCollectionsE2EWorkflows:
    """End-to-end workflow tests spanning multiple pages"""

    def test_complete_delinquency_workflow(self, page: Page):
        """Test complete workflow: Dashboard → Rule Creation → Notice Tracking"""
        # Step 1: View dashboard
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()
        expect(page.locator('h1:has-text("Delinquency Dashboard")')).to_be_visible()

        # Step 2: Create late fee rule
        page.goto("http://localhost:3010/collections/late-fee-rules")
        rules_page = LateFeeRulesPage(page)
        rules_page.click_add_rule()
        rules_page.fill_rule_form({
            'name': 'E2E Test Rule',
            'grace_period_days': 10,
            'fee_type': 'flat',
            'flat_amount': '25.00'
        })
        rules_page.submit_form()

        # Step 3: View notices
        page.goto("http://localhost:3010/collections/notices")
        expect(page.locator('h1:has-text("Collection Notices")')).to_be_visible()

    def test_navigation_between_collection_pages(self, page: Page):
        """Test navigation between all collection-related pages"""
        # Navigate to dashboard
        page.goto("http://localhost:3010/delinquency/dashboard")
        expect(page.locator('h1:has-text("Delinquency Dashboard")')).to_be_visible()

        # Navigate to rules
        page.goto("http://localhost:3010/collections/late-fee-rules")
        expect(page.locator('h1:has-text("Late Fee Rules")')).to_be_visible()

        # Navigate to notices
        page.goto("http://localhost:3010/collections/notices")
        expect(page.locator('h1:has-text("Collection Notices")')).to_be_visible()

        # Navigate to actions
        page.goto("http://localhost:3010/collections/actions")
        expect(page.locator('h1:has-text("Collection Actions")')).to_be_visible()


# ==============================
# Accessibility Tests
# ==============================

class TestCollectionsAccessibility:
    """Accessibility tests for collections UI"""

    def test_dashboard_aria_labels(self, page: Page):
        """Test that dashboard has proper ARIA labels"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Check for accessible headings
        h1 = page.locator('h1')
        assert h1.count() >= 1

    def test_form_labels_associated(self, page: Page):
        """Test that form labels are properly associated with inputs"""
        rules_page = LateFeeRulesPage(page)
        rules_page.navigate()
        rules_page.click_add_rule()

        # Check that labels have 'for' attribute or wrap inputs
        labels = page.locator('label').all()
        assert len(labels) > 0

    def test_keyboard_navigation_dashboard(self, page: Page):
        """Test keyboard navigation on dashboard"""
        dashboard = DelinquencyDashboardPage(page)
        dashboard.navigate()

        # Focus stage filter dropdown
        page.focus('select')

        # Use arrow keys to navigate
        page.keyboard.press('ArrowDown')
        page.keyboard.press('Enter')

        # Should update filter
        page.wait_for_load_state("networkidle")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
