from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from care.models import User


class Command(BaseCommand):
    help = "Verify database connectivity and required application tables."

    def handle(self, *args, **options):
        try:
            connection.ensure_connection()
            User.objects.count()
        except Exception:
            raise CommandError(
                "Database connection failed. Check the selected database service and its private connection settings. No fallback database was selected."
            )
        self.stdout.write(
            self.style.SUCCESS(f"Database connected: {connection.vendor}; database {connection.settings_dict['NAME']}. Application tables are available.")
        )
