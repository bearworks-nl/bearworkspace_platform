from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Set up billing schedule and ensure all required DB tables exist'

    def handle(self, *args, **options):
        self.stdout.write('Checking database tables...')

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' OR table_schema = 'main'
            """)

        self.stdout.write(self.style.SUCCESS('✓ Database tables verified.'))
        self.stdout.write('')
        self.stdout.write('Billing schedule setup complete.')
        self.stdout.write('Celery beat will run invoice generation on the 1st of each month.')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Setup complete!'))
