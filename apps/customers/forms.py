from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name", "email", "phone",
            "address_line1", "address_line2", "city", "postal_code", "country",
            "vat_number", "status", "logo", "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
