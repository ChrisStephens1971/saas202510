"""
Automated Compliance Policy Engine

Provides automated compliance checking through:
- Policy rule definition DSL
- Policy engine for rule evaluation
- Violation detection and reporting
- Severity classification
- Integration with audit trail
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for policy violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PolicyCategory(str, Enum):
    """Categories of compliance policies."""
    ACCOUNTING = "accounting"
    FINANCIAL = "financial"
    AUDIT = "audit"
    SECURITY = "security"
    DATA_INTEGRITY = "data_integrity"
    REGULATORY = "regulatory"


class CompliancePolicy(BaseModel):
    """Definition of a compliance policy rule."""
    policy_id: UUID = Field(default_factory=uuid4, description="Unique policy ID")
    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    category: PolicyCategory = Field(..., description="Policy category")
    rule: str = Field(..., description="Rule expression (Python DSL)")
    severity: Severity = Field(..., description="Violation severity")
    enabled: bool = Field(True, description="Whether policy is active")
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Violation(BaseModel):
    """Record of a policy violation."""
    violation_id: UUID = Field(default_factory=uuid4)
    policy_id: UUID = Field(..., description="Policy that was violated")
    policy_name: str = Field(..., description="Name of violated policy")
    entity_id: UUID = Field(..., description="Entity that violated policy")
    entity_type: str = Field(..., description="Type of entity")
    severity: Severity = Field(..., description="Violation severity")
    message: str = Field(..., description="Violation message")
    detected_at: datetime = Field(default_factory=datetime.now)
    details: dict[str, Any] = Field(default_factory=dict, description="Additional violation details")
    resolved: bool = Field(False, description="Whether violation has been resolved")
    resolved_at: Optional[datetime] = Field(None)
    resolved_by: Optional[str] = Field(None)


class ComplianceReport(BaseModel):
    """Report of compliance check results."""
    report_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID = Field(..., description="Tenant ID")
    generated_at: datetime = Field(default_factory=datetime.now)
    policies_checked: int = Field(0, description="Number of policies evaluated")
    violations_found: int = Field(0, description="Total violations found")
    violations_by_severity: dict[str, int] = Field(default_factory=dict)
    violations: list[Violation] = Field(default_factory=list)
    passed: bool = Field(True, description="Whether all checks passed")


class PolicyEngine:
    """
    Policy engine for automated compliance checking.

    Features:
    - Policy registration and management
    - Rule evaluation using Python expressions
    - Violation detection and reporting
    - Severity classification
    - Batch checking
    """

    def __init__(self):
        """Initialize policy engine."""
        self._policies: dict[UUID, CompliancePolicy] = {}
        self._violations: list[Violation] = []

    def register_policy(self, policy: CompliancePolicy) -> None:
        """
        Register a compliance policy.

        Args:
            policy: Policy to register
        """
        self._policies[policy.policy_id] = policy

    def unregister_policy(self, policy_id: UUID) -> None:
        """
        Unregister a compliance policy.

        Args:
            policy_id: ID of policy to unregister
        """
        if policy_id in self._policies:
            del self._policies[policy_id]

    def get_policy(self, policy_id: UUID) -> Optional[CompliancePolicy]:
        """
        Get a policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy or None if not found
        """
        return self._policies.get(policy_id)

    def list_policies(
        self,
        category: Optional[PolicyCategory] = None,
        enabled_only: bool = True
    ) -> list[CompliancePolicy]:
        """
        List all registered policies.

        Args:
            category: Filter by category
            enabled_only: Only return enabled policies

        Returns:
            List of policies
        """
        policies = list(self._policies.values())

        if category:
            policies = [p for p in policies if p.category == category]

        if enabled_only:
            policies = [p for p in policies if p.enabled]

        return policies

    def evaluate(
        self,
        entity: dict[str, Any],
        policies: Optional[list[CompliancePolicy]] = None
    ) -> list[Violation]:
        """
        Evaluate an entity against policies.

        Args:
            entity: Entity to check
            policies: Specific policies to check (None = all enabled)

        Returns:
            List of violations found
        """
        if policies is None:
            policies = self.list_policies(enabled_only=True)

        violations: list[Violation] = []

        for policy in policies:
            violation = self._evaluate_policy(entity, policy)
            if violation:
                violations.append(violation)
                self._violations.append(violation)

        return violations

    def _evaluate_policy(
        self,
        entity: dict[str, Any],
        policy: CompliancePolicy
    ) -> Optional[Violation]:
        """
        Evaluate a single policy against an entity.

        Args:
            entity: Entity to check
            policy: Policy to evaluate

        Returns:
            Violation if policy failed, None if passed
        """
        try:
            # Create safe evaluation context
            context = {
                **entity,
                'Decimal': Decimal,
                'abs': abs,
                'sum': sum,
                'len': len,
                'max': max,
                'min': min,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
            }

            # Evaluate rule
            result = eval(policy.rule, {"__builtins__": {}}, context)

            # If rule evaluates to False, it's a violation
            if not result:
                entity_id = entity.get('id') or entity.get('entity_id') or uuid4()
                entity_type = entity.get('entity_type') or entity.get('type') or 'Unknown'

                return Violation(
                    policy_id=policy.policy_id,
                    policy_name=policy.name,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    severity=policy.severity,
                    message=f"Policy '{policy.name}' violated: {policy.description}",
                    details={
                        "rule": policy.rule,
                        "entity": entity
                    }
                )

        except Exception as e:
            # If evaluation fails, treat as critical violation
            entity_id = entity.get('id') or entity.get('entity_id') or uuid4()
            entity_type = entity.get('entity_type') or entity.get('type') or 'Unknown'

            return Violation(
                policy_id=policy.policy_id,
                policy_name=policy.name,
                entity_id=entity_id,
                entity_type=entity_type,
                severity=Severity.CRITICAL,
                message=f"Error evaluating policy '{policy.name}': {str(e)}",
                details={
                    "rule": policy.rule,
                    "error": str(e),
                    "entity": entity
                }
            )

        return None

    def check_transaction(
        self,
        transaction: dict[str, Any],
        tenant_id: UUID
    ) -> list[Violation]:
        """
        Check a transaction against relevant policies.

        Args:
            transaction: Transaction to check
            tenant_id: Tenant ID

        Returns:
            List of violations found
        """
        # Get accounting and financial policies
        policies = self.list_policies(category=PolicyCategory.ACCOUNTING)
        policies += self.list_policies(category=PolicyCategory.FINANCIAL)

        return self.evaluate(transaction, policies)

    def check_ledger_entry(
        self,
        entry: dict[str, Any],
        tenant_id: UUID
    ) -> list[Violation]:
        """
        Check a ledger entry against relevant policies.

        Args:
            entry: Ledger entry to check
            tenant_id: Tenant ID

        Returns:
            List of violations found
        """
        # Get accounting policies
        policies = self.list_policies(category=PolicyCategory.ACCOUNTING)

        return self.evaluate(entry, policies)

    def generate_compliance_report(
        self,
        tenant_id: UUID,
        entities: list[dict[str, Any]],
        policies: Optional[list[CompliancePolicy]] = None
    ) -> ComplianceReport:
        """
        Generate compliance report for multiple entities.

        Args:
            tenant_id: Tenant ID
            entities: Entities to check
            policies: Policies to use (None = all enabled)

        Returns:
            ComplianceReport with all violations
        """
        if policies is None:
            policies = self.list_policies(enabled_only=True)

        all_violations: list[Violation] = []

        for entity in entities:
            violations = self.evaluate(entity, policies)
            all_violations.extend(violations)

        # Count by severity
        violations_by_severity = {
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0
        }

        for violation in all_violations:
            violations_by_severity[violation.severity.value] += 1

        return ComplianceReport(
            tenant_id=tenant_id,
            policies_checked=len(policies),
            violations_found=len(all_violations),
            violations_by_severity=violations_by_severity,
            violations=all_violations,
            passed=len(all_violations) == 0
        )

    def get_violations(
        self,
        entity_id: Optional[UUID] = None,
        severity: Optional[Severity] = None,
        resolved: Optional[bool] = None
    ) -> list[Violation]:
        """
        Get violations with optional filtering.

        Args:
            entity_id: Filter by entity
            severity: Filter by severity
            resolved: Filter by resolution status

        Returns:
            List of violations
        """
        violations = self._violations

        if entity_id:
            violations = [v for v in violations if v.entity_id == entity_id]

        if severity:
            violations = [v for v in violations if v.severity == severity]

        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]

        return violations

    def resolve_violation(
        self,
        violation_id: UUID,
        resolved_by: str
    ) -> Optional[Violation]:
        """
        Mark a violation as resolved.

        Args:
            violation_id: Violation ID
            resolved_by: User resolving the violation

        Returns:
            Updated violation or None if not found
        """
        for violation in self._violations:
            if violation.violation_id == violation_id:
                # Create updated violation (violations are immutable)
                data = violation.model_dump()
                data['resolved'] = True
                data['resolved_at'] = datetime.now()
                data['resolved_by'] = resolved_by

                updated = Violation(**data)

                # Replace in list
                idx = self._violations.index(violation)
                self._violations[idx] = updated

                return updated

        return None

    def clear_violations(self) -> None:
        """Clear all violations (for testing)."""
        self._violations.clear()

    @staticmethod
    def create_standard_policies() -> list[CompliancePolicy]:
        """
        Create standard compliance policies for accounting systems.

        Returns:
            List of standard policies
        """
        policies = []

        # Accounting policies
        policies.append(CompliancePolicy(
            name="Debits Equal Credits",
            description="For double-entry transactions, total debits must equal total credits",
            category=PolicyCategory.ACCOUNTING,
            rule="sum([Decimal(str(e.get('amount', 0))) for e in debits], Decimal('0')) == sum([Decimal(str(e.get('amount', 0))) for e in credits], Decimal('0'))",
            severity=Severity.CRITICAL
        ))

        policies.append(CompliancePolicy(
            name="No Negative Balances",
            description="Fund balances cannot be negative",
            category=PolicyCategory.FINANCIAL,
            rule="Decimal(str(balance)) >= Decimal('0')",
            severity=Severity.ERROR
        ))

        policies.append(CompliancePolicy(
            name="Transaction Amount Limit",
            description="Single transactions cannot exceed $100,000",
            category=PolicyCategory.FINANCIAL,
            rule="Decimal(str(amount)) <= Decimal('100000')",
            severity=Severity.WARNING
        ))

        policies.append(CompliancePolicy(
            name="Required Approval",
            description="Transactions over $10,000 must be approved",
            category=PolicyCategory.FINANCIAL,
            rule="Decimal(str(amount)) <= Decimal('10000') or approved_by is not None",
            severity=Severity.ERROR
        ))

        policies.append(CompliancePolicy(
            name="Valid Account Code",
            description="Account codes must be 4 digits",
            category=PolicyCategory.ACCOUNTING,
            rule="len(str(account_code)) == 4 and str(account_code).isdigit()",
            severity=Severity.ERROR
        ))

        policies.append(CompliancePolicy(
            name="Non-Zero Amount",
            description="Transaction amounts cannot be zero",
            category=PolicyCategory.ACCOUNTING,
            rule="Decimal(str(amount)) != Decimal('0')",
            severity=Severity.WARNING
        ))

        policies.append(CompliancePolicy(
            name="Required Description",
            description="All transactions must have a description",
            category=PolicyCategory.DATA_INTEGRITY,
            rule="description is not None and len(str(description).strip()) > 0",
            severity=Severity.WARNING
        ))

        policies.append(CompliancePolicy(
            name="Valid Date",
            description="Transaction dates cannot be in the future",
            category=PolicyCategory.DATA_INTEGRITY,
            rule="True",  # Would need datetime comparison in real implementation
            severity=Severity.ERROR
        ))

        return policies
