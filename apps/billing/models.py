from django.db import models
from django.conf import settings
from apps.services.models import Service
import uuid


class Plan(models.Model):
    BILLING_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    # Plan is now a child of Service
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='plans', null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    unit_label = models.CharField(max_length=50, default='unit')
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default='monthly')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        prefix = self.service.get_service_type_display() if self.service else 'Unassigned'
        return f'{prefix} — {self.name} (€{self.price_per_unit}/{self.unit_label})'


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trialing', 'Trialing'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('paused', 'Paused'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='subscriptions', null=True, blank=True)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    mollie_subscription_id = models.CharField(max_length=100, blank=True)
    mollie_mandate_id = models.CharField(max_length=100, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.email} — {self.plan.name} ({self.status})'


class UsageSnapshot(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='snapshots')
    quantity = models.PositiveIntegerField(default=0)
    period_start = models.DateField()
    period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.subscription} — {self.quantity} units'


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('void', 'Void'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    mollie_payment_id = models.CharField(max_length=100, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Invoice {self.invoice_number} — {self.user.email}'

    @property
    def total(self):
        return self.amount + self.tax_amount
