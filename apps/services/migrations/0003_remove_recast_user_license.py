from django.db import migrations, models


def remove_user_license_services(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    Service.objects.filter(service_type='recast_user_license').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_recast_license_workflow'),
    ]

    operations = [
        migrations.RunPython(remove_user_license_services, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='service',
            name='service_type',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('recast_workspace', 'Recast Application Workspace'),
                    ('windows_365', 'Windows 365 Cloud PC'),
                    ('intune', 'Microsoft Intune'),
                ],
            ),
        ),
    ]
