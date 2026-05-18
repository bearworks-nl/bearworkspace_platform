from django.urls import path
from . import views

app_name = "organisations"

urlpatterns = [
    path("", views.OrganisationListView.as_view(), name="list"),
    path("create/", views.OrganisationCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.OrganisationDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.OrganisationUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/members/", views.OrganisationMembersView.as_view(), name="members"),
    path("<uuid:pk>/members/add/", views.AddMemberView.as_view(), name="add_member"),
    path("<uuid:pk>/members/<uuid:membership_pk>/remove/", views.RemoveMemberView.as_view(), name="remove_member"),
]
