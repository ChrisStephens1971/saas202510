"""
Pytest configuration and fixtures.

This file is automatically loaded by pytest and provides
shared fixtures and configuration for all tests.
"""

import pytest
from hypothesis import settings

# Configure Hypothesis settings for financial testing
settings.register_profile(
    "financial",
    max_examples=200,  # More examples for financial correctness
    deadline=10000,  # 10 seconds per test case
    print_blob=True,  # Print failing examples
)

# Use the financial profile by default
settings.load_profile("financial")
