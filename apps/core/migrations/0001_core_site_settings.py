from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='branding/', help_text='Upload a logo image. Recommended: SVG or PNG with transparent background, min 64px tall.')),
                ('logo_text', models.CharField(default='WorkspaceMgr', max_length=60, help_text='Text shown next to the logo in the sidebar.')),
                ('favicon', models.ImageField(blank=True, null=True, upload_to='branding/', help_text='Optional favicon (.ico or .png, 32×32px).')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Site settings',
                'verbose_name_plural': 'Site settings',
            },
        ),
    ]