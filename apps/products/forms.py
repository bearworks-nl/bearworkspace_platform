from django import forms
from .models import (
    ProductInstance, ProductType,
    RecastWorkspaceConfig, Windows365Config, IntunePolicy,
)
import json


class EnableProductForm(forms.Form):
    organisation = forms.UUIDField()
    product_type = forms.ChoiceField(choices=ProductType.choices)
    plan = forms.UUIDField()


class RecastConfigForm(forms.ModelForm):
    class Meta:
        model = RecastWorkspaceConfig
        fields = ["workspace_url", "api_key", "workspace_id"]
        widgets = {
            "api_key": forms.PasswordInput(render_value=True),
        }


class Windows365ConfigForm(forms.ModelForm):
    class Meta:
        model = Windows365Config
        fields = ["provisioning_policy_id", "user_settings_id"]


class IntunePolicyForm(forms.ModelForm):
    json_payload = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 16, "class": "font-mono text-sm"}),
        label="JSON payload",
    )

    class Meta:
        model = IntunePolicy
        fields = ["name", "policy_type", "json_payload"]

    def clean_json_payload(self):
        raw = self.cleaned_data["json_payload"]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")
        return parsed
