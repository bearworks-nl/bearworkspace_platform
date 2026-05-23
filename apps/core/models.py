from django.db import models


class SiteSettings(models.Model):
    """
    Singleton model for site-wide branding settings.
    Only one row should ever exist (pk=1). Use SiteSettings.get() to retrieve it.
    """
    logo = models.ImageField(
        upload_to='branding/',
        null=True,
        blank=True,
        help_text='Upload a logo image. Recommended: SVG or PNG with transparent background, min 64px tall.',
    )
    logo_text = models.CharField(
        max_length=60,
        default='WorkspaceMgr',
        help_text='Text shown next to the logo in the sidebar.',
    )
    favicon = models.ImageField(
        upload_to='branding/',
        null=True,
        blank=True,
        help_text='Optional favicon (.ico or .png, 32×32px).',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site settings'
        verbose_name_plural = 'Site settings'

    def __str__(self):
        return 'Site settings'

    @classmethod
    def get(cls):
        """Always returns the singleton instance, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
