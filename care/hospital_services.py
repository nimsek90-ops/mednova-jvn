"""Shared transactional hospital workflows; no payment or clinical simulation."""
from django.db import transaction
from django.utils import timezone
from .models import (User, Appointment, Medicine, Prescription, PrescriptionItem,
    DispensingEvent, StockMovement, Supplier, PurchaseOrder, GoodsReceipt, Bed, Admission)
from .security import audit
from .services import BookingError


def require_actor(user, *roles):
    actor = User.objects.get(pk=user.pk)
    if not actor.is_active or actor.approval != 'approved' or actor.role not in roles:
        raise BookingError('Your account is not permitted to perform this action.')
    return actor


@transaction.atomic
def partial_dispense(item_id, quantity, key, user):
    actor = require_actor(user, 'pharmacist')
    snapshot = PrescriptionItem.objects.select_related('prescription').get(pk=item_id)
    Appointment.objects.select_for_update().get(pk=snapshot.prescription.appointment_id)
    rx = Prescription.objects.select_for_update().get(pk=snapshot.prescription_id)
    previous = DispensingEvent.objects.filter(key=key).first()
    if previous:
        if previous.item_id == item_id and previous.pharmacist_id == actor.pk and previous.quantity == quantity:
            return previous
        raise BookingError('This submission reference has already been used.')
    item = PrescriptionItem.objects.select_for_update().get(pk=item_id)
    med = Medicine.objects.select_for_update().get(pk=item.medicine_id)
    if rx.dispensed or rx.appointment.status == 'cancelled' or not 1 <= quantity <= item.remaining:
        raise BookingError('Choose a quantity within the unfilled prescription amount.')
    if med.safety_status != 'available' or med.expiry < timezone.localdate() or med.stock < quantity:
        raise BookingError('Batch unavailable, expired, recalled or quarantined. Nothing dispensed.')
    med.stock -= quantity
    med.save(update_fields=['stock'])
    item.dispensed_quantity += quantity
    item.save(update_fields=['dispensed_quantity'])
    event = DispensingEvent.objects.create(key=key, item=item, pharmacist=actor, quantity=quantity)
    StockMovement.objects.create(medicine=med, actor=actor, prescription=rx,
        quantity=-quantity, balance=med.stock, reason='Partial prescription issue')
    if all(line.remaining == 0 for line in rx.items.all()):
        rx.dispensed = True
        rx.dispensed_by = actor
        rx.dispensed_at = timezone.now()
        rx.save()
    audit(actor, 'prescription.partial_issue', event.pk)
    return event


@transaction.atomic
def receive_purchase(order_id, quantity, reference, user):
    actor = require_actor(user, 'pharmacist', 'admin')
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id)
    existing = GoodsReceipt.objects.filter(reference=reference).first()
    if existing:
        if existing.order_id == order.pk and existing.quantity == quantity and existing.received_by_id == actor.pk:
            return existing
        raise BookingError('This delivery reference is already in use.')
    med = Medicine.objects.select_for_update().get(pk=order.medicine_id)
    if order.status != 'approved' or not 1 <= quantity <= order.quantity-order.received:
        raise BookingError('Receipt requires an approved order and its outstanding quantity.')
    if med.expiry < timezone.localdate() or med.safety_status != 'available':
        raise BookingError('Resolve batch expiry or quarantine before accepting a delivery.')
    receipt = GoodsReceipt.objects.create(order=order, quantity=quantity, reference=reference, received_by=actor)
    med.stock += quantity
    med.save(update_fields=['stock'])
    order.received += quantity
    if order.received == order.quantity:
        order.status = 'received'
    order.save(update_fields=['received', 'status'])
    StockMovement.objects.create(medicine=med, actor=actor, quantity=quantity, balance=med.stock, reason=f'Goods receipt {receipt.pk}')
    audit(actor, 'purchase.received', receipt.pk)
    return receipt


@transaction.atomic
def update_admission(admission_id, action, actor, bed_id=None):
    user = require_actor(actor, 'doctor', 'receptionist', 'admin')
    admission = Admission.objects.select_for_update().get(pk=admission_id)
    if user.role == 'doctor':
        if admission.doctor_id != user.pk or action != 'ready' or admission.status != 'admitted':
            raise BookingError('Only the responsible doctor can authorize discharge readiness.')
        admission.status = 'discharge_ready'
    elif action in ('allocate', 'transfer'):
        if admission.status not in ('requested', 'admitted'):
            raise BookingError('Bed allocation is unavailable for this request.')
        bed = Bed.objects.select_for_update().get(pk=bed_id, active=True)
        if Admission.objects.filter(bed=bed).exclude(pk=admission.pk).exists():
            raise BookingError('The selected bed is occupied.')
        admission.bed = bed
        admission.last_bed = str(bed)
        admission.status = 'admitted'
    elif action == 'discharge' and admission.status == 'discharge_ready':
        admission.bed = None
        admission.status = 'discharged'
    elif action == 'cancel' and admission.status == 'requested':
        admission.status = 'cancelled'
    else:
        raise BookingError('This admission transition is not permitted.')
    admission.save()
    audit(user, 'admission.'+action, admission.pk)
    return admission
