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
                "Database connection failed. Check the MySQL service and the MYSQL_* values in your private .env. If this is the first run, use SETUP_WINDOWS.cmd."
            )
        self.stdout.write(
            self.style.SUCCESS(f"Database connected: {connection.vendor}; schema {connection.settings_dict['NAME']}. Application tables are available.")
        )
