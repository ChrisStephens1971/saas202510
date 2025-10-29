# GitHub Actions Workflows

This directory contains automated CI/CD workflows for the QA/Testing Infrastructure project.

## Workflows

### Test Suite (`test.yml`)

**Purpose:** Automated testing on every push and pull request

**Triggers:**
- Push to `master`, `main`, or `develop` branches
- Pull requests targeting `master`, `main`, or `develop` branches

**Jobs:**

#### 1. Test Job (Matrix Build)
Runs the complete test suite across multiple Python versions.

**Python Versions:**
- Python 3.11
- Python 3.12

**Steps:**
1. **Checkout code** - Retrieves latest code from repository
2. **Set up Python** - Installs specified Python version with pip caching
3. **Install dependencies** - Installs project with dev dependencies
4. **Run linting** - Checks code quality with `ruff` (continues on error)
5. **Run type checking** - Validates types with `mypy` (continues on error)
6. **Run test suite** - Executes all tests with pytest
7. **Run integration tests** - Runs integration test suite
8. **Run property-based tests** - Runs Hypothesis property-based tests
9. **Generate coverage** - Creates coverage report (XML format)
10. **Upload to Codecov** - Uploads coverage data (optional)
11. **Test summary** - Adds results to GitHub Actions summary

**Exit Criteria:**
- All pytest tests must pass
- Linting and type checking are informational only (won't fail build)
- Coverage upload is optional

#### 2. Data Type Validation Job
Verifies compliance with strict data type requirements.

**Depends on:** Test job must pass first

**Validates:**
- ✅ All money amounts use `Decimal` (not float)
- ✅ All dates use `date` type (not datetime)
- ✅ All Decimal amounts have exactly 2 decimal places (NUMERIC(15,2) compliance)

**Tests run:**
```bash
pytest tests/ -k "test_.*_use_decimal" -v
pytest tests/ -k "test_.*_dates_use_date" -v
pytest tests/ -k "test_.*_decimal_with_2_places" -v
```

**Exit Criteria:** All data type validation tests must pass (strict)

#### 3. Compliance Tests Job
Runs financial compliance verification tests.

**Depends on:** Test job must pass first

**Validates:**
- Audit trail immutability
- Point-in-time reconstruction
- Double-entry bookkeeping rules
- Tenant isolation

**Tests run:**
```bash
pytest tests/compliance/ -v --tb=short
```

**Exit Criteria:** All compliance tests must pass (strict)

## Test Coverage

Current test coverage (as of latest run):
- **97 tests** across all suites
- **Sprint 10:** Budget Management (35 tests)
- **Sprint 11:** Dashboard Metrics (22 tests)
- **Sprint 12:** Bank Reconciliation (18 tests)
- **Sprint 13:** Funds Management (22 tests)

## Running Tests Locally

Before pushing, run the same tests that CI runs:

```bash
# Full test suite
pytest tests/ -v

# Integration tests only
pytest tests/integration/ -v

# Property-based tests only
pytest tests/property/ -v

# Compliance tests only
pytest tests/compliance/ -v

# Data type validation
pytest tests/ -k "test_.*_use_decimal" -v
pytest tests/ -k "test_.*_dates_use_date" -v

# With coverage
pytest tests/ --cov=src/qa_testing --cov-report=term-missing
```

## Viewing Results

**GitHub Actions UI:**
1. Go to repository on GitHub
2. Click "Actions" tab
3. Select a workflow run to view details
4. Expand jobs to see step-by-step results

**Test Summary:**
Each run generates a summary with:
- Python version tested
- Number of tests passed/failed
- Coverage percentage (if generated)
- Links to detailed logs

## Debugging Failed Tests

**View logs:**
1. Click on failed job in Actions UI
2. Expand the failing step
3. Review pytest output with `-v` verbosity

**Common failures:**
- **Data type errors:** Check that Decimal has 2 places, dates are `date` not `datetime`
- **Import errors:** Ensure all dependencies in `pyproject.toml`
- **Hypothesis failures:** Review property-based test invariants

## Adding New Tests

When adding tests:
1. ✅ Follow existing patterns in `tests/integration/` or `tests/property/`
2. ✅ Use `Decimal` for all money amounts
3. ✅ Use `date` for all dates
4. ✅ Add to appropriate test class
5. ✅ Run locally before pushing
6. ✅ CI will automatically run on push

## Performance

**Typical run times:**
- Full test suite: ~7-10 seconds
- Integration tests: ~4-5 seconds
- Property-based tests: ~3-4 seconds
- Compliance tests: ~2-3 seconds

**Optimizations:**
- Pip caching enabled (faster dependency installation)
- Matrix build parallelizes Python version testing
- Job dependencies optimize workflow execution order

## Future Enhancements

Planned improvements:
- [ ] PostgreSQL service container for integration tests
- [ ] Performance benchmarking with large datasets
- [ ] E2E tests with frontend + backend
- [ ] Nightly builds for extended test suites
- [ ] Automated deployment to test environment
- [ ] Slack/email notifications on test failures

## Troubleshooting

**Issue: Tests pass locally but fail in CI**
- Check Python version (CI runs 3.11 and 3.12)
- Review environment differences
- Check for hardcoded paths or absolute imports

**Issue: Dependencies not installing**
- Verify `pyproject.toml` has all required packages
- Check for version conflicts
- Review pip cache issues

**Issue: Timeout errors**
- Increase timeout in workflow if needed
- Optimize slow tests
- Consider splitting into smaller jobs

## Related Documentation

- **Test Completion Summary:** `docs/TEST-COMPLETION-SUMMARY.md`
- **Project Setup:** `CLAUDE.md`
- **Main README:** `README.md`
- **Contributing:** `CONTRIBUTING.md`

---

**Last Updated:** 2025-10-28
**Maintained by:** QA/Testing Infrastructure Team
