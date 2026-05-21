from django.db import models
from apps.environments.models import Environment


SERVICE_TYPE_CHOICES = [
    ('recast_workspace', 'Recast Application Workspace'),
    ('windows_365', 'Windows 365 Cloud PC'),
    ('intune', 'Microsoft Intune'),
]


class Service(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('configuring', 'Configuring'),
        ('error', 'Error'),
    ]

    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='services')
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPE_CHOICES)
    name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Optional display name. Defaults to the service type name if left blank.'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='configuring')
    enabled = models.BooleanField(default=False)

    # Step 2: tracks whether the service has been connected
    is_connected = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['environment', 'service_type', 'name']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.name if self.name else self.get_service_type_display()

    @property
    def icon(self):
        icons = {
            'recast_workspace': '🖥️',
            'windows_365': '☁️',
            'intune': '🛡️',
        }
        return icons.get(self.service_type, '⚙️')


class RecastConfig(models.Model):
    service = models.OneToOneField(Service, on_delete=models.CASCADE, related_name='recast_config')
    api_url = models.URLField()
    api_key = models.CharField(max_length=500)
    workspace_count = models.PositiveIntegerField(default=0)
    last_synced = models.DateTimeField(null=True, blank=True)

    # Step 3: license data read from the Recast API
    license_count = models.PositiveIntegerField(default=0)
    license_numbers = models.JSONField(default=list, blank=True)
    # Step 4: matched order reference (free-text for now; FK to Order when that model exists)
    matched_order_ref = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f'Recast Config for {self.service}'


class Windows365Config(models.Model):
    service = models.OneToOneField(Service, on_delete=models.CASCADE, related_name='w365_config')
    application_id = models.CharField(max_length=200)
    tenant_id = models.CharField(max_length=200)
    client_secret = models.CharField(max_length=500, blank=True)
    device_count = models.PositiveIntegerField(default=0)
    last_synced = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'W365 Config for {self.service}'


class IntuneConfig(models.Model):
    service = models.OneToOneField(Service, on_delete=models.CASCADE, related_name='intune_config')
    application_id = models.CharField(max_length=200)
    tenant_id = models.CharField(max_length=200)
    client_secret = models.CharField(max_length=500, blank=True)
    policy_json = models.JSONField(default=dict, blank=True)
    last_deployed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Intune Config for {self.service}'
