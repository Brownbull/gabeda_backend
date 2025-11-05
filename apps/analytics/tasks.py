"""
Celery tasks for analytics processing.
Handles asynchronous CSV processing and dataset generation.
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from .models import DataUpload, ProcessingJob, ModelResult, DataExport
from .services import DatasetGenerationService, PipelineExecutionService, ExportGenerationService
import logging
import traceback

logger = logging.getLogger(__name__)


def validate_csv_columns(data_upload):
    """
    Validate uploaded CSV columns against CompanyConfig schema.
    
    Args:
        data_upload: DataUpload instance with file
        
    Returns:
        tuple: (is_valid, error_message)
            - (True, None) if validation passes
            - (False, "error message") if validation fails
    """
    from .models import CompanyConfig
    import pandas as pd
    
    try:
        # Check if company has a configuration
        try:
            config = CompanyConfig.objects.get(company=data_upload.company)
        except CompanyConfig.DoesNotExist:
            # No config found - skip validation (will use default mapping or require manual mapping)
            logger.info(f"No CompanyConfig found for company {data_upload.company.name} - skipping validation")
            return (True, None)
        
        logger.info(f"Found CompanyConfig for company {data_upload.company.name}")
        
        # Read CSV to get columns
        try:
            df = pd.read_csv(data_upload.file.path, nrows=1)  # Just read first row to get columns
            csv_columns = set(df.columns)
        except Exception as e:
            return (False, f"Failed to read CSV file: {str(e)}")
        
        # Get expected columns from config
        expected_columns = set()
        missing_columns = []
        
        for field_name, field_config in config.data_schema.items():
            source_column = field_config.get('source_column')
            if source_column:
                expected_columns.add(source_column)
                
                # Check if column exists in CSV
                if source_column not in csv_columns:
                    missing_columns.append(source_column)
        
        # Check validation result
        if missing_columns:
            error_msg = (
                f"CSV file is missing required columns: {', '.join(sorted(missing_columns))}. "
                f"Expected columns: {', '.join(sorted(expected_columns))}. "
                f"Found columns: {', '.join(sorted(csv_columns))}"
            )
            return (False, error_msg)
        
        logger.info(f"CSV columns validation passed for upload {data_upload.id}")
        return (True, None)
        
    except Exception as e:
        logger.error(f"Error during column validation: {str(e)}")
        return (False, f"Validation error: {str(e)}")



@shared_task(bind=True, max_retries=3)
def process_csv_upload(self, upload_id):
    """
    Celery task to process uploaded CSV file asynchronously.

    This task:
    1. Creates ProcessingJob record for tracking
    2. Updates status to 'processing'
    3. Calls DatasetGenerationService to run /src analytics pipeline
    4. Updates status to 'completed' or 'failed' based on result
    5. Stores processing metadata (transactions created, results created, etc.)
    6. Updates ProcessingJob with final status

    Args:
        self: Celery task instance (bind=True)
        upload_id (str): UUID of the DataUpload record

    Returns:
        dict: Processing result with success status and metadata

    Raises:
        Retries up to 3 times with exponential backoff on failure
    """
    logger.info(f"Starting CSV processing for upload {upload_id}")
    processing_job = None
    start_time = timezone.now()

    try:
        # Get upload record
        data_upload = DataUpload.objects.select_related('company').get(id=upload_id)
        logger.info(f"Found upload record: {data_upload.file_name}")


        # Validate CSV columns against CompanyConfig
        is_valid, validation_error = validate_csv_columns(data_upload)
        if not is_valid:
            logger.error(f"CSV validation failed for upload {upload_id}: {validation_error}")
            data_upload.status = 'failed'
            data_upload.error_message = validation_error
            data_upload.save(update_fields=['status', 'error_message', 'updated_at'])
            
            # Create failed ProcessingJob for tracking
            processing_job = ProcessingJob.objects.create(
                company=data_upload.company,
                upload=data_upload,
                celery_task_id=self.request.id,
                models_to_execute=['csv_processing'],
                status='failed',
                error_message=validation_error,
                started_at=start_time,
                completed_at=timezone.now()
            )
            
            return {
                'success': False,
                'error': validation_error,
                'upload_id': str(upload_id)
            }
        logger.info(f"CSV validation passed for upload {upload_id}")

        # Create ProcessingJob for tracking (visible in /jobs page)
        processing_job = ProcessingJob.objects.create(
            company=data_upload.company,
            upload=data_upload,
            celery_task_id=self.request.id,
            models_to_execute=['csv_processing'],
            status='running',
            current_model='csv_processing'
        )
        processing_job.started_at = start_time
        processing_job.save(update_fields=['started_at'])
        logger.info(f"Created ProcessingJob {processing_job.id} for upload {upload_id}")

        # Update status to processing
        data_upload.status = 'processing'
        data_upload.processing_started_at = start_time
        data_upload.save(update_fields=['status', 'processing_started_at', 'updated_at'])
        logger.info(f"Updated status to 'processing' for upload {upload_id}")

        # Process the CSV using DatasetGenerationService
        service = DatasetGenerationService(data_upload)
        result = service.process()

        # Update status based on result
        if result['success']:
            completed_at = timezone.now()
            processing_time = (completed_at - start_time).total_seconds()
            
            data_upload.status = 'completed'
            data_upload.processing_completed_at = completed_at
            data_upload.processing_metadata = {
                'transactions_created': result.get('transactions_created', 0),
                'datasets_created': result.get('datasets_created', 0),
                'results_created': result.get('results_created', 0),
                'processing_time_seconds': processing_time,
                'completed_at': completed_at.isoformat(),
            }
            
            # Update ProcessingJob to completed
            if processing_job:
                processing_job.status = 'completed'
                processing_job.completed_at = completed_at
                processing_job.progress = 100
                processing_job.processing_time_seconds = processing_time
                processing_job.models_completed = ['csv_processing']
                processing_job.current_model = None
                processing_job.save(update_fields=[
                    'status', 'completed_at', 'progress', 'processing_time_seconds',
                    'models_completed', 'current_model'
                ])
            
            logger.info(
                f"CSV processing completed successfully for upload {upload_id}: "
                f"{result.get('transactions_created', 0)} transactions, "
                f"{result.get('results_created', 0)} results"
            )
        else:
            failed_at = timezone.now()
            error_msg = result.get('error', 'Unknown error occurred')
            
            data_upload.status = 'failed'
            data_upload.error_message = error_msg
            data_upload.processing_metadata = {
                'error': error_msg,
                'failed_at': failed_at.isoformat(),
            }
            
            # Update ProcessingJob to failed
            if processing_job:
                processing_job.status = 'failed'
                processing_job.completed_at = failed_at
                processing_job.error_message = error_msg
                processing_job.current_model = None
                processing_job.save(update_fields=[
                    'status', 'completed_at', 'error_message', 'current_model'
                ])
            
            logger.error(f"CSV processing failed for upload {upload_id}: {error_msg}")

        data_upload.save(update_fields=['status', 'processing_completed_at', 'processing_metadata', 'error_message', 'updated_at'])

        return result

    except DataUpload.DoesNotExist:
        error_msg = f"DataUpload {upload_id} not found"
        logger.error(error_msg)
        raise Exception(error_msg)

    except Exception as exc:
        logger.error(f"Error processing CSV upload {upload_id}: {exc}", exc_info=True)

        # Update upload record and ProcessingJob with error
        try:
            data_upload = DataUpload.objects.get(id=upload_id)
            failed_at = timezone.now()
            error_msg = f"Processing error: {str(exc)}"
            
            data_upload.status = 'failed'
            data_upload.error_message = error_msg
            data_upload.processing_metadata = {
                'error': str(exc),
                'failed_at': failed_at.isoformat(),
                'retry_count': self.request.retries,
            }
            data_upload.save(update_fields=['status', 'error_message', 'processing_metadata', 'updated_at'])
            
            # Update ProcessingJob if it was created
            if processing_job:
                processing_job.status = 'failed'
                processing_job.completed_at = failed_at
                processing_job.error_message = error_msg
                processing_job.error_traceback = traceback.format_exc()
                processing_job.save(update_fields=[
                    'status', 'completed_at', 'error_message', 'error_traceback'
                ])
        except Exception as save_exc:
            logger.error(f"Failed to update error status for upload {upload_id}: {save_exc}")

        # Retry task (up to 3 times with exponential backoff: 4s, 16s, 64s)
        raise self.retry(exc=exc, countdown=2 ** (self.request.retries * 2))


@shared_task(bind=True, max_retries=1)
def process_pipeline(self, job_id):
    """
    Celery task to execute the 9-model analytics pipeline.

    This task:
    1. Updates job status to 'running'
    2. Executes each model in sequence (transactions, daily, weekly, etc.)
    3. Stores ModelResult records for each model (filters + attrs)
    4. Updates job progress in real-time
    5. Updates job status to 'completed' or 'failed'

    Args:
        self: Celery task instance (bind=True)
        job_id (str): UUID of the ProcessingJob record

    Returns:
        dict: Processing result with success status and metadata

    Raises:
        Retries once on failure
    """
    logger.info(f"Starting pipeline execution for job {job_id}")
    start_time = timezone.now()

    try:
        # Get job record
        job = ProcessingJob.objects.select_related('company', 'upload').get(id=job_id)
        logger.info(f"Found job record: {job.company.name} - {job.upload.file_name}")

        # Update status to running
        job.status = 'running'
        job.started_at = start_time
        job.save(update_fields=['status', 'started_at'])
        logger.info(f"Updated status to 'running' for job {job_id}")

        # Execute pipeline using PipelineExecutionService
        service = PipelineExecutionService(job)
        result = service.execute()

        # Calculate processing time
        end_time = timezone.now()
        processing_time = (end_time - start_time).total_seconds()

        # Update status based on result
        if result['success']:
            job.status = 'completed'
            job.completed_at = end_time
            job.processing_time_seconds = processing_time
            job.current_model = None
            logger.info(
                f"Pipeline execution completed successfully for job {job_id}: "
                f"{len(job.models_completed)} models executed in {processing_time:.2f}s"
            )
        else:
            job.status = 'failed'
            job.error_message = result.get('error', 'Unknown error occurred')
            job.error_traceback = result.get('traceback', '')
            job.completed_at = end_time
            job.processing_time_seconds = processing_time
            logger.error(f"Pipeline execution failed for job {job_id}: {job.error_message}")

        job.save(update_fields=[
            'status', 'completed_at', 'processing_time_seconds',
            'current_model', 'error_message', 'error_traceback'
        ])

        return result

    except ProcessingJob.DoesNotExist:
        error_msg = f"ProcessingJob {job_id} not found"
        logger.error(error_msg)
        raise Exception(error_msg)

    except Exception as exc:
        logger.error(f"Error executing pipeline for job {job_id}: {exc}", exc_info=True)
        error_traceback = traceback.format_exc()

        # Update job record with error
        try:
            job = ProcessingJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = f"Pipeline execution error: {str(exc)}"
            job.error_traceback = error_traceback
            job.completed_at = timezone.now()

            # Calculate processing time if started
            if job.started_at:
                processing_time = (job.completed_at - job.started_at).total_seconds()
                job.processing_time_seconds = processing_time

            job.save(update_fields=[
                'status', 'error_message', 'error_traceback',
                'completed_at', 'processing_time_seconds'
            ])
        except Exception as save_exc:
            logger.error(f"Failed to update error status for job {job_id}: {save_exc}")

        # Retry task once (pipeline failures are usually non-recoverable)
        if self.request.retries < 1:
            raise self.retry(exc=exc, countdown=60)  # Wait 1 minute before retry
        else:
            raise exc


@shared_task(bind=True, max_retries=2)
def generate_export(self, export_id):
    """
    Celery task to generate Excel/CSV export from processing job results.

    This task:
    1. Updates export status to 'generating'
    2. Fetches ModelResult records for the specified models
    3. Generates Excel/CSV file using ExportGenerationService
    4. Stores file path and download URL
    5. Sets expiration time (7 days from now)
    6. Updates export status to 'completed' or 'failed'

    Args:
        self: Celery task instance (bind=True)
        export_id (str): UUID of the DataExport record

    Returns:
        dict: Export result with success status and file info

    Raises:
        Retries up to 2 times on failure
    """
    logger.info(f"Starting export generation for export {export_id}")

    try:
        # Get export record
        export = DataExport.objects.select_related('company', 'job', 'requested_by').get(id=export_id)
        logger.info(f"Found export record: {export.export_format} for job {export.job.id}")

        # Update status to generating
        export.status = 'generating'
        export.save(update_fields=['status'])
        logger.info(f"Updated status to 'generating' for export {export_id}")

        # Generate export using ExportGenerationService
        service = ExportGenerationService(export)
        result = service.generate()

        # Update status based on result
        if result['success']:
            export.status = 'completed'
            export.file_path = result.get('file_path')
            export.file_size_bytes = result.get('file_size_bytes')
            export.download_url = result.get('download_url')
            export.completed_at = timezone.now()

            # Set expiration (7 days from now)
            from datetime import timedelta
            export.expires_at = timezone.now() + timedelta(days=7)

            logger.info(
                f"Export generation completed successfully for export {export_id}: "
                f"{export.file_size_bytes / 1024:.2f} KB"
            )
        else:
            export.status = 'failed'
            export.error_message = result.get('error', 'Unknown error occurred')
            logger.error(f"Export generation failed for export {export_id}: {export.error_message}")

        export.save(update_fields=[
            'status', 'file_path', 'file_size_bytes', 'download_url',
            'completed_at', 'expires_at', 'error_message'
        ])

        return result

    except DataExport.DoesNotExist:
        error_msg = f"DataExport {export_id} not found"
        logger.error(error_msg)
        raise Exception(error_msg)

    except Exception as exc:
        logger.error(f"Error generating export {export_id}: {exc}", exc_info=True)

        # Update export record with error
        try:
            export = DataExport.objects.get(id=export_id)
            export.status = 'failed'
            export.error_message = f"Export generation error: {str(exc)}"
            export.save(update_fields=['status', 'error_message'])
        except Exception as save_exc:
            logger.error(f"Failed to update error status for export {export_id}: {save_exc}")

        # Retry task (up to 2 times with exponential backoff: 8s, 32s)
        raise self.retry(exc=exc, countdown=2 ** ((self.request.retries + 1) * 3))
