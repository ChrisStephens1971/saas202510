"""
Property-based tests for multi-tenant isolation.

These tests validate that tenant data is properly isolated and
no cross-tenant data access can occur.

CRITICAL: These tests validate security boundaries. Failures indicate
catastrophic security vulnerabilities that could leak sensitive financial data.
"""

from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from qa_testing.generators import MemberGenerator, PropertyGenerator, TransactionGenerator
from qa_testing.validators import (
    TenantIsolationValidator,
    TenantIsolationViolation,
)


class TestSchemaIsolation:
    """Tests for schema-per-tenant isolation."""

    @pytest.mark.property
    @given(st.uuids())
    def test_schema_name_matches_tenant_id(self, tenant_id):
        """
        Property: For ANY tenant ID, schema name must match tenant.

        Schema-per-tenant architecture requires schema name = tenant_{uuid}.
        """
        # Expected schema format
        expected_schema = f"tenant_{str(tenant_id).replace('-', '_')}"

        # Should validate successfully
        assert TenantIsolationValidator.validate_schema_isolation(
            expected_schema,
            tenant_id,
        )

    @pytest.mark.property
    @given(st.uuids())
    def test_wrong_schema_name_fails_validation(self, tenant_id):
        """
        Property: For ANY tenant ID, wrong schema name must fail validation.
        """
        # Use a different schema name
        wrong_schema = f"tenant_{uuid4().hex}"

        # Should fail validation
        with pytest.raises(TenantIsolationViolation, match="doesn't match tenant"):
            TenantIsolationValidator.validate_schema_isolation(
                wrong_schema,
                tenant_id,
            )


class TestQueryFiltering:
    """Tests for query tenant filtering."""

    def test_query_with_tenant_filter_passes(self):
        """Test that queries with tenant_id filter pass validation."""
        tenant_id = uuid4()

        queries = [
            f"SELECT * FROM members WHERE tenant_id = '{tenant_id}'",
            f"SELECT * FROM transactions WHERE tenant_id = '{tenant_id}' AND amount > 100",
            f"UPDATE members SET status = 'active' WHERE tenant_id = '{tenant_id}'",
            f"DELETE FROM transactions WHERE tenant_id = '{tenant_id}'",
        ]

        for query in queries:
            # Should pass validation
            assert TenantIsolationValidator.validate_query_has_tenant_filter(
                query,
                tenant_id,
            )

    def test_query_without_tenant_filter_fails(self):
        """Test that queries without tenant_id filter fail validation."""
        tenant_id = uuid4()

        queries = [
            "SELECT * FROM members",  # No filter!
            "SELECT * FROM transactions WHERE amount > 100",  # No tenant_id
            "UPDATE members SET status = 'active'",  # No filter
            "DELETE FROM transactions WHERE date < '2024-01-01'",  # No tenant_id
        ]

        for query in queries:
            # Should fail validation
            with pytest.raises(TenantIsolationViolation, match="lacks tenant_id filter"):
                TenantIsolationValidator.validate_query_has_tenant_filter(
                    query,
                    tenant_id,
                )

    def test_query_with_schema_name_passes(self):
        """Test that schema-per-tenant queries pass validation."""
        tenant_id = uuid4()

        queries = [
            f"SET search_path TO tenant_{str(tenant_id).replace('-', '_')}",
            "SELECT * FROM members",  # In tenant-specific schema
            "SELECT * FROM transactions WHERE amount > 100",
        ]

        # Schema-based queries should pass
        assert TenantIsolationValidator.validate_query_has_tenant_filter(
            queries[0],
            tenant_id,
        )


class TestCrossTenantAccessPrevention:
    """Tests for preventing cross-tenant data access."""

    @pytest.mark.property
    @given(st.uuids(), st.uuids())
    def test_cannot_access_other_tenant_data(self, tenant_a, tenant_b):
        """
        Property: Tenant A CANNOT access Tenant B's data.

        This is the fundamental tenant isolation property.
        """
        # Skip if same tenant
        if tenant_a == tenant_b:
            return

        # Create property for tenant A
        property_a = PropertyGenerator.create()
        property_a.id = tenant_a  # Set as tenant ID

        # Validate entity belongs to tenant A
        assert TenantIsolationValidator.validate_no_cross_tenant_references(
            property_a,
            tenant_a,
        )

        # Try to access as tenant B - should fail
        with pytest.raises(TenantIsolationViolation, match="expected tenant"):
            TenantIsolationValidator.validate_no_cross_tenant_references(
                property_a,
                tenant_b,
            )

    @pytest.mark.property
    @given(st.uuids())
    def test_entity_without_tenant_id_fails_validation(self, tenant_id):
        """
        Property: Entities without tenant_id ALWAYS fail validation.

        All entities must have tenant_id for isolation to work.
        """

        # Create object without tenant_id
        class BadEntity:
            pass

        bad_entity = BadEntity()

        # Should fail validation
        with pytest.raises(TenantIsolationViolation, match="lacks tenant_id field"):
            TenantIsolationValidator.validate_no_cross_tenant_references(
                bad_entity,
                tenant_id,
            )

    def test_member_isolation_between_tenants(self):
        """Test that members are isolated by tenant."""
        # Create members for two different properties (tenants)
        property_a = PropertyGenerator.create()
        property_b = PropertyGenerator.create()

        member_a = MemberGenerator.create(property_id=property_a.id)
        member_b = MemberGenerator.create(property_id=property_b.id)

        # Member A belongs to property A (tenant A)
        member_a.tenant_id = property_a.id
        assert TenantIsolationValidator.validate_no_cross_tenant_references(
            member_a,
            property_a.id,
        )

        # Member B belongs to property B (tenant B)
        member_b.tenant_id = property_b.id
        assert TenantIsolationValidator.validate_no_cross_tenant_references(
            member_b,
            property_b.id,
        )

        # Member A CANNOT be accessed as property B's member
        with pytest.raises(TenantIsolationViolation):
            TenantIsolationValidator.validate_no_cross_tenant_references(
                member_a,
                property_b.id,
            )

    def test_transaction_isolation_between_tenants(self):
        """Test that transactions are isolated by tenant."""
        property_a = PropertyGenerator.create()
        property_b = PropertyGenerator.create()

        # Create transactions for each tenant
        txn_a = TransactionGenerator.create_payment(
            property_id=property_a.id,
            member_id=property_a.id,
        )
        txn_b = TransactionGenerator.create_payment(
            property_id=property_b.id,
            member_id=property_b.id,
        )

        # Set tenant IDs
        txn_a.tenant_id = property_a.id
        txn_b.tenant_id = property_b.id

        # Validate isolation
        assert TenantIsolationValidator.validate_no_cross_tenant_references(
            txn_a,
            property_a.id,
        )

        # Cannot access txn_a as tenant B
        with pytest.raises(TenantIsolationViolation):
            TenantIsolationValidator.validate_no_cross_tenant_references(
                txn_a,
                property_b.id,
            )


class TestForeignKeyIsolation:
    """Tests for foreign key isolation within tenant."""

    def test_foreign_key_within_same_tenant(self):
        """Test that foreign keys within same tenant are valid."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Set tenant IDs
        property.tenant_id = property.id
        member.tenant_id = property.id

        # FK should be valid (same tenant)
        assert TenantIsolationValidator.validate_foreign_key_within_tenant(
            member,
            property,
        )

    def test_foreign_key_across_tenants_fails(self):
        """Test that foreign keys across tenants fail validation."""
        property_a = PropertyGenerator.create()
        member_b = MemberGenerator.create(property_id=property_a.id)

        # Set different tenant IDs
        property_a.tenant_id = property_a.id
        member_b.tenant_id = uuid4()  # Different tenant!

        # FK validation should fail
        with pytest.raises(TenantIsolationViolation, match="crosses tenant boundary"):
            TenantIsolationValidator.validate_foreign_key_within_tenant(
                member_b,
                property_a,
            )

    def test_transaction_references_correct_tenant(self):
        """Test that transaction references stay within tenant."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=member.id,
        )

        # Set tenant IDs
        property.tenant_id = property.id
        member.tenant_id = property.id
        transaction.tenant_id = property.id

        # All FKs should be valid
        assert TenantIsolationValidator.validate_foreign_key_within_tenant(
            transaction,
            property,
        )
        assert TenantIsolationValidator.validate_foreign_key_within_tenant(
            transaction,
            member,
        )


class TestSearchIsolation:
    """Tests for search result isolation."""

    def test_search_results_filtered_by_tenant(self):
        """Test that search results only include tenant's data."""
        tenant_id = uuid4()

        # Create members for this tenant
        members = []
        for i in range(5):
            member = MemberGenerator.create()
            member.tenant_id = tenant_id
            members.append(member)

        # Validate search results
        assert TenantIsolationValidator.validate_search_respects_tenant(
            members,
            tenant_id,
        )

    def test_search_results_with_other_tenant_fails(self):
        """Test that search with other tenant's data fails."""
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Create members for different tenants
        members = []
        for i in range(3):
            member = MemberGenerator.create()
            member.tenant_id = tenant_a
            members.append(member)

        # Add one member from tenant B (data leak!)
        leaked_member = MemberGenerator.create()
        leaked_member.tenant_id = tenant_b
        members.append(leaked_member)

        # Should fail validation
        with pytest.raises(TenantIsolationViolation, match="leaked to tenant"):
            TenantIsolationValidator.validate_search_respects_tenant(
                members,
                tenant_a,
            )

    def test_empty_search_results_pass_validation(self):
        """Test that empty search results pass validation."""
        tenant_id = uuid4()

        # Empty results should pass
        assert TenantIsolationValidator.validate_search_respects_tenant(
            [],
            tenant_id,
        )


class TestQueryAnalyzer:
    """Tests for SQL query analyzer."""

    def test_analyzer_detects_tenant_filter(self):
        """Test that analyzer detects tenant filters in queries."""
        from qa_testing.validators import QueryAnalyzer

        query = "SELECT * FROM members WHERE tenant_id = '12345'"

        assert QueryAnalyzer.has_tenant_filter(query)

    def test_analyzer_detects_missing_tenant_filter(self):
        """Test that analyzer detects missing tenant filters."""
        from qa_testing.validators import QueryAnalyzer

        query = "SELECT * FROM members WHERE status = 'active'"

        assert not QueryAnalyzer.has_tenant_filter(query)

    def test_analyzer_extracts_table_names(self):
        """Test that analyzer extracts table names from query."""
        from qa_testing.validators import QueryAnalyzer

        query = """
        SELECT m.*, t.*
        FROM members m
        JOIN transactions t ON m.id = t.member_id
        WHERE m.tenant_id = '12345'
        """

        tables = QueryAnalyzer.extract_table_references(query)

        assert "members" in tables
        assert "transactions" in tables

    def test_analyzer_calculates_risk_level(self):
        """Test that analyzer calculates query risk level."""
        from qa_testing.validators import QueryAnalyzer

        # High risk: no tenant filter
        risky_query = "SELECT * FROM members"
        analysis = QueryAnalyzer.analyze_query(risky_query)
        assert analysis["risk_level"] == "high"
        assert not analysis["has_tenant_filter"]

        # Low risk: has tenant filter
        safe_query = "SELECT * FROM members WHERE tenant_id = '12345'"
        analysis = QueryAnalyzer.analyze_query(safe_query)
        assert analysis["risk_level"] == "low"
        assert analysis["has_tenant_filter"]
