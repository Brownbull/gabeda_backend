"""
API tests for ProcessingJob endpoints.
Tests authentication, permissions, and CRUD operations.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.analytics.models import DataUpload, ProcessingJob
from apps.accounts.models import Company, User, CompanyMember


@pytest.mark.django_db
class TestProcessingJobAPI:
    """Test ProcessingJob API endpoints"""

    @pytest.fixture
    def api_client(self):
        """Create API client"""
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create test user"""
        return User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )

    @pytest.fixture
    def test_company(self):
        """Create test company"""
        return Company.objects.create(
            name="Test Company",
            rut="12345678-9"
        )

    @pytest.fixture
    def company_membership(self, test_user, test_company):
        """Create company membership"""
        return CompanyMember.objects.create(
            user=test_user,
            company=test_company,
            role='admin'
        )

    @pytest.fixture
    def completed_upload(self, test_company, test_user):
        """Create completed upload"""
        return DataUpload.objects.create(
            company=test_company,
            uploaded_by=test_user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="completed"
        )

    def test_list_jobs_requires_authentication(self, api_client):
        """Test that listing jobs requires authentication"""
        # Act
        response = api_client.get('/api/analytics/jobs/')

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_jobs_success(self, api_client, test_user, test_company, company_membership):
        """Test listing jobs for authenticated user"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Act
        response = api_client.get('/api/analytics/jobs/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Response is paginated (OrderedDict with 'results' key)
        assert 'results' in response.data
        assert isinstance(response.data['results'], list)

    def test_create_job_requires_authentication(self, api_client, completed_upload):
        """Test that creating a job requires authentication"""
        # Arrange
        data = {
            'upload_id': str(completed_upload.id),
            'models_to_execute': ['transactions', 'daily']
        }

        # Act
        response = api_client.post('/api/analytics/jobs/create_job/', data)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_job_success(self, api_client, test_user, company_membership, completed_upload):
        """Test creating a processing job successfully"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        data = {
            'upload_id': str(completed_upload.id),
            'models_to_execute': ['transactions', 'daily']
        }

        # Act
        response = api_client.post('/api/analytics/jobs/create_job/', data, format='json')

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert 'job' in response.data
        assert response.data['job']['status'] == 'queued'
        assert response.data['job']['celery_task_id'] is not None

    def test_create_job_validates_upload_status(self, api_client, test_user, test_company, company_membership):
        """Test that job creation validates upload status"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Create pending upload (not completed)
        upload = DataUpload.objects.create(
            company=test_company,
            uploaded_by=test_user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="pending"  # Not completed!
        )

        data = {
            'upload_id': str(upload.id)
        }

        # Act
        response = api_client.post('/api/analytics/jobs/create_job/', data, format='json')

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
