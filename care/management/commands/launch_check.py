from urllib.parse import urlparse
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from care.models import Hospital


class Command(BaseCommand):
    help = "Check required deployment configuration. This does not deploy the website."

    def handle(self, *args, **options):
        errors = []
        if settings.LOCAL or settings.TESTING:
            errors.append("Use APP_ENV=production without MEDNOVA_TESTING.")
        origin = urlparse(settings.PUBLIC_ORIGIN)
        if (
            origin.scheme != "https"
            or not origin.hostname
            or origin.hostname in ("localhost", "127.0.0.1")
        ):
            errors.append(
                "Connect the approved custom domain and set PUBLIC_ORIGIN to its HTTPS origin."
            )
        if origin.hostname and origin.hostname not in settings.ALLOWED_HOSTS:
            errors.append("Add the custom domain to ALLOWED_HOSTS.")
        if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:
            errors.append("Connect and test the password-reset email service.")
        if not settings.TURN_URL or not settings.TURN_SECRET:
            errors.append(
                "Configure and test an authenticated TURN relay for video calls."
            )
        h = Hospital.objects.first()
        if not h or not all(
            [
                h.legal_name,
                h.address,
                h.phone,
                h.email,
                h.privacy_email,
                h.cancellation_policy,
            ]
        ):
            errors.append(
                "Complete verified hospital identity, contacts and cancellation/refund policy."
            )
        if settings.RAZORPAY_KEY_ID and not all(
            [settings.RAZORPAY_KEY_SECRET, settings.RAZORPAY_WEBHOOK_SECRET]
        ):
            errors.append(
                "Finish payment secrets and captured-payment webhook configuration or disable online payments."
            )
        if errors:
            raise CommandError("\n".join(errors))
        call_command("check", deploy=True)
        self.stdout.write(
            self.style.SUCCESS(
                "Configuration check passed. Browser, MySQL concurrency, backups and provider tests still require recorded verification before launch."
            )
        )
