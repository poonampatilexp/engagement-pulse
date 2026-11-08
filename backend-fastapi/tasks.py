import logging
import uuid
import dramatiq
from dramatiq.brokers.redis import RedisBroker

from config import settings

logger = logging.getLogger(__name__)

FASTAPI_QUEUE_NAME = settings.DRAMATIQ_QUEUE_NAME

# Configure Dramatiq RedisBroker using settings.REDIS_URL
redis_broker = RedisBroker(url=settings.REDIS_URL)
dramatiq.set_broker(redis_broker)


@dramatiq.actor(queue_name=FASTAPI_QUEUE_NAME, max_retries=3)
def process_csv_import_task(job_id: str):
    """Dramatiq background worker actor that delegates CSV import processing

    to CSVImportJobService.
    """
    logger.info("Processing CSV import task for job: %s", job_id)
    from csv_service import CSVImportJobService

    job = CSVImportJobService.process_job(job_id)
    if job:
        logger.info(
            "Job %s finished with status '%s' (processed %d/%d rows)",
            job_id,
            job.status,
            job.processed_rows,
            job.total_rows,
        )
    return job

