from django import forms
from .models import Organisation, OrganisationMembership
from apps.accounts.models import User


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = ["name", "description", "azure_tenant_id", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class MembershipForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select,
        label="User",
    )

    class Meta:
        model = OrganisationMembership
        fields = ["user", "role"]

    def __init__(self, organisation=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if organisation:
            existing = organisation.memberships.values_list("user_id", flat=True)
            self.fields["user"].queryset = User.objects.filter(
                is_active=True,
                customer=organisation.customer,
            ).exclude(id__in=existing)
