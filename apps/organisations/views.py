from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.text import slugify
from django.contrib import messages
from apps.core.middleware import LoginRequiredMixin, CustomerScopedMixin, CustomerAdminRequiredMixin
from .models import Organisation, OrganisationMembership
from .forms import OrganisationForm, MembershipForm


class OrganisationListView(CustomerScopedMixin, View):
    def get(self, request):
        filters = self.get_customer_filter()
        orgs = Organisation.objects.filter(**filters).select_related("customer").order_by("name")
        return render(request, "organisations/list.html", {"organisations": orgs})


class OrganisationDetailView(CustomerScopedMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organisation, pk=pk)
        return render(request, "organisations/detail.html", {
            "org": org,
            "products": org.products.all(),
            "memberships": org.memberships.select_related("user").all(),
        })


class OrganisationCreateView(CustomerAdminRequiredMixin, View):
    def _customer_ctx(self, request):
        ctx = {}
        if request.user.is_superadmin:
            from apps.customers.models import Customer
            ctx["customers"] = Customer.objects.all().order_by("name")
        return ctx

    def get(self, request):
        ctx = {"form": OrganisationForm(), **self._customer_ctx(request)}
        return render(request, "organisations/form.html", ctx)

    def post(self, request):
        form = OrganisationForm(request.POST)
        if form.is_valid():
            org = form.save(commit=False)

            if request.user.is_superadmin:
                from apps.customers.models import Customer
                customer_id = request.POST.get("customer")
                if not customer_id:
                    messages.error(request, "Please select a customer.")
                    ctx = {"form": form, **self._customer_ctx(request)}
                    return render(request, "organisations/form.html", ctx)
                org.customer = get_object_or_404(Customer, pk=customer_id)
            else:
                if not request.user.customer:
                    messages.error(request, "Your account is not linked to a customer. Contact a super admin.")
                    return render(request, "organisations/form.html", {"form": form})
                org.customer = request.user.customer

            # Ensure unique slug within the customer
            base_slug = slugify(org.name)
            slug = base_slug
            counter = 1
            while Organisation.objects.filter(customer=org.customer, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            org.slug = slug
            org.save()
            messages.success(request, f"Organisation '{org.name}' created.")
            return redirect("organisations:detail", pk=org.pk)

        ctx = {"form": form, **self._customer_ctx(request)}
        return render(request, "organisations/form.html", ctx)


class OrganisationUpdateView(CustomerAdminRequiredMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organisation, pk=pk)
        return render(request, "organisations/form.html", {"form": OrganisationForm(instance=org), "org": org})

    def post(self, request, pk):
        org = get_object_or_404(Organisation, pk=pk)
        form = OrganisationForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, "partials/toast.html", {"message": "Saved.", "type": "success"})
            messages.success(request, "Organisation updated.")
            return redirect("organisations:detail", pk=org.pk)
        return render(request, "organisations/form.html", {"form": form, "org": org})


class OrganisationMembersView(CustomerScopedMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organisation, pk=pk)
        return render(request, "organisations/members.html", {
            "org": org,
            "memberships": org.memberships.select_related("user").all(),
            "form": MembershipForm(organisation=org),
        })


class AddMemberView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk):
        org = get_object_or_404(Organisation, pk=pk)
        form = MembershipForm(organisation=org, data=request.POST)
        if form.is_valid():
            membership = form.save(commit=False)
            membership.organisation = org
            membership.save()
            if request.htmx:
                memberships = org.memberships.select_related("user").all()
                return render(request, "partials/members_table.html", {
                    "org": org,
                    "memberships": memberships,
                    "form": MembershipForm(organisation=org),
                })
            messages.success(request, "Member added.")
        return redirect("organisations:members", pk=pk)


class RemoveMemberView(CustomerAdminRequiredMixin, View):
    def post(self, request, pk, membership_pk):
        org = get_object_or_404(Organisation, pk=pk)
        membership = get_object_or_404(OrganisationMembership, pk=membership_pk, organisation=org)
        membership.delete()
        if request.htmx:
            memberships = org.memberships.select_related("user").all()
            return render(request, "partials/members_table.html", {
                "org": org,
                "memberships": memberships,
                "form": MembershipForm(organisation=org),
            })
        messages.success(request, "Member removed.")
        return redirect("organisations:members", pk=pk)
