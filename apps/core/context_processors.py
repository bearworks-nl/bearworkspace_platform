from apps.environments.models import Environment


def sidebar_context(request):
    if not request.user.is_authenticated:
        return {}

    environments = (
        Environment.objects
        .filter(owner=request.user)
        .prefetch_related('services')
        .order_by('name')[:10]
    )

    # Detect the currently active environment from the URL.
    # Works for /environments/<pk>/..., /services/<pk>/... etc.
    active_env_pk = None
    resolver = getattr(request, 'resolver_match', None)
    if resolver:
        # Direct environment pk in the URL
        active_env_pk = resolver.kwargs.get('pk') or resolver.kwargs.get('env_pk')

        # For service URLs, look up the service's environment
        if not active_env_pk and 'pk' in resolver.kwargs:
            try:
                from apps.services.models import Service
                svc = Service.objects.filter(pk=resolver.kwargs['pk']).select_related('environment').first()
                if svc:
                    active_env_pk = svc.environment_id
            except Exception:
                pass

        # Fallback: ?env= query param used on services list
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
