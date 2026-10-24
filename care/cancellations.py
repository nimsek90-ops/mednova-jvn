"""Patient-owned recovery from a doctor cancellation using canonical availability."""
from datetime import timedelta
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from django.views.decorators.http import require_GET
from .models import Appointment, AppointmentCancellation
from .security import roles
from .scheduling import available_slots


@roles('patient')
@require_GET
def alternatives(request, pk):
    event = get_object_or_404(AppointmentCancellation.objects.select_related(
        'appointment__slot__doctor__doctor_profile', 'doctor'), appointment_id=pk, patient=request.user)
    from .views import approved_profiles
    appt = event.appointment
    profile = event.doctor.doctor_profile
    specialties = list(profile.specialties.filter(active=True).values_list('pk', flat=True))
    doctors = approved_profiles().filter(Q(department_id=profile.department_id) | Q(specialties__pk__in=specialties)).distinct()
    doctor_ids = list(doctors.values_list('user_id', flat=True))
    candidates = available_slots(doctor_ids=doctor_ids).filter(consultation_type__in=['both', appt.mode])
    same = list(candidates.filter(doctor_id=event.doctor_id).order_by('start')[:8])
    same_specialty = set(doctors.filter(specialties__pk__in=specialties).values_list('user_id', flat=True))
    others = list(candidates.exclude(doctor_id=event.doctor_id).filter(
        start__gte=event.original_start-timedelta(days=3), start__lte=event.original_start+timedelta(days=3))[:300])
    others.sort(key=lambda slot: (slot.doctor_id not in same_specialty, abs((slot.start-event.original_start).total_seconds()), slot.pk))
    return render(request, 'care/cancellation_alternatives.html', {'event':event, 'same_slots':same, 'other_slots':others[:8]})
