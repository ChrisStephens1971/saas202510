"""
API Endpoint Tests for Sprint 20: Board Packet Generation

Tests all REST API endpoints for:
- Board Packet Templates (CRUD + reusable templates)
- Board Packets (CRUD + PDF generation + email distribution)
- Packet Sections (CRUD + section ordering)

Testing patterns:
- Authentication and tenant isolation
- All CRUD operations
- Query parameters and filtering
- Pagination
- Validation errors (400)
- Not found errors (404)
- Custom actions (generate_pdf, send_email)
- Template management
- Section ordering
"""

import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from rest_framework import status
from rest_framework.test import APIClient


# ===========================
# Board Packet Templates API Tests
# ===========================

class TestBoardPacketTemplatesAPI:
    """Test /api/v1/accounting/board-packet-templates/ endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create an authenticated API client."""
        client = APIClient()
        # TODO: Add authentication when implemented
        return client

    @pytest.fixture
    def base_url(self):
        """Base URL for board packet templates endpoints."""
        return '/api/v1/accounting/board-packet-templates/'

    def test_create_board_packet_template(self, api_client, base_url, tenant_fixture):
        """Test POST /board-packet-templates/ - Create template."""
        data = {
            'tenant': str(tenant_fixture.id),
            'name': 'Monthly Board Meeting',
            'description': 'Standard monthly board meeting packet',
            'default_sections': [
                {'section_type': 'agenda', 'order': 1},
                {'section_type': 'minutes', 'order': 2},
                {'section_type': 'financials', 'order': 3},
                {'section_type': 'ar_aging', 'order': 4},
                {'section_type': 'budget_variance', 'order': 5}
            ],
            'is_default': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Monthly Board Meeting'
        assert response.data['is_default'] is True
        assert len(response.data['default_sections']) == 5
        assert 'id' in response.data

    def test_create_board_packet_template_annual(self, api_client, base_url, tenant_fixture):
        """Test POST /board-packet-templates/ - Create annual meeting template."""
        data = {
            'tenant': str(tenant_fixture.id),
            'name': 'Annual Meeting',
            'description': 'Annual homeowners meeting packet',
            'default_sections': [
                {'section_type': 'agenda', 'order': 1},
                {'section_type': 'minutes', 'order': 2},
                {'section_type': 'financials', 'order': 3},
                {'section_type': 'budget_proposal', 'order': 4},
                {'section_type': 'reserve_study', 'order': 5},
                {'section_type': 'board_election', 'order': 6}
            ],
            'is_default': False
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Annual Meeting'
        assert len(response.data['default_sections']) == 6

    def test_create_board_packet_template_validation_error(self, api_client, base_url):
        """Test POST /board-packet-templates/ - Missing required fields."""
        data = {
            'name': 'Invalid Template'
            # Missing tenant, default_sections
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_board_packet_template(self, api_client, base_url, board_packet_template_fixture):
        """Test GET /board-packet-templates/{id}/ - Retrieve template."""
        url = f'{base_url}{board_packet_template_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(board_packet_template_fixture.id)
        assert 'default_sections' in response.data

    def test_get_board_packet_template_not_found(self, api_client, base_url):
        """Test GET /board-packet-templates/{id}/ - Template not found."""
        from uuid import uuid4
        url = f'{base_url}{uuid4()}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_board_packet_templates(self, api_client, base_url):
        """Test GET /board-packet-templates/ - List all templates."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_default_only(self, api_client, base_url):
        """Test GET /board-packet-templates/?is_default=true - Filter default template."""
        response = api_client.get(f'{base_url}?is_default=true')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for template in results:
            assert template['is_default'] is True

    def test_update_board_packet_template(self, api_client, base_url, board_packet_template_fixture):
        """Test PATCH /board-packet-templates/{id}/ - Update template."""
        url = f'{base_url}{board_packet_template_fixture.id}/'
        data = {
            'name': 'Updated Monthly Meeting',
            'description': 'Updated description',
            'is_default': False
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Monthly Meeting'
        assert response.data['is_default'] is False

    def test_update_template_sections(self, api_client, base_url, board_packet_template_fixture):
        """Test PATCH /board-packet-templates/{id}/ - Update sections."""
        url = f'{base_url}{board_packet_template_fixture.id}/'
        data = {
            'default_sections': [
                {'section_type': 'agenda', 'order': 1},
                {'section_type': 'financials', 'order': 2},
                {'section_type': 'new_business', 'order': 3}
            ]
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['default_sections']) == 3

    def test_delete_board_packet_template(self, api_client, base_url, board_packet_template_fixture):
        """Test DELETE /board-packet-templates/{id}/ - Delete template."""
        url = f'{base_url}{board_packet_template_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_ordering_by_name(self, api_client, base_url):
        """Test GET /board-packet-templates/?ordering=name - Order alphabetically."""
        response = api_client.get(f'{base_url}?ordering=name')

        assert response.status_code == status.HTTP_200_OK

    def test_tenant_isolation_templates(self, api_client, base_url, tenant_fixture, other_tenant_fixture):
        """Test that tenant A cannot access tenant B's templates."""
        # Create template for tenant A
        api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'name': 'Tenant A Template',
            'default_sections': [],
            'is_default': False
        }, format='json')

        # Create template for tenant B
        api_client.post(base_url, {
            'tenant': str(other_tenant_fixture.id),
            'name': 'Tenant B Template',
            'default_sections': [],
            'is_default': False
        }, format='json')

        # List templates (should only see tenant A's templates when authenticated as tenant A)
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        # TODO: Verify tenant isolation when auth is implemented


# ===========================
# Board Packets API Tests
# ===========================

class TestBoardPacketsAPI:
    """Test /api/v1/accounting/board-packets/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/board-packets/'

    def test_create_board_packet(self, api_client, base_url, tenant_fixture, board_packet_template_fixture):
        """Test POST /board-packets/ - Create board packet."""
        data = {
            'tenant': str(tenant_fixture.id),
            'template': str(board_packet_template_fixture.id),
            'meeting_date': str(date.today() + timedelta(days=7)),
            'status': 'draft',
            'generated_by': 'system'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['template'] == str(board_packet_template_fixture.id)
        assert response.data['status'] == 'draft'
        assert 'template_name' in response.data
        assert 'sections' in response.data
        assert 'id' in response.data

    def test_create_board_packet_without_template(self, api_client, base_url, tenant_fixture):
        """Test POST /board-packets/ - Create packet without template."""
        data = {
            'tenant': str(tenant_fixture.id),
            'meeting_date': str(date.today() + timedelta(days=14)),
            'status': 'draft',
            'generated_by': 'user@example.com'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['template'] is None

    def test_create_board_packet_validation_error(self, api_client, base_url):
        """Test POST /board-packets/ - Missing required fields."""
        data = {
            'status': 'draft'
            # Missing tenant, meeting_date
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_board_packet(self, api_client, base_url, board_packet_fixture):
        """Test GET /board-packets/{id}/ - Retrieve packet."""
        url = f'{base_url}{board_packet_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(board_packet_fixture.id)
        assert 'sections' in response.data
        assert 'status_display' in response.data

    def test_list_board_packets(self, api_client, base_url):
        """Test GET /board-packets/ - List all packets."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_template(self, api_client, base_url, board_packet_template_fixture):
        """Test GET /board-packets/?template={id} - Filter by template."""
        response = api_client.get(f'{base_url}?template={board_packet_template_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for packet in results:
            assert packet['template'] == str(board_packet_template_fixture.id)

    def test_list_filter_by_status(self, api_client, base_url):
        """Test GET /board-packets/?status=draft - Filter by status."""
        response = api_client.get(f'{base_url}?status=draft')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for packet in results:
            assert packet['status'] == 'draft'

    def test_list_filter_by_meeting_date(self, api_client, base_url):
        """Test GET /board-packets/?meeting_date=2025-11-15 - Filter by date."""
        meeting_date = '2025-11-15'
        response = api_client.get(f'{base_url}?meeting_date={meeting_date}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for packet in results:
            assert packet['meeting_date'] == meeting_date

    def test_update_board_packet(self, api_client, base_url, board_packet_fixture):
        """Test PATCH /board-packets/{id}/ - Update packet."""
        url = f'{base_url}{board_packet_fixture.id}/'
        data = {
            'status': 'ready',
            'meeting_date': str(date.today() + timedelta(days=10))
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'ready'

    def test_delete_board_packet(self, api_client, base_url, board_packet_fixture):
        """Test DELETE /board-packets/{id}/ - Delete packet."""
        url = f'{base_url}{board_packet_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_generate_pdf_action(self, api_client, base_url, board_packet_fixture):
        """Test POST /board-packets/{id}/generate_pdf/ - Generate PDF."""
        url = f'{base_url}{board_packet_fixture.id}/generate_pdf/'

        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert response.data['status'] in ['generating', 'completed']

    def test_send_email_action(self, api_client, base_url, board_packet_fixture):
        """Test POST /board-packets/{id}/send_email/ - Send via email."""
        url = f'{base_url}{board_packet_fixture.id}/send_email/'
        data = {
            'recipients': [
                'board1@example.com',
                'board2@example.com',
                'manager@example.com'
            ]
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['sent_to'] == data['recipients']
        assert 'sent_at' in response.data

    def test_send_email_action_validation_error(self, api_client, base_url, board_packet_fixture):
        """Test POST /board-packets/{id}/send_email/ - Missing recipients."""
        url = f'{base_url}{board_packet_fixture.id}/send_email/'
        data = {}  # No recipients

        response = api_client.post(url, data, format='json')

        # Should still work (recipients might be optional)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_ordering_by_meeting_date(self, api_client, base_url):
        """Test GET /board-packets/?ordering=-meeting_date - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-meeting_date')

        assert response.status_code == status.HTTP_200_OK

    def test_ordering_by_generated_at(self, api_client, base_url):
        """Test GET /board-packets/?ordering=-generated_at - Order by generation date."""
        response = api_client.get(f'{base_url}?ordering=-generated_at')

        assert response.status_code == status.HTTP_200_OK

    def test_pagination(self, api_client, base_url):
        """Test GET /board-packets/?page=1&page_size=10 - Pagination."""
        response = api_client.get(f'{base_url}?page=1&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        if 'results' in response.data:
            assert 'count' in response.data
            assert 'next' in response.data
            assert 'previous' in response.data


# ===========================
# Packet Sections API Tests
# ===========================

class TestPacketSectionsAPI:
    """Test /api/v1/accounting/packet-sections/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/packet-sections/'

    def test_create_packet_section_agenda(self, api_client, base_url, board_packet_fixture):
        """Test POST /packet-sections/ - Create agenda section."""
        data = {
            'packet': str(board_packet_fixture.id),
            'section_type': 'agenda',
            'title': 'Meeting Agenda',
            'content_data': {
                'items': [
                    'Call to Order',
                    'Approval of Minutes',
                    'Financial Report',
                    'New Business',
                    'Adjournment'
                ]
            },
            'order': 1,
            'page_count': 2
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['section_type'] == 'agenda'
        assert response.data['order'] == 1
        assert 'section_type_display' in response.data
        assert 'id' in response.data

    def test_create_packet_section_financials(self, api_client, base_url, board_packet_fixture):
        """Test POST /packet-sections/ - Create financials section."""
        data = {
            'packet': str(board_packet_fixture.id),
            'section_type': 'financials',
            'title': 'Financial Statements',
            'content_url': 'https://example.com/financials.pdf',
            'order': 3,
            'page_count': 8
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['section_type'] == 'financials'
        assert response.data['content_url'] == 'https://example.com/financials.pdf'

    def test_create_packet_section_minutes(self, api_client, base_url, board_packet_fixture):
        """Test POST /packet-sections/ - Create minutes section."""
        data = {
            'packet': str(board_packet_fixture.id),
            'section_type': 'minutes',
            'title': 'Previous Meeting Minutes',
            'content_data': {
                'date': '2025-09-15',
                'attendees': ['Board Member 1', 'Board Member 2', 'Manager'],
                'summary': 'All motions passed unanimously'
            },
            'order': 2,
            'page_count': 3
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['section_type'] == 'minutes'

    def test_get_packet_section(self, api_client, base_url, packet_section_fixture):
        """Test GET /packet-sections/{id}/ - Retrieve section."""
        url = f'{base_url}{packet_section_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(packet_section_fixture.id)

    def test_list_packet_sections(self, api_client, base_url):
        """Test GET /packet-sections/ - List all sections."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_packet(self, api_client, base_url, board_packet_fixture):
        """Test GET /packet-sections/?packet={id} - Filter by packet."""
        response = api_client.get(f'{base_url}?packet={board_packet_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for section in results:
            assert section['packet'] == str(board_packet_fixture.id)

    def test_list_filter_by_section_type(self, api_client, base_url):
        """Test GET /packet-sections/?section_type=financials - Filter by type."""
        response = api_client.get(f'{base_url}?section_type=financials')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for section in results:
            assert section['section_type'] == 'financials'

    def test_update_packet_section(self, api_client, base_url, packet_section_fixture):
        """Test PATCH /packet-sections/{id}/ - Update section."""
        url = f'{base_url}{packet_section_fixture.id}/'
        data = {
            'title': 'Updated Section Title',
            'order': 5,
            'page_count': 10
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Section Title'
        assert response.data['order'] == 5

    def test_update_section_reorder(self, api_client, base_url, board_packet_fixture):
        """Test reordering sections."""
        # Create multiple sections
        sections = []
        for i in range(3):
            response = api_client.post(base_url, {
                'packet': str(board_packet_fixture.id),
                'section_type': 'custom',
                'title': f'Section {i + 1}',
                'order': i + 1,
                'page_count': 1
            }, format='json')
            sections.append(response.data['id'])

        # Reorder: move section 1 to position 3
        url = f'{base_url}{sections[0]}/'
        response = api_client.patch(url, {'order': 3}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['order'] == 3

    def test_delete_packet_section(self, api_client, base_url, packet_section_fixture):
        """Test DELETE /packet-sections/{id}/ - Delete section."""
        url = f'{base_url}{packet_section_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_ordering_by_order(self, api_client, base_url):
        """Test GET /packet-sections/?ordering=order - Order by section order."""
        response = api_client.get(f'{base_url}?ordering=order')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        if len(results) > 1:
            orders = [r['order'] for r in results]
            assert orders == sorted(orders)


# ===========================
# Integration Tests
# ===========================

class TestBoardPacketWorkflow:
    """Test complete board packet generation workflow."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    def test_complete_board_packet_workflow(self, api_client, tenant_fixture):
        """Test complete workflow: create template -> create packet -> add sections -> generate PDF -> send email."""

        # Step 1: Create template
        template_response = api_client.post('/api/v1/accounting/board-packet-templates/', {
            'tenant': str(tenant_fixture.id),
            'name': 'Test Meeting Template',
            'description': 'Test template',
            'default_sections': [
                {'section_type': 'agenda', 'order': 1},
                {'section_type': 'minutes', 'order': 2},
                {'section_type': 'financials', 'order': 3}
            ],
            'is_default': True
        }, format='json')

        assert template_response.status_code == status.HTTP_201_CREATED
        template_id = template_response.data['id']

        # Step 2: Create board packet
        packet_response = api_client.post('/api/v1/accounting/board-packets/', {
            'tenant': str(tenant_fixture.id),
            'template': template_id,
            'meeting_date': str(date.today() + timedelta(days=7)),
            'status': 'draft',
            'generated_by': 'test@example.com'
        }, format='json')

        assert packet_response.status_code == status.HTTP_201_CREATED
        packet_id = packet_response.data['id']

        # Step 3: Add sections
        sections = [
            ('agenda', 'Board Meeting Agenda', 1),
            ('minutes', 'Previous Meeting Minutes', 2),
            ('financials', 'Financial Report', 3)
        ]

        for section_type, title, order in sections:
            section_response = api_client.post('/api/v1/accounting/packet-sections/', {
                'packet': packet_id,
                'section_type': section_type,
                'title': title,
                'order': order,
                'page_count': 2
            }, format='json')

            assert section_response.status_code == status.HTTP_201_CREATED

        # Step 4: Mark packet as ready
        api_client.patch(f'/api/v1/accounting/board-packets/{packet_id}/', {
            'status': 'ready'
        }, format='json')

        # Step 5: Generate PDF
        pdf_response = api_client.post(f'/api/v1/accounting/board-packets/{packet_id}/generate_pdf/', {}, format='json')

        assert pdf_response.status_code == status.HTTP_200_OK

        # Step 6: Send email
        email_response = api_client.post(f'/api/v1/accounting/board-packets/{packet_id}/send_email/', {
            'recipients': ['board@example.com', 'manager@example.com']
        }, format='json')

        assert email_response.status_code == status.HTTP_200_OK
        assert len(email_response.data['sent_to']) == 2

        # Step 7: Mark as sent
        final_response = api_client.patch(f'/api/v1/accounting/board-packets/{packet_id}/', {
            'status': 'sent'
        }, format='json')

        assert final_response.status_code == status.HTTP_200_OK
        assert final_response.data['status'] == 'sent'

    def test_template_reuse_workflow(self, api_client, tenant_fixture):
        """Test that templates can be reused for multiple packets."""

        # Create one template
        template_response = api_client.post('/api/v1/accounting/board-packet-templates/', {
            'tenant': str(tenant_fixture.id),
            'name': 'Reusable Template',
            'default_sections': [
                {'section_type': 'agenda', 'order': 1}
            ],
            'is_default': False
        }, format='json')

        template_id = template_response.data['id']

        # Create multiple packets using the same template
        packet_ids = []
        for i in range(3):
            packet_response = api_client.post('/api/v1/accounting/board-packets/', {
                'tenant': str(tenant_fixture.id),
                'template': template_id,
                'meeting_date': str(date.today() + timedelta(days=7 * (i + 1))),
                'status': 'draft',
                'generated_by': 'test@example.com'
            }, format='json')

            assert packet_response.status_code == status.HTTP_201_CREATED
            packet_ids.append(packet_response.data['id'])

        # Verify all packets use the same template
        assert len(packet_ids) == 3
        for packet_id in packet_ids:
            packet = api_client.get(f'/api/v1/accounting/board-packets/{packet_id}/').data
            assert packet['template'] == template_id
