"""
Test superuser/staff permissions for accessing resources across companies.
Tests that admin users can access any resource regardless of company membership.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.analytics.models import DataUpload, ProcessingJob
from apps.accounts.models import User, Company, CompanyMember


@pytest.mark.django_db
class TestSuperuserPermissions:
    """Test that superusers can access resources across all companies"""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def superuser(self):
        """Create a superuser (admin)"""
        return User.objects.create_user(
            email="admin@gabeda.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True
        )

    @pytest.fixture
    def regular_user(self):
        """Create a regular user"""
        return User.objects.create_user(
            email="user@test.com",
            password="userpass123"
        )

    @pytest.fixture
    def company_a(self):
        """Company A"""
        return Company.objects.create(
            name="Company A",
            rut="11111111-1"
        )

    @pytest.fixture
    def company_b(self):
        """Company B"""
        return Company.objects.create(
            name="Company B",
            rut="22222222-2"
        )

    @pytest.fixture
    def upload_company_a(self, company_a, regular_user):
        """Upload belonging to Company A"""
        return DataUpload.objects.create(
            company=company_a,
            uploaded_by=regular_user,
            file_name="company_a_data.csv",
            file_size=1024,
            file_path="uploads/company_a_data.csv",
            status="completed"
        )

    @pytest.fixture
    def upload_company_b(self, company_b, regular_user):
        """Upload belonging to Company B"""
        return DataUpload.objects.create(
            company=company_b,
            uploaded_by=regular_user,
            file_name="company_b_data.csv",
            file_size=2048,
            file_path="uploads/company_b_data.csv",
            status="completed"
        )

    @pytest.fixture
    def user_member_of_company_a(self, regular_user, company_a):
        """Make regular user a member of Company A only"""
        return CompanyMember.objects.create(
            user=regular_user,
            company=company_a,
            role='admin'
        )

    def test_superuser_can_access_any_upload(
        self, api_client, superuser, upload_company_a, upload_company_b
    ):
        """Superuser can access uploads from any company"""
        # Arrange
        api_client.force_authenticate(user=superuser)

        # Act - Access upload from Company A
        response_a = api_client.get(f'/api/analytics/uploads/{upload_company_a.id}/')

        # Assert - Superuser can access Company A's upload
        assert response_a.status_code == status.HTTP_200_OK
        assert response_a.data['id'] == str(upload_company_a.id)
        assert str(response_a.data['company']) == str(upload_company_a.company_id)

        # Act - Access upload from Company B
        response_b = api_client.get(f'/api/analytics/uploads/{upload_company_b.id}/')

        # Assert - Superuser can access Company B's upload
        assert response_b.status_code == status.HTTP_200_OK
        assert response_b.data['id'] == str(upload_company_b.id)
        assert str(response_b.data['company']) == str(upload_company_b.company_id)

    def test_superuser_can_list_all_uploads(
        self, api_client, superuser, upload_company_a, upload_company_b
    ):
        """Superuser can list uploads from all companies"""
        # Arrange
        api_client.force_authenticate(user=superuser)

        # Act
        response = api_client.get('/api/analytics/uploads/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        upload_ids = [u['id'] for u in response.data['results']]
        assert str(upload_company_a.id) in upload_ids
        assert str(upload_company_b.id) in upload_ids

    def test_regular_user_cannot_access_other_company_upload(
        self, api_client, regular_user, user_member_of_company_a,
        upload_company_a, upload_company_b
    ):
        """Regular user can only access uploads from their companies"""
        # Arrange
        api_client.force_authenticate(user=regular_user)

        # Act - Try to access Company A's upload (user is a member)
        response_a = api_client.get(f'/api/analytics/uploads/{upload_company_a.id}/')

        # Assert - Regular user CAN access their company's upload
        assert response_a.status_code == status.HTTP_200_OK
        assert response_a.data['id'] == str(upload_company_a.id)

        # Act - Try to access Company B's upload (user is NOT a member)
        response_b = api_client.get(f'/api/analytics/uploads/{upload_company_b.id}/')

        # Assert - Regular user CANNOT access other company's upload
        assert response_b.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_user_can_access_any_upload(
        self, api_client, upload_company_a, upload_company_b
    ):
        """Staff user (not superuser but is_staff=True) can access any upload"""
        # Arrange
        staff_user = User.objects.create_user(
            email="staff@gabeda.com",
            password="staffpass123",
            is_staff=True,
            is_superuser=False  # Staff but not superuser
        )
        api_client.force_authenticate(user=staff_user)

        # Act
        response_a = api_client.get(f'/api/analytics/uploads/{upload_company_a.id}/')
        response_b = api_client.get(f'/api/analytics/uploads/{upload_company_b.id}/')

        # Assert - Staff can access both
        assert response_a.status_code == status.HTTP_200_OK
        assert response_b.status_code == status.HTTP_200_OK

    def test_superuser_can_access_job_from_any_company(
        self, api_client, superuser, company_a, company_b, upload_company_a, upload_company_b
    ):
        """Superuser can access processing jobs from any company"""
        # Arrange
        job_a = ProcessingJob.objects.create(
            company=company_a,
            upload=upload_company_a,
            models_to_execute=['transactions'],
            status='completed'
        )
        job_b = ProcessingJob.objects.create(
            company=company_b,
            upload=upload_company_b,
            models_to_execute=['daily'],
            status='running'
        )
        api_client.force_authenticate(user=superuser)

        # Act
        response_a = api_client.get(f'/api/analytics/jobs/{job_a.id}/')
        response_b = api_client.get(f'/api/analytics/jobs/{job_b.id}/')

        # Assert
        assert response_a.status_code == status.HTTP_200_OK
        assert response_a.data['id'] == str(job_a.id)
        assert response_b.status_code == status.HTTP_200_OK
        assert response_b.data['id'] == str(job_b.id)
