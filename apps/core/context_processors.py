from apps.environments.models import Environment


def sidebar_context(request):
    if not request.user.is_authenticated:
        return {}

    environments = (
        Environment.objects
        .filter(owner=request.user)
        .prefetch_related('services')
        .order_by('sort_order', 'name')[:10]
    )

    active_env_pk = None
    resolver = getattr(request, 'resolver_match', None)

    if resolver:
        pk = resolver.kwargs.get('pk')
        app = getattr(resolver, 'app_name', '') or ''

        if app == 'services' and pk:
            try:
                from apps.services.models import Service
                svc = (Service.objects
                       .filter(pk=pk)
                       .select_related('environment')
                       .first())
                if svc:
                    active_env_pk = svc.environment_id
            except Exception:
                pass

        elif app == 'environments' and pk:
            active_env_pk = pk

        elif resolver.kwargs.get('env_pk'):
            active_env_pk = resolver.kwargs.get('env_pk')

        if not active_env_pk:
            active_env_pk = request.GET.get('env')

    if active_env_pk:
        try:
            active_env_pk = int(active_env_pk)
        except (ValueError, TypeError):
            active_env_pk = None

    return {
        'sidebar_environments': environments,
        'sidebar_active_env_pk': active_env_pk,
    }


def site_settings(request):
    """Makes SiteSettings available in every template as `site_settings`."""
    from apps.core.models import SiteSettings
    return {'site_settings': SiteSettings.get()}
