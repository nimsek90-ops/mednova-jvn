from datetime import timedelta
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from care.models import Signal, RateBucket


class Command(BaseCommand):
    help = "Delete expired call signaling, rate-limit buckets and login sessions. Does not delete medical records."

    def handle(self, *args, **options):
        signals = Signal.objects.filter(
            created__lt=timezone.now() - timedelta(minutes=15)
        ).delete()[0]
        buckets = RateBucket.objects.filter(expires__lt=timezone.now()).delete()[0]
        call_command("clearsessions")
        self.stdout.write(
            f"Removed {signals} expired signals and {buckets} expired rate-limit records."
        )
