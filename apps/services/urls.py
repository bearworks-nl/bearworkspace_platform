from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceListView.as_view(), name="list"),
    path("enable/", views.EnableServiceView.as_view(), name="enable"),
    path("plans-for-type/", views.PlansForTypeView.as_view(), name="plans_for_type"),
    path("<uuid:pk>/", views.ServiceDetailView.as_view(), name="detail"),
    path("<uuid:pk>/disable/", views.DisableServiceView.as_view(), name="disable"),
    # Recast
    path("<uuid:pk>/recast/config/", views.RecastConfigView.as_view(), name="recast_config"),
    # Windows 365
    path("<uuid:pk>/windows365/config/", views.Windows365ConfigView.as_view(), name="windows365_config"),
    path("<uuid:pk>/windows365/sync/", views.Windows365SyncView.as_view(), name="windows365_sync"),
    # Intune
    path("<uuid:pk>/intune/config/", views.IntuneConfigView.as_view(), name="intune_config"),
    path("<uuid:pk>/intune/policies/", views.IntunePoliciesView.as_view(), name="intune_policies"),
    path("<uuid:pk>/intune/policies/create/", views.IntunePolicyCreateView.as_view(), name="intune_policy_create"),
    path("<uuid:pk>/intune/policies/<uuid:policy_pk>/edit/", views.IntunePolicyEditView.as_view(), name="intune_policy_edit"),
    path("<uuid:pk>/intune/policies/<uuid:policy_pk>/deploy/", views.IntunePolicyDeployView.as_view(), name="intune_policy_deploy"),
]
