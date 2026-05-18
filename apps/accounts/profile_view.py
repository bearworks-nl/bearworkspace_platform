# ── Replace the ProfileView in apps/accounts/views.py ─────────────────────────
# Also add EmailChangeForm to the import at the top:
#   from .forms import LoginForm, PasswordResetRequestForm, SetNewPasswordForm, ProfileForm, EmailChangeForm

@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    template_name = "accounts/profile.html"

    def _context(self, request, form=None, email_form=None):
        return {
            "form":       form       or ProfileForm(instance=request.user),
            "email_form": email_form or EmailChangeForm(user=request.user),
        }

    def get(self, request):
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        form_type = request.POST.get("form_type")

        # ── Profile (name + avatar) ──────────────────────────────────────────
        if form_type == "profile":
            form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                if request.htmx:
                    return render(request, "partials/toast.html", {"message": "Profile updated.", "type": "success"})
                messages.success(request, "Profile updated.")
                return redirect("accounts:profile")
            return render(request, self.template_name, self._context(request, form=form))

        # ── Email change ─────────────────────────────────────────────────────
        if form_type == "email":
            email_form = EmailChangeForm(user=request.user, data=request.POST)
            if email_form.is_valid():
                request.user.email = email_form.cleaned_data["new_email"]
                request.user.save(update_fields=["email"])
                if request.htmx:
                    return render(request, "partials/toast.html", {"message": "Email address updated.", "type": "success"})
                messages.success(request, "Email address updated.")
                return redirect("accounts:profile")
            return render(request, self.template_name, self._context(request, email_form=email_form))

        # Fallback
        return redirect("accounts:profile")
