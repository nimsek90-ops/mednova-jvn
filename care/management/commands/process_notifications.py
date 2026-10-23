from django.core.management.base import BaseCommand
from care.delivery import reminders, process_outbox

class Command(BaseCommand):
    help = 'Create deduplicated reminders and process a bounded email outbox.'
    def handle(self, *args, **options):
        reminders()
        sent = process_outbox()
        from care.payments import retry_proof_emails
        proof_sent = retry_proof_emails()
        self.stdout.write(f'Email messages accepted by backend: {sent}. SMS provider is not configured.')
        self.stdout.write(f'Hospital payment-proof emails accepted by backend: {proof_sent}.')
