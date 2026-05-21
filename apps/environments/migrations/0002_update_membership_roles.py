from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='environmentmembership',
            name='role',
            field=models.CharField(
                choices=[
                    ('env_admin',  'Environment Admin'),
                    ('env_member', 'Environment Member'),
                ],
                default='env_member',
                max_length=20,
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE environments_environmentmembership SET role = 'env_member' WHERE role = 'customer_member';",
            reverse_sql="UPDATE environments_environmentmembership SET role = 'customer_member' WHERE role = 'env_member';",
        ),
    ]
