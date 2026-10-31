import pytest
from apps.projects.models import Project, Risk, RiskSeverity, RiskStatus, SeverityWeight, StatusWeight
from apps.projects.services.scoring_service import RiskScoringService


@pytest.mark.django_db
class TestRiskScoringService:

    def test_seed_default_weights_is_idempotent(self):
        """Verifies that seed_default_weights runs cleanly multiple times."""
        RiskScoringService.seed_default_weights()
        RiskScoringService.seed_default_weights()

        assert SeverityWeight.objects.count() == 4
        assert StatusWeight.objects.count() == 3

        sev_map, stat_map = RiskScoringService.get_weights()
        assert sev_map[RiskSeverity.LOW] == 1
        assert sev_map[RiskSeverity.MEDIUM] == 2
        assert sev_map[RiskSeverity.HIGH] == 3
        assert sev_map[RiskSeverity.CRITICAL] == 4

        assert stat_map[RiskStatus.OPEN] == 3
        assert stat_map[RiskStatus.MITIGATING] == 2
        assert stat_map[RiskStatus.CLOSED] == 0

    def test_zero_score_for_project_without_risks(self, seeded_data):
        """A project without risks must have a score of 0."""
        project = seeded_data['project_acme']
        score = RiskScoringService.recalculate_project_score(project.id)
        assert score == 0
        project.refresh_from_db()
        assert project.risk_score == 0

    def test_risk_score_calculation_with_multiple_risks(self, seeded_data):
        """
        Calculates individual contributions:
        - High (3) x Open (3) = 9
        - Medium (2) x Mitigating (2) = 4
        - Critical (4) x Closed (0) = 0
        Total expected = 13.
        """
        project = seeded_data['project_acme']

        Risk.objects.create(
            project=project,
            title='Risk 1',
            severity=RiskSeverity.HIGH,
            status=RiskStatus.OPEN
        )
        Risk.objects.create(
            project=project,
            title='Risk 2',
            severity=RiskSeverity.MEDIUM,
            status=RiskStatus.MITIGATING
        )
        Risk.objects.create(
            project=project,
            title='Risk 3',
            severity=RiskSeverity.CRITICAL,
            status=RiskStatus.CLOSED
        )

        score = RiskScoringService.recalculate_project_score(project.id)
        assert score == 13

        project.refresh_from_db()
        assert project.risk_score == 13

    def test_score_recalculation_on_status_change(self, seeded_data):
        """Tests recalculation when closing and reopening a risk."""
        project = seeded_data['project_acme']

        risk = Risk.objects.create(
            project=project,
            title='Critical Risk',
            severity=RiskSeverity.CRITICAL,
            status=RiskStatus.OPEN
        )
        # Critical (4) x Open (3) = 12
        assert RiskScoringService.recalculate_project_score(project.id) == 12

        # Close risk: Critical (4) x Closed (0) = 0
        risk.status = RiskStatus.CLOSED
        risk.save()
        assert RiskScoringService.recalculate_project_score(project.id) == 0

        # Reopen risk: Critical (4) x Mitigating (2) = 8
        risk.status = RiskStatus.MITIGATING
        risk.save()
        assert RiskScoringService.recalculate_project_score(project.id) == 8

    def test_maximum_score_capped_at_100(self, seeded_data):
        """
        Project risk score must never exceed 100.
        10 Critical Open risks = 10 x (4 x 3) = 120 -> capped at 100.
        """
        project = seeded_data['project_acme']

        for i in range(10):
            Risk.objects.create(
                project=project,
                title=f'Critical Risk {i}',
                severity=RiskSeverity.CRITICAL,
                status=RiskStatus.OPEN
            )

        score = RiskScoringService.recalculate_project_score(project.id)
        assert score == 100

        project.refresh_from_db()
        assert project.risk_score == 100

    def test_recalculation_on_risk_deletion(self, seeded_data):
        """When a risk is deleted, the project score updates accordingly."""
        project = seeded_data['project_acme']

        r1 = Risk.objects.create(
            project=project,
            title='Risk 1',
            severity=RiskSeverity.HIGH,
            status=RiskStatus.OPEN
        ) # 9
        r2 = Risk.objects.create(
            project=project,
            title='Risk 2',
            severity=RiskSeverity.LOW,
            status=RiskStatus.OPEN
        ) # 3
        assert RiskScoringService.recalculate_project_score(project.id) == 12

        r1.delete()
        assert RiskScoringService.recalculate_project_score(project.id) == 3


@pytest.mark.django_db(transaction=True)
class TestPostgreSQLConcurrencyScoring:

    def test_concurrent_risk_creations_maintain_accurate_project_score(self, seeded_data):
        """
        Simulates concurrent risk creations on the same project across multiple threads.
        Each thread acquires the project lock before mutating, recalculating the score.
        Verifies that the final persisted score equals the exact sum of all created risks,
        proving no transaction calculates from an outdated snapshot or overwrites a newer score.
        """
        import concurrent.futures
        from django.db import connection
        from apps.projects.services.risk_service import RiskService

        project = seeded_data['project_acme']
        consultant = seeded_data['consultant']

        num_threads = 5
        # Each thread creates 1 Medium (2) x Open (3) = 6 point risk
        # Total expected score = 5 x 6 = 30

        def worker(idx):
            try:
                RiskService.create_risk(
                    user=consultant,
                    project_id=project.id,
                    title=f'Concurrent Risk {idx}',
                    severity=RiskSeverity.MEDIUM,
                    status=RiskStatus.OPEN
                )
            finally:
                connection.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        project.refresh_from_db()
        assert project.risk_score == 30
        assert project.risks.count() == 5

    def test_concurrent_mixed_mutations_maintain_accurate_project_score(self, seeded_data):
        """
        Simulates concurrent create, update, and delete operations on the same project.
        Verifies that serialized Project row locks prevent stale snapshot overwrites.
        """
        import concurrent.futures
        from django.db import connection
        from apps.projects.services.risk_service import RiskService

        project = seeded_data['project_acme']
        consultant = seeded_data['consultant']

        # Setup initial risks:
        # r1: Low (1) x Open (3) = 3
        # r2: Critical (4) x Open (3) = 12
        r1 = RiskService.create_risk(consultant, project.id, title='R1', severity=RiskSeverity.LOW, status=RiskStatus.OPEN)
        r2 = RiskService.create_risk(consultant, project.id, title='R2', severity=RiskSeverity.CRITICAL, status=RiskStatus.OPEN)

        project.refresh_from_db()
        assert project.risk_score == 15

        # Concurrent operations:
        # Thread A: Update r1 -> Critical (4) x Open (3) = 12
        # Thread B: Delete r2 -> removes 12
        # Thread C: Create r3 -> High (3) x Mitigating (2) = 6
        # Expected final risks: r1 (12) + r3 (6) = 18.
        def op_a():
            try:
                RiskService.update_risk(consultant, r1.id, severity=RiskSeverity.CRITICAL, status=RiskStatus.OPEN)
            finally:
                connection.close()

        def op_b():
            try:
                RiskService.delete_risk(consultant, r2.id)
            finally:
                connection.close()

        def op_c():
            try:
                RiskService.create_risk(consultant, project.id, title='R3', severity=RiskSeverity.HIGH, status=RiskStatus.MITIGATING)
            finally:
                connection.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(op) for op in [op_a, op_b, op_c]]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        project.refresh_from_db()
        assert project.risk_score == 18

