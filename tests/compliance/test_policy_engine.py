"""
Tests for Policy Engine

Covers:
- Policy registration and management
- Policy evaluation
- Violation detection
- Severity classification
- Compliance report generation
- Transaction and ledger entry checking
- Standard policies
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from qa_testing.compliance import (
    CompliancePolicy,
    PolicyCategory,
    PolicyEngine,
    Severity,
    Violation,
)


@pytest.fixture
def engine():
    """Create a fresh policy engine."""
    return PolicyEngine()


@pytest.fixture
def tenant_id():
    """Create a test tenant ID."""
    return uuid4()


@pytest.fixture
def sample_policy():
    """Create a sample policy."""
    return CompliancePolicy(
        name="Test Policy",
        description="Test policy for validation",
        category=PolicyCategory.ACCOUNTING,
        rule="amount > 0",
        severity=Severity.ERROR
    )


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    return {
        "id": uuid4(),
        "entity_type": "Transaction",
        "amount": 100,
        "account_code": "1100",
        "description": "Test transaction"
    }


# ==============================================================================
# Test Policy Registration
# ==============================================================================

class TestPolicyRegistration:
    """Test policy registration and management."""

    def test_register_policy(self, engine, sample_policy):
        """Test registering a policy."""
        engine.register_policy(sample_policy)

        retrieved = engine.get_policy(sample_policy.policy_id)
        assert retrieved is not None
        assert retrieved.name == sample_policy.name

    def test_unregister_policy(self, engine, sample_policy):
        """Test unregistering a policy."""
        engine.register_policy(sample_policy)
        engine.unregister_policy(sample_policy.policy_id)

        retrieved = engine.get_policy(sample_policy.policy_id)
        assert retrieved is None

    def test_list_all_policies(self, engine):
        """Test listing all policies."""
        policy1 = CompliancePolicy(
            name="Policy 1",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="True",
            severity=Severity.ERROR
        )
        policy2 = CompliancePolicy(
            name="Policy 2",
            description="Test",
            category=PolicyCategory.FINANCIAL,
            rule="True",
            severity=Severity.WARNING
        )

        engine.register_policy(policy1)
        engine.register_policy(policy2)

        policies = engine.list_policies()
        assert len(policies) == 2

    def test_list_policies_by_category(self, engine):
        """Test filtering policies by category."""
        accounting_policy = CompliancePolicy(
            name="Accounting Policy",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="True",
            severity=Severity.ERROR
        )
        financial_policy = CompliancePolicy(
            name="Financial Policy",
            description="Test",
            category=PolicyCategory.FINANCIAL,
            rule="True",
            severity=Severity.WARNING
        )

        engine.register_policy(accounting_policy)
        engine.register_policy(financial_policy)

        accounting_policies = engine.list_policies(category=PolicyCategory.ACCOUNTING)
        assert len(accounting_policies) == 1
        assert accounting_policies[0].name == "Accounting Policy"

    def test_list_enabled_policies_only(self, engine):
        """Test listing only enabled policies."""
        enabled_policy = CompliancePolicy(
            name="Enabled",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="True",
            severity=Severity.ERROR,
            enabled=True
        )
        disabled_policy = CompliancePolicy(
            name="Disabled",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="True",
            severity=Severity.ERROR,
            enabled=False
        )

        engine.register_policy(enabled_policy)
        engine.register_policy(disabled_policy)

        policies = engine.list_policies(enabled_only=True)
        assert len(policies) == 1
        assert policies[0].name == "Enabled"


# ==============================================================================
# Test Policy Evaluation
# ==============================================================================

class TestPolicyEvaluation:
    """Test policy evaluation against entities."""

    def test_evaluate_passing_policy(self, engine):
        """Test evaluating an entity that passes policy."""
        policy = CompliancePolicy(
            name="Positive Amount",
            description="Amount must be positive",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        engine.register_policy(policy)

        entity = {"amount": 100, "id": uuid4()}
        violations = engine.evaluate(entity, [policy])

        assert len(violations) == 0

    def test_evaluate_failing_policy(self, engine):
        """Test evaluating an entity that fails policy."""
        policy = CompliancePolicy(
            name="Positive Amount",
            description="Amount must be positive",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        engine.register_policy(policy)

        entity = {"amount": -100, "id": uuid4()}
        violations = engine.evaluate(entity, [policy])

        assert len(violations) == 1
        assert violations[0].policy_name == "Positive Amount"
        assert violations[0].severity == Severity.ERROR

    def test_evaluate_multiple_policies(self, engine):
        """Test evaluating against multiple policies."""
        policy1 = CompliancePolicy(
            name="Policy 1",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        policy2 = CompliancePolicy(
            name="Policy 2",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount < 1000",
            severity=Severity.WARNING
        )

        entity = {"amount": 1500, "id": uuid4()}
        violations = engine.evaluate(entity, [policy1, policy2])

        # Should pass policy1 but fail policy2
        assert len(violations) == 1
        assert violations[0].policy_name == "Policy 2"

    def test_evaluate_with_decimal_amounts(self, engine):
        """Test evaluation with Decimal amounts."""
        policy = CompliancePolicy(
            name="Amount Limit",
            description="Amount must not exceed 1000",
            category=PolicyCategory.FINANCIAL,
            rule="Decimal(str(amount)) <= Decimal('1000')",
            severity=Severity.ERROR
        )

        entity = {"amount": "500.50", "id": uuid4()}
        violations = engine.evaluate(entity, [policy])

        assert len(violations) == 0

    def test_evaluate_complex_rule(self, engine):
        """Test evaluation with complex rule."""
        policy = CompliancePolicy(
            name="Approval Required",
            description="Large amounts require approval",
            category=PolicyCategory.FINANCIAL,
            rule="Decimal(str(amount)) <= Decimal('10000') or approved_by is not None",
            severity=Severity.ERROR
        )

        # Should fail - amount > 10000 and no approval
        entity1 = {"amount": "15000", "approved_by": None, "id": uuid4()}
        violations1 = engine.evaluate(entity1, [policy])
        assert len(violations1) == 1

        # Should pass - amount > 10000 but has approval
        entity2 = {"amount": "15000", "approved_by": "admin", "id": uuid4()}
        violations2 = engine.evaluate(entity2, [policy])
        assert len(violations2) == 0

    def test_evaluate_with_error_handling(self, engine):
        """Test that evaluation errors are caught and reported."""
        policy = CompliancePolicy(
            name="Invalid Rule",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="nonexistent_field > 0",  # This will cause an error
            severity=Severity.ERROR
        )

        entity = {"amount": 100, "id": uuid4()}
        violations = engine.evaluate(entity, [policy])

        # Should have a critical violation due to evaluation error
        assert len(violations) == 1
        assert violations[0].severity == Severity.CRITICAL


# ==============================================================================
# Test Violation Detection
# ==============================================================================

class TestViolationDetection:
    """Test violation detection and tracking."""

    def test_violation_contains_details(self, engine):
        """Test that violations contain detailed information."""
        policy = CompliancePolicy(
            name="Test Policy",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )

        entity = {
            "id": uuid4(),
            "entity_type": "Transaction",
            "amount": -100
        }

        violations = engine.evaluate(entity, [policy])

        assert len(violations) == 1
        violation = violations[0]

        assert violation.policy_id == policy.policy_id
        assert violation.policy_name == policy.name
        assert violation.severity == Severity.ERROR
        assert violation.entity_id == entity["id"]
        assert "rule" in violation.details
        assert "entity" in violation.details

    def test_get_violations_unfiltered(self, engine):
        """Test getting all violations."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="False",  # Always fails
            severity=Severity.ERROR
        )

        entity1 = {"id": uuid4(), "amount": 100}
        entity2 = {"id": uuid4(), "amount": 200}

        engine.evaluate(entity1, [policy])
        engine.evaluate(entity2, [policy])

        violations = engine.get_violations()
        assert len(violations) == 2

    def test_get_violations_by_entity(self, engine):
        """Test filtering violations by entity."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="False",
            severity=Severity.ERROR
        )

        entity_id1 = uuid4()
        entity_id2 = uuid4()

        engine.evaluate({"id": entity_id1, "amount": 100}, [policy])
        engine.evaluate({"id": entity_id2, "amount": 200}, [policy])

        violations = engine.get_violations(entity_id=entity_id1)
        assert len(violations) == 1
        assert violations[0].entity_id == entity_id1

    def test_get_violations_by_severity(self, engine):
        """Test filtering violations by severity."""
        error_policy = CompliancePolicy(
            name="Error",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="False",
            severity=Severity.ERROR
        )
        warning_policy = CompliancePolicy(
            name="Warning",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="False",
            severity=Severity.WARNING
        )

        entity = {"id": uuid4(), "amount": 100}

        engine.evaluate(entity, [error_policy, warning_policy])

        errors = engine.get_violations(severity=Severity.ERROR)
        warnings = engine.get_violations(severity=Severity.WARNING)

        assert len(errors) == 1
        assert len(warnings) == 1

    def test_resolve_violation(self, engine):
        """Test resolving a violation."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="False",
            severity=Severity.ERROR
        )

        entity = {"id": uuid4(), "amount": 100}
        violations = engine.evaluate(entity, [policy])

        violation_id = violations[0].violation_id
        resolved = engine.resolve_violation(violation_id, "admin")

        assert resolved is not None
        assert resolved.resolved is True
        assert resolved.resolved_by == "admin"
        assert resolved.resolved_at is not None


# ==============================================================================
# Test Compliance Reports
# ==============================================================================

class TestComplianceReports:
    """Test compliance report generation."""

    def test_generate_report_all_passing(self, engine, tenant_id):
        """Test generating report when all entities pass."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        engine.register_policy(policy)

        entities = [
            {"id": uuid4(), "amount": 100},
            {"id": uuid4(), "amount": 200},
        ]

        report = engine.generate_compliance_report(tenant_id, entities, [policy])

        assert report.passed is True
        assert report.violations_found == 0
        assert len(report.violations) == 0

    def test_generate_report_with_violations(self, engine, tenant_id):
        """Test generating report with violations."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        engine.register_policy(policy)

        entities = [
            {"id": uuid4(), "amount": 100},
            {"id": uuid4(), "amount": -50},  # Violation
            {"id": uuid4(), "amount": 200},
        ]

        report = engine.generate_compliance_report(tenant_id, entities, [policy])

        assert report.passed is False
        assert report.violations_found == 1
        assert len(report.violations) == 1

    def test_report_counts_by_severity(self, engine, tenant_id):
        """Test that report counts violations by severity."""
        error_policy = CompliancePolicy(
            name="Error",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        warning_policy = CompliancePolicy(
            name="Warning",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount < 1000",
            severity=Severity.WARNING
        )
        engine.register_policy(error_policy)
        engine.register_policy(warning_policy)

        entities = [
            {"id": uuid4(), "amount": -50},  # Error
            {"id": uuid4(), "amount": 1500},  # Warning
        ]

        report = engine.generate_compliance_report(tenant_id, entities, [error_policy, warning_policy])

        assert report.violations_by_severity["error"] == 1
        assert report.violations_by_severity["warning"] == 1


# ==============================================================================
# Test Specific Check Methods
# ==============================================================================

class TestSpecificChecks:
    """Test transaction and ledger entry checking."""

    def test_check_transaction(self, engine, tenant_id):
        """Test checking a transaction."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        engine.register_policy(policy)

        transaction = {"id": uuid4(), "amount": -100}
        violations = engine.check_transaction(transaction, tenant_id)

        assert len(violations) == 1

    def test_check_ledger_entry(self, engine, tenant_id):
        """Test checking a ledger entry."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="amount > 0",
            severity=Severity.ERROR
        )
        engine.register_policy(policy)

        entry = {"id": uuid4(), "amount": -100}
        violations = engine.check_ledger_entry(entry, tenant_id)

        assert len(violations) == 1


# ==============================================================================
# Test Standard Policies
# ==============================================================================

class TestStandardPolicies:
    """Test standard policy creation."""

    def test_create_standard_policies(self):
        """Test creating standard policies."""
        policies = PolicyEngine.create_standard_policies()

        assert len(policies) > 0

        # Verify we have policies for different categories
        categories = {p.category for p in policies}
        assert PolicyCategory.ACCOUNTING in categories
        assert PolicyCategory.FINANCIAL in categories

        # Verify we have policies with different severities
        severities = {p.severity for p in policies}
        assert Severity.CRITICAL in severities
        assert Severity.ERROR in severities
        assert Severity.WARNING in severities

    def test_standard_policy_no_negative_balance(self):
        """Test the no negative balance policy."""
        engine = PolicyEngine()
        policies = PolicyEngine.create_standard_policies()

        # Find the no negative balance policy
        policy = next((p for p in policies if "Negative Balance" in p.name), None)
        assert policy is not None

        engine.register_policy(policy)

        # Test with negative balance
        entity = {"id": uuid4(), "balance": "-100.00"}
        violations = engine.evaluate(entity, [policy])
        assert len(violations) == 1

        # Test with positive balance
        entity = {"id": uuid4(), "balance": "100.00"}
        violations = engine.evaluate(entity, [policy])
        assert len(violations) == 0

    def test_standard_policy_amount_limit(self):
        """Test the transaction amount limit policy."""
        engine = PolicyEngine()
        policies = PolicyEngine.create_standard_policies()

        policy = next((p for p in policies if "Amount Limit" in p.name), None)
        assert policy is not None

        engine.register_policy(policy)

        # Test exceeding limit
        entity = {"id": uuid4(), "amount": "150000"}
        violations = engine.evaluate(entity, [policy])
        assert len(violations) == 1

        # Test within limit
        entity = {"id": uuid4(), "amount": "50000"}
        violations = engine.evaluate(entity, [policy])
        assert len(violations) == 0

    def test_standard_policy_required_approval(self):
        """Test the required approval policy."""
        engine = PolicyEngine()
        policies = PolicyEngine.create_standard_policies()

        policy = next((p for p in policies if "Required Approval" in p.name), None)
        assert policy is not None

        engine.register_policy(policy)

        # Test large amount without approval
        entity = {"id": uuid4(), "amount": "15000", "approved_by": None}
        violations = engine.evaluate(entity, [policy])
        assert len(violations) == 1

        # Test large amount with approval
        entity = {"id": uuid4(), "amount": "15000", "approved_by": "admin"}
        violations = engine.evaluate(entity, [policy])
        assert len(violations) == 0

        # Test small amount without approval (should pass)
        entity = {"id": uuid4(), "amount": "5000", "approved_by": None}
        violations = engine.evaluate(entity, [policy])
        assert len(violations) == 0


# ==============================================================================
# Test Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_evaluate_empty_entity(self, engine):
        """Test evaluating an empty entity."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="True",
            severity=Severity.ERROR
        )

        violations = engine.evaluate({}, [policy])
        assert len(violations) == 0

    def test_evaluate_with_no_policies(self, engine):
        """Test evaluating with no policies."""
        entity = {"id": uuid4(), "amount": 100}
        violations = engine.evaluate(entity, [])

        assert len(violations) == 0

    def test_clear_violations(self, engine):
        """Test clearing all violations."""
        policy = CompliancePolicy(
            name="Test",
            description="Test",
            category=PolicyCategory.ACCOUNTING,
            rule="False",
            severity=Severity.ERROR
        )

        engine.evaluate({"id": uuid4(), "amount": 100}, [policy])
        assert len(engine.get_violations()) == 1

        engine.clear_violations()
        assert len(engine.get_violations()) == 0

    def test_resolve_nonexistent_violation(self, engine):
        """Test resolving a violation that doesn't exist."""
        fake_id = uuid4()
        result = engine.resolve_violation(fake_id, "admin")

        assert result is None
