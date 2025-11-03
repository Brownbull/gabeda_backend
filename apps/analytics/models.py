from django.db import models
from django.utils import timezone
import uuid
from apps.accounts.models import Company, User


class DataUpload(models.Model):
    """
    Tracks CSV file uploads and their processing status
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('validating', 'Validating'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='data_uploads')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploads')

    # File info
    file_name = models.CharField('file name', max_length=255)
    file_size = models.IntegerField('file size (bytes)')
    file_path = models.CharField('file path', max_length=500)

    # Processing status
    status = models.CharField('status', max_length=20, choices=STATUS_CHOICES, default='pending')
    row_count = models.IntegerField('row count', null=True, blank=True)
    error_message = models.TextField('error message', blank=True)

    # Processing metadata (stores results from Celery task)
    processing_metadata = models.JSONField(
        'processing metadata',
        null=True,
        blank=True,
        help_text='Metadata from processing (transactions created, datasets created, processing time, etc.)'
    )

    # Timestamps
    uploaded_at = models.DateTimeField('uploaded at', default=timezone.now)
    processing_started_at = models.DateTimeField('processing started at', null=True, blank=True)
    processing_completed_at = models.DateTimeField('processing completed at', null=True, blank=True)
    updated_at = models.DateTimeField('updated at', auto_now=True)

    # Analysis metadata
    analysis_start_date = models.DateField('analysis start date', null=True, blank=True)
    analysis_end_date = models.DateField('analysis end date', null=True, blank=True)

    class Meta:
        db_table = 'data_uploads'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.company.name} ({self.status})"


class Transaction(models.Model):
    """
    Individual transaction records from uploaded CSV files
    Multi-tenant: Each transaction belongs to a company
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    upload = models.ForeignKey(DataUpload, on_delete=models.CASCADE, related_name='transactions')

    # Original transaction data
    transaction_id = models.CharField('transaction ID', max_length=100)
    date = models.DateField('transaction date')
    product_id = models.CharField('product ID', max_length=100)
    product_description = models.CharField('product description', max_length=500)
    quantity = models.DecimalField('quantity', max_digits=10, decimal_places=2)
    unit_price = models.DecimalField('unit price', max_digits=12, decimal_places=2)
    total = models.DecimalField('total', max_digits=12, decimal_places=2)

    # Optional fields
    cost = models.DecimalField('cost', max_digits=12, decimal_places=2, null=True, blank=True)
    customer_id = models.CharField('customer ID', max_length=100, blank=True)
    category = models.CharField('category', max_length=100, blank=True)

    # Time components (auto-extracted from date if available in CSV)
    hour = models.IntegerField('hour', null=True, blank=True)
    weekday = models.IntegerField('weekday', null=True, blank=True)  # 0=Monday, 6=Sunday
    month = models.IntegerField('month', null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField('created at', auto_now_add=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-date', 'transaction_id']
        indexes = [
            models.Index(fields=['company', 'date']),
            models.Index(fields=['company', 'product_id']),
            models.Index(fields=['upload']),
            models.Index(fields=['date']),
            models.Index(fields=['transaction_id']),
        ]
        unique_together = [('company', 'transaction_id', 'upload')]

    def __str__(self):
        return f"{self.transaction_id} - {self.product_description} ({self.date})"


class Dataset(models.Model):
    """
    Generated datasets from GabeDA analysis pipeline
    Stores references to generated dataset files
    """
    DATASET_TYPE_CHOICES = [
        ('raw', 'Raw Data'),
        ('filtered', 'Filtered Data'),
        ('aggregated', 'Aggregated Data'),
        ('analytics', 'Analytics Results'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='datasets')
    upload = models.ForeignKey(DataUpload, on_delete=models.CASCADE, related_name='datasets')

    # Dataset info
    name = models.CharField('dataset name', max_length=200)
    dataset_type = models.CharField('dataset type', max_length=20, choices=DATASET_TYPE_CHOICES)
    description = models.TextField('description', blank=True)

    # File info
    file_path = models.CharField('file path', max_length=500)
    file_size = models.IntegerField('file size (bytes)', null=True, blank=True)
    row_count = models.IntegerField('row count', null=True, blank=True)
    column_count = models.IntegerField('column count', null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField('created at', auto_now_add=True)
    context_folder = models.CharField('context folder', max_length=500, blank=True)

    class Meta:
        db_table = 'datasets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'dataset_type']),
            models.Index(fields=['upload']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.dataset_type}) - {self.company.name}"


class CompanyConfig(models.Model):
    """
    Stores CSV column mapping and format configuration per company
    Mirrors base_cfg['data_schema'] and base_cfg['default_formats'] from notebooks
    """

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='analytics_config',
        help_text='Company this configuration belongs to'
    )

    # Configuration JSON - mirrors notebook base_cfg structure
    data_schema = models.JSONField(
        'data schema',
        help_text='Column mapping: {in_dt: {source_column: "Fecha venta", dtype: "date", format: "%d-%m-%Y"}}'
    )

    default_formats = models.JSONField(
        'default formats',
        default=dict,
        blank=True,
        help_text='Default formats: {date: "%m/%d/%Y %H:%M", float: {thousands: ".", decimal: ","}}'
    )

    # Metadata
    created_at = models.DateTimeField('created at', auto_now_add=True)
    updated_at = models.DateTimeField('updated at', auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_configs'
    )

    class Meta:
        db_table = 'analytics_company_config'
        verbose_name = 'Company Configuration'
        verbose_name_plural = 'Company Configurations'

    def __str__(self):
        return f"Configuration for {self.company.name}"

    @property
    def required_columns(self):
        """
        Returns list of required column names from data_schema
        17 standard columns from notebook
        """
        return list(self.data_schema.keys())

    def get_base_cfg_dict(self):
        """
        Convert CompanyConfig to base_cfg dictionary format for notebook execution
        """
        return {
            'data_schema': self.data_schema,
            'default_formats': self.default_formats,
            'client': self.company.name,
        }


class AnalyticsResult(models.Model):
    """
    Stores analytics results, KPIs, and insights generated by GabeDA
    """
    RESULT_TYPE_CHOICES = [
        ('kpi', 'KPI'),
        ('alert', 'Alert'),
        ('insight', 'Insight'),
        ('forecast', 'Forecast'),
        ('pareto', 'Pareto Analysis'),
        ('inventory', 'Inventory Health'),
        ('peak_times', 'Peak Times'),
        ('cross_sell', 'Cross-Sell Opportunity'),
        ('rfm', 'RFM Segmentation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='analytics_results')
    upload = models.ForeignKey(DataUpload, on_delete=models.CASCADE, related_name='analytics_results')

    # Result info
    result_type = models.CharField('result type', max_length=20, choices=RESULT_TYPE_CHOICES)
    title = models.CharField('title', max_length=200)
    value = models.JSONField('value')  # Store flexible result data
    metadata = models.JSONField('metadata', default=dict, blank=True)

    # Accessibility by role
    visible_to_roles = models.JSONField('visible to roles', default=dict, blank=True)
    # Empty list = visible to all roles
    # Example: ['admin', 'business_owner', 'analyst']

    # Timestamps
    created_at = models.DateTimeField('created at', auto_now_add=True)
    analysis_date = models.DateField('analysis date', null=True, blank=True)

    class Meta:
        db_table = 'analytics_results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'result_type']),
            models.Index(fields=['upload']),
            models.Index(fields=['created_at']),
            models.Index(fields=['result_type']),
        ]

    def __str__(self):
        return f"{self.title} ({self.result_type}) - {self.company.name}"


class ProcessingJob(models.Model):
    """
    Tracks async processing jobs for the 9-model pipeline execution
    Links upload → processing → results
    """
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='processing_jobs')
    upload = models.ForeignKey(DataUpload, on_delete=models.CASCADE, related_name='processing_jobs')

    # Celery task tracking
    celery_task_id = models.CharField('celery task ID', max_length=255, null=True, blank=True)

    # Model execution tracking
    models_to_execute = models.JSONField(
        'models to execute',
        default=list,
        help_text='List of model names: ["transactions", "daily", "weekly", "monthly", ...]'
    )
    models_completed = models.JSONField(
        'models completed',
        default=list,
        help_text='List of completed model names'
    )
    current_model = models.CharField('current model', max_length=50, null=True, blank=True)

    # Status and progress
    status = models.CharField('status', max_length=20, choices=STATUS_CHOICES, default='queued')
    progress = models.IntegerField('progress (%)', default=0)

    # Performance metrics
    processing_time_seconds = models.FloatField('processing time (seconds)', null=True, blank=True)
    last_checkpoint = models.CharField('last checkpoint', max_length=100, null=True, blank=True)

    # Error tracking
    error_message = models.TextField('error message', blank=True)
    error_traceback = models.TextField('error traceback', blank=True)

    # Timestamps
    created_at = models.DateTimeField('created at', auto_now_add=True)
    started_at = models.DateTimeField('started at', null=True, blank=True)
    completed_at = models.DateTimeField('completed at', null=True, blank=True)

    class Meta:
        db_table = 'processing_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['upload']),
            models.Index(fields=['celery_task_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Job {self.id} - {self.company.name} ({self.status})"

    @property
    def is_complete(self):
        """Check if job is in terminal state"""
        return self.status in ['completed', 'failed', 'cancelled']

    def add_completed_model(self, model_name):
        """Add a model to completed list"""
        if model_name not in self.models_completed:
            self.models_completed.append(model_name)
            self.progress = int((len(self.models_completed) / len(self.models_to_execute)) * 100)
            self.save(update_fields=['models_completed', 'progress'])


class ModelResult(models.Model):
    """
    Stores results from individual model executions (daily, weekly, monthly, etc.)
    Each model produces filters + attributes datasets
    """
    RESULT_TYPE_CHOICES = [
        ('filters', 'Filters'),
        ('attrs', 'Attributes'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='model_results')
    job = models.ForeignKey(ProcessingJob, on_delete=models.CASCADE, related_name='model_results')

    # Model identification
    model_name = models.CharField(
        'model name',
        max_length=50,
        help_text='Model name: transactions, daily, weekly, monthly, product_daily, etc.'
    )
    result_type = models.CharField(
        'result type',
        max_length=10,
        choices=RESULT_TYPE_CHOICES,
        help_text='filters or attrs'
    )

    # Data dimensions
    row_count = models.IntegerField('row count')
    column_count = models.IntegerField('column count')
    columns = models.JSONField('columns', help_text='List of column names')

    # Data storage
    data_path = models.CharField(
        'data path',
        max_length=500,
        null=True,
        blank=True,
        help_text='Path to parquet/CSV file if stored separately'
    )
    data_preview = models.JSONField(
        'data preview',
        null=True,
        blank=True,
        help_text='First 10 rows for quick viewing'
    )

    # Performance metrics
    execution_time_ms = models.IntegerField('execution time (ms)', null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField('created at', auto_now_add=True)

    class Meta:
        db_table = 'model_results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'job']),
            models.Index(fields=['job', 'model_name']),
            models.Index(fields=['company', 'model_name', 'result_type']),
            models.Index(fields=['created_at']),
        ]
        unique_together = [('job', 'model_name', 'result_type')]

    def __str__(self):
        return f"{self.model_name}_{self.result_type} - Job {self.job.id}"


class DataExport(models.Model):
    """
    Tracks Excel exports generated from processing jobs
    """
    FORMAT_CHOICES = [
        ('excel', 'Excel (XLSX)'),
        ('csv', 'CSV'),
        ('pdf', 'PDF Report'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='data_exports')
    job = models.ForeignKey(ProcessingJob, on_delete=models.CASCADE, related_name='exports')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='exports')

    # Export configuration
    export_format = models.CharField(
        'export format',
        max_length=20,
        choices=FORMAT_CHOICES,
        default='excel'
    )
    models_included = models.JSONField(
        'models included',
        default=list,
        help_text='List of model names included in export'
    )

    # File information
    file_path = models.CharField('file path', max_length=500, null=True, blank=True)
    file_size_bytes = models.BigIntegerField('file size (bytes)', null=True, blank=True)
    download_url = models.CharField('download URL', max_length=500, null=True, blank=True)

    # Status tracking
    status = models.CharField('status', max_length=20, choices=STATUS_CHOICES, default='pending')
    celery_task_id = models.CharField('celery task ID', max_length=255, null=True, blank=True)
    error_message = models.TextField('error message', blank=True)

    # Timestamps
    created_at = models.DateTimeField('created at', auto_now_add=True)
    completed_at = models.DateTimeField('completed at', null=True, blank=True)
    expires_at = models.DateTimeField(
        'expires at',
        null=True,
        blank=True,
        help_text='Download link expiration time'
    )

    class Meta:
        db_table = 'data_exports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['job']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Export {self.export_format} - Job {self.job.id} ({self.status})"

    @property
    def is_expired(self):
        """Check if download link has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
