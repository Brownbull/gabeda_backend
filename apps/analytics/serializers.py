from rest_framework import serializers
from .models import (
    DataUpload, Transaction, Dataset, AnalyticsResult, CompanyConfig,
    ProcessingJob, ModelResult, DataExport
)


class DataUploadSerializer(serializers.ModelSerializer):
    """Serializer for DataUpload model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DataUpload
        fields = [
            'id', 'company', 'company_name', 'uploaded_by', 'uploaded_by_email',
            'file_name', 'file_size', 'file_path', 'status', 'status_display',
            'row_count', 'error_message', 'uploaded_at', 'processing_started_at',
            'processing_completed_at', 'analysis_start_date', 'analysis_end_date'
        ]
        read_only_fields = [
            'id', 'uploaded_by', 'file_size', 'file_path', 'status',
            'row_count', 'error_message', 'uploaded_at', 'processing_started_at',
            'processing_completed_at'
        ]


class CSVUploadSerializer(serializers.Serializer):
    """Serializer for CSV file upload"""

    file = serializers.FileField(required=True)

    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file extension
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are allowed.")

        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(f"File size cannot exceed 50MB. Current size: {value.size / (1024*1024):.2f}MB")

        # Check file is not empty
        if value.size == 0:
            raise serializers.ValidationError("Uploaded file is empty.")

        return value


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_file_name = serializers.CharField(source='upload.file_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'company', 'company_name', 'upload', 'upload_file_name',
            'transaction_id', 'date', 'product_id', 'product_description',
            'quantity', 'unit_price', 'total', 'cost', 'customer_id',
            'category', 'hour', 'weekday', 'month', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_file_name = serializers.CharField(source='upload.file_name', read_only=True)
    dataset_type_display = serializers.CharField(source='get_dataset_type_display', read_only=True)

    class Meta:
        model = Dataset
        fields = [
            'id', 'company', 'company_name', 'upload', 'upload_file_name',
            'name', 'dataset_type', 'dataset_type_display', 'description',
            'file_path', 'file_size', 'row_count', 'column_count',
            'context_folder', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AnalyticsResultSerializer(serializers.ModelSerializer):
    """Serializer for AnalyticsResult model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_file_name = serializers.CharField(source='upload.file_name', read_only=True)
    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)

    class Meta:
        model = AnalyticsResult
        fields = [
            'id', 'company', 'company_name', 'upload', 'upload_file_name',
            'result_type', 'result_type_display', 'title', 'value',
            'metadata', 'visible_to_roles', 'created_at', 'analysis_date'
        ]
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        """Filter results based on user role"""
        representation = super().to_representation(instance)

        # Get current user's role for this company
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from apps.accounts.models import CompanyMember

            member = CompanyMember.objects.filter(
                company=instance.company,
                user=request.user
            ).first()

            if member:
                # If visible_to_roles is empty, visible to all
                # Otherwise, check if user's role is in the list
                visible_to_roles = instance.visible_to_roles
                if visible_to_roles and member.role not in visible_to_roles:
                    # User doesn't have access to this result
                    return None

        return representation


class AnalyticsResultListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing analytics results"""

    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)

    class Meta:
        model = AnalyticsResult
        fields = [
            'id', 'result_type', 'result_type_display', 'title',
            'analysis_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CompanyConfigSerializer(serializers.ModelSerializer):
    """Serializer for CompanyConfig model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    required_columns = serializers.ListField(read_only=True)

    class Meta:
        model = CompanyConfig
        fields = [
            'id', 'company', 'company_name', 'data_schema', 'default_formats',
            'required_columns', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'company', 'created_at', 'updated_at', 'created_by']

    def validate_data_schema(self, value):
        """
        Validate data_schema structure
        Based on COLUMN_SCHEMA from src/core/constants.py:
        - REQUIRED columns (optional=0): 5 fields that MUST be present
        - OPTIONAL columns (optional=1): 12 fields that CAN be present
        """
        # REQUIRED columns from COLUMN_SCHEMA (optional=0)
        required_fields = [
            'in_dt',          # Transaction datetime
            'in_trans_id',    # Transaction ID
            'in_product_id',  # Product ID
            'in_quantity',    # Quantity
            'in_price_total'  # Total price
        ]

        # Check all required fields are present
        missing_fields = [f for f in required_fields if f not in value]
        if missing_fields:
            raise serializers.ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Validate each field has required properties
        for field_name, field_config in value.items():
            if 'source_column' not in field_config:
                raise serializers.ValidationError(
                    f"Field '{field_name}' missing 'source_column'"
                )
            if 'dtype' not in field_config:
                raise serializers.ValidationError(
                    f"Field '{field_name}' missing 'dtype'"
                )

            # Validate dtype
            valid_dtypes = ['date', 'str', 'float', 'int']
            if field_config['dtype'] not in valid_dtypes:
                raise serializers.ValidationError(
                    f"Field '{field_name}' has invalid dtype '{field_config['dtype']}'. "
                    f"Valid types: {', '.join(valid_dtypes)}"
                )

        return value

    def validate_default_formats(self, value):
        """Validate default_formats structure"""
        if not value:
            return value

        # Optional validation for format structure
        if 'date' in value and not isinstance(value['date'], str):
            raise serializers.ValidationError("'date' format must be a string")

        if 'float' in value:
            if not isinstance(value['float'], dict):
                raise serializers.ValidationError("'float' format must be a dict")
            if 'thousands' not in value['float'] or 'decimal' not in value['float']:
                raise serializers.ValidationError(
                    "'float' format must have 'thousands' and 'decimal' keys"
                )

        if 'int' in value:
            if not isinstance(value['int'], dict):
                raise serializers.ValidationError("'int' format must be a dict")
            if 'thousands' not in value['int'] or 'decimal' not in value['int']:
                raise serializers.ValidationError(
                    "'int' format must have 'thousands' and 'decimal' keys"
                )

        return value


class ProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for ProcessingJob model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_file_name = serializers.CharField(source='upload.file_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProcessingJob
        fields = [
            'id', 'company', 'company_name', 'upload', 'upload_file_name',
            'celery_task_id', 'models_to_execute', 'models_completed', 'current_model',
            'status', 'status_display', 'progress', 'is_complete',
            'processing_time_seconds', 'last_checkpoint',
            'error_message', 'error_traceback',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'celery_task_id', 'models_completed', 'current_model',
            'status', 'progress', 'processing_time_seconds', 'last_checkpoint',
            'error_message', 'error_traceback',
            'created_at', 'started_at', 'completed_at'
        ]


class ProcessingJobListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing processing jobs"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProcessingJob
        fields = [
            'id', 'company', 'company_name', 'status', 'status_display',
            'progress', 'current_model', 'models_to_execute', 'models_completed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ModelResultSerializer(serializers.ModelSerializer):
    """Serializer for ModelResult model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    job_id = serializers.UUIDField(source='job.id', read_only=True)
    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)

    class Meta:
        model = ModelResult
        fields = [
            'id', 'company', 'company_name', 'job', 'job_id',
            'model_name', 'result_type', 'result_type_display',
            'row_count', 'column_count', 'columns',
            'data_path', 'data_preview', 'execution_time_ms',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ModelResultListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing model results"""

    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)

    class Meta:
        model = ModelResult
        fields = [
            'id', 'model_name', 'result_type', 'result_type_display',
            'row_count', 'column_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DataExportSerializer(serializers.ModelSerializer):
    """Serializer for DataExport model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    job_id = serializers.UUIDField(source='job.id', read_only=True)
    requested_by_email = serializers.EmailField(source='requested_by.email', read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = DataExport
        fields = [
            'id', 'company', 'company_name', 'job', 'job_id',
            'requested_by', 'requested_by_email',
            'export_format', 'export_format_display', 'models_included',
            'file_path', 'file_size_bytes', 'download_url',
            'status', 'status_display', 'celery_task_id', 'error_message',
            'is_expired', 'created_at', 'completed_at', 'expires_at'
        ]
        read_only_fields = [
            'id', 'requested_by', 'file_path', 'file_size_bytes', 'download_url',
            'status', 'celery_task_id', 'error_message',
            'created_at', 'completed_at'
        ]


class DataExportListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing data exports"""

    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = DataExport
        fields = [
            'id', 'export_format', 'export_format_display',
            'status', 'status_display', 'is_expired',
            'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProcessingJobCreateSerializer(serializers.Serializer):
    """Serializer for creating a new processing job"""

    upload_id = serializers.UUIDField(required=True)
    models_to_execute = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='List of model names to execute. Default: all 9 models'
    )

    def validate_upload_id(self, value):
        """Validate that upload exists and belongs to user's company"""
        try:
            upload = DataUpload.objects.get(id=value)
        except DataUpload.DoesNotExist:
            raise serializers.ValidationError("Upload not found.")

        # Check status
        if upload.status != 'completed':
            raise serializers.ValidationError(
                f"Upload must be in 'completed' status. Current status: {upload.status}"
            )

        return value

    def validate_models_to_execute(self, value):
        """Validate model names"""
        valid_models = [
            'transactions', 'daily', 'daily_hour', 'weekly', 'monthly',
            'product_daily', 'product_month', 'customer_daily', 'customer_profile'
        ]

        if not value:
            # Default to all models
            return valid_models

        invalid_models = [m for m in value if m not in valid_models]
        if invalid_models:
            raise serializers.ValidationError(
                f"Invalid model names: {', '.join(invalid_models)}. "
                f"Valid names: {', '.join(valid_models)}"
            )

        return value
