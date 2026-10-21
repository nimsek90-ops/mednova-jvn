from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import User, Prescription, Payment
from .delivery import publish

@receiver(pre_save, sender=User)
def user_previous(sender, instance, **kwargs):
    instance._previous_approval = User.objects.filter(pk=instance.pk).values_list('approval', flat=True).first() if instance.pk else None

@receiver(post_save, sender=User)
def user_event(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    if created:
        publish(instance, 'Your account has been registered. Staff access requires approval.', f'registration:{instance.pk}')
    elif instance._previous_approval != instance.approval:
        publish(instance, 'Your staff approval status changed. Sign in to review it.', f'approval:{instance.pk}:{instance.approval}:{__import__("hashlib").sha256(instance.review_note.encode()).hexdigest()[:24]}')

@receiver(post_save, sender=Prescription)
def prescription_event(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        publish(instance.appointment.patient, 'A prescription is available in your account.', f'prescription:{instance.pk}', instance.appointment)

@receiver(post_save, sender=Payment)
def payment_event(sender, instance, raw=False, **kwargs):
    if not raw and instance.status in ('paid', 'refunded'):
        publish(instance.appointment.patient, 'Your payment record has been updated.', f'payment:{instance.pk}:{instance.status}', instance.appointment)
