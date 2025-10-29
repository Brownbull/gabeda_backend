"""
Celery tasks for analytics processing.
Handles asynchronous CSV processing and dataset generation.
"""
from celery import shared_task
from django.utils import timezone
from .models import DataUpload
from .services import DatasetGenerationService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_csv_upload(self, upload_id):
    """
    Celery task to process uploaded CSV file asynchronously.

    This task:
    1. Updates status to 'processing'
    2. Calls DatasetGenerationService to run /src analytics pipeline
    3. Updates status to 'completed' or 'failed' based on result
    4. Stores processing metadata (transactions created, results created, etc.)

    Args:
        self: Celery task instance (bind=True)
        upload_id (str): UUID of the DataUpload record

    Returns:
        dict: Processing result with success status and metadata

    Raises:
        Retries up to 3 times with exponential backoff on failure
    """
    logger.info(f"Starting CSV processing for upload {upload_id}")

    try:
        # Get upload record
        data_upload = DataUpload.objects.get(id=upload_id)
        logger.info(f"Found upload record: {data_upload.file_name}")

        # Update status to processing
        data_upload.status = 'processing'
        data_upload.save(update_fields=['status', 'updated_at'])
        logger.info(f"Updated status to 'processing' for upload {upload_id}")

        # Process the CSV using DatasetGenerationService
        service = DatasetGenerationService(data_upload)
        result = service.process()

        # Update status based on result
        if result['success']:
            data_upload.status = 'completed'
            data_upload.processing_completed_at = timezone.now()
            data_upload.processing_metadata = {
                'transactions_created': result.get('transactions_created', 0),
                'datasets_created': result.get('datasets_created', 0),
                'results_created': result.get('results_created', 0),
                'processing_time_seconds': result.get('processing_time_seconds'),
                'completed_at': timezone.now().isoformat(),
            }
            logger.info(
                f"CSV processing completed successfully for upload {upload_id}: "
                f"{result.get('transactions_created', 0)} transactions, "
                f"{result.get('results_created', 0)} results"
            )
        else:
            data_upload.status = 'failed'
            data_upload.error_message = result.get('error', 'Unknown error occurred')
            data_upload.processing_metadata = {
                'error': result.get('error'),
                'failed_at': timezone.now().isoformat(),
            }
            logger.error(f"CSV processing failed for upload {upload_id}: {data_upload.error_message}")

        data_upload.save(update_fields=['status', 'processing_completed_at', 'processing_metadata', 'error_message', 'updated_at'])

        return result

    except DataUpload.DoesNotExist:
        error_msg = f"DataUpload {upload_id} not found"
        logger.error(error_msg)
        raise Exception(error_msg)

    except Exception as exc:
        logger.error(f"Error processing CSV upload {upload_id}: {exc}", exc_info=True)

        # Update upload record with error
        try:
            data_upload = DataUpload.objects.get(id=upload_id)
            data_upload.status = 'failed'
            data_upload.error_message = f"Processing error: {str(exc)}"
            data_upload.processing_metadata = {
                'error': str(exc),
                'failed_at': timezone.now().isoformat(),
                'retry_count': self.request.retries,
            }
            data_upload.save(update_fields=['status', 'error_message', 'processing_metadata', 'updated_at'])
        except Exception as save_exc:
            logger.error(f"Failed to update error status for upload {upload_id}: {save_exc}")

        # Retry task (up to 3 times with exponential backoff: 4s, 16s, 64s)
        raise self.retry(exc=exc, countdown=2 ** (self.request.retries * 2))
