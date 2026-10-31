from django.core.management.base import BaseCommand
from django.db import transaction
from apps.organisations.models import Organisation, ConsultantOrganisationAccess
from apps.users.models import User, UserRole


class Command(BaseCommand):
    help = 'Seeds initial organisations, consultant, and client viewers in an idempotent manner.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting repeatable seed process...'))

        # 1. Create Organisations
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

        # 2. Seed Consultant (assigned to both organisations)
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

        # 3. Seed Client Viewer 1 (Acme Corp)
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

        # 4. Seed Client Viewer 2 (Globex Corporation)
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

        self.stdout.write(self.style.SUCCESS('Seed completed successfully!'))

