import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('service_type', models.CharField(max_length=30)),
                ('price_per_unit', models.DecimalField(decimal_places=4, max_digits=10)),
                ('currency', models.CharField(default='EUR', max_length=3)),
                ('interval', models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=10)),
                ('unit_type', models.CharField(choices=[('per_user', 'Per User'), ('per_device', 'Per Device'), ('per_env', 'Per Environment')], max_length=20)),
                ('included_units', models.PositiveIntegerField(default=0, help_text='Free units before billing kicks in')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['service_type', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('trialing', 'Trialing'), ('active', 'Active'), ('past_due', 'Past Due'), ('paused', 'Paused'), ('cancelled', 'Cancelled')], default='trialing', max_length=20)),
                ('mollie_subscription_id', models.CharField(blank=True, max_length=50)),
                ('mollie_mandate_id', models.CharField(blank=True, max_length=50)),
                ('trial_ends_at', models.DateTimeField(blank=True, null=True)),
                ('current_period_start', models.DateTimeField(default=django.utils.timezone.now)),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='billing.plan')),
                ('service', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to='services.serviceinstance')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UsageSnapshot',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('unit_count', models.PositiveIntegerField()),
                ('unit_type', models.CharField(max_length=20)),
                ('captured_at', models.DateTimeField(auto_now_add=True)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_snapshots', to='billing.subscription')),
            ],
            options={
                'ordering': ['-period_start'],
                'unique_together': {('subscription', 'period_start')},
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('invoice_number', models.CharField(max_length=30, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='EUR', max_length=3)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('open', 'Open'), ('paid', 'Paid'), ('failed', 'Failed'), ('void', 'Void')], default='open', max_length=10)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('issued_at', models.DateTimeField()),
                ('due_at', models.DateTimeField()),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('mollie_payment_id', models.CharField(blank=True, max_length=50)),
                ('pdf', models.FileField(blank=True, null=True, upload_to='invoices/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invoices', to='billing.subscription')),
                ('usage_snapshot', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice', to='billing.usagesnapshot')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
