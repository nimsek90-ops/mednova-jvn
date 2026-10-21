from django.core.management import call_command
from django.core.management.base import BaseCommand
from care.models import User, Hospital


class Command(BaseCommand):
    help = "Create the first administrator interactively; no default credentials."

    def handle(self, *args, **options):
        Hospital.objects.get_or_create(pk=1)
        if User.objects.filter(role="admin", is_active=True).exists():
            self.stdout.write(
                "An administrator account already exists. It has not been changed."
            )
            return
        self.stdout.write(
            "Create your administrator account. Use a unique strong password."
        )
        call_command("createsuperuser")
