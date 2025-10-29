# UI/E2E Tests for Sprints 17-20

Comprehensive Playwright-based browser automation tests for the HOA Accounting System frontend UI.

## Test Coverage

### Sprint 17: Delinquency & Collections (`test_collections_ui.py`)
**43 tests** covering:
- **DelinquencyDashboardPage**: Overview with summary stats, aging breakdown, stage filtering
- **LateFeeRulesPage**: Create/edit/delete late fee rules (flat/percentage/both)
- **CollectionNoticesPage**: View and filter collection notices
- **CollectionActionsPage**: Board approval workflow for legal actions
- **E2E Workflows**: Complete delinquency management workflows
- **Accessibility**: ARIA labels, keyboard navigation

**Key UI Components Tested:**
- Summary cards (Total Delinquent, Total Balance, Avg Days, 90+ Days)
- Stage breakdown visualization
- Delinquent accounts table with aging buckets
- Late fee rules management modal
- Form validation (required fields, numeric inputs)
- Status badges with correct colors

### Sprint 18: Auto-Matching Engine (`test_matching_ui.py`)
**38 tests** covering:
- **TransactionMatchingPage**: AI-powered match suggestions with confidence scores
- **MatchRulesPage**: Auto-match rules configuration
- **MatchStatisticsPage**: Performance dashboard with metrics
- **E2E Workflows**: Accept/reject matches, view statistics
- **Accessibility**: Button titles, keyboard navigation

**Key UI Components Tested:**
- Match cards with confidence score badges (color-coded: 90%+ green, 70-89% yellow, <70% orange)
- Accept/reject action buttons
- Bank transaction vs matched entry comparison
- Match explanations
- Rules table with accuracy tracking
- Statistics metrics (auto-match rate, avg confidence, total matches)

### Sprint 19: Violation Tracking (`test_violations_ui.py`)
**40 tests** covering:
- **ViolationsPage**: List, filter, and manage HOA violations
- **Severity Levels**: Minor (yellow), Moderate (orange), Major (red), Critical (red)
- **Status Workflow**: Reported → Notice Sent → Hearing Scheduled → Resolved
- **Photo Evidence**: Photo count indicators with camera icons
- **Filtering**: Combined severity and status filters
- **Accessibility**: Heading hierarchy, keyboard navigation

**Key UI Components Tested:**
- Violation cards with owner, property address, description
- Severity and status badges (color-coded)
- Fine amounts with currency formatting
- Photo count with camera icon
- Reported date formatting
- Filter dropdowns (severity and status)
- Report Violation button
- Responsive layout (desktop, tablet, mobile)

### Sprint 20: Board Packet Generation (`test_board_packets_ui.py`)
**39 tests** covering:
- **BoardPacketsPage**: Generate and manage board meeting packets
- **PDF Generation**: Generate button for draft packets
- **Email Distribution**: Send button with email prompt
- **Status Workflow**: Draft → Generating → Ready → Sent
- **Metrics Display**: Sections count, page count, recipients count
- **Accessibility**: Button focus, keyboard navigation

**Key UI Components Tested:**
- Packet cards with meeting date and template name
- Status badges (Draft: gray, Generating: blue, Ready: green, Sent: purple)
- Action buttons (Generate, Download, Send) based on status
- Packet metrics (sections, pages, recipients)
- Empty state message
- Responsive layout across devices

## Test Statistics

| Sprint | File | Tests | Lines | Coverage Areas |
|--------|------|-------|-------|----------------|
| **17** | `test_collections_ui.py` | **43** | 870 | Dashboard, Rules, Notices, Actions |
| **18** | `test_matching_ui.py` | **38** | 664 | Matching, Rules, Statistics |
| **19** | `test_violations_ui.py` | **40** | 704 | Violations, Photos, Filters |
| **20** | `test_board_packets_ui.py` | **39** | 726 | Packets, Generation, Distribution |
| **TOTAL** | - | **160** | 2,964 | Complete UI Test Suite |

## Test Patterns

### Page Object Model (POM)
All tests use the Page Object Model pattern for maintainability:

```python
class DelinquencyDashboardPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "http://localhost:3010/delinquency/dashboard"

    def navigate(self):
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def get_total_delinquent(self) -> str:
        return self.page.locator('text="Total Delinquent" ~ p').inner_text()
```

### Test Categories

1. **Functional Tests**: Verify UI components render and function correctly
2. **E2E Workflow Tests**: Test complete user workflows across multiple pages
3. **Responsive Design Tests**: Test layouts on desktop (1920x1080), tablet (768x1024), mobile (375x667)
4. **Accessibility Tests**: Verify ARIA labels, keyboard navigation, focus indicators
5. **Form Validation Tests**: Test input validation and error messages
6. **Filter/Search Tests**: Test filtering and data manipulation
7. **Empty State Tests**: Verify appropriate messages when no data exists

## Running the Tests

### Prerequisites

```bash
# Install Playwright
pip install playwright pytest-playwright

# Install browsers
playwright install chromium
```

### Run All UI Tests

```bash
# Run all UI tests
pytest tests/ui/ -v

# Run with browser visible (for debugging)
pytest tests/ui/ -v --headed

# Run specific sprint
pytest tests/ui/test_collections_ui.py -v
pytest tests/ui/test_matching_ui.py -v
pytest tests/ui/test_violations_ui.py -v
pytest tests/ui/test_board_packets_ui.py -v
```

### Run by Marker

```bash
# Run only collections tests
pytest -m collections -v

# Run only matching tests
pytest -m matching -v

# Run only violations tests
pytest -m violations -v

# Run only board packets tests
pytest -m board_packets -v

# Run only responsive design tests
pytest -m responsive -v

# Run only accessibility tests
pytest -m accessibility -v
```

### Run with Screenshots/Videos

```bash
# Capture screenshots on failure
pytest tests/ui/ --screenshot=only-on-failure

# Record videos
pytest tests/ui/ --video=on
```

## Test Configuration

### Viewport Sizes

- **Desktop**: 1280x720 (default), 1920x1080 (tested)
- **Tablet**: 768x1024 (iPad)
- **Mobile**: 375x667 (iPhone SE)

### Timeouts

- **Default Timeout**: 10 seconds
- **Navigation Timeout**: 30 seconds

### Browser Configuration

- **Browser**: Chromium (headless by default)
- **Slow Motion**: 50ms (for debugging)
- **Locale**: en-US
- **Timezone**: America/New_York

## Fixtures

### `page` (function-scoped)
Basic page fixture with default configuration.

```python
def test_example(page: Page):
    page.goto("http://localhost:3010")
```

### `authenticated_page` (function-scoped)
Pre-authenticated page for protected routes.

```python
def test_protected_route(authenticated_page: Page):
    authenticated_page.goto("http://localhost:3010/dashboard")
```

### `mobile_page` (function-scoped)
Page with mobile viewport (375x667).

```python
def test_mobile_layout(mobile_page: Page):
    mobile_page.goto("http://localhost:3010")
```

### `tablet_page` (function-scoped)
Page with tablet viewport (768x1024).

```python
def test_tablet_layout(tablet_page: Page):
    tablet_page.goto("http://localhost:3010")
```

## Common Test Patterns

### Testing Forms

```python
def test_create_late_fee_rule(page: Page):
    rules_page = LateFeeRulesPage(page)
    rules_page.navigate()
    rules_page.click_add_rule()

    rules_page.fill_rule_form({
        'name': 'Standard Late Fee',
        'grace_period_days': 10,
        'fee_type': 'flat',
        'flat_amount': '25.00'
    })

    rules_page.submit_form()
    expect(page.locator('tr:has-text("Standard Late Fee")')).to_be_visible()
```

### Testing Filters

```python
def test_filter_by_severity(page: Page):
    violations_page = ViolationsPage(page)
    violations_page.navigate()

    violations_page.filter_by_severity('critical')

    # Verify filtered results
    severity_badges = page.locator('.rounded-full:has-text("Critical")').all()
    assert len(severity_badges) > 0
```

### Testing Status Badges

```python
def test_severity_badge_colors(page: Page):
    violations_page = ViolationsPage(page)
    violations_page.navigate()

    critical_badges = page.locator('.rounded-full:has-text("Critical")').all()
    for badge in critical_badges:
        badge_class = badge.get_attribute('class')
        assert 'bg-red-200' in badge_class
```

### Testing E2E Workflows

```python
def test_complete_matching_workflow(page: Page):
    # Step 1: Review matches
    matching_page = TransactionMatchingPage(page)
    matching_page.navigate()
    matching_page.accept_match(0)

    # Step 2: View statistics
    page.goto("http://localhost:3010/matching/statistics")
    expect(page.locator('h1:has-text("Match Statistics")')).to_be_visible()

    # Step 3: Review rules
    page.goto("http://localhost:3010/matching/rules")
    expect(page.locator('h1:has-text("Match Rules")')).to_be_visible()
```

## Debugging Tips

### Run with Browser Visible

```bash
pytest tests/ui/test_collections_ui.py::test_dashboard_loads_successfully -v --headed
```

### Slow Down Execution

```python
# In conftest.py, increase slow_mo value
browser = p.chromium.launch(headless=False, slow_mo=1000)  # 1 second delay
```

### Capture Screenshots

```python
# In a test
page.screenshot(path="debug.png")
```

### Pause Execution

```python
# In a test
page.pause()  # Opens Playwright Inspector
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: UI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
      - name: Run UI tests
        run: pytest tests/ui/ -v --screenshot=only-on-failure
      - name: Upload screenshots
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: screenshots
          path: test-results/
```

## Best Practices

1. **Use Page Object Model**: Encapsulate page interactions in dedicated classes
2. **Wait for Network Idle**: Use `wait_for_load_state("networkidle")` after navigation
3. **Use Locators Wisely**: Prefer role-based selectors, then test IDs, then text content
4. **Handle Dynamic Content**: Use `expect().to_be_visible()` instead of hard waits
5. **Test Accessibility**: Include keyboard navigation and ARIA label tests
6. **Test Responsive Design**: Verify layouts on multiple viewport sizes
7. **Clean Test Data**: Ensure tests don't interfere with each other
8. **Use Meaningful Assertions**: Assert on visible user behavior, not implementation details

## Common Selectors

```python
# By text content
page.locator('h1:has-text("Board Packets")')
page.locator('button:has-text("New Packet")')

# By CSS class
page.locator('.bg-white.rounded-lg.border')
page.locator('.rounded-full:has-text("Critical")')

# By attribute
page.locator('button[title="Accept Match"]')
page.locator('select[name="severity"]')

# By test ID (if added to frontend)
page.locator('[data-testid="delinquency-dashboard"]')

# Nth element
page.locator('button:has-text("Generate")').nth(0)

# All elements
page.locator('.violation-card').all()
```

## Troubleshooting

### Test Fails with "Timeout"
- Increase timeout: `page.set_default_timeout(30000)`
- Wait for network: `page.wait_for_load_state("networkidle")`
- Check if element exists: `expect(locator).to_be_visible()`

### Element Not Found
- Use Playwright Inspector: `page.pause()`
- Verify selector: `page.locator('selector').count()`
- Check for dynamic content loading

### Test Works Locally but Fails in CI
- Ensure browser is installed: `playwright install chromium`
- Use headless mode in CI
- Increase timeouts for slower CI environments

## Test Maintenance

### Adding New Tests

1. Create Page Object Model class if needed
2. Write test using POM methods
3. Add appropriate markers (`@pytest.mark.collections`, etc.)
4. Run test locally with `--headed` for debugging
5. Verify test passes in headless mode

### Updating Tests

1. Update POM methods when UI changes
2. Update selectors to match new UI structure
3. Re-run all tests in affected area
4. Update documentation if test coverage changes

## Related Frontend Commits

- **Sprint 17**: `cf77633` - Delinquency & Collections UI
- **Sprint 18**: `cf77633` - Auto-Matching Engine UI
- **Sprint 19**: `cf77633` - Violation Tracking UI
- **Sprint 20**: `cf77633` - Board Packet Generation UI

All frontend UI for Sprints 17-20 was implemented in commit `cf77633` (Oct 29, 2025).

## Frontend Stack

- **Framework**: React + TypeScript
- **Styling**: Tailwind CSS
- **Icons**: lucide-react
- **Routing**: React Router
- **API Client**: Axios
- **Base URL**: `http://localhost:3010`

## Status

- **Test Files**: 4
- **Total Tests**: 160
- **Total Lines**: 2,964
- **Coverage**: Complete UI test suite for Sprints 17-20
- **Status**: Ready for execution once frontend is running

---

**Last Updated**: 2025-10-29
**Project**: saas202510 (QA/Testing Infrastructure)
**Related Project**: saas202509 (HOA Accounting System)
