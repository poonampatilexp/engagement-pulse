import uuid
from django.conf import settings
from django.db import models


class RiskSeverity(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class RiskStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    MITIGATING = 'mitigating', 'Mitigating'
    CLOSED = 'closed', 'Closed'


class SeverityWeight(models.Model):
    severity = models.CharField(
        max_length=20,
        choices=RiskSeverity.choices,
        unique=True
    )
    weight = models.PositiveIntegerField()

    class Meta:
        db_table = 'severity_weights'
        ordering = ['weight']

    def __str__(self):
        return f"{self.severity}: {self.weight}"


class StatusWeight(models.Model):
    status = models.CharField(
        max_length=20,
        choices=RiskStatus.choices,
        unique=True
    )
    weight = models.PositiveIntegerField()

    class Meta:
        db_table = 'status_weights'
        ordering = ['weight']

    def __str__(self):
        return f"{self.status}: {self.weight}"


class Project(models.Model):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='projects'
    )
    name = models.CharField(max_length=255)
    risk_score = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-updated_at', 'name']

    def __str__(self):
        return f"{self.name} ({self.organisation.name})"


class Risk(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='risks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    severity = models.CharField(
        max_length=20,
        choices=RiskSeverity.choices,
        default=RiskSeverity.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=RiskStatus.choices,
        default=RiskStatus.OPEN
    )
    owner = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'risks'
        ordering = ['-updated_at', 'title']

    def __str__(self):
        return f"{self.title} [{self.severity}/{self.status}]"


class JobStatus(models.TextChoices):
    QUEUED = 'queued', 'Queued'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class CSVImportJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='csv_jobs'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='csv_jobs'
    )
    file = models.FileField(upload_to='csv_imports/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.QUEUED,
        db_index=True
    )
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    error_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'csv_import_jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"CSVJob {self.id} [{self.status}] - {self.filename}"



