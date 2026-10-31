import dramatiq
from apps.projects.services.csv_job_service import CSVImportJobService


@dramatiq.actor
def process_csv_import_task(job_id: str):
    """
    Dramatiq background worker actor that delegates CSV import processing
    to CSVImportJobService.
    """
    CSVImportJobService.process_job(job_id)

