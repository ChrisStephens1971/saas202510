"""
Pytest configuration for UI/E2E tests

Provides Playwright fixtures and configuration for browser testing.
"""

import pytest
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


@pytest.fixture(scope="session")
def browser():
    """
    Session-scoped browser instance.
    Launches Chromium browser for all tests.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,  # Set to False for debugging
            slow_mo=50      # Slow down operations by 50ms for debugging
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser):
    """
    Function-scoped browser context.
    Provides isolated browser context for each test.
    """
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        timezone_id="America/New_York",
        permissions=[],  # No special permissions by default
        record_video_dir=None  # Set to a directory for video recording
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext):
    """
    Function-scoped page instance.
    Provides a new page for each test.
    """
    page = context.new_page()

    # Set default timeout
    page.set_default_timeout(10000)  # 10 seconds

    # Set default navigation timeout
    page.set_default_navigation_timeout(30000)  # 30 seconds

    yield page
    page.close()


@pytest.fixture(scope="function")
def authenticated_page(page: Page):
    """
    Authenticated page fixture.
    Logs in the user before running tests that require authentication.
    """
    # Navigate to login page
    page.goto("http://localhost:3010/login")

    # Fill in login credentials (adjust selectors as needed)
    page.fill('input[name="email"]', "test@example.com")
    page.fill('input[name="password"]', "testpassword123")

    # Submit login form
    page.click('button[type="submit"]')

    # Wait for navigation to complete
    page.wait_for_load_state("networkidle")

    yield page


@pytest.fixture(scope="function")
def mobile_page(browser: Browser):
    """
    Mobile viewport page fixture.
    Provides a page with mobile viewport dimensions.
    """
    context = browser.new_context(
        viewport={"width": 375, "height": 667},  # iPhone SE dimensions
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True
    )
    page = context.new_page()
    page.set_default_timeout(10000)

    yield page

    page.close()
    context.close()


@pytest.fixture(scope="function")
def tablet_page(browser: Browser):
    """
    Tablet viewport page fixture.
    Provides a page with tablet viewport dimensions.
    """
    context = browser.new_context(
        viewport={"width": 768, "height": 1024},  # iPad dimensions
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True
    )
    page = context.new_page()
    page.set_default_timeout(10000)

    yield page

    page.close()
    context.close()


# Pytest configuration
def pytest_configure(config):
    """
    Pytest configuration hook.
    Registers custom markers for UI tests.
    """
    config.addinivalue_line(
        "markers", "ui: UI/E2E tests using Playwright"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests"
    )
    config.addinivalue_line(
        "markers", "collections: Delinquency & Collections UI tests (Sprint 17)"
    )
    config.addinivalue_line(
        "markers", "matching: Auto-Matching Engine UI tests (Sprint 18)"
    )
    config.addinivalue_line(
        "markers", "violations: Violation Tracking UI tests (Sprint 19)"
    )
    config.addinivalue_line(
        "markers", "board_packets: Board Packet Generation UI tests (Sprint 20)"
    )
    config.addinivalue_line(
        "markers", "responsive: Responsive design tests"
    )
    config.addinivalue_line(
        "markers", "accessibility: Accessibility tests"
    )


# Pytest collection hook
def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers automatically.
    """
    for item in items:
        # Add UI marker to all tests in this directory
        if "ui" in str(item.fspath):
            item.add_marker(pytest.mark.ui)

        # Add sprint-specific markers based on file name
        if "collections" in str(item.fspath):
            item.add_marker(pytest.mark.collections)
        elif "matching" in str(item.fspath):
            item.add_marker(pytest.mark.matching)
        elif "violations" in str(item.fspath):
            item.add_marker(pytest.mark.violations)
        elif "board_packets" in str(item.fspath):
            item.add_marker(pytest.mark.board_packets)

        # Add markers based on test name
        if "responsive" in item.name.lower():
            item.add_marker(pytest.mark.responsive)
        if "accessibility" in item.name.lower():
            item.add_marker(pytest.mark.accessibility)
        if "e2e" in item.name.lower():
            item.add_marker(pytest.mark.slow)
