"""
Integration tests for complete upload → job → progress workflow.
Tests the full data flow from CSV upload to job completion.
"""
import pytest
import os
import tempfile
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from apps.analytics.models import DataUpload, Transaction, ProcessingJob, ModelResult
from apps.accounts.models import User, Company, CompanyMember


@pytest.mark.django_db
class TestUploadWorkflow:
    """Integration tests for upload → job workflow"""

    @pytest.fixture
    def api_client(self):
        """Create API client"""
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create test user"""
        return User.objects.create_user(
            email="workflow@test.com",
            password="testpass123",
            first_name="Workflow",
            last_name="User"
        )

    @pytest.fixture
    def test_company(self):
        """Create test company"""
        return Company.objects.create(
            name="Workflow Test Co",
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
    def valid_csv_content(self):
        """Generate valid CSV content"""
        csv_data = """trans_id,fecha,producto,glosa,cantidad,precio_unitario,total
T001,2024-01-01,P001,Product 1,2,100.0,200.0
T002,2024-01-02,P002,Product 2,1,150.0,150.0
T003,2024-01-03,P001,Product 1,3,100.0,300.0
"""
        return csv_data.encode('utf-8')

    @pytest.fixture
    def valid_csv_file(self, valid_csv_content):
        """Create valid CSV file"""
        return SimpleUploadedFile(
            "test_transactions.csv",
            valid_csv_content,
            content_type="text/csv"
        )

    def test_complete_workflow_upload_to_job_creation(
        self, api_client, test_user, test_company, company_membership, valid_csv_file
    ):
        """
        Test complete workflow: Upload CSV → Process → Auto-create Job

        Steps:
        1. Upload CSV file
        2. Verify DataUpload created
        3. Process CSV (sync for testing)
        4. Verify Transactions created
        5. Create ProcessingJob
        6. Verify Job created with correct config
        """
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Act - Step 1: Upload CSV
        upload_response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': valid_csv_file},
            format='multipart'
        )

        # Assert - Upload successful
        assert upload_response.status_code == status.HTTP_201_CREATED
        assert 'upload' in upload_response.data
        upload_id = upload_response.data['upload']['id']

        # Verify DataUpload created
        upload = DataUpload.objects.get(id=upload_id)
        assert upload.company == test_company
        assert upload.uploaded_by == test_user
        assert upload.status == 'pending'

        # Act - Step 2: Process CSV (simulate Celery task completion)
        from apps.analytics.services import DatasetGenerationService
        service = DatasetGenerationService(upload)
        result = service.process()

        # Assert - Processing successful
        assert result['success'] is True
        assert result['transactions_created'] == 3
        upload.refresh_from_db()
        assert upload.status == 'completed'

        # Verify Transactions created
        transactions = Transaction.objects.filter(upload=upload)
        assert transactions.count() == 3

        # Act - Step 3: Create Processing Job
        job_response = api_client.post(
            '/api/analytics/jobs/create_job/',
            {
                'upload_id': str(upload_id),
                'models_to_execute': ['transactions', 'daily', 'weekly']
            },
            format='json'
        )

        # Assert - Job created
        assert job_response.status_code == status.HTTP_201_CREATED
        assert 'job' in job_response.data
        job = ProcessingJob.objects.get(id=job_response.data['job']['id'])
        assert job.company == test_company
        assert job.upload == upload
        assert job.status == 'queued'
        assert set(job.models_to_execute) == {'transactions', 'daily', 'weekly'}
        assert job.celery_task_id is not None

    def test_upload_invalid_csv_format(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test uploading invalid CSV (missing required columns)"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        invalid_csv = SimpleUploadedFile(
            "invalid.csv",
            b"col1,col2\nval1,val2\n",  # Missing required columns
            content_type="text/csv"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': invalid_csv},
            format='multipart'
        )

        # Assert - Upload accepted but processing will fail
        assert response.status_code == status.HTTP_201_CREATED
        upload = DataUpload.objects.get(id=response.data['upload']['id'])

        # Process and verify failure
        from apps.analytics.services import DatasetGenerationService
        service = DatasetGenerationService(upload)
        result = service.process()

        assert result['success'] is False
        assert 'error' in result
        upload.refresh_from_db()
        assert upload.status == 'failed'

    def test_upload_without_company_membership(
        self, api_client, test_user, test_company, valid_csv_file
    ):
        """Test upload fails when user is not company member"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        # No company membership created

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': valid_csv_file},
            format='multipart'
        )

        # Assert - Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_job_for_pending_upload(
        self, api_client, test_user, test_company, company_membership, valid_csv_file
    ):
        """Test job creation fails for non-completed upload"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Upload but don't process
        upload = DataUpload.objects.create(
            company=test_company,
            uploaded_by=test_user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="pending"  # Not completed
        )

        # Act
        response = api_client.post(
            '/api/analytics/jobs/create_job/',
            {'upload_id': str(upload.id)},
            format='json'
        )

        # Assert - Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_job_creation(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test creating multiple jobs for same upload"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        upload = DataUpload.objects.create(
            company=test_company,
            uploaded_by=test_user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="completed"
        )

        # Act - Create first job
        response1 = api_client.post(
            '/api/analytics/jobs/create_job/',
            {'upload_id': str(upload.id)},
            format='json'
        )

        # Assert - First job created
        assert response1.status_code == status.HTTP_201_CREATED

        # Act - Create second job for same upload
        response2 = api_client.post(
            '/api/analytics/jobs/create_job/',
            {'upload_id': str(upload.id)},
            format='json'
        )

        # Assert - Second job also created (multiple jobs per upload allowed)
        assert response2.status_code == status.HTTP_201_CREATED
        assert ProcessingJob.objects.filter(upload=upload).count() == 2

    def test_job_status_polling(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test job status endpoint returns correct progress"""
        # Arrange
        api_client.force_authenticate(user=test_user)
        upload = DataUpload.objects.create(
            company=test_company,
            uploaded_by=test_user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="completed"
        )
        job = ProcessingJob.objects.create(
            company=test_company,
            upload=upload,
            models_to_execute=['model1', 'model2', 'model3'],
            status='running'
        )

        # Simulate partial completion
        job.add_completed_model('model1')
        job.add_completed_model('model2')

        # Act
        response = api_client.get(f'/api/analytics/jobs/{job.id}/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['progress'] == 66  # 2/3 = 66%
        assert len(response.data['models_completed']) == 2
        assert response.data['status'] == 'running'

    def test_large_csv_upload(
        self, api_client, test_user, test_company, company_membership
    ):
        """Test uploading large CSV file (stress test)"""
        # Arrange
        api_client.force_authenticate(user=test_user)

        # Generate large CSV (1000 rows)
        rows = ["trans_id,fecha,producto,glosa,cantidad,precio_unitario,total"]
        for i in range(1000):
            rows.append(f"T{i:04d},2024-01-01,P001,Product 1,1,100.0,100.0")

        large_csv = SimpleUploadedFile(
            "large.csv",
            "\n".join(rows).encode('utf-8'),
            content_type="text/csv"
        )

        # Act
        response = api_client.post(
            f'/api/analytics/companies/{test_company.id}/upload/',
            {'file': large_csv},
            format='multipart'
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        upload = DataUpload.objects.get(id=response.data['upload']['id'])

        # Process
        from apps.analytics.services import DatasetGenerationService
        service = DatasetGenerationService(upload)
        result = service.process()

        # Verify all rows processed
        assert result['success'] is True
        assert result['transactions_created'] == 1000
