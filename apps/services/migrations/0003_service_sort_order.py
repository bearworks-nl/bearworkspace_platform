from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_alter_service_options_alter_service_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, db_index=True),
        ),
        migrations.AlterModelOptions(
            name='service',
            options={'ordering': ['sort_order', 'environment', 'service_type', 'name']},
        ),
    ]
