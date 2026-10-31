from typing import Dict, Tuple
from django.db import transaction
from apps.projects.models import (
    Project,
    Risk,
    SeverityWeight,
    StatusWeight,
    RiskSeverity,
    RiskStatus,
)

DEFAULT_SEVERITY_WEIGHTS: Dict[str, int] = {
    RiskSeverity.LOW: 1,
    RiskSeverity.MEDIUM: 2,
    RiskSeverity.HIGH: 3,
    RiskSeverity.CRITICAL: 4,
}

DEFAULT_STATUS_WEIGHTS: Dict[str, int] = {
    RiskStatus.OPEN: 3,
    RiskStatus.MITIGATING: 2,
    RiskStatus.CLOSED: 0,
}


class RiskScoringService:
    @staticmethod
    def seed_default_weights():
        """
        Idempotently seeds default severity and status weights in PostgreSQL.
        """
        for severity, weight in DEFAULT_SEVERITY_WEIGHTS.items():
            SeverityWeight.objects.update_or_create(
                severity=severity,
                defaults={'weight': weight}
            )
        for status, weight in DEFAULT_STATUS_WEIGHTS.items():
            StatusWeight.objects.update_or_create(
                status=status,
                defaults={'weight': weight}
            )

    @classmethod
    def get_weights(cls) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Retrieves current weights from database, falling back to defaults if unseeded.
        """
        sev_qs = SeverityWeight.objects.all()
        stat_qs = StatusWeight.objects.all()

        sev_map = {item.severity: item.weight for item in sev_qs} if sev_qs.exists() else DEFAULT_SEVERITY_WEIGHTS
        stat_map = {item.status: item.weight for item in stat_qs} if stat_qs.exists() else DEFAULT_STATUS_WEIGHTS

        return sev_map, stat_map

    @classmethod
    def calculate_risk_contribution(
        cls,
        severity: str,
        status: str,
        sev_weights: Dict[str, int] = None,
        stat_weights: Dict[str, int] = None
    ) -> int:
        """
        Calculates individual risk contribution = SeverityWeight × StatusWeight.
        """
        if sev_weights is None or stat_weights is None:
            sev_weights, stat_weights = cls.get_weights()

        w_sev = sev_weights.get(severity, DEFAULT_SEVERITY_WEIGHTS.get(severity, 0))
        w_stat = stat_weights.get(status, DEFAULT_STATUS_WEIGHTS.get(status, 0))
        return w_sev * w_stat

    @classmethod
    def recalculate_project_score(cls, project_id: int, project: Project = None) -> int:
        """
        Recalculates and persists a project's risk_score inside a database transaction
        with row-level locking (select_for_update) to guarantee concurrency safety.
        Formula: min(100, sum of all risk contributions)
        A project without risks has a score of 0.
        """
        with transaction.atomic():
            if project is None:
                project = Project.objects.select_for_update().get(id=project_id)

            sev_weights, stat_weights = cls.get_weights()

            risks = Risk.objects.filter(project_id=project_id).values('severity', 'status')
            raw_score = sum(
                cls.calculate_risk_contribution(
                    r['severity'],
                    r['status'],
                    sev_weights,
                    stat_weights
                )
                for r in risks
            )

            # Bounded between 0 and 100
            bounded_score = min(100, max(0, raw_score))
            project.risk_score = bounded_score
            project.save(update_fields=['risk_score', 'updated_at'])
            return bounded_score

