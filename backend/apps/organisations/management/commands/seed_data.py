from django.core.management.base import BaseCommand
from django.db import transaction
from apps.organisations.models import Organisation, ConsultantOrganisationAccess
from apps.projects.models import Project, Risk, RiskSeverity, RiskStatus
from apps.projects.services.scoring_service import RiskScoringService
from apps.users.models import User, UserRole


class Command(BaseCommand):
    help = 'Seeds initial organisations, scoring weights, users, and sample projects/risks idempotently.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting repeatable seed process...'))

        # 1. Seed Scoring Weights
        RiskScoringService.seed_default_weights()
        self.stdout.write("Seeded risk scoring weights (Severity: low=1, med=2, high=3, crit=4 | Status: open=3, mit=2, closed=0)")

        # 2. Create Organisations
        acme, _ = Organisation.objects.update_or_create(
            slug='acme-corp',
            defaults={'name': 'Acme Corp'}
        )
        globex, _ = Organisation.objects.update_or_create(
            slug='globex-corp',
            defaults={'name': 'Globex Corporation'}
        )
        self.stdout.write(f"Seeded organisations: {acme.name}, {globex.name}")

        default_password = 'Password123!'

        # 3. Seed Consultant (assigned to both organisations)
        consultant_email = 'consultant@engagementpulse.com'
        consultant, created = User.objects.get_or_create(
            email=consultant_email,
            defaults={
                'name': 'Alice Consultant',
                'role': UserRole.CONSULTANT,
                'is_staff': True,
            }
        )
        consultant.name = 'Alice Consultant'
        consultant.role = UserRole.CONSULTANT
        consultant.organisation = None
        consultant.set_password(default_password)
        consultant.save()

        # Assign consultant to both organisations
        ConsultantOrganisationAccess.objects.get_or_create(
            user=consultant,
            organisation=acme
        )
        ConsultantOrganisationAccess.objects.get_or_create(
            user=consultant,
            organisation=globex
        )
        self.stdout.write(f"Seeded consultant: {consultant.email} (assigned to {acme.name} & {globex.name})")

        # 4. Seed Client Viewer 1 (Acme Corp)
        viewer_acme_email = 'viewer.acme@example.com'
        viewer_acme, _ = User.objects.get_or_create(
            email=viewer_acme_email,
            defaults={
                'name': 'Bob Acme Viewer',
                'role': UserRole.CLIENT_VIEWER,
                'organisation': acme,
            }
        )
        viewer_acme.name = 'Bob Acme Viewer'
        viewer_acme.role = UserRole.CLIENT_VIEWER
        viewer_acme.organisation = acme
        viewer_acme.set_password(default_password)
        viewer_acme.save()
        self.stdout.write(f"Seeded client viewer: {viewer_acme.email} (assigned to {acme.name})")

        # 5. Seed Client Viewer 2 (Globex Corporation)
        viewer_globex_email = 'viewer.globex@example.com'
        viewer_globex, _ = User.objects.get_or_create(
            email=viewer_globex_email,
            defaults={
                'name': 'Carol Globex Viewer',
                'role': UserRole.CLIENT_VIEWER,
                'organisation': globex,
            }
        )
        viewer_globex.name = 'Carol Globex Viewer'
        viewer_globex.role = UserRole.CLIENT_VIEWER
        viewer_globex.organisation = globex
        viewer_globex.set_password(default_password)
        viewer_globex.save()
        self.stdout.write(f"Seeded client viewer: {viewer_globex.email} (assigned to {globex.name})")

        # 6. Seed Sample Project & Risks for Acme Corp
        acme_project, _ = Project.objects.update_or_create(
            organisation=acme,
            name='ERP Modernisation',
            defaults={'risk_score': 0}
        )
        Risk.objects.update_or_create(
            project=acme_project,
            title='Legacy Database Migration Delay',
            defaults={
                'description': 'Schema changes may delay production rollout.',
                'severity': RiskSeverity.HIGH,
                'status': RiskStatus.OPEN,
                'owner': 'Data Engineering Lead'
            }
        )
        Risk.objects.update_or_create(
            project=acme_project,
            title='Third-party API Rate Limiting',
            defaults={
                'description': 'Integration partner experiencing throughput throttles.',
                'severity': RiskSeverity.MEDIUM,
                'status': RiskStatus.MITIGATING,
                'owner': 'Integration Team'
            }
        )
        acme_score = RiskScoringService.recalculate_project_score(acme_project.id)
        self.stdout.write(f"Seeded project '{acme_project.name}' with risk score: {acme_score}")

        # 7. Seed Sample Project & Risks for Globex Corporation
        globex_project, _ = Project.objects.update_or_create(
            organisation=globex,
            name='Cloud Infrastructure Migration',
            defaults={'risk_score': 0}
        )
        Risk.objects.update_or_create(
            project=globex_project,
            title='Security Audit Compliance Gap',
            defaults={
                'description': 'IAM roles require segregation of duties verification.',
                'severity': RiskSeverity.CRITICAL,
                'status': RiskStatus.OPEN,
                'owner': 'Security Architect'
            }
        )
        globex_score = RiskScoringService.recalculate_project_score(globex_project.id)
        self.stdout.write(f"Seeded project '{globex_project.name}' with risk score: {globex_score}")

        self.stdout.write(self.style.SUCCESS('Seed completed successfully!'))

