from django.db import models
from django.utils import timezone
import uuid
from decimal import Decimal


class Plan(models.Model):
    """Pricing plan for a product type."""

    class Interval(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    class UnitType(models.TextChoices):
        PER_USER = "per_user", "Per User"
        PER_DEVICE = "per_device", "Per Device"
        PER_ORG = "per_org", "Per Organisation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=30)  # matches ProductType choices
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=4)
    currency = models.CharField(max_length=3, default="EUR")
    interval = models.CharField(max_length=10, choices=Interval.choices, default=Interval.MONTHLY)
    unit_type = models.CharField(max_length=20, choices=UnitType.choices)
    included_units = models.PositiveIntegerField(default=0, help_text="Free units before billing kicks in")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["product_type", "name"]

    def __str__(self):
        return f"{self.name} — {self.currency} {self.price_per_unit}/{self.get_unit_type_display()}"


class Subscription(models.Model):
    """Per-product subscription for an organisation."""

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        "products.ProductInstance",
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
        return f"{self.product} — {self.plan.name} ({self.status})"

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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("21.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    period_start = models.DateField()
    period_end = models.DateField()

    # Mollie payment references
    mollie_payment_id = models.CharField(max_length=50, blank=True)
    mollie_payment_url = models.URLField(blank=True)

    pdf = models.FileField(upload_to="invoices/", blank=True, null=True)
    notes = models.TextField(blank=True)

    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice_number} — {self.subscription.product.organisation}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_number()
        self.tax_amount = (self.amount * self.tax_rate / 100).quantize(Decimal("0.01"))
        self.total_amount = (self.amount + self.tax_amount).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        from django.utils import timezone
        year = timezone.now().year
        last = Invoice.objects.filter(invoice_number__startswith=f"INV-{year}-").count()
        return f"INV-{year}-{last + 1:05d}"
