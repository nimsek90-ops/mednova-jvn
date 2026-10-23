from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import User, Slot, Appointment, Payment, Prescription, Medicine, Notification, Hospital
from .security import audit


class BookingError(Exception):
    pass


def notify(appt, message):
    from .delivery import publish
    import uuid
    event_id = uuid.uuid4().hex
    for user in User.objects.filter(pk__in={appt.patient_id, appt.slot.doctor_id}):
        publish(user, message, f'appointment:{event_id}:{user.pk}', appt)


def cancellation_allowed(appt):
    hospital = Hospital.objects.first()
    notice = hospital.cancellation_notice_minutes if hospital else 0
    return appt.slot.start > timezone.now() + timedelta(minutes=notice)


@transaction.atomic
def book(patient, slot_id, mode, reason, existing=None, actor=None):
    if mode not in ("in_person", "video") or not isinstance(reason, str) or not reason.strip() or len(reason) > 400:
        raise BookingError("Choose a valid consultation type and reason (up to 400 characters).")
    # Serialize each patient's bookings and each doctor's calendar, including range overlap checks.
    patient = User.objects.select_for_update().get(pk=patient.pk)
    candidate = Slot.objects.get(pk=slot_id)
    doctor_ids = {candidate.doctor_id}
    if existing:
        previous = Appointment.objects.get(pk=existing.pk)
        if previous.patient_id != patient.pk:
            raise BookingError("This appointment does not belong to this patient.")
        doctor_ids.add(previous.slot.doctor_id)
    locked_doctors = {u.pk: u for u in User.objects.select_for_update().filter(pk__in=doctor_ids).order_by("pk")}
    doctor = locked_doctors[candidate.doctor_id]
    slot = Slot.objects.select_for_update().get(pk=slot_id)
    from .scheduling import slot_restriction, slot_end, overlaps
    restriction = slot_restriction(slot, include_urgent=bool(actor and actor.role == 'receptionist' and actor.is_active and actor.approval == 'approved'))
    if restriction:
        raise BookingError(restriction)
    if slot.consultation_type not in ("both", mode):
        raise BookingError("This slot does not support that consultation type.")
    if (
        patient.role != "patient"
        or not patient.is_active
        or patient.approval != "approved"
    ):
        raise BookingError("Patient account is unavailable.")
    if doctor.role != "doctor" or not doctor.is_active or doctor.approval != "approved":
        raise BookingError("This doctor is not available.")
    if slot.booked or not slot.active or not timezone.now() < slot.start < timezone.now()+timedelta(days=90):
        raise BookingError("This slot is no longer available. Choose another time.")
    if Appointment.objects.filter(slot=slot).exclude(status="cancelled").exists():
        raise BookingError("This slot is no longer available. Choose another time.")
    neighbors = Appointment.objects.filter(slot__start__gt=slot.start-timedelta(hours=5),
        slot__start__lt=slot_end(slot)).exclude(status='cancelled').exclude(pk=existing.pk if existing else None).select_related('slot')
    if any(overlaps(slot.start, slot_end(slot), a.slot.start, slot_end(a.slot)) for a in neighbors.filter(slot__doctor=doctor)):
        raise BookingError("The doctor already has an appointment at this time.")
    if (
        not hasattr(doctor, "doctor_profile")
        or not doctor.doctor_profile.department
        or not doctor.doctor_profile.department.active
    ):
        raise BookingError("The doctor profile is unavailable.")
    if any(overlaps(slot.start, slot_end(slot), a.slot.start, slot_end(a.slot)) for a in neighbors.filter(patient=patient)):
        raise BookingError("You already have an appointment at this time.")
    from .scheduling import day_bounds
    day_start, day_end = day_bounds(timezone.localdate(slot.start))
    visits = Appointment.objects.filter(slot__doctor=doctor, slot__start__gte=day_start, slot__start__lt=day_end).exclude(status='cancelled').exclude(pk=existing.pk if existing else None)
    if doctor.doctor_profile.daily_limit and visits.count() >= doctor.doctor_profile.daily_limit:
        raise BookingError('The doctor has reached the daily booking limit.')
    if slot.session_id and visits.filter(slot__session_id=slot.session_id).count() >= slot.session.capacity:
        raise BookingError('This session has reached its booking limit.')
    if existing:
        appt = Appointment.objects.select_for_update().get(pk=existing.pk)
        if (
            appt.status not in ("pending", "confirmed")
            or not cancellation_allowed(appt)
        ):
            raise BookingError("This appointment cannot be rescheduled.")
        payment = Payment.objects.select_for_update().get(appointment=appt)
        if payment.status == "awaiting":
            raise BookingError("Payment verification is pending. Contact reception before rescheduling.")
        if mode == 'video' and payment.status == 'paid' and payment.amount > 0 and payment.method in ('cash', 'offline'):
            raise BookingError('Video appointments require online payment. Contact reception before changing a cash-paid visit to video.')
        if payment.status != "unpaid" and slot.doctor_id != appt.slot.doctor_id:
            raise BookingError(
                "Paid visits can only be rescheduled with the same doctor."
            )
        Slot.objects.filter(pk=appt.slot_id).update(booked=False)
        appt.slot = slot
        appt.status = "pending"
        appt.mode = mode
        appt.reason = reason
        if payment.status in ("unpaid", "rejected"):
            payment.status = "unpaid"
            payment.current_proof = None
            payment.received_by = None
            payment.verified_at = None
            payment.rejection_reason = ""
            payment.verification_version += 1
            if mode == "video" and payment.method == "offline":
                payment.method = ""
            appt.fee = doctor.doctor_profile.fee
            payment.amount = appt.fee
            payment.order_id = ""
            payment.save()
        appt.save()
        audit(patient, "appointment.rescheduled", appt.pk)
    else:
        appt = Appointment.objects.create(
            patient=patient,
            slot=slot,
            mode=mode,
            reason=reason,
            fee=doctor.doctor_profile.fee,
        )
        Payment.objects.create(
            appointment=appt,
            amount=appt.fee,
            status="paid" if appt.fee == 0 else "unpaid",
            method="free" if appt.fee == 0 else "",
        )
        audit(patient, "appointment.created", appt.pk)
    slot.booked = True
    slot.save(update_fields=["booked"])
    notify(appt, "Appointment rescheduled." if existing else "Appointment requested.")
    return appt


@transaction.atomic
def change_status(appt, user, status, reason=''):
    User.objects.select_for_update().get(pk=appt.patient_id)
    snapshot = Appointment.objects.select_related("slot").get(pk=appt.pk)
    User.objects.select_for_update().get(pk=snapshot.slot.doctor_id)
    appt = Appointment.objects.select_for_update().get(pk=appt.pk)
    actor = User.objects.get(pk=user.pk)
    allowed = {
        "patient": {"cancelled"}, "doctor": {"confirmed", "cancelled", "completed", "no_show"},
        "receptionist": {"confirmed", "cancelled", "no_show"}, "admin": {"confirmed", "cancelled", "no_show"},
    }
    if (not actor.is_active or actor.approval != "approved"
        or status not in allowed.get(actor.role, set())
        or (actor.role == "patient" and actor.pk != appt.patient_id)
        or (actor.role == "doctor" and actor.pk != appt.slot.doctor_id)):
        raise BookingError("You cannot change this appointment.")
    if actor.role == "patient" and not cancellation_allowed(appt):
        raise BookingError("The cancellation notice period has passed. Contact the hospital.")
    transitions = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"completed", "cancelled", "no_show"},
    }
    if status not in transitions.get(appt.status, set()):
        raise BookingError("This status change is not available.")
    if status == "confirmed" and appt.slot.start <= timezone.now():
        raise BookingError("A past appointment cannot be confirmed.")
    if status in ("completed", "no_show") and appt.slot.start > timezone.now():
        raise BookingError("The consultation has not started yet.")
    if len(reason) > 300:
        raise BookingError('Cancellation reason must be at most 300 characters.')
    appt.status = status
    if status == 'cancelled':
        appt.cancellation_reason = reason.strip()
    appt.save(update_fields=["status", 'cancellation_reason'])
    from .models import QueueEntry
    if status in ('completed','no_show'):
        QueueEntry.objects.filter(appointment=appt, status__in=['waiting','called','in_consultation']).update(status='completed' if status=='completed' else 'cancelled', updated=timezone.now())
    if status == "cancelled":
        from .models import QueueEntry
        QueueEntry.objects.filter(appointment=appt, status__in=["waiting", "called", 'in_consultation']).update(status="cancelled", updated=timezone.now())
        Slot.objects.filter(pk=appt.slot_id).update(booked=False)
        Payment.objects.filter(appointment=appt, status="paid", amount__gt=0).update(
            status="refund_due"
        )
        if appt.slot.start > timezone.now():
            from .models import WaitingList
            from .delivery import publish
            for entry in WaitingList.objects.filter(doctor_id=appt.slot.doctor_id, mode=appt.mode, active=True).select_related('patient'):
                publish(entry.patient, 'An appointment time may now be available with your requested doctor. Sign in to review current availability.',
                    f'waiting:{appt.pk}:{entry.pk}:{appt.slot_id}')
    audit(user, "appointment." + status, appt.pk)
    notify(appt, "Appointment " + status + ".")


@transaction.atomic
def dispense(rx, user):
    actor = User.objects.get(pk=user.pk)
    if actor.role != "pharmacist" or not actor.is_active or actor.approval != "approved":
        raise BookingError("Only an approved pharmacist can dispense prescriptions.")
    Appointment.objects.select_for_update().get(pk=rx.appointment_id)
    rx = Prescription.objects.select_for_update().get(pk=rx.pk)
    if rx.appointment.status == "cancelled":
        raise BookingError("A cancelled appointment's prescription cannot be dispensed.")
    if rx.dispensed:
        raise BookingError("This prescription has already been dispensed.")
    items = list(rx.items.order_by("medicine_id"))
    if not items:
        raise BookingError("There are no medicines to dispense.")
    for item in items:
        quantity = item.remaining
        if quantity == 0:
            continue
        med = Medicine.objects.select_for_update().get(pk=item.medicine_id)
        if med.stock < quantity or med.expiry < timezone.localdate() or med.safety_status != 'available':
            raise BookingError(
                "Stock unavailable or expired. No medicines were dispensed."
            )
        med.stock -= quantity
        med.save(update_fields=["stock"])
        from .models import StockMovement
        if quantity:
            StockMovement.objects.create(medicine=med, actor=user, prescription=rx, quantity=-quantity, balance=med.stock, reason='Prescription dispensing')
            from .models import DispensingEvent
            DispensingEvent.objects.create(item=item, pharmacist=user, quantity=quantity)
            item.dispensed_quantity = item.quantity
            item.save(update_fields=['dispensed_quantity'])
    rx.dispensed = True
    rx.dispensed_by = user
    rx.dispensed_at = timezone.now()
    rx.save()
    audit(user, "prescription.dispensed", rx.pk)
