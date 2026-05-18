from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.text import slugify
from django.contrib import messages
from apps.core.middleware import SuperAdminRequiredMixin, CustomerScopedMixin
from .models import Customer
from .forms import CustomerForm


class CustomerListView(SuperAdminRequiredMixin, View):
    def get(self, request):
        customers = Customer.objects.all().order_by("name")
        return render(request, "customers/list.html", {"customers": customers})


class CustomerDetailView(CustomerScopedMixin, View):
    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        return render(request, "customers/detail.html", {
            "customer": customer,
            "environments": customer.environments.filter(is_active=True),
            "users": customer.users.filter(is_active=True),
        })


class CustomerCreateView(SuperAdminRequiredMixin, View):
    def get(self, request):
        return render(request, "customers/form.html", {"form": CustomerForm()})

    def post(self, request):
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.slug = slugify(customer.name)
            customer.save()
            messages.success(request, f"Customer '{customer.name}' created.")
            return redirect("customers:detail", pk=customer.pk)
        return render(request, "customers/form.html", {"form": form})


class CustomerUpdateView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        return render(request, "customers/form.html", {"form": CustomerForm(instance=customer), "customer": customer})

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, "partials/toast.html", {"message": "Saved.", "type": "success"})
            messages.success(request, "Customer updated.")
            return redirect("customers:detail", pk=customer.pk)
        return render(request, "customers/form.html", {"form": form, "customer": customer})
