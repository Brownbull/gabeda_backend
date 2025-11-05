"""
Edge case tests for upload and job creation API endpoints.
Tests boundary conditions, error handling, and security scenarios.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from apps.analytics.models import DataUpload, ProcessingJob
from apps.accounts.models import User, Company, CompanyMember


@pytest.mark.django_db
class TestUploadEdgeCases:
    """Edge case tests for CSV upload endpoint"""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def test_user(self):
        return User.objects.create_user(
            email="edge@test.com",
            password="testpass123"
        )

    @pytest.fixture
    def test_company(self):
        return Company.objects.create(
            name="Edge Test Co",
            rut="98765432-1"
        )

    @pytest.fixture
    def company_membership(self, test_user, test_company):
        return CompanyMember.objects.create(
            user=test_user,
            company=test_company,
            role='admin'
        )

    def test_upload_empty_file(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test uploading empty CSV file"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        empty_file = SimpleUploadedFile(
            "empty.csv",
            b"",
            content_type="text/csv"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': empty_file},
            format='multipart'
        )

        # Assert - Should accept but processing will fail
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED]

    def test_upload_non_csv_file(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test uploading non-CSV file"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        pdf_file = SimpleUploadedFile(
            "file.pdf",
            b"%PDF-1.4 fake pdf content",
            content_type="application/pdf"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': pdf_file},
            format='multipart'
        )

        # Assert - Should reject non-CSV
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_csv_with_special_characters(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test CSV with special characters in data"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        csv_content = (
            b"trans_id,fecha,producto,glosa,cantidad,precio_unitario,total\n"
            b'T001,2024-01-01,P001,"Product with, comma",1,100.0,100.0\n'
            b'T002,2024-01-02,P002,"Product with ""quotes""",1,150.0,150.0\n'
            b"T003,2024-01-03,P003,Special Product Name,1,200.0,200.0\n"
        )
        csv_with_special = SimpleUploadedFile(
            "special.csv",
            csv_content,
            content_type="text/csv"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': csv_with_special},
            format='multipart'
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_csv_with_missing_values(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test CSV with NULL/missing values"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        csv_content = (
            b"trans_id,fecha,producto,glosa,cantidad,precio_unitario,total\n"
            b"T001,2024-01-01,P001,,1,100.0,100.0\n"
            b"T002,2024-01-02,,Product 2,1,,150.0\n"
            b"T003,,,Product 3,1,100.0,\n"
        )
        csv_with_nulls = SimpleUploadedFile(
            "nulls.csv",
            csv_content,
            content_type="text/csv"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': csv_with_nulls},
            format='multipart'
        )

        # Assert - Upload accepted, processing may handle NULLs
        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_without_authentication(
        self, api_client, test_company
    ):
        """Test upload without authentication token"""
        # Arrange
        csv_file = SimpleUploadedFile(
            "test.csv",
            b"trans_id,fecha\nT001,2024-01-01\n",
            content_type="text/csv"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_to_nonexistent_company(
        self, api_client, test_user
    ):
        """Test upload to company that doesn't exist"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        csv_file = SimpleUploadedFile(
            "test.csv",
            b"trans_id,fecha\nT001,2024-01-01\n",
            content_type="text/csv"
        )
        fake_company_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{fake_company_id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        # Assert - Returns 403 for security (doesn't reveal company existence)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_csv_with_inconsistent_columns(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test CSV where rows have different number of columns"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        csv_content = (
            b"trans_id,fecha,producto,glosa,cantidad,precio_unitario,total\n"
            b"T001,2024-01-01,P001,Product 1,1,100.0,100.0\n"
            b"T002,2024-01-02,P002,Product 2,1,150.0\n"
            b"T003,2024-01-03,P003,Product 3,1,200.0,200.0,extra_col\n"
        )
        bad_csv = SimpleUploadedFile(
            "bad.csv",
            csv_content,
            content_type="text/csv"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': bad_csv},
            format='multipart'
        )

        # Assert - Upload accepted but processing may fail
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestJobCreationEdgeCases:
    """Edge case tests for job creation endpoint"""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def test_user(self):
        return User.objects.create_user(
            email="job@test.com",
            password="testpass123"
        )

    @pytest.fixture
    def test_company(self):
        return Company.objects.create(
            name="Job Test Co",
            rut="11111111-1"
        )

    @pytest.fixture
    def company_membership(self, test_user, test_company):
        return CompanyMember.objects.create(
            user=test_user,
            company=test_company,
            role='admin'
        )

    @pytest.fixture
    def completed_upload(self, test_user, test_company):
        return DataUpload.objects.create(
            company=test_company,
            uploaded_by=test_user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="completed"
        )

    def test_create_job_with_invalid_model_names(
        self, api_client, test_user, company_membership, completed_upload
    ):
        """Test job creation with invalid model names"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Act
        response = api_client.post(
            '/api/analytics/jobs/create_job/',
            {
                'upload_id': str(completed_upload.id),
                'models_to_execute': ['invalid_model', 'fake_model']
            },
            format='json'
        )

        # Assert - System validates model names upfront and rejects invalid ones
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_job_with_empty_models_list(
        self, api_client, test_user, company_membership, completed_upload
    ):
        """Test job creation with empty models list"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Act
        response = api_client.post(
            '/api/analytics/jobs/create_job/',
            {
                'upload_id': str(completed_upload.id),
                'models_to_execute': []
            },
            format='json'
        )

        # Assert - Should use default models
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data['job']['models_to_execute']) == 9  # All 9 models

    def test_create_job_with_duplicate_model_names(
        self, api_client, test_user, company_membership, completed_upload
    ):
        """Test job creation with duplicate model names"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Act
        response = api_client.post(
            '/api/analytics/jobs/create_job/',
            {
                'upload_id': str(completed_upload.id),
                'models_to_execute': ['transactions', 'transactions', 'daily']
            },
            format='json'
        )

        # Assert - Duplicates should be handled
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_job_with_missing_upload_id(
        self, api_client, test_user, company_membership
    ):
        """Test job creation without upload_id"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Act
        response = api_client.post(
            '/api/analytics/jobs/create_job/',
            {'models_to_execute': ['transactions']},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_job_with_invalid_upload_id(
        self, api_client, test_user, company_membership
    ):
        """Test job creation with non-existent upload ID"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        fake_upload_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = api_client.post(
            '/api/analytics/jobs/create_job/',
            {'upload_id': fake_upload_id},
            format='json'
        )

        # Assert
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]

    def test_job_status_for_nonexistent_job(
        self, api_client, test_user, company_membership
    ):
        """Test retrieving status of non-existent job"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        fake_job_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = api_client.get(f'/api/analytics/jobs/{fake_job_id}/')

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_concurrent_job_execution(
        self, api_client, test_user, company_membership, completed_upload
    ):
        """Test creating multiple jobs concurrently"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Act - Create 3 jobs
        jobs = []
        for i in range(3):
            response = api_client.post(
                '/api/analytics/jobs/create_job/',
                {
                    'upload_id': str(completed_upload.id),
                    'models_to_execute': ['transactions']
                },
                format='json'
            )
            jobs.append(response.data['job']['id'])

        # Assert - All jobs created
        assert ProcessingJob.objects.filter(upload=completed_upload).count() == 3
        assert all(job_id for job_id in jobs)

    def test_job_progress_calculation_accuracy(
        self, api_client, test_user, test_company, company_membership, completed_upload
    ):
        """Test that job progress calculation is accurate"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        job = ProcessingJob.objects.create(
            company=test_company,
            upload=completed_upload,
            models_to_execute=['m1', 'm2', 'm3', 'm4', 'm5'],
            status='running'
        )

        # Act & Assert - Test progress at different completion stages
        job.add_completed_model('m1')
        assert job.progress == 20  # 1/5 = 20%

        job.add_completed_model('m2')
        job.add_completed_model('m3')
        assert job.progress == 60  # 3/5 = 60%

        job.add_completed_model('m4')
        job.add_completed_model('m5')
        assert job.progress == 100  # 5/5 = 100%
