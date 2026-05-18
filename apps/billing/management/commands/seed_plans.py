from django.core.management.base import BaseCommand
from apps.billing.models import Plan
from apps.products.models import ProductType


DEFAULT_PLANS = [
    # Recast Workspace — billed per user
    {
        "name": "Recast Workspace — Standard",
        "product_type": ProductType.RECAST_WORKSPACE,
        "price_per_unit": "4.9500",
        "currency": "EUR",
        "interval": "monthly",
        "unit_type": "per_user",
        "included_units": 0,
        "is_active": True,
    },
    {
        "name": "Recast Workspace — Enterprise",
        "product_type": ProductType.RECAST_WORKSPACE,
        "price_per_unit": "3.9500",
        "currency": "EUR",
        "interval": "monthly",
        "unit_type": "per_user",
        "included_units": 10,
        "is_active": True,
    },
    # Windows 365 — billed per device
    {
        "name": "Windows 365 — Standard",
        "product_type": ProductType.WINDOWS_365,
        "price_per_unit": "9.9500",
        "currency": "EUR",
        "interval": "monthly",
        "unit_type": "per_device",
        "included_units": 0,
        "is_active": True,
    },
    {
        "name": "Windows 365 — Enterprise",
        "product_type": ProductType.WINDOWS_365,
        "price_per_unit": "7.9500",
        "currency": "EUR",
        "interval": "monthly",
        "unit_type": "per_device",
        "included_units": 5,
        "is_active": True,
    },
    # Intune — billed per organisation (flat)
    {
        "name": "Intune — Standard",
        "product_type": ProductType.INTUNE,
        "price_per_unit": "49.0000",
        "currency": "EUR",
        "interval": "monthly",
        "unit_type": "per_org",
        "included_units": 0,
        "is_active": True,
    },
    {
        "name": "Intune — Enterprise",
        "product_type": ProductType.INTUNE,
        "price_per_unit": "39.0000",
        "currency": "EUR",
        "interval": "monthly",
        "unit_type": "per_org",
        "included_units": 0,
        "is_active": True,
    },
]


class Command(BaseCommand):
    help = "Seed default billing plans for all product types"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-create plans even if they already exist",
        )

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for plan_data in DEFAULT_PLANS:
            if options["force"]:
                plan, was_created = Plan.objects.update_or_create(
                    name=plan_data["name"],
                    product_type=plan_data["product_type"],
                    defaults=plan_data,
                )
            else:
                exists = Plan.objects.filter(
                    name=plan_data["name"],
                    product_type=plan_data["product_type"],
                ).exists()
                if exists:
                    skipped += 1
                    continue
                plan = Plan.objects.create(**plan_data)
                was_created = True

            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {plan.name}"))
            else:
                self.stdout.write(f"  ~ Updated: {plan.name}")

        self.stdout.write("")
        if created:
            self.stdout.write(self.style.SUCCESS(f"{created} plan(s) created."))
        if skipped:
            self.stdout.write(f"{skipped} plan(s) already exist (use --force to update).")
