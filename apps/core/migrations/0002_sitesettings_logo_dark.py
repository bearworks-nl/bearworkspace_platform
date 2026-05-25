from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_core_site_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='logo_dark',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='branding/',
                help_text='Logo for dark theme. If left empty, the default logo is used for both themes.',
            ),
        ),
    ]