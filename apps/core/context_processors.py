def global_context(request):
    ctx = {}
    try:
        if request.user.is_authenticated:
            ctx["current_user"] = request.user
            if request.user.is_superadmin:
                from apps.customers.models import Customer
                ctx["total_customers"] = Customer.objects.count()
    except Exception:
        pass
    return ctx
