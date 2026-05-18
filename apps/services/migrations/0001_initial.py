import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('environments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IntuneConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_sync', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='IntunePolicy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('graph_id', models.CharField(blank=True, max_length=100)),
                ('name', models.CharField(max_length=255)),
                ('policy_type', models.CharField(choices=[('device_configuration', 'Device Configuration'), ('compliance', 'Compliance'), ('app_protection', 'App Protection'), ('enrollment', 'Enrollment'), ('security_baseline', 'Security Baseline')], max_length=30)),
                ('json_payload', models.JSONField(default=dict)),
                ('is_deployed', models.BooleanField(default=False)),
                ('last_deployed', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='policies', to='services.intuneconfig')),
            ],
            options={
                'verbose_name_plural': 'Intune policies',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ServiceInstance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('service_type', models.CharField(choices=[('recast_workspace', 'Recast Application Workspace'), ('windows_365', 'Windows 365 Cloud PC'), ('intune', 'Microsoft Intune')], max_length=30)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('provisioning', 'Provisioning'), ('error', 'Error')], default='provisioning', max_length=20)),
                ('enabled_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('environment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='environments.environment')),
            ],
            options={
                'ordering': ['service_type'],
                'unique_together': {('environment', 'service_type')},
            },
        ),
        migrations.AddField(
            model_name='intuneconfig',
            name='service',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='intune_config', to='services.serviceinstance'),
        ),
        migrations.CreateModel(
            name='RecastWorkspaceConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('workspace_url', models.URLField()),
                ('api_key', models.CharField(max_length=255)),
                ('workspace_id', models.CharField(blank=True, max_length=100)),
                ('last_sync', models.DateTimeField(blank=True, null=True)),
                ('sync_status', models.CharField(blank=True, max_length=50)),
                ('service', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='recast_config', to='services.serviceinstance')),
            ],
        ),
        migrations.CreateModel(
            name='Windows365Config',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provisioning_policy_id', models.CharField(blank=True, max_length=100)),
                ('user_settings_id', models.CharField(blank=True, max_length=100)),
                ('service', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='windows365_config', to='services.serviceinstance')),
            ],
        ),
        migrations.CreateModel(
            name='CloudPC',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('graph_id', models.CharField(max_length=100, unique=True)),
                ('display_name', models.CharField(max_length=255)),
                ('user_principal_name', models.EmailField(blank=True)),
                ('status', models.CharField(choices=[('provisioned', 'Provisioned'), ('provisioning', 'Provisioning'), ('deprovisioning', 'Deprovisioning'), ('failed', 'Failed'), ('unknown', 'Unknown')], default='unknown', max_length=20)),
                ('last_synced', models.DateTimeField(blank=True, null=True)),
                ('config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cloud_pcs', to='services.windows365config')),
            ],
        ),
    ]
