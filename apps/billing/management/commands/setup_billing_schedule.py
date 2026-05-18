"""
Run this as a Django management command to set up the Celery beat schedule
for billing snapshots: python manage.py setup_billing_schedule
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create Celery beat periodic task for monthly billing snapshots"

    def handle(self, *args, **options):
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json

        # Run on 1st of each month at 02:00 Amsterdam time
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="2",
            day_of_month="1",
            month_of_year="*",
            day_of_week="*",
            timezone="Europe/Amsterdam",
        )

        task, created = PeriodicTask.objects.update_or_create(
            name="Monthly billing snapshot",
            defaults={
                "crontab": schedule,
                "task": "billing.snapshot_usage",
                "args": json.dumps([]),
                "enabled": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Billing schedule created."))
        else:
            self.stdout.write(self.style.SUCCESS("Billing schedule updated."))
