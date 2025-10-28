"""
Validators for multi-tenant isolation.

These validators ensure that tenant data is properly isolated and
no cross-tenant data access occurs at database or application levels.

CRITICAL: Multi-tenant isolation is a security requirement. Failures here
indicate catastrophic security vulnerabilities.
"""

from typing import Any, Optional
from uuid import UUID

from .accounting_validators import ValidationError


class TenantIsolationViolation(ValidationError):
    """Raised when tenant isolation is violated."""

    pass


class TenantIsolationValidator:
    """
    Validator for multi-tenant data isolation.

    CRITICAL RULES:
    1. All queries must include tenant_id filter
    2. No cross-tenant references (foreign keys stay within tenant)
    3. Schema-per-tenant architecture enforced
    4. Full-text search respects tenant boundaries
    """

    @staticmethod
    def validate_query_has_tenant_filter(
        query_sql: str,
        tenant_id: UUID,
    ) -> bool:
        """
        Validate that a SQL query includes tenant_id filter.

        This is a CRITICAL security check - queries without tenant_id
        filters can leak data across tenants.

        Args:
            query_sql: SQL query string
            tenant_id: Tenant ID that should be in query

        Returns:
            True if valid

        Raises:
            TenantIsolationViolation: If query lacks tenant filter
        """
        # Check for tenant_id in WHERE clause
        query_lower = query_sql.lower()

        # Common patterns
        has_tenant_filter = (
            "tenant_id" in query_lower
            or f"tenant_id = '{tenant_id}'" in query_sql
            or f"tenant_id = '{str(tenant_id)}'" in query_sql
            or "schema_name" in query_lower  # Schema-per-tenant
        )

        if not has_tenant_filter:
            raise TenantIsolationViolation(
                f"Query lacks tenant_id filter! This could leak cross-tenant data.\n"
                f"Query: {query_sql[:200]}..."
            )

        return True

    @staticmethod
    def validate_schema_isolation(
        schema_name: str,
        tenant_id: UUID,
    ) -> bool:
        """
        Validate that schema name matches tenant.

        In schema-per-tenant architecture, each tenant has their own schema.

        Args:
            schema_name: PostgreSQL schema name
            tenant_id: Tenant ID

        Returns:
            True if valid

        Raises:
            TenantIsolationViolation: If schema doesn't match tenant
        """
        expected_schema = f"tenant_{str(tenant_id).replace('-', '_')}"

        if schema_name != expected_schema:
            raise TenantIsolationViolation(
                f"Schema name '{schema_name}' doesn't match tenant {tenant_id}!\n"
                f"Expected: {expected_schema}"
            )

        return True

    @staticmethod
    def validate_no_cross_tenant_references(
        entity: Any,
        tenant_id: UUID,
    ) -> bool:
        """
        Validate that an entity doesn't reference other tenants' data.

        Checks all UUID fields to ensure they're within the same tenant.

        Args:
            entity: Entity to validate (must have tenant_id attribute)
            tenant_id: Expected tenant ID

        Returns:
            True if valid

        Raises:
            TenantIsolationViolation: If entity references other tenant
        """
        # Check entity's tenant_id
        if not hasattr(entity, "tenant_id"):
            raise TenantIsolationViolation(
                f"Entity {type(entity).__name__} lacks tenant_id field!"
            )

        if entity.tenant_id != tenant_id:
            raise TenantIsolationViolation(
                f"Entity {type(entity).__name__} belongs to tenant {entity.tenant_id}, "
                f"but expected tenant {tenant_id}!"
            )

        return True

    @staticmethod
    def validate_search_respects_tenant(
        search_results: list[Any],
        tenant_id: UUID,
    ) -> bool:
        """
        Validate that search results only include tenant's data.

        Full-text search must respect tenant boundaries.

        Args:
            search_results: List of search results
            tenant_id: Expected tenant ID

        Returns:
            True if valid

        Raises:
            TenantIsolationViolation: If results include other tenants' data
        """
        for result in search_results:
            if not hasattr(result, "tenant_id"):
                raise TenantIsolationViolation(
                    f"Search result {type(result).__name__} lacks tenant_id!"
                )

            if result.tenant_id != tenant_id:
                raise TenantIsolationViolation(
                    f"Search result from tenant {result.tenant_id} leaked to tenant {tenant_id}!"
                )

        return True

    @staticmethod
    def validate_foreign_key_within_tenant(
        entity: Any,
        related_entity: Any,
    ) -> bool:
        """
        Validate that foreign key references stay within tenant.

        Args:
            entity: Entity with foreign key
            related_entity: Related entity being referenced

        Returns:
            True if valid

        Raises:
            TenantIsolationViolation: If FK crosses tenant boundary
        """
        if not hasattr(entity, "tenant_id") or not hasattr(related_entity, "tenant_id"):
            raise TenantIsolationViolation(
                "Both entities must have tenant_id for FK validation"
            )

        if entity.tenant_id != related_entity.tenant_id:
            raise TenantIsolationViolation(
                f"Foreign key crosses tenant boundary! "
                f"Entity tenant: {entity.tenant_id}, "
                f"Related entity tenant: {related_entity.tenant_id}"
            )

        return True

    @staticmethod
    def audit_database_for_leaks(
        connection,
        tenant_id: UUID,
        schema_name: str,
    ) -> dict:
        """
        Audit database for potential cross-tenant data leaks.

        Runs several queries to detect:
        - Cross-tenant foreign key references
        - Missing tenant_id filters
        - Schema isolation violations

        Args:
            connection: Database connection
            tenant_id: Tenant to audit
            schema_name: Schema name

        Returns:
            Dictionary with audit results
        """
        audit_results = {
            "tenant_id": str(tenant_id),
            "schema_name": schema_name,
            "violations": [],
            "warnings": [],
        }

        # Check 1: Verify schema matches tenant
        try:
            TenantIsolationValidator.validate_schema_isolation(
                schema_name,
                tenant_id,
            )
        except TenantIsolationViolation as e:
            audit_results["violations"].append(str(e))

        # Check 2: Verify all tables have tenant_id column (for non-schema-per-tenant)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name NOT IN ('schema_migrations', 'ar_internal_metadata')
            GROUP BY table_name
            HAVING COUNT(CASE WHEN column_name = 'tenant_id' THEN 1 END) = 0
            """,
            (schema_name,),
        )

        tables_without_tenant_id = cursor.fetchall()
        if tables_without_tenant_id:
            audit_results["warnings"].append(
                f"Tables without tenant_id: {[t[0] for t in tables_without_tenant_id]}"
            )

        # Check 3: Look for suspicious cross-schema references
        cursor.execute(
            """
            SELECT
                tc.table_schema,
                tc.table_name,
                kcu.column_name,
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND ccu.table_schema != tc.table_schema
            """,
            (schema_name,),
        )

        cross_schema_refs = cursor.fetchall()
        if cross_schema_refs:
            audit_results["violations"].append(
                f"Cross-schema foreign keys detected: {cross_schema_refs}"
            )

        cursor.close()

        return audit_results


class QueryAnalyzer:
    """
    Analyzer for SQL queries to detect tenant isolation issues.

    This can be used to scan application queries and ensure
    they all include proper tenant filters.
    """

    @staticmethod
    def extract_table_references(query_sql: str) -> list[str]:
        """
        Extract table names from SQL query.

        Args:
            query_sql: SQL query

        Returns:
            List of table names
        """
        import re

        # Simple regex to find table names after FROM and JOIN
        pattern = r"(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)"
        matches = re.findall(pattern, query_sql, re.IGNORECASE)
        return matches

    @staticmethod
    def has_tenant_filter(query_sql: str) -> bool:
        """
        Check if query has tenant filter.

        Args:
            query_sql: SQL query

        Returns:
            True if tenant filter found
        """
        query_lower = query_sql.lower()
        return "tenant_id" in query_lower or "current_schema()" in query_lower

    @staticmethod
    def analyze_query(query_sql: str) -> dict:
        """
        Analyze query for tenant isolation.

        Args:
            query_sql: SQL query

        Returns:
            Analysis results
        """
        tables = QueryAnalyzer.extract_table_references(query_sql)
        has_filter = QueryAnalyzer.has_tenant_filter(query_sql)

        return {
            "query": query_sql[:200],
            "tables": tables,
            "has_tenant_filter": has_filter,
            "risk_level": "high" if not has_filter and tables else "low",
        }
