from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environments', '0003_alter_environmentmembership_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='environment',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, db_index=True),
        ),
    ]
