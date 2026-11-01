import logging
import dramatiq
from apps.projects.services.csv_job_service import CSVImportJobService

logger = logging.getLogger(__name__)


@dramatiq.actor
def process_csv_import_task(job_id: str):
    """
    Dramatiq background worker actor that delegates CSV import processing
    to CSVImportJobService.
    """
    logger.info("Processing CSV import task for job: %s", job_id)
    job = CSVImportJobService.process_job(job_id)
    if job:
        logger.info("Job %s completed with status '%s' (processed %d/%d rows)", job_id, job.status, job.processed_rows, job.total_rows)
    return job

