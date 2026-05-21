from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('superadmin', 'Super Admin'),
                    ('env_admin',  'Environment Admin'),
                    ('env_member', 'Environment Member'),
                ],
                default='env_admin',
                max_length=20,
            ),
        ),
        # Migrate old role values to new ones
        migrations.RunSQL(
            sql="""
                UPDATE accounts_user SET role = 'env_admin'  WHERE role = 'customer_admin';
                UPDATE accounts_user SET role = 'env_member' WHERE role = 'customer_member';
            """,
            reverse_sql="""
                UPDATE accounts_user SET role = 'customer_admin'  WHERE role = 'env_admin';
                UPDATE accounts_user SET role = 'customer_member' WHERE role = 'env_member';
            """,
        ),
    ]
