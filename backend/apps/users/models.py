from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.users.managers import CustomUserManager


class UserRole(models.TextChoices):
    CONSULTANT = 'consultant', 'Consultant'
    CLIENT_VIEWER = 'client_viewer', 'Client Viewer'


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=UserRole.choices)
    # A client viewer belongs to one organisation.
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='client_viewers'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'role']

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_consultant(self) -> bool:
        return self.role == UserRole.CONSULTANT

    @property
    def is_client_viewer(self) -> bool:
        return self.role == UserRole.CLIENT_VIEWER

    def clean(self):
        super().clean()
        if self.role == UserRole.CLIENT_VIEWER and not self.organisation_id:
            raise ValidationError(
                {'organisation': 'Client viewers must belong to an organisation.'}
            )
        if self.role == UserRole.CONSULTANT and self.organisation_id:
            raise ValidationError(
                {'organisation': 'Consultants should not have a direct organisation assigned; use ConsultantOrganisationAccess.'}
            )

