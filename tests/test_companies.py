"""
Test suite for company management endpoints
"""
import pytest
from rest_framework import status
from apps.accounts.models import Company, CompanyMember

pytestmark = [pytest.mark.companies, pytest.mark.django_db]


class TestCompanyCreation:
    """Test company creation endpoint"""

    def test_create_company_success(self, authenticated_client, company_data, user):
        """Test authenticated user can create a company"""
        response = authenticated_client.post('/api/accounts/companies/', company_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == company_data['name']
        assert response.data['industry'] == company_data['industry']
        assert response.data['created_by_email'] == user.email

        # Verify company was created
        company_id = response.data['id']
        assert Company.objects.filter(id=company_id).exists()

        # Verify creator was added as admin member
        member = CompanyMember.objects.get(company_id=company_id, user=user)
        assert member.role == 'admin'

    def test_create_company_unauthenticated(self, api_client, company_data):
        """Test unauthenticated user cannot create company"""
        response = api_client.post('/api/accounts/companies/', company_data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_company_missing_fields(self, authenticated_client):
        """Test company creation fails with missing required fields"""
        response = authenticated_client.post('/api/accounts/companies/', {
            'name': 'Test Company'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_company_invalid_industry(self, authenticated_client, company_data):
        """Test company creation fails with invalid industry"""
        company_data['industry'] = 'invalid_industry'

        response = authenticated_client.post('/api/accounts/companies/', company_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCompanyList:
    """Test company list endpoint"""

    def test_list_companies_authenticated(self, authenticated_client, company_with_admin):
        """Test authenticated user sees their companies"""
        response = authenticated_client.get('/api/accounts/companies/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any(c['id'] == str(company_with_admin.id) for c in response.data)

    def test_list_companies_empty(self, authenticated_client):
        """Test user with no companies sees empty list"""
        response = authenticated_client.get('/api/accounts/companies/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_list_companies_unauthenticated(self, api_client):
        """Test unauthenticated user cannot list companies"""
        response = api_client.get('/api/accounts/companies/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_companies_excludes_non_member_companies(
        self, authenticated_client, company_with_admin, create_company, create_user
    ):
        """Test user only sees companies they're a member of"""
        # Create another company with different user
        other_user = create_user(email='other@example.com')
        other_company = create_company(created_by=other_user, name='Other Company')
        CompanyMember.objects.create(company=other_company, user=other_user, role='admin')

        response = authenticated_client.get('/api/accounts/companies/')

        assert response.status_code == status.HTTP_200_OK
        company_ids = [c['id'] for c in response.data]
        assert str(company_with_admin.id) in company_ids
        assert str(other_company.id) not in company_ids


class TestCompanyDetail:
    """Test company detail endpoint"""

    def test_get_company_detail_success(self, authenticated_client, company_with_admin):
        """Test member can get company details"""
        response = authenticated_client.get(f'/api/accounts/companies/{company_with_admin.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(company_with_admin.id)
        assert response.data['name'] == company_with_admin.name

    def test_get_company_detail_non_member(
        self, authenticated_client, create_company, create_user
    ):
        """Test non-member cannot get company details"""
        other_user = create_user(email='other@example.com')
        other_company = create_company(created_by=other_user)

        response = authenticated_client.get(f'/api/accounts/companies/{other_company.id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCompanyUpdate:
    """Test company update endpoint"""

    def test_update_company_success(self, authenticated_client, company_with_admin):
        """Test member can update company"""
        response = authenticated_client.patch(
            f'/api/accounts/companies/{company_with_admin.id}/',
            {'name': 'Updated Company Name'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Company Name'

        company_with_admin.refresh_from_db()
        assert company_with_admin.name == 'Updated Company Name'

    def test_update_company_non_member(
        self, authenticated_client, create_company, create_user
    ):
        """Test non-member cannot update company"""
        other_user = create_user(email='other@example.com')
        other_company = create_company(created_by=other_user)

        response = authenticated_client.patch(
            f'/api/accounts/companies/{other_company.id}/',
            {'name': 'Hacked Name'}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCompanyDelete:
    """Test company deletion endpoint"""

    def test_delete_company_success(self, authenticated_client, company_with_admin):
        """Test member can delete company"""
        company_id = company_with_admin.id

        response = authenticated_client.delete(f'/api/accounts/companies/{company_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.objects.filter(id=company_id).exists()

    def test_delete_company_non_member(
        self, authenticated_client, create_company, create_user
    ):
        """Test non-member cannot delete company"""
        other_user = create_user(email='other@example.com')
        other_company = create_company(created_by=other_user)

        response = authenticated_client.delete(f'/api/accounts/companies/{other_company.id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCompanyMembers:
    """Test company member management endpoints"""

    def test_list_company_members(self, authenticated_client, company_with_admin, user):
        """Test listing company members"""
        response = authenticated_client.get(
            f'/api/accounts/companies/{company_with_admin.id}/members/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any(m['user_email'] == user.email for m in response.data)

    def test_add_member_success(
        self, authenticated_client, company_with_admin, create_user
    ):
        """Test admin can add member to company"""
        new_user = create_user(email='newmember@example.com')

        response = authenticated_client.post(
            f'/api/accounts/companies/{company_with_admin.id}/add_member/',
            {
                'email': new_user.email,
                'role': 'analyst'
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user_email'] == new_user.email
        assert response.data['role'] == 'analyst'

        # Verify member was added
        assert CompanyMember.objects.filter(
            company=company_with_admin,
            user=new_user,
            role='analyst'
        ).exists()

    def test_add_member_non_admin(
        self, authenticated_client, company_with_analyst, create_user
    ):
        """Test non-admin cannot add members"""
        new_user = create_user(email='newmember@example.com')

        response = authenticated_client.post(
            f'/api/accounts/companies/{company_with_analyst.id}/add_member/',
            {
                'email': new_user.email,
                'role': 'analyst'
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_add_member_nonexistent_user(self, authenticated_client, company_with_admin):
        """Test adding non-existent user fails"""
        response = authenticated_client.post(
            f'/api/accounts/companies/{company_with_admin.id}/add_member/',
            {
                'email': 'nonexistent@example.com',
                'role': 'analyst'
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_member_duplicate(
        self, authenticated_client, company_with_admin, user
    ):
        """Test adding duplicate member fails"""
        response = authenticated_client.post(
            f'/api/accounts/companies/{company_with_admin.id}/add_member/',
            {
                'email': user.email,
                'role': 'analyst'
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_member_success(
        self, authenticated_client, company_with_admin, create_user
    ):
        """Test admin can remove member"""
        # Add a member first
        member_user = create_user(email='member@example.com')
        CompanyMember.objects.create(
            company=company_with_admin,
            user=member_user,
            role='analyst'
        )

        response = authenticated_client.delete(
            f'/api/accounts/companies/{company_with_admin.id}/remove_member/',
            {'user_id': str(member_user.id)},
            format='json'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify member was removed
        assert not CompanyMember.objects.filter(
            company=company_with_admin,
            user=member_user
        ).exists()

    def test_remove_member_non_admin(
        self, authenticated_client, company_with_analyst, create_user
    ):
        """Test non-admin cannot remove members"""
        member_user = create_user(email='member@example.com')

        response = authenticated_client.delete(
            f'/api/accounts/companies/{company_with_analyst.id}/remove_member/',
            {'user_id': str(member_user.id)},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMemberships:
    """Test user memberships endpoint"""

    def test_list_memberships(self, authenticated_client, company_with_admin, user):
        """Test user can list their memberships"""
        response = authenticated_client.get('/api/accounts/memberships/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any(
            m['company'] == str(company_with_admin.id) and m['user'] == str(user.id)
            for m in response.data
        )

    def test_list_memberships_empty(self, authenticated_client):
        """Test user with no memberships sees empty list"""
        response = authenticated_client.get('/api/accounts/memberships/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0
