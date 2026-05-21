from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        # Step 2: connection flag on Service
        migrations.AddField(
            model_name='service',
            name='is_connected',
            field=models.BooleanField(default=False),
        ),
        # Step 3: license data on RecastConfig
        migrations.AddField(
            model_name='recastconfig',
            name='license_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='recastconfig',
            name='license_numbers',
            field=models.JSONField(default=list, blank=True),
        ),
        # Step 4: matched order reference
        migrations.AddField(
            model_name='recastconfig',
            name='matched_order_ref',
            field=models.CharField(max_length=500, blank=True),
        ),
    ]
