from django.conf import settings
from django.db import models


class Organisation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organisations'
        ordering = ['name']

    def __str__(self):
        return self.name


class ConsultantOrganisationAccess(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consultant_access'
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='consultant_access'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consultant_organisation_access'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'organisation'],
                name='unique_consultant_organisation'
            )
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.organisation.name}"

