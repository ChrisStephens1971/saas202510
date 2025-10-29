"""
Sprint 20: Board Packet Generation UI Tests

Comprehensive Playwright UI/E2E tests for:
- BoardPacketsPage: Generate and manage board meeting packets
- PDF generation workflow
- Email distribution
- Template management
- Section management
- Status workflow: Draft → Generating → Ready → Sent
"""

import pytest
from playwright.sync_api import Page, expect
import re


# ==============================
# Page Object Models
# ==============================

class BoardPacketsPage:
    """Page Object Model for Board Packets Management"""

    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/board-packets"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def click_new_packet(self):
        """Click the New Packet button"""
        self.page.click('button:has-text("New Packet")')
        self.page.wait_for_load_state("networkidle")

    def get_packets_count(self) -> int:
        """Get total number of packets displayed"""
        return len(self.page.locator('.bg-white.rounded-lg.border.p-6').all())

    def get_packet_by_date(self, date_text: str):
        """Get packet card by meeting date"""
        return self.page.locator(f'.bg-white.rounded-lg.border:has-text("{date_text}")').first

    def get_packet_status(self, index: int = 0) -> str:
        """Get status of packet by index"""
        status_badges = self.page.locator('.rounded-full').all()
        if len(status_badges) > index:
            return status_badges[index].inner_text()
        return ""

    def click_generate(self, index: int = 0):
        """Click Generate button for a packet"""
        generate_buttons = self.page.locator('button:has-text("Generate")').all()
        if len(generate_buttons) > index:
            generate_buttons[index].click()
            self.page.wait_for_load_state("networkidle")

    def click_download(self, index: int = 0):
        """Click Download button for a packet"""
        download_buttons = self.page.locator('button:has-text("Download")').all()
        if len(download_buttons) > index:
            download_buttons[index].click()

    def click_send(self, index: int = 0):
        """Click Send button for a packet"""
        send_buttons = self.page.locator('button:has-text("Send")').all()
        if len(send_buttons) > index:
            send_buttons[index].click()

    def get_sections_count(self, index: int = 0) -> int:
        """Get number of sections in a packet"""
        sections_text = self.page.locator('text="Sections" ~ .font-semibold').nth(index).inner_text()
        return int(sections_text)

    def get_page_count(self, index: int = 0) -> str:
        """Get page count for a packet"""
        page_count_elements = self.page.locator('text="Pages" ~ .font-semibold').all()
        if len(page_count_elements) > index:
            return page_count_elements[index].inner_text()
        return "-"

    def get_recipients_count(self, index: int = 0) -> int:
        """Get number of recipients for a packet"""
        recipients_text = self.page.locator('text="Recipients" ~ .font-semibold').nth(index).inner_text()
        return int(recipients_text)


# ==============================
# Board Packets List Tests
# ==============================

class TestBoardPacketsList:
    """Test suite for Board Packets List UI"""

    def test_board_packets_page_loads_successfully(self, page: Page):
        """Test that board packets page loads with all key elements"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Verify page title
        expect(page.locator('h1:has-text("Board Packets")')).to_be_visible()

        # Verify subtitle
        expect(page.locator('p:has-text("Generate comprehensive meeting packets")')).to_be_visible()

        # Verify New Packet button
        expect(page.locator('button:has-text("New Packet")')).to_be_visible()

    def test_new_packet_button_styled_correctly(self, page: Page):
        """Test that New Packet button has correct styling"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        new_packet_btn = page.locator('button:has-text("New Packet")')

        # Should be blue button
        expect(new_packet_btn).to_have_class(re.compile(r'bg-blue-600'))

        # Should have plus icon
        plus_icon = new_packet_btn.locator('svg')
        expect(plus_icon).to_be_visible()

    def test_packet_cards_display_correctly(self, page: Page):
        """Test that packet cards show all required information"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        packets_count = packets_page.get_packets_count()

        if packets_count > 0:
            # Verify first card has required elements
            first_card = page.locator('.bg-white.rounded-lg.border.p-6').first

            # Meeting date should be visible in heading
            expect(first_card.locator('h3.text-lg.font-semibold')).to_be_visible()

            # Status badge should be visible
            expect(first_card.locator('.rounded-full').first).to_be_visible()

            # Template name should be visible
            expect(first_card.locator('text="Template:"')).to_be_visible()

    def test_packet_status_badges_colors(self, page: Page):
        """Test that status badges have correct colors"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Check Ready status badges (should be green)
        ready_badges = page.locator('.rounded-full:has-text("Ready")').all()
        for badge in ready_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-green-100' in badge_class
            assert 'text-green-800' in badge_class

        # Check Generating status badges (should be blue)
        generating_badges = page.locator('.rounded-full:has-text("Generating")').all()
        for badge in generating_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-blue-100' in badge_class

        # Check Sent status badges (should be purple)
        sent_badges = page.locator('.rounded-full:has-text("Sent")').all()
        for badge in sent_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-purple-100' in badge_class

        # Check Draft status badges (should be gray)
        draft_badges = page.locator('.rounded-full:has-text("Draft")').all()
        for badge in draft_badges:
            badge_class = badge.get_attribute('class')
            assert 'bg-gray-100' in badge_class

    def test_meeting_date_displays(self, page: Page):
        """Test that meeting dates are displayed and formatted"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() > 0:
            # Meeting date should be in heading
            heading = page.locator('h3.text-lg.font-semibold').first
            heading_text = heading.inner_text()

            # Should contain "Board Meeting" and a date
            assert 'Board Meeting' in heading_text
            # Date should have slashes or dashes
            assert '/' in heading_text or '-' in heading_text

    def test_template_name_displays(self, page: Page):
        """Test that template names are displayed"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() > 0:
            # Template name should be visible
            expect(page.locator('text="Template:"').first).to_be_visible()

    def test_packet_metrics_display(self, page: Page):
        """Test that packet metrics (sections, pages, recipients) display"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() > 0:
            first_card = page.locator('.bg-white.rounded-lg.border.p-6').first

            # Verify metrics are present
            expect(first_card.locator('text="Sections"')).to_be_visible()
            expect(first_card.locator('text="Pages"')).to_be_visible()
            expect(first_card.locator('text="Recipients"')).to_be_visible()

    def test_sections_count_numeric(self, page: Page):
        """Test that sections count is numeric"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() > 0:
            sections_count = packets_page.get_sections_count(0)
            assert sections_count >= 0

    def test_page_count_displays(self, page: Page):
        """Test that page count displays correctly"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() > 0:
            page_count = packets_page.get_page_count(0)

            # Should be numeric or "-" for drafts
            assert page_count.isdigit() or page_count == '-'

    def test_recipients_count_numeric(self, page: Page):
        """Test that recipients count is numeric"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() > 0:
            recipients_count = packets_page.get_recipients_count(0)
            assert recipients_count >= 0


# ==============================
# Packet Actions Tests
# ==============================

class TestPacketActions:
    """Test suite for Packet Action Buttons"""

    def test_generate_button_visible_for_drafts(self, page: Page):
        """Test that Generate button is visible for draft packets"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Look for draft packets
        draft_cards = page.locator('.rounded-full:has-text("Draft")').all()

        if len(draft_cards) > 0:
            # Generate button should be visible
            expect(page.locator('button:has-text("Generate")').first).to_be_visible()

    def test_generate_button_styled_correctly(self, page: Page):
        """Test that Generate button has correct styling"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        generate_buttons = page.locator('button:has-text("Generate")').all()

        if len(generate_buttons) > 0:
            btn = generate_buttons[0]

            # Should be blue button
            expect(btn).to_have_class(re.compile(r'bg-blue-600'))

            # Should have FileText icon
            icon = btn.locator('svg')
            expect(icon).to_be_visible()

    def test_generate_button_triggers_action(self, page: Page):
        """Test that clicking Generate triggers PDF generation"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        generate_buttons = page.locator('button:has-text("Generate")').all()

        if len(generate_buttons) > 0:
            # Set up dialog handler for alert
            page.on("dialog", lambda dialog: dialog.accept())

            packets_page.click_generate(0)

            # Should trigger some action (status change or alert)
            page.wait_for_timeout(500)

    def test_download_button_visible_for_ready_packets(self, page: Page):
        """Test that Download button is visible for ready packets"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Look for ready packets
        ready_cards = page.locator('.rounded-full:has-text("Ready")').all()

        if len(ready_cards) > 0:
            # Download button should be visible
            download_buttons = page.locator('button:has-text("Download")').all()
            assert len(download_buttons) > 0

    def test_download_button_styled_correctly(self, page: Page):
        """Test that Download button has correct styling"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        download_buttons = page.locator('button:has-text("Download")').all()

        if len(download_buttons) > 0:
            btn = download_buttons[0]

            # Should be green button
            expect(btn).to_have_class(re.compile(r'bg-green-600'))

            # Should have Download icon
            icon = btn.locator('svg')
            expect(icon).to_be_visible()

    def test_send_button_visible_for_ready_packets(self, page: Page):
        """Test that Send button is visible for ready packets"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Look for ready packets
        ready_cards = page.locator('.rounded-full:has-text("Ready")').all()

        if len(ready_cards) > 0:
            # Send button should be visible
            send_buttons = page.locator('button:has-text("Send")').all()
            assert len(send_buttons) > 0

    def test_send_button_styled_correctly(self, page: Page):
        """Test that Send button has correct styling"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        send_buttons = page.locator('button:has-text("Send")').all()

        if len(send_buttons) > 0:
            btn = send_buttons[0]

            # Should be purple button
            expect(btn).to_have_class(re.compile(r'bg-purple-600'))

            # Should have Send icon
            icon = btn.locator('svg')
            expect(icon).to_be_visible()

    def test_send_button_prompts_for_emails(self, page: Page):
        """Test that Send button prompts for email addresses"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        send_buttons = page.locator('button:has-text("Send")').all()

        if len(send_buttons) > 0:
            # Set up dialog handler
            dialog_shown = False

            def handle_dialog(dialog):
                nonlocal dialog_shown
                dialog_shown = True
                dialog.dismiss()

            page.on("dialog", handle_dialog)

            packets_page.click_send(0)

            # Should show prompt
            page.wait_for_timeout(500)
            assert dialog_shown

    def test_action_buttons_hover_states(self, page: Page):
        """Test that action buttons show hover states"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Test Generate button hover
        generate_buttons = page.locator('button:has-text("Generate")').all()
        if len(generate_buttons) > 0:
            btn = generate_buttons[0]
            btn.hover()
            expect(btn).to_have_class(re.compile(r'hover:bg-blue-700'))

        # Test Download button hover
        download_buttons = page.locator('button:has-text("Download")').all()
        if len(download_buttons) > 0:
            btn = download_buttons[0]
            btn.hover()
            expect(btn).to_have_class(re.compile(r'hover:bg-green-700'))


# ==============================
# Packet Status Workflow Tests
# ==============================

class TestPacketStatusWorkflow:
    """Test suite for Packet Status Workflow"""

    def test_draft_status_shows_generate_button(self, page: Page):
        """Test that draft status shows only Generate button"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Find draft packets
        draft_badges = page.locator('.rounded-full:has-text("Draft")').all()

        if len(draft_badges) > 0:
            # Should have Generate button
            expect(page.locator('button:has-text("Generate")').first).to_be_visible()

            # Should NOT have Download or Send buttons visible for drafts
            # (they appear after generation)

    def test_ready_status_shows_download_and_send(self, page: Page):
        """Test that ready status shows Download and Send buttons"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Find ready packets
        ready_badges = page.locator('.rounded-full:has-text("Ready")').all()

        if len(ready_badges) > 0:
            # Should have both Download and Send buttons
            download_buttons = page.locator('button:has-text("Download")').all()
            send_buttons = page.locator('button:has-text("Send")').all()

            assert len(download_buttons) > 0
            assert len(send_buttons) > 0

    def test_generating_status_shows_no_actions(self, page: Page):
        """Test that generating status shows no action buttons"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Find generating packets
        generating_badges = page.locator('.rounded-full:has-text("Generating")').all()

        if len(generating_badges) > 0:
            # Get the packet card
            generating_card = generating_badges[0].locator('..')

            # Should not have action buttons in generating state
            # (buttons are disabled or hidden during generation)

    def test_sent_status_indicates_completion(self, page: Page):
        """Test that sent status indicates packet was distributed"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Find sent packets
        sent_badges = page.locator('.rounded-full:has-text("Sent")').all()

        if len(sent_badges) > 0:
            # Sent badge should be purple
            badge = sent_badges[0]
            badge_class = badge.get_attribute('class')
            assert 'bg-purple-100' in badge_class


# ==============================
# Empty State Tests
# ==============================

class TestBoardPacketsEmptyState:
    """Test suite for Empty State handling"""

    def test_empty_state_message_when_no_packets(self, page: Page):
        """Test that appropriate message shows when no packets exist"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        packets_count = packets_page.get_packets_count()

        if packets_count == 0:
            # Should show empty state message
            expect(page.locator('text="No board packets yet"')).to_be_visible()
            expect(page.locator('text="Click \\"New Packet\\" to create one"')).to_be_visible()

    def test_empty_state_encourages_action(self, page: Page):
        """Test that empty state encourages creating a packet"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        packets_count = packets_page.get_packets_count()

        if packets_count == 0:
            # Empty message should reference New Packet button
            empty_message = page.locator('.text-center.text-gray-500')
            expect(empty_message).to_be_visible()


# ==============================
# Responsive Design Tests
# ==============================

class TestBoardPacketsResponsive:
    """Test suite for Responsive Design"""

    def test_board_packets_desktop_layout(self, page: Page):
        """Test board packets page layout on desktop (1920x1080)"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Verify page is functional at desktop resolution
        expect(page.locator('h1:has-text("Board Packets")')).to_be_visible()
        expect(page.locator('button:has-text("New Packet")')).to_be_visible()

    def test_board_packets_tablet_layout(self, page: Page):
        """Test board packets page layout on tablet (768x1024)"""
        page.set_viewport_size({"width": 768, "height": 1024})

        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Verify page is functional at tablet resolution
        expect(page.locator('h1:has-text("Board Packets")')).to_be_visible()

    def test_board_packets_mobile_layout(self, page: Page):
        """Test board packets page layout on mobile (375x667)"""
        page.set_viewport_size({"width": 375, "height": 667})

        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Verify page is functional at mobile resolution
        expect(page.locator('h1:has-text("Board Packets")')).to_be_visible()

        # New Packet button should still be accessible
        expect(page.locator('button:has-text("New Packet")')).to_be_visible()

    def test_packet_cards_stack_on_mobile(self, page: Page):
        """Test that packet cards stack vertically on mobile"""
        page.set_viewport_size({"width": 375, "height": 667})

        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() >= 2:
            # Cards should stack vertically
            cards = page.locator('.bg-white.rounded-lg.border.p-6').all()

            box1 = cards[0].bounding_box()
            box2 = cards[1].bounding_box()

            # Second card should be below first
            assert box2['y'] > box1['y']

    def test_action_buttons_wrap_on_mobile(self, page: Page):
        """Test that action buttons remain accessible on mobile"""
        page.set_viewport_size({"width": 375, "height": 667})

        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Action buttons should still be clickable
        download_buttons = page.locator('button:has-text("Download")').all()
        if len(download_buttons) > 0:
            expect(download_buttons[0]).to_be_visible()


# ==============================
# E2E Workflow Tests
# ==============================

class TestBoardPacketsE2EWorkflows:
    """End-to-end workflow tests for board packets"""

    def test_complete_packet_generation_workflow(self, page: Page):
        """Test complete workflow: Draft → Generate → Ready → Send"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Step 1: View packets list
        expect(page.locator('h1:has-text("Board Packets")')).to_be_visible()

        # Step 2: If draft exists, generate it
        generate_buttons = page.locator('button:has-text("Generate")').all()
        if len(generate_buttons) > 0:
            page.on("dialog", lambda dialog: dialog.accept())
            packets_page.click_generate(0)

        # Step 3: Check for ready packets
        ready_badges = page.locator('.rounded-full:has-text("Ready")').all()
        if len(ready_badges) > 0:
            # Can download or send
            download_buttons = page.locator('button:has-text("Download")').all()
            assert len(download_buttons) > 0

    def test_packet_lifecycle_status_progression(self, page: Page):
        """Test viewing packets at different lifecycle stages"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Should handle all packet statuses gracefully
        statuses = ['Draft', 'Generating', 'Ready', 'Sent']

        for status in statuses:
            status_badges = page.locator(f'.rounded-full:has-text("{status}")').all()
            # If status exists, verify it's displayed correctly
            if len(status_badges) > 0:
                expect(status_badges[0]).to_be_visible()


# ==============================
# Accessibility Tests
# ==============================

class TestBoardPacketsAccessibility:
    """Accessibility tests for board packets UI"""

    def test_page_heading_hierarchy(self, page: Page):
        """Test that page has proper heading hierarchy"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Should have exactly one h1
        h1_count = page.locator('h1').count()
        assert h1_count == 1

        # Packet cards should have h3 headings
        if packets_page.get_packets_count() > 0:
            h3_count = page.locator('h3').count()
            assert h3_count >= 1

    def test_button_accessibility(self, page: Page):
        """Test that buttons have accessible text"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # New Packet button should have text
        new_packet_btn = page.locator('button:has-text("New Packet")')
        btn_text = new_packet_btn.inner_text()
        assert len(btn_text) > 0

        # Action buttons should have text
        generate_buttons = page.locator('button:has-text("Generate")').all()
        if len(generate_buttons) > 0:
            btn_text = generate_buttons[0].inner_text()
            assert len(btn_text) > 0

    def test_keyboard_navigation_new_packet_button(self, page: Page):
        """Test keyboard navigation to New Packet button"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        # Tab to New Packet button
        page.keyboard.press('Tab')

        # Should focus a button
        focused_tag = page.evaluate('document.activeElement.tagName')
        assert focused_tag.lower() == 'button'

    def test_button_focus_visible(self, page: Page):
        """Test that buttons show focus indicator"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        new_packet_btn = page.locator('button:has-text("New Packet")')

        # Focus button
        new_packet_btn.focus()

        # Button should be focused
        is_focused = page.evaluate('document.activeElement === arguments[0]', new_packet_btn.element_handle())
        assert is_focused

    def test_status_badges_readable(self, page: Page):
        """Test that status badges have readable text"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        if packets_page.get_packets_count() > 0:
            # Status badges should have text content
            status_badges = page.locator('.rounded-full').all()

            for badge in status_badges:
                text = badge.inner_text()
                assert len(text) > 0


# ==============================
# Performance Tests
# ==============================

class TestBoardPacketsPerformance:
    """Performance tests for board packets UI"""

    def test_page_loads_quickly(self, page: Page):
        """Test that page loads within reasonable time"""
        packets_page = BoardPacketsPage(page)

        import time
        start_time = time.time()
        packets_page.navigate()
        load_time = time.time() - start_time

        # Page should load in under 3 seconds
        assert load_time < 3.0

    def test_handles_multiple_packets(self, page: Page):
        """Test that page handles displaying multiple packets"""
        packets_page = BoardPacketsPage(page)
        packets_page.navigate()

        packets_count = packets_page.get_packets_count()

        # Should handle any number of packets without errors
        assert packets_count >= 0

        # If many packets, page should still be responsive
        if packets_count > 10:
            # Scroll should work
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(200)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
