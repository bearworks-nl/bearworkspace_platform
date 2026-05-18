from django.db import models
from django.utils import timezone
import uuid
from decimal import Decimal


class Plan(models.Model):
    """Pricing plan for a service type."""

    class Interval(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    class UnitType(models.TextChoices):
        PER_USER = "per_user", "Per User"
        PER_DEVICE = "per_device", "Per Device"
        PER_ENV = "per_env", "Per Environment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=30)  # matches ServiceType choices
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=4)
    currency = models.CharField(max_length=3, default="EUR")
    interval = models.CharField(max_length=10, choices=Interval.choices, default=Interval.MONTHLY)
    unit_type = models.CharField(max_length=20, choices=UnitType.choices)
    included_units = models.PositiveIntegerField(default=0, help_text="Free units before billing kicks in")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["service_type", "name"]

    def __str__(self):
        return f"{self.name} — {self.currency} {self.price_per_unit}/{self.get_unit_type_display()}"


class Subscription(models.Model):
    """Per-service subscription for an environment."""

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.OneToOneField(
        "services.ServiceInstance",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)

    # Mollie references
    mollie_subscription_id = models.CharField(max_length=50, blank=True)
    mollie_mandate_id = models.CharField(max_length=50, blank=True)

    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.service} — {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        return self.status in (self.Status.ACTIVE, self.Status.TRIALING)

    def calculate_amount(self, unit_count):
        """Calculate charge amount for a given unit count."""
        billable = max(0, unit_count - self.plan.included_units)
        return Decimal(billable) * self.plan.price_per_unit


class UsageSnapshot(models.Model):
    """Monthly usage record captured by Celery beat."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="usage_snapshots",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    unit_count = models.PositiveIntegerField()
    unit_type = models.CharField(max_length=20)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_start"]
        unique_together = [["subscription", "period_start"]]

    def __str__(self):
        return f"{self.subscription} — {self.period_start}: {self.unit_count} {self.unit_type}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        VOID = "void", "Void"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=30, unique=True)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    usage_snapshot = models.OneToOneField(
        UsageSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    period_start = models.DateField()
    period_end = models.DateField()
    issued_at = models.DateTimeField()
    due_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    mollie_payment_id = models.CharField(max_length=50, blank=True)
    pdf = models.FileField(upload_to="invoices/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice_number} — {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from django.utils import timezone
            ts = timezone.now()
            count = Invoice.objects.filter(created_at__year=ts.year, created_at__month=ts.month).count() + 1
            self.invoice_number = f"INV-{ts.year}{ts.month:02d}-{count:04d}"
        super().save(*args, **kwargs)
