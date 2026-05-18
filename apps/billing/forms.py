from django import forms
from .models import Plan, Subscription
from apps.products.models import ProductType


class PlanForm(forms.ModelForm):
    product_type = forms.ChoiceField(choices=ProductType.choices)

    class Meta:
        model = Plan
        fields = [
            "name", "product_type", "price_per_unit", "currency",
            "interval", "unit_type", "included_units", "is_active",
        ]
        widgets = {
            "price_per_unit": forms.NumberInput(attrs={"step": "0.0001", "min": "0"}),
            "included_units": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["currency"].initial = "EUR"


class SubscriptionPlanChangeForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ["plan", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(is_active=True)
