"""
Integration Tests for Import Fixes and Deployment (Sprint 22 Fix)

Tests the import resolution and deployment configuration including:
- Module import path validation
- Dependency resolution
- Deployment configuration verification
- Production readiness checks
- Database migration validation
- Environment configuration testing
"""

import pytest
import importlib
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess
import yaml
import json

from qa_testing.validators import (
    ImportValidator, DeploymentValidator, ConfigValidator,
    MigrationValidator, EnvironmentValidator
)
from qa_testing.deployment import (
    DeploymentChecker, DependencyResolver, ConfigurationManager
)


class TestImportFixes:
    """Test import fixes and module resolution"""

    def test_all_modules_importable(self):
        """Test that all required modules can be imported"""
        required_modules = [
            'accounting.models',
            'accounting.serializers',
            'accounting.api_views',
            'accounting.services.auditor_export_service',
            'accounting.services.resale_disclosure_service',
            'accounting.services.pdf_generator',
            'accounting.urls'
        ]

        import_errors = []

        for module_name in required_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                import_errors.append({
                    'module': module_name,
                    'error': str(e)
                })

        assert len(import_errors) == 0, f"Import errors found: {import_errors}"

    def test_circular_import_detection(self):
        """Test for circular import issues"""
        # Arrange
        modules_to_check = [
            'accounting.models',
            'accounting.services.auditor_export_service',
            'accounting.services.resale_disclosure_service'
        ]

        # Act
        circular_imports = ImportValidator.detect_circular_imports(modules_to_check)

        # Assert
        assert len(circular_imports) == 0, f"Circular imports detected: {circular_imports}"

    def test_relative_import_resolution(self):
        """Test that relative imports are properly resolved"""
        # Check Sprint 21 services
        from accounting.services import auditor_export_service

        # Verify service methods exist
        assert hasattr(auditor_export_service, 'AuditorExportService')
        service = auditor_export_service.AuditorExportService()
        assert hasattr(service, 'generate_csv')
        assert hasattr(service, 'link_evidence')
        assert hasattr(service, 'verify_integrity')

        # Check Sprint 22 services
        from accounting.services import resale_disclosure_service

        assert hasattr(resale_disclosure_service, 'ResaleDisclosureService')
        service = resale_disclosure_service.ResaleDisclosureService()
        assert hasattr(service, 'generate_pdf')
        assert hasattr(service, 'get_state_template')
        assert hasattr(service, 'create_invoice')

    def test_dependency_versions(self):
        """Test that all dependencies are at correct versions"""
        required_dependencies = {
            'django': '4.2.0',
            'djangorestframework': '3.14.0',
            'reportlab': '4.2.5',  # For PDF generation
            'celery': '5.3.0',
            'redis': '5.0.0',
            'psycopg2': '2.9.0',
            'python-dateutil': '2.8.2',
            'pytz': '2024.1'
        }

        import pkg_resources

        version_mismatches = []

        for package, required_version in required_dependencies.items():
            try:
                installed_version = pkg_resources.get_distribution(package).version
                if not ImportValidator.version_compatible(installed_version, required_version):
                    version_mismatches.append({
                        'package': package,
                        'required': required_version,
                        'installed': installed_version
                    })
            except pkg_resources.DistributionNotFound:
                version_mismatches.append({
                    'package': package,
                    'required': required_version,
                    'installed': 'NOT INSTALLED'
                })

        assert len(version_mismatches) == 0, f"Version mismatches: {version_mismatches}"

    def test_import_performance(self):
        """Test that imports complete within acceptable time"""
        import time

        slow_imports = []
        threshold = 1.0  # 1 second threshold

        modules = [
            'accounting.models',
            'accounting.services.auditor_export_service',
            'accounting.services.resale_disclosure_service',
            'accounting.services.pdf_generator'
        ]

        for module_name in modules:
            # Clear from cache if already imported
            if module_name in sys.modules:
                del sys.modules[module_name]

            start_time = time.time()
            importlib.import_module(module_name)
            import_time = time.time() - start_time

            if import_time > threshold:
                slow_imports.append({
                    'module': module_name,
                    'time': import_time
                })

        assert len(slow_imports) == 0, f"Slow imports detected: {slow_imports}"


class TestDeploymentConfiguration:
    """Test deployment configuration and readiness"""

    def test_docker_configuration(self):
        """Test Docker configuration files"""
        # Check Dockerfile exists and is valid
        dockerfile_path = Path('Dockerfile')
        assert dockerfile_path.exists(), "Dockerfile not found"

        with open(dockerfile_path, 'r') as f:
            dockerfile_content = f.read()

        # Verify required elements
        assert 'FROM python:3.11' in dockerfile_content
        assert 'WORKDIR' in dockerfile_content
        assert 'COPY requirements.txt' in dockerfile_content
        assert 'RUN pip install' in dockerfile_content
        assert 'EXPOSE 8010' in dockerfile_content  # Backend port for saas202510

        # Check docker-compose.yml
        compose_path = Path('docker-compose.yml')
        assert compose_path.exists(), "docker-compose.yml not found"

        with open(compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)

        # Verify services
        assert 'services' in compose_config
        assert 'backend' in compose_config['services']
        assert 'postgres' in compose_config['services']
        assert 'redis' in compose_config['services']

        # Verify ports
        backend_ports = compose_config['services']['backend']['ports']
        assert '8010:8010' in backend_ports

    def test_environment_configuration(self):
        """Test environment variable configuration"""
        # Check .env.example exists
        env_example_path = Path('.env.example')
        assert env_example_path.exists(), ".env.example not found"

        with open(env_example_path, 'r') as f:
            env_content = f.read()

        required_vars = [
            'DATABASE_URL',
            'REDIS_URL',
            'SECRET_KEY',
            'DEBUG',
            'ALLOWED_HOSTS',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_S3_BUCKET',
            'EMAIL_HOST',
            'EMAIL_PORT',
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'AUDITOR_EXPORT_PATH',
            'RESALE_DISCLOSURE_PATH',
            'PDF_GENERATION_TIMEOUT'
        ]

        for var in required_vars:
            assert var in env_content, f"Missing environment variable: {var}"

    def test_database_migrations(self):
        """Test database migration files"""
        migrations_path = Path('backend/accounting/migrations')
        assert migrations_path.exists(), "Migrations directory not found"

        # Check for Sprint 21 and 22 migrations
        expected_migrations = [
            '0016_add_auditor_export_model.py',
            '0017_add_resale_disclosure_model.py'
        ]

        migration_files = list(migrations_path.glob('*.py'))
        migration_names = [f.name for f in migration_files]

        for expected in expected_migrations:
            assert expected in migration_names, f"Missing migration: {expected}"

        # Verify migration dependencies
        for migration_file in expected_migrations:
            with open(migrations_path / migration_file, 'r') as f:
                content = f.read()
                assert 'dependencies = [' in content
                assert 'operations = [' in content

    def test_nginx_configuration(self):
        """Test nginx configuration for production"""
        nginx_conf_path = Path('nginx/nginx.conf')
        assert nginx_conf_path.exists(), "nginx.conf not found"

        with open(nginx_conf_path, 'r') as f:
            nginx_content = f.read()

        # Verify proxy configuration
        assert 'upstream backend' in nginx_content
        assert 'server backend:8010' in nginx_content
        assert 'proxy_pass http://backend' in nginx_content

        # Verify static files configuration
        assert 'location /static/' in nginx_content
        assert 'location /media/' in nginx_content

        # Verify security headers
        assert 'add_header X-Frame-Options' in nginx_content
        assert 'add_header X-Content-Type-Options' in nginx_content
        assert 'add_header X-XSS-Protection' in nginx_content

    def test_production_settings(self):
        """Test production Django settings"""
        settings_path = Path('backend/settings/production.py')
        assert settings_path.exists(), "Production settings not found"

        with open(settings_path, 'r') as f:
            settings_content = f.read()

        # Verify production configurations
        assert 'DEBUG = False' in settings_content
        assert 'ALLOWED_HOSTS' in settings_content
        assert 'SECURE_SSL_REDIRECT = True' in settings_content
        assert 'SESSION_COOKIE_SECURE = True' in settings_content
        assert 'CSRF_COOKIE_SECURE = True' in settings_content

        # Verify database configuration
        assert 'DATABASES' in settings_content
        assert 'psycopg2' in settings_content

        # Verify static files configuration
        assert 'STATIC_ROOT' in settings_content
        assert 'MEDIA_ROOT' in settings_content

    def test_deployment_scripts(self):
        """Test deployment automation scripts"""
        scripts = [
            'scripts/deploy.sh',
            'scripts/backup.sh',
            'scripts/restore.sh',
            'scripts/health_check.sh'
        ]

        for script_path in scripts:
            path = Path(script_path)
            assert path.exists(), f"Deployment script not found: {script_path}"

            # Verify script is executable
            assert os.access(path, os.X_OK), f"Script not executable: {script_path}"

            with open(path, 'r') as f:
                content = f.read()
                # Verify shebang
                assert content.startswith('#!/bin/bash'), f"Missing shebang in {script_path}"

    def test_ci_cd_configuration(self):
        """Test CI/CD pipeline configuration"""
        # GitHub Actions workflow
        workflow_path = Path('.github/workflows/deploy.yml')
        assert workflow_path.exists(), "GitHub Actions workflow not found"

        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)

        # Verify workflow triggers
        assert 'on' in workflow
        assert 'push' in workflow['on']
        assert 'branches' in workflow['on']['push']
        assert 'main' in workflow['on']['push']['branches']

        # Verify jobs
        assert 'jobs' in workflow
        assert 'test' in workflow['jobs']
        assert 'deploy' in workflow['jobs']

        # Verify test job steps
        test_steps = workflow['jobs']['test']['steps']
        step_names = [step.get('name', '') for step in test_steps]
        assert 'Run tests' in step_names
        assert 'Check imports' in step_names

    def test_monitoring_configuration(self):
        """Test monitoring and logging configuration"""
        # Check logging configuration
        logging_config_path = Path('backend/logging_config.py')
        assert logging_config_path.exists(), "Logging configuration not found"

        with open(logging_config_path, 'r') as f:
            logging_content = f.read()

        # Verify logging handlers
        assert 'handlers' in logging_content
        assert 'console' in logging_content
        assert 'file' in logging_content
        assert 'error_file' in logging_content

        # Verify log levels
        assert 'DEBUG' in logging_content
        assert 'INFO' in logging_content
        assert 'ERROR' in logging_content

        # Check monitoring endpoints
        urls_path = Path('backend/accounting/urls.py')
        with open(urls_path, 'r') as f:
            urls_content = f.read()

        assert 'health/' in urls_content
        assert 'metrics/' in urls_content


class TestProductionReadiness:
    """Test production readiness criteria"""

    def test_security_configuration(self):
        """Test security configurations"""
        security_checks = []

        # Check for hardcoded secrets
        files_to_check = Path('.').rglob('*.py')
        for file_path in files_to_check:
            with open(file_path, 'r') as f:
                content = f.read()
                if 'SECRET_KEY = ' in content and 'os.environ' not in content:
                    security_checks.append(f"Hardcoded secret in {file_path}")

        # Check for debug mode in production
        prod_settings = Path('backend/settings/production.py')
        if prod_settings.exists():
            with open(prod_settings, 'r') as f:
                if 'DEBUG = True' in f.read():
                    security_checks.append("DEBUG enabled in production settings")

        assert len(security_checks) == 0, f"Security issues: {security_checks}"

    def test_performance_configuration(self):
        """Test performance optimization settings"""
        # Check caching configuration
        settings_path = Path('backend/settings/production.py')
        with open(settings_path, 'r') as f:
            settings_content = f.read()

        assert 'CACHES' in settings_content
        assert 'redis' in settings_content.lower()

        # Check database connection pooling
        assert 'CONN_MAX_AGE' in settings_content

        # Check static file compression
        assert 'STATICFILES_STORAGE' in settings_content
        assert 'CompressedManifestStaticFilesStorage' in settings_content

    def test_backup_and_recovery(self):
        """Test backup and recovery procedures"""
        # Check backup script
        backup_script = Path('scripts/backup.sh')
        with open(backup_script, 'r') as f:
            backup_content = f.read()

        # Verify database backup
        assert 'pg_dump' in backup_content
        assert 'BACKUP_DIR' in backup_content

        # Verify file backup
        assert 'tar' in backup_content or 'aws s3 sync' in backup_content

        # Check restore script
        restore_script = Path('scripts/restore.sh')
        with open(restore_script, 'r') as f:
            restore_content = f.read()

        assert 'pg_restore' in restore_content or 'psql' in restore_content

    def test_health_checks(self):
        """Test health check endpoints"""
        health_checks = [
            '/api/health/',
            '/api/health/db/',
            '/api/health/redis/',
            '/api/health/storage/'
        ]

        # Verify health check implementations
        views_path = Path('backend/accounting/api_views.py')
        with open(views_path, 'r') as f:
            views_content = f.read()

        for endpoint in health_checks:
            endpoint_name = endpoint.strip('/').split('/')[-1] or 'health'
            assert f'def {endpoint_name}' in views_content or f'class {endpoint_name.title()}' in views_content

    def test_documentation_completeness(self):
        """Test deployment documentation"""
        required_docs = [
            'README.md',
            'DEPLOYMENT.md',
            'API_DOCUMENTATION.md',
            'TROUBLESHOOTING.md'
        ]

        missing_docs = []
        for doc_file in required_docs:
            doc_path = Path(doc_file)
            if not doc_path.exists():
                missing_docs.append(doc_file)

        assert len(missing_docs) == 0, f"Missing documentation: {missing_docs}"

        # Check deployment guide content
        deployment_doc = Path('DEPLOYMENT.md')
        if deployment_doc.exists():
            with open(deployment_doc, 'r') as f:
                content = f.read()

            required_sections = [
                '## Prerequisites',
                '## Installation',
                '## Configuration',
                '## Database Setup',
                '## Running Migrations',
                '## Static Files',
                '## Monitoring',
                '## Troubleshooting'
            ]

            for section in required_sections:
                assert section in content, f"Missing section in DEPLOYMENT.md: {section}"

    def test_error_handling(self):
        """Test error handling and logging"""
        # Check for proper exception handling in services
        services = [
            'backend/accounting/services/auditor_export_service.py',
            'backend/accounting/services/resale_disclosure_service.py'
        ]

        for service_path in services:
            path = Path(service_path)
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()

                # Verify exception handling
                assert 'try:' in content
                assert 'except' in content
                assert 'logger' in content or 'logging' in content

    def test_data_validation(self):
        """Test data validation in Sprint 22 features"""
        # Check serializers for validation
        serializers_path = Path('backend/accounting/serializers.py')
        with open(serializers_path, 'r') as f:
            content = f.read()

        # Verify AuditorExport serializer validation
        assert 'class AuditorExportSerializer' in content
        assert 'validate_start_date' in content or 'validate' in content
        assert 'validate_end_date' in content or 'validate' in content

        # Verify ResaleDisclosure serializer validation
        assert 'class ResaleDisclosureSerializer' in content
        assert 'required=True' in content
        assert 'validators=' in content or 'validate' in content

    def test_api_versioning(self):
        """Test API versioning configuration"""
        urls_path = Path('backend/accounting/urls.py')
        with open(urls_path, 'r') as f:
            content = f.read()

        # Verify API versioning
        assert 'api/v1/' in content
        assert 'auditor-exports' in content
        assert 'resale-disclosures' in content

    def test_rate_limiting(self):
        """Test rate limiting configuration"""
        settings_path = Path('backend/settings/production.py')
        with open(settings_path, 'r') as f:
            content = f.read()

        # Verify rate limiting middleware or decorator
        assert 'ratelimit' in content.lower() or 'throttle' in content.lower()

    def test_database_indexes(self):
        """Test database indexes for performance"""
        migration_files = [
            'backend/accounting/migrations/0016_add_auditor_export_model.py',
            'backend/accounting/migrations/0017_add_resale_disclosure_model.py'
        ]

        for migration_file in migration_files:
            path = Path(migration_file)
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()

                # Verify indexes on frequently queried fields
                assert 'db_index=True' in content or 'index_together' in content or 'indexes' in content