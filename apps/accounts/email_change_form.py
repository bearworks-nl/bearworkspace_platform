# ── Add this class to apps/accounts/forms.py ──────────────────────────────────
# Place it after the ProfileForm class at the bottom of the file.

class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label="New email address",
        widget=forms.EmailInput(attrs={"placeholder": "new@example.com"}),
    )
    password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm with your current password"}),
        help_text="We need your current password to confirm this change.",
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        email = self.cleaned_data["new_email"].lower()
        if email == self.user.email.lower():
            raise forms.ValidationError("This is already your current email address.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password. Please try again.")
        return password
