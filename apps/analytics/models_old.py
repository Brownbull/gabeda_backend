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
    visible_to_roles = models.JSONField('visible to roles', default=list, blank=True)
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
