"""One availability contract for the directory, booking and reception workflows."""
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from .models import User, Slot, Appointment, ScheduleSession, ScheduleBlock
from .services import BookingError
from .security import audit


def slot_end(slot):
    return slot.start + timedelta(minutes=slot.duration + slot.buffer)


def overlaps(start, end, other_start, other_end):
    return start < other_end and other_start < end


def day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
    return start, start + timedelta(days=1)


def slot_restriction(slot, include_urgent=False):
    if slot.session_id and (not slot.session.active or (slot.session.visit_type == 'urgent' and not include_urgent)):
        return 'This session is unavailable for this booking.'
    if ScheduleBlock.objects.filter(doctor_id=slot.doctor_id, start__lt=slot_end(slot), end__gt=slot.start).exists():
        return 'The doctor is unavailable during this time.'
    return ''


def available_slots(doctor=None, include_urgent=False, doctor_ids=None):
    qs = Slot.objects.filter(active=True, booked=False, start__gt=timezone.now(),
                             start__lt=timezone.now()+timedelta(days=90)).select_related('session', 'doctor__doctor_profile')
    if doctor is not None:
        qs = qs.filter(doctor=doctor)
    if doctor_ids is not None:
        qs = qs.filter(doctor_id__in=doctor_ids)
    # Bounded publishing horizon; server-side booking rechecks all rules under locks.
    rejected = []
    doctor_ids = qs.values_list('doctor_id', flat=True).distinct()
    blocks = {}
    for block in ScheduleBlock.objects.filter(doctor_id__in=doctor_ids, end__gt=timezone.now()):
        blocks.setdefault(block.doctor_id, []).append(block)
    visits = Appointment.objects.filter(slot__doctor_id__in=doctor_ids,
        slot__start__gt=timezone.now()-timedelta(days=1), slot__start__lt=timezone.now()+timedelta(days=91)).exclude(status='cancelled')
    daily, sessions, occupied = {}, {}, {}
    for doctor_id, session_id, starts, duration, buffer in visits.values_list('slot__doctor_id','slot__session_id','slot__start','slot__duration','slot__buffer'):
        occupied.setdefault(doctor_id, []).append((starts, starts + timedelta(minutes=duration+buffer)))
        day = timezone.localdate(starts)
        daily[(doctor_id,day)] = daily.get((doctor_id,day),0)+1
        sessions[(session_id,day)] = sessions.get((session_id,day),0)+1
    for slot in qs:
        if (slot.session_id and (not slot.session.active or (slot.session.visit_type=='urgent' and not include_urgent))) or any(
                  overlaps(slot.start,slot_end(slot),block.start,block.end) for block in blocks.get(slot.doctor_id,[])) or any(
                  overlaps(slot.start,slot_end(slot),start,end) for start,end in occupied.get(slot.doctor_id, [])):
            rejected.append(slot.pk)
            continue
        day = timezone.localdate(slot.start)
        profile = getattr(slot.doctor, 'doctor_profile', None)
        if profile and profile.daily_limit and daily.get((slot.doctor_id,day),0) >= profile.daily_limit:
            rejected.append(slot.pk)
        elif slot.session_id and sessions.get((slot.session_id,day),0) >= slot.session.capacity:
            rejected.append(slot.pk)
    return qs.exclude(pk__in=rejected)


@transaction.atomic
def publish_schedule(doctor, first, last):
    User.objects.select_for_update().get(pk=doctor.pk)
    if not timezone.localdate() <= first <= last <= timezone.localdate()+timedelta(days=90):
        raise BookingError('Publish dates must be within the next 90 days.')
    created = 0
    day = first
    while day <= last:
        for session in ScheduleSession.objects.filter(doctor=doctor, active=True, weekday=day.weekday()):
            start = timezone.make_aware(datetime.combine(day, session.start))
            end = timezone.make_aware(datetime.combine(day, session.end))
            step = timedelta(minutes=session.duration+session.buffer)
            while start+step <= end:
                if start > timezone.now():
                    nearby = Slot.objects.filter(doctor=doctor, active=True, start__lt=start+step,
                                                 start__gt=start-timedelta(hours=5))
                    if not any(overlaps(start, start+step, s.start, slot_end(s)) for s in nearby):
                        candidate = Slot(doctor=doctor, start=start, duration=session.duration,
                                         buffer=session.buffer, consultation_type=session.mode, session=session)
                        if not slot_restriction(candidate, include_urgent=True):
                            previous = Slot.objects.filter(doctor=doctor,start=start).first()
                            if previous is None:
                                candidate.save()
                                created += 1
                            elif previous.session_id==session.pk and not previous.booked and not previous.active:
                                previous.active=True
                                previous.save(update_fields=['active'])
                                created += 1
                start += step
        day += timedelta(days=1)
    audit(doctor, 'schedule.published', created)
    return created


@transaction.atomic
def add_block(doctor, start, end, reason):
    User.objects.select_for_update().get(pk=doctor.pk)
    if start >= end or end <= timezone.now() or end-start > timedelta(days=366):
        raise BookingError('Choose a future blocked period up to 366 days.')
    for slot in Slot.objects.filter(doctor=doctor, booked=True, start__lt=end, start__gt=start-timedelta(hours=5)):
        if overlaps(start, end, slot.start, slot_end(slot)):
            raise BookingError('Reschedule or cancel booked visits before blocking this period.')
    block = ScheduleBlock.objects.create(doctor=doctor, start=start, end=end, reason=reason)
    audit(doctor, 'schedule.blocked', block.pk)
    return block
