"""Bounded cron-compatible email outbox. Email contains no clinical details.

Delivery is at least once: an SMTP acceptance followed by process failure can
cause a duplicate on retry. Reminder creation is idempotent by appointment.
"""
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from .models import Notification, DeliveryOutbox, Appointment


@transaction.atomic
def publish(recipient, message, key, appointment=None):
    existing = DeliveryOutbox.objects.filter(dedupe_key=key).first()
    if existing:
        return existing.notification
    try:
        with transaction.atomic():
            notice = Notification.objects.create(recipient=recipient, message=message, appointment=appointment)
            DeliveryOutbox.objects.create(notification=notice, dedupe_key=key)
        return notice
    except IntegrityError:
        return DeliveryOutbox.objects.get(dedupe_key=key).notification


def reminders():
    now = timezone.now()
    for appt in Appointment.objects.filter(status='confirmed', slot__start__gt=now, slot__start__lte=now+timedelta(hours=24)).select_related('patient')[:200]:
        # Date/time is included in key so a rescheduled appointment gets a new reminder.
        publish(appt.patient, 'An appointment is coming up. Sign in to review its details.', f'reminder:{appt.pk}:{appt.slot.start.isoformat()}', appt)


def process_outbox(limit=30):
    import time
    deadline = time.monotonic()+30
    sent = 0
    for _ in range(limit):
        if time.monotonic() >= deadline:
            break
        now = timezone.now()
        with transaction.atomic():
            row = DeliveryOutbox.objects.select_for_update().filter(
                Q(status__in=['pending', 'failed', 'unavailable'], next_attempt__lte=now) |
                Q(status='sending', lease_until__lt=now), attempts__lt=5
            ).order_by('pk').first()
            if not row:
                break
            if not settings.EMAIL_HOST:
                row.status = 'unavailable'
                row.last_error = 'SMTP not configured'
                row.next_attempt = now+timedelta(hours=1)
                row.save()
                continue
            row.status = 'sending'
            row.attempts += 1
            row.lease_until = now+timedelta(minutes=5)
            row.save()
            row_id = row.pk
            recipient = row.notification.recipient.email
        try:
            delivered = send_mail('MedNova account notification', 'You have a new account notification. Sign in to the hospital website to review it. Do not reply with medical information.', settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
            if delivered != 1:
                raise RuntimeError('SMTP did not accept the message')
        except Exception:
            DeliveryOutbox.objects.filter(pk=row_id).update(status='failed', last_error='Email delivery failed', next_attempt=timezone.now()+timedelta(minutes=15), lease_until=None)
        else:
            DeliveryOutbox.objects.filter(pk=row_id).update(status='sent', sent_at=timezone.now(), lease_until=None, last_error='')
            sent += 1
    return sent
