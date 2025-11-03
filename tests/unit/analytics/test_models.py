"""
Unit tests for analytics models.
Tests basic model functionality and business logic.
"""
import pytest
from django.utils import timezone
from apps.analytics.models import DataUpload, ProcessingJob, ModelResult, DataExport
from apps.accounts.models import Company, User


@pytest.mark.django_db
class TestDataUploadModel:
    """Test DataUpload model"""

    def test_create_data_upload_success(self):
        """Test creating a DataUpload instance"""
        # Arrange
        company = Company.objects.create(
            name="Test Company",
            rut="12345678-9"
        )
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )

        # Act
        upload = DataUpload.objects.create(
            company=company,
            uploaded_by=user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="pending"
        )

        # Assert
        assert upload.id is not None
        assert upload.status == "pending"
        assert upload.company == company
        assert upload.uploaded_by == user

    def test_status_choices(self):
        """Test that valid status choices are accepted"""
        valid_statuses = ['pending', 'validating', 'processing', 'completed', 'failed']

        company = Company.objects.create(name="Test Co", rut="12345678-9")
        user = User.objects.create_user(email="test@test.com", password="pass")

        for status in valid_statuses:
            upload = DataUpload.objects.create(
                company=company,
                uploaded_by=user,
                file_name=f"test_{status}.csv",
                file_size=1024,
                file_path=f"uploads/test_{status}.csv",
                status=status
            )
            assert upload.status == status


@pytest.mark.django_db
class TestProcessingJobModel:
    """Test ProcessingJob model"""

    def test_add_completed_model_updates_progress(self):
        """Test that adding completed models updates progress percentage"""
        # Arrange
        company = Company.objects.create(name="Test Co", rut="12345678-9")
        user = User.objects.create_user(email="test@test.com", password="pass")
        upload = DataUpload.objects.create(
            company=company,
            uploaded_by=user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="completed"
        )

        job = ProcessingJob.objects.create(
            company=company,
            upload=upload,
            models_to_execute=['model1', 'model2', 'model3'],
            status='running'
        )

        # Act & Assert
        assert job.progress == 0

        job.add_completed_model('model1')
        assert job.progress == 33  # 1/3 = 33%

        job.add_completed_model('model2')
        assert job.progress == 66  # 2/3 = 66%

        job.add_completed_model('model3')
        assert job.progress == 100  # 3/3 = 100%

    def test_is_complete_property(self):
        """Test is_complete property for terminal states"""
        company = Company.objects.create(name="Test Co", rut="12345678-9")
        user = User.objects.create_user(email="test@test.com", password="pass")
        upload = DataUpload.objects.create(
            company=company,
            uploaded_by=user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv"
        )

        # Test non-terminal states
        job = ProcessingJob.objects.create(
            company=company,
            upload=upload,
            status='queued'
        )
        assert job.is_complete is False

        job.status = 'running'
        job.save()
        assert job.is_complete is False

        # Test terminal states
        job.status = 'completed'
        job.save()
        assert job.is_complete is True

        job.status = 'failed'
        job.save()
        assert job.is_complete is True

        job.status = 'cancelled'
        job.save()
        assert job.is_complete is True
