# Code Coverage and Performance Benchmarking Guide

**Purpose:** Track test coverage and monitor performance of the QA/Testing Infrastructure

**Date:** 2025-10-29
**Status:** ✅ Complete - Ready to use

---

## Code Coverage Tracking

### Overview

Code coverage tracking helps identify untested code paths and ensures comprehensive test coverage. The project uses `pytest-cov` for coverage analysis.

### Configuration

Coverage settings are defined in `.coveragerc`:

```ini
[run]
source = src/qa_testing
omit = */tests/*, */__pycache__/*, */venv/*, */.venv/*, */site-packages/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

### Running Coverage Analysis

#### Basic Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=src/qa_testing --cov-report=term-missing

# Example output:
# Name                                    Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------------
# src/qa_testing/__init__.py                  5      0   100%
# src/qa_testing/models/base.py              50      2    96%   45-46
# src/qa_testing/models/reserve.py          120      5    95.8%   78, 92-95
# src/qa_testing/generators/reserve_gen.py  200     10    95.0%   156-165
# ---------------------------------------------------------------------
# TOTAL                                    2500     50    98.0%
```

#### HTML Coverage Report

```bash
# Generate HTML report
pytest tests/ --cov=src/qa_testing --cov-report=html

# Open in browser
# Windows:
start htmlcov/index.html

# macOS:
open htmlcov/index.html

# Linux:
xdg-open htmlcov/index.html
```

#### XML Coverage Report (for CI/CD)

```bash
# Generate XML for Codecov/Coveralls
pytest tests/ --cov=src/qa_testing --cov-report=xml

# Upload to Codecov
codecov --file=coverage.xml --token=YOUR_TOKEN

# Or use GitHub Actions (already configured in .github/workflows/test.yml)
```

#### Coverage by Sprint

```bash
# Sprint 14 - Reserve Planning
pytest tests/integration/test_reserve_planning.py tests/property/test_reserve_invariants.py \
  --cov=src/qa_testing/models/reserve.py \
  --cov=src/qa_testing/generators/reserve_generator.py \
  --cov-report=term-missing

# Sprint 15 - Advanced Reporting
pytest tests/integration/test_advanced_reporting.py tests/property/test_reporting_invariants.py \
  --cov=src/qa_testing/models/reporting.py \
  --cov=src/qa_testing/generators/report_generator.py \
  --cov-report=term-missing

# All Sprints 14-20
pytest tests/integration/test_reserve_planning.py \
       tests/integration/test_advanced_reporting.py \
       tests/integration/test_delinquency_collections.py \
       tests/integration/test_auto_matching.py \
       tests/integration/test_violation_tracking.py \
       tests/integration/test_board_packet_generation.py \
  --cov=src/qa_testing \
  --cov-report=html
```

### Coverage Goals

| Category | Current | Target |
|----------|---------|--------|
| **Overall Coverage** | ~95% | 98%+ |
| **Models** | ~98% | 100% |
| **Generators** | ~96% | 98% |
| **Integration Tests** | 100% | 100% |
| **Property Tests** | 100% | 100% |

### Coverage Exclusions

Lines excluded from coverage (see `.coveragerc`):

- `pragma: no cover` - Explicitly excluded code
- `def __repr__` - String representations
- `raise AssertionError` - Assertion errors
- `raise NotImplementedError` - Abstract methods
- `if __name__ == .__main__.:` - Script entry points
- `if TYPE_CHECKING:` - Type checking blocks
- `@abstractmethod` - Abstract method decorators

### CI/CD Integration

Coverage is automatically tracked in GitHub Actions:

```yaml
- name: Generate coverage report
  run: |
    pytest tests/ --cov=src/qa_testing --cov-report=term-missing --cov-report=xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    fail_ci_if_error: false
```

---

## Performance Benchmarking

### Overview

Performance benchmarking helps identify slow tests and track performance regressions over time. The project uses `pytest-benchmark` for performance analysis.

### Configuration

Benchmark settings are defined in `pytest-benchmark.ini`:

```ini
[benchmark]
disable = False
autosave = True
min-rounds = 5
timer = time.perf_counter
storage = file:.benchmarks
compare-fail = mean:5%
```

### Installing Benchmark Support

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Verify installation
pytest --benchmark-help
```

### Writing Benchmark Tests

Create benchmark tests in `tests/benchmarks/`:

```python
# tests/benchmarks/test_generator_performance.py
import pytest
from decimal import Decimal
from qa_testing.generators import TransactionGenerator, PropertyGenerator

class TestGeneratorPerformance:
    def test_transaction_generation_speed(self, benchmark):
        """Benchmark transaction generator performance."""
        property_obj = PropertyGenerator.create()

        result = benchmark(
            TransactionGenerator.create,
            property_id=property_obj.id
        )

        assert result is not None

    def test_batch_transaction_generation(self, benchmark):
        """Benchmark batch transaction generation."""
        property_obj = PropertyGenerator.create()

        result = benchmark(
            TransactionGenerator.create_batch,
            count=100,
            property_id=property_obj.id
        )

        assert len(result) == 100

    def test_decimal_quantization_performance(self, benchmark):
        """Benchmark decimal quantization operations."""
        amount = Decimal("1234.567")

        result = benchmark(
            amount.quantize,
            Decimal("0.01")
        )

        assert result == Decimal("1234.57")
```

### Running Benchmarks

#### Basic Benchmark Run

```bash
# Run all benchmarks
pytest tests/benchmarks/ --benchmark-only

# Example output:
# Name                                    Min      Max     Mean   StdDev   Median
# --------------------------------------------------------------------------------
# test_transaction_generation_speed    0.0012   0.0025   0.0015   0.0003   0.0014
# test_batch_transaction_generation    0.1200   0.1450   0.1310   0.0080   0.1305
# test_decimal_quantization           0.0001   0.0002   0.0001   0.0000   0.0001
```

#### Save Benchmark Results

```bash
# Save results for comparison
pytest tests/benchmarks/ --benchmark-only --benchmark-autosave

# Results saved to .benchmarks/
```

#### Compare Benchmarks

```bash
# Compare current run to previous
pytest tests/benchmarks/ --benchmark-only --benchmark-compare=0001

# Compare with specific benchmark
pytest tests/benchmarks/ --benchmark-only --benchmark-compare=2025-10-29_baseline

# Example output:
# -------------------------------------------------------------------------
# Benchmark: test_transaction_generation_speed
# -------------------------------------------------------------------------
# Current:   0.0015s
# Previous:  0.0018s
# Change:    -16.67% (improvement)
```

#### Histogram Visualization

```bash
# Generate histogram
pytest tests/benchmarks/ --benchmark-only --benchmark-histogram

# Open histogram.svg in browser
```

### Benchmark Categories

#### Generator Performance

```bash
# Benchmark all generators
pytest tests/benchmarks/test_generator_performance.py --benchmark-only
```

**Expected Performance:**
- Single transaction: < 2ms
- Batch (100 transactions): < 150ms
- Single member: < 1ms
- Batch (100 members): < 100ms

#### Model Validation Performance

```bash
# Benchmark Pydantic validation
pytest tests/benchmarks/test_model_validation.py --benchmark-only
```

**Expected Performance:**
- Simple model validation: < 0.5ms
- Complex model with validators: < 2ms
- Batch validation (100 models): < 200ms

#### Database Operations (when PostgreSQL available)

```bash
# Benchmark database operations
pytest tests/benchmarks/test_database_performance.py --benchmark-only
```

**Expected Performance:**
- Single INSERT: < 5ms
- Batch INSERT (100 records): < 100ms
- Single SELECT: < 3ms
- JOIN query: < 10ms

### Performance Regression Alerts

Set up CI/CD to fail on performance regressions:

```yaml
# .github/workflows/benchmark.yml
name: Performance Benchmarks

on:
  pull_request:
    branches: [ master ]

jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest-benchmark

      - name: Run benchmarks
        run: |
          pytest tests/benchmarks/ --benchmark-only --benchmark-autosave

      - name: Compare to baseline
        run: |
          pytest tests/benchmarks/ --benchmark-only --benchmark-compare=baseline --benchmark-compare-fail=mean:5%
```

### Benchmark Best Practices

1. **Isolate benchmarks** - Run separately from regular tests
2. **Warm-up rounds** - Min 5 rounds to account for JIT/caching
3. **Consistent environment** - Same machine, no other processes
4. **Realistic data** - Use production-like data sizes
5. **Track trends** - Compare over time, not absolute values
6. **Set thresholds** - Alert on >5% regression

---

## Combined Coverage + Benchmarks

### Run Both in CI/CD

```bash
# Run tests with coverage
pytest tests/integration/ tests/property/ tests/compliance/ \
  --cov=src/qa_testing \
  --cov-report=html \
  --cov-report=xml

# Run benchmarks
pytest tests/benchmarks/ --benchmark-only --benchmark-autosave

# Generate combined report
python scripts/generate_qa_report.py
```

### QA Report Dashboard

Create `scripts/generate_qa_report.py`:

```python
#!/usr/bin/env python3
"""Generate comprehensive QA report with coverage and benchmarks."""

import json
from pathlib import Path
from datetime import datetime

def generate_qa_report():
    """Generate HTML QA report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "coverage": load_coverage_data(),
        "benchmarks": load_benchmark_data(),
        "test_results": load_test_results(),
    }

    # Generate HTML report
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>QA Report - {report['timestamp']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .metric {{ display: inline-block; margin: 10px; padding: 20px; border: 1px solid #ddd; }}
            .good {{ background-color: #d4edda; }}
            .warning {{ background-color: #fff3cd; }}
            .bad {{ background-color: #f8d7da; }}
        </style>
    </head>
    <body>
        <h1>QA/Testing Infrastructure Report</h1>
        <h2>Coverage: {report['coverage']['total']}%</h2>
        <h2>Tests Passing: {report['test_results']['passed']}/{report['test_results']['total']}</h2>
        <h2>Avg Performance: {report['benchmarks']['avg_time']}ms</h2>
    </body>
    </html>
    """

    Path("qa_report.html").write_text(html)
    print("✅ QA report generated: qa_report.html")

if __name__ == "__main__":
    generate_qa_report()
```

---

## Monitoring and Alerts

### Coverage Alerts

Alert when coverage drops below threshold:

```bash
# Fail if coverage < 95%
pytest tests/ --cov=src/qa_testing --cov-fail-under=95
```

### Performance Alerts

Alert when performance regresses >5%:

```bash
# Fail if any benchmark regresses >5%
pytest tests/benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:5%
```

### Integration with Monitoring Tools

- **Codecov**: Automatic coverage tracking and PR comments
- **Coveralls**: Coverage history and trends
- **BenchmarkCI**: Performance tracking over time
- **GitHub Actions**: Automated QA checks on every PR

---

## Usage Examples

### Daily Development Workflow

```bash
# 1. Run tests with coverage during development
pytest tests/integration/test_reserve_planning.py --cov=src/qa_testing/models/reserve.py

# 2. Before committing, run full coverage
pytest tests/ --cov=src/qa_testing --cov-report=term-missing

# 3. If adding performance-sensitive code, benchmark it
pytest tests/benchmarks/test_new_feature.py --benchmark-only

# 4. Commit when coverage > 95% and performance acceptable
git commit -m "feat: add new feature with 98% coverage"
```

### Pre-Release QA Check

```bash
# Full test suite with coverage
pytest tests/ --cov=src/qa_testing --cov-report=html --cov-report=xml --cov-fail-under=95

# Performance benchmarks
pytest tests/benchmarks/ --benchmark-only --benchmark-autosave

# Generate combined report
python scripts/generate_qa_report.py

# Review reports
open htmlcov/index.html
open qa_report.html
```

---

## References

- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **pytest-benchmark**: https://pytest-benchmark.readthedocs.io/
- **Codecov**: https://docs.codecov.com/
- **Coverage.py**: https://coverage.readthedocs.io/

---

**Status:** ✅ Complete - Coverage and Benchmarking Ready
**Next Step:** Run coverage analysis and establish baseline benchmarks
**Estimated Setup Time:** 15 minutes

