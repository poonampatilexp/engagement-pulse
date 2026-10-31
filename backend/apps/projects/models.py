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

