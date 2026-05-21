from django.db import models
from django.conf import settings


class Environment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('provisioning', 'Provisioning'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='environments',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    azure_tenant_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class EnvironmentMembership(models.Model):
    """
    Links a user to one or more environments with a role.
    A user can be env_admin or env_member in each environment independently.
    """
    ROLE_CHOICES = [
        ('env_admin',  'Environment Admin'),
        ('env_member', 'Environment Member'),
    ]

    environment = models.ForeignKey(
        Environment,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='env_memberships',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='env_member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('environment', 'user')
        ordering = ['environment', 'role']

    def __str__(self):
        return f'{self.user.email} — {self.get_role_display()} in {self.environment.name}'
