from django.db import models
import uuid


class ServiceType(models.TextChoices):
    RECAST_WORKSPACE = "recast_workspace", "Recast Application Workspace"
    WINDOWS_365 = "windows_365", "Windows 365 Cloud PC"
    INTUNE = "intune", "Microsoft Intune"


class ServiceInstance(models.Model):
    """A service enabled for a specific environment."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PROVISIONING = "provisioning", "Provisioning"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    environment = models.ForeignKey(
        "environments.Environment",
        on_delete=models.CASCADE,
        related_name="services",
    )
    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROVISIONING)
    enabled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["environment", "service_type"]]
        ordering = ["service_type"]

    def __str__(self):
        return f"{self.environment} — {self.get_service_type_display()}"


# ── Recast Application Workspace ──────────────────────────────────────────────

class RecastWorkspaceConfig(models.Model):
    service = models.OneToOneField(
        ServiceInstance,
        on_delete=models.CASCADE,
        related_name="recast_config",
    )
    workspace_url = models.URLField()
    api_key = models.CharField(max_length=255)
    workspace_id = models.CharField(max_length=100, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Recast config for {self.service}"


# ── Windows 365 ───────────────────────────────────────────────────────────────

class Windows365Config(models.Model):
    service = models.OneToOneField(
        ServiceInstance,
        on_delete=models.CASCADE,
        related_name="windows365_config",
    )
    provisioning_policy_id = models.CharField(max_length=100, blank=True)
    user_settings_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Windows 365 config for {self.service}"


class CloudPC(models.Model):
    class Status(models.TextChoices):
        PROVISIONED = "provisioned", "Provisioned"
        PROVISIONING = "provisioning", "Provisioning"
        DEPROVISIONING = "deprovisioning", "Deprovisioning"
        FAILED = "failed", "Failed"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(Windows365Config, on_delete=models.CASCADE, related_name="cloud_pcs")
    graph_id = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=255)
    user_principal_name = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNKNOWN)
    last_synced = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.display_name


# ── Microsoft Intune ──────────────────────────────────────────────────────────

class IntuneConfig(models.Model):
    service = models.OneToOneField(
        ServiceInstance,
        on_delete=models.CASCADE,
        related_name="intune_config",
    )
    last_sync = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Intune config for {self.service}"


class IntunePolicy(models.Model):
    class PolicyType(models.TextChoices):
        DEVICE_CONFIGURATION = "device_configuration", "Device Configuration"
        COMPLIANCE = "compliance", "Compliance"
        APP_PROTECTION = "app_protection", "App Protection"
        ENROLLMENT = "enrollment", "Enrollment"
        SECURITY_BASELINE = "security_baseline", "Security Baseline"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(IntuneConfig, on_delete=models.CASCADE, related_name="policies")
    graph_id = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=255)
    policy_type = models.CharField(max_length=30, choices=PolicyType.choices)
    json_payload = models.JSONField(default=dict)
    is_deployed = models.BooleanField(default=False)
    last_deployed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Intune policies"
        ordering = ["name"]

    def __str__(self):
        return self.name
