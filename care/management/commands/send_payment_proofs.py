from django.core.management.base import BaseCommand
from care.models import PaymentProof
from care.payments import send_proof_email


class Command(BaseCommand):
    help = 'Retry up to 20 pending/failed/unconfigured hospital payment-proof emails using current hospital settings.'

    def handle(self, *args, **options):
        ids = list(PaymentProof.objects.exclude(email_status='sent').order_by('submitted_at').values_list('pk', flat=True)[:20])
        sent = sum(send_proof_email(pk) for pk in ids)
        self.stdout.write(f'Payment proof emails sent: {sent}; attempted: {len(ids)}. Delivery does not confirm payments.')
