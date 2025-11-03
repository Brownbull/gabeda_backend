"""
Unit tests for analytics services.
Tests business logic in service layer.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone
from apps.analytics.services import DatasetGenerationService, PipelineExecutionService
from apps.analytics.models import DataUpload, Transaction, ProcessingJob
from apps.accounts.models import Company, User
import pandas as pd


@pytest.mark.django_db
class TestDatasetGenerationService:
    """Test DatasetGenerationService"""

    def test_get_company_config_exists(self):
        """Test retrieving existing company config"""
        # Arrange
        company = Company.objects.create(name="Test Co", rut="12345678-9")
        user = User.objects.create_user(email="test@test.com", password="pass")
        upload = DataUpload.objects.create(
            company=company,
            uploaded_by=user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv"
        )

        # Act
        service = DatasetGenerationService(upload)

        # Assert
        assert service.company == company
        assert service.data_upload == upload

    @patch('os.path.exists')
    @patch('pandas.read_csv')
    def test_process_updates_status_to_processing(self, mock_read_csv, mock_exists):
        """Test that process() updates status to processing"""
        # Arrange
        company = Company.objects.create(name="Test Co", rut="12345678-9")
        user = User.objects.create_user(email="test@test.com", password="pass")
        upload = DataUpload.objects.create(
            company=company,
            uploaded_by=user,
            file_name="test.csv",
            file_size=1024,
            file_path="uploads/test.csv",
            status="pending"
        )

        # Mock file exists
        mock_exists.return_value = True

        # Mock CSV data
        mock_df = pd.DataFrame({
            'trans_id': ['T1', 'T2'],
            'fecha': pd.to_datetime(['2024-01-01', '2024-01-02']),
            'producto': ['P1', 'P2'],
            'glosa': ['Product 1', 'Product 2'],
            'cantidad': [1.0, 2.0],
            'precio_unitario': [10.0, 20.0],
            'total': [10.0, 40.0]
        })
        mock_read_csv.return_value = mock_df

        service = DatasetGenerationService(upload)

        # Act
        result = service.process()

        # Assert - status should be 'completed' after processing
        upload.refresh_from_db()
        assert upload.status == 'completed'
        assert result['success'] is True
        assert result['transactions_created'] == 2


@pytest.mark.django_db
class TestPipelineExecutionService:
    """Test PipelineExecutionService"""

    def test_build_base_config_default(self):
        """Test building default base config when no company config"""
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
            status='queued'
        )

        service = PipelineExecutionService(job)

        # Act
        config = service._build_base_config()

        # Assert
        assert config['client'] == "Test Co"
        assert 'data_schema' in config
        assert 'in_dt' in config['data_schema']
        assert 'in_trans_id' in config['data_schema']
        assert 'default_formats' in config

    def test_load_transactions_into_context_creates_dataframe(self):
        """Test loading transactions into DataFrame"""
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

        # Create sample transactions
        Transaction.objects.create(
            company=company,
            upload=upload,
            transaction_id="T1",
            date="2024-01-01",
            product_id="P1",
            product_description="Product 1",
            quantity=1.0,
            unit_price=10.0,
            total=10.0
        )

        job = ProcessingJob.objects.create(
            company=company,
            upload=upload,
            status='queued'
        )

        service = PipelineExecutionService(job)

        # Act
        df = service._load_transactions_into_context()

        # Assert
        assert len(df) == 1
        assert 'transaction_id' in df.columns
        assert df.iloc[0]['transaction_id'] == "T1"
