from apps.environments.models import Environment


def sidebar_context(request):
    if request.user.is_authenticated:
        environments = Environment.objects.filter(owner=request.user)[:10]
        return {'sidebar_environments': environments}
    return {}
