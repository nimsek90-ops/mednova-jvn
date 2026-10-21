"""Persisted patient tools and appointment-scoped clinical workflows."""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import (User, Appointment, WellnessEntry, WellnessRevision, HealthAssessment,
                     ClinicalNote, QueueEntry, QueueCounter, StockMovement)
from .security import roles, audit, rate_limit

DISCLAIMER = "This is a non-clinical lifestyle indicator. It is not a medical diagnosis, validated clinical score or prediction of disease."


def wellness_score(sleep, water, exercise_days, stress):
    result = Decimal(25)*Decimal(sleep)/8 + Decimal(20)*Decimal(water)/8 + Decimal(25)*Decimal(exercise_days)/5 + Decimal(30)*(10-Decimal(stress))/10
    return max(0, min(100, int(result.quantize(Decimal('1'), rounding=ROUND_HALF_UP))))


class WellnessForm(forms.ModelForm):
    class Meta:
        model = WellnessEntry
        fields = ['date', 'sleep', 'water', 'exercise_days', 'stress']
        labels = {'sleep': 'Sleep hours (0–24)', 'water': 'Water glasses (0–30)', 'exercise_days': 'Active days in the last seven days (0–7)', 'stress': 'Stress level (0–10)'}
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def clean_date(self):
        value = self.cleaned_data['date']
        if value > timezone.localdate() or value < timezone.localdate()-timedelta(days=365):
            raise forms.ValidationError('Choose today or a date within the previous 365 days.')
        return value


@roles('patient')
@rate_limit('wellness', 60, 3600)
@require_http_methods(['GET', 'POST'])
def wellness(request):
    initial = {'date': request.GET.get('date', timezone.localdate())}
    form = WellnessForm(request.POST if request.method == 'POST' else None, initial=initial)
    if request.method == 'GET' and request.GET.get('date'):
        try:
            entry = WellnessEntry.objects.filter(patient=request.user, date=request.GET['date']).first()
        except (ValueError, forms.ValidationError):
            entry = None
        if entry:
            form = WellnessForm(instance=entry)
    if request.method == 'POST' and form.is_valid():
        values = form.cleaned_data
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            entry, _ = WellnessEntry.objects.get_or_create(patient=request.user, date=values['date'], defaults={**values, 'score': wellness_score(values['sleep'], values['water'], values['exercise_days'], values['stress'])})
            for field, value in values.items():
                setattr(entry, field, value)
            entry.score = wellness_score(entry.sleep, entry.water, entry.exercise_days, entry.stress)
            entry.save()
            WellnessRevision.objects.create(entry=entry, values={**{key: str(value) for key, value in values.items()}, 'score': entry.score})
            audit(request.user, 'wellness.saved', entry.pk)
        messages.success(request, 'Wellness entry saved. Previous versions are retained.')
        return redirect('wellness')
    entries = WellnessEntry.objects.filter(patient=request.user).prefetch_related('revisions')
    today = timezone.localdate()
    pagination = Paginator(entries, 30).get_page(request.GET.get('page'))
    previous_week = entries.filter(date__gte=today-timedelta(days=13), date__lte=today-timedelta(days=7)).aggregate(value=Avg('score'))['value']
    previous_month = entries.filter(date__gte=today-timedelta(days=59), date__lte=today-timedelta(days=30)).aggregate(value=Avg('score'))['value']
    return render(request, 'care/wellness.html', {'form': form, 'entries': pagination, 'pagination': pagination, 'previous_week': previous_week, 'previous_month': previous_month, 'latest': entries.first(), 'weekly': entries.filter(date__gte=today-timedelta(days=6)).aggregate(value=Avg('score'))['value'], 'monthly': entries.filter(date__gte=today-timedelta(days=29)).aggregate(value=Avg('score'))['value'], 'disclaimer': DISCLAIMER})


class AssessmentForm(forms.Form):
    sleep_quality = forms.ChoiceField(choices=[('rested', 'Usually rested'), ('variable', 'Sometimes rested'), ('poor', 'Rarely rested')])
    hydration = forms.ChoiceField(choices=[('regular', 'Drink regularly'), ('variable', 'Sometimes forget'), ('low', 'Often forget')])
    activity = forms.ChoiceField(choices=[('regular', 'Regular activity'), ('some', 'Some activity'), ('little', 'Little activity')])
    balanced_meals = forms.ChoiceField(choices=[('often', 'Often'), ('sometimes', 'Sometimes'), ('rarely', 'Rarely')])
    stress = forms.IntegerField(min_value=0, max_value=10)


def assessment_results(answers):
    results = []
    for key, target, text in [
        ('sleep_quality', 'rested', 'Consider keeping a consistent sleep routine.'),
        ('hydration', 'regular', 'Consider a routine for drinking regularly, following any clinician-set fluid restrictions.'),
        ('activity', 'regular', 'Consider discussing activity suitable for your circumstances with a qualified professional.'),
        ('balanced_meals', 'often', 'Consider learning about balanced meals from a qualified professional.')]:
        if answers[key] != target:
            results.append(text)
    if answers['stress'] >= 7:
        results.append('You reported high stress. Consider seeking support from a qualified professional.')
    return results or ['Your answers describe consistent lifestyle routines. This questionnaire cannot assess your health or exclude illness.']


@require_http_methods(['GET', 'POST'])
def health_hub(request):
    form = AssessmentForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.path)
        if request.user.role != 'patient' or request.user.approval != 'approved' or not request.user.is_active:
            raise PermissionDenied
        if form.is_valid():
            HealthAssessment.objects.create(patient=request.user, answers=form.cleaned_data, result=assessment_results(form.cleaned_data))
            audit(request.user, 'health_questionnaire.saved')
            messages.success(request, 'Lifestyle questionnaire saved.')
            return redirect('health_hub')
    history = HealthAssessment.objects.filter(patient=request.user) if request.user.is_authenticated and request.user.role == 'patient' else []
    pagination = Paginator(history, 30).get_page(request.GET.get('page'))
    return render(request, 'care/health_hub.html', {'form': form, 'history': pagination, 'pagination': pagination, 'disclaimer': DISCLAIMER})


class SymptomForm(forms.Form):
    symptoms = forms.MultipleChoiceField(choices=[('chest', 'Chest pain'), ('breathing', 'Severe breathing difficulty / unable to speak normally'), ('stroke', 'Sudden face droop, arm weakness or speech difficulty'), ('bleeding', 'Severe uncontrolled bleeding'), ('unconscious', 'Unconsciousness'), ('other', 'Other symptoms')], widget=forms.CheckboxSelectMultiple)
    duration = forms.ChoiceField(choices=[('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days or longer')])
    severity = forms.ChoiceField(choices=[('mild', 'Mild'), ('moderate', 'Moderate'), ('severe', 'Severe')])


@require_http_methods(['GET', 'POST'])
def symptoms(request):
    form = SymptomForm(request.POST if request.method == 'POST' else None)
    result = None
    if request.method == 'POST' and form.is_valid():
        emergency = bool(set(form.cleaned_data['symptoms']) & {'chest', 'breathing', 'stroke', 'bleeding', 'unconscious'})
        result = 'emergency' if emergency else ('urgent' if form.cleaned_data['severity'] == 'severe' else 'general')
    return render(request, 'care/symptoms.html', {'form': form, 'result': result})


def public_information(request, kind):
    if kind not in ('about', 'pharmacy'):
        from django.http import Http404
        raise Http404
    return render(request, 'care/information.html', {'kind': kind})


def clinical_access(user, appt):
    return user.role == 'patient' and appt.patient_id == user.pk or user.role == 'doctor' and appt.slot.doctor_id == user.pk


class NoteForm(forms.ModelForm):
    expected_version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    class Meta:
        model = ClinicalNote
        fields = ['complaint', 'examination', 'assessment', 'plan', 'follow_up', 'correction_reason']
        widgets = {name: forms.Textarea(attrs={'rows': 3}) for name in ['complaint', 'examination', 'assessment', 'plan', 'follow_up']}


@roles('patient', 'doctor')
@require_http_methods(['GET', 'POST'])
def notes(request, pk):
    appt = get_object_or_404(Appointment.objects.select_related('slot'), pk=pk)
    if not clinical_access(request.user, appt):
        raise PermissionDenied
    latest = appt.notes.first()
    version = latest.version if latest else 0
    can_write = request.user.role == 'doctor' and appt.status in ('confirmed', 'completed') and appt.slot.start <= timezone.now()
    form = NoteForm(request.POST if request.method == 'POST' else None, initial={**({field: getattr(latest, field) for field in ['complaint', 'examination', 'assessment', 'plan', 'follow_up']} if latest else {}), 'expected_version': version})
    if request.method == 'POST':
        if not can_write:
            raise PermissionDenied
        if form.is_valid():
            with transaction.atomic():
                locked = Appointment.objects.select_for_update().get(pk=pk)
                current = locked.notes.first()
                if locked.status not in ('confirmed', 'completed'):
                    form.add_error(None, 'Appointment is no longer eligible.')
                elif form.cleaned_data['expected_version'] != (current.version if current else 0):
                    form.add_error(None, 'Another version was saved. Reload before making a correction.')
                elif current and not form.cleaned_data['correction_reason'].strip():
                    form.add_error('correction_reason', 'Explain the correction. Existing versions are preserved.')
                else:
                    note = form.save(commit=False)
                    note.appointment = locked
                    note.author = request.user
                    note.version = (current.version if current else 0) + 1
                    note.save()
                    audit(request.user, 'clinical_note.finalized', note.pk)
                    messages.success(request, 'Clinical note finalized. Corrections require a new version.')
                    return redirect('notes', pk=pk)
    audit(request.user, 'clinical_note.viewed', pk)
    return render(request, 'care/notes.html', {'appt': appt, 'notes': appt.notes.select_related('author'), 'form': form, 'can_write': can_write})


@roles('patient', 'doctor')
def timeline(request, patient_id):
    patient = get_object_or_404(User, pk=patient_id, role='patient')
    visits = Appointment.objects.filter(patient=patient).select_related('slot__doctor').prefetch_related('notes', 'reports', 'prescription__items__medicine')
    if request.user.role == 'patient':
        if request.user.pk != patient.pk:
            raise PermissionDenied
    else:
        # Only records from this doctor's own care episodes. No hospital-wide clinical access.
        visits = visits.filter(slot__doctor=request.user)
        if not visits.exists():
            raise PermissionDenied
    audit(request.user, 'medical_timeline.viewed', patient.pk)
    return render(request, 'care/timeline.html', {'patient': patient, 'visits': visits})


@transaction.atomic
def enqueue(appt):
    existing = QueueEntry.objects.filter(appointment=appt).first()
    if existing:
        return existing
    today = timezone.localdate()
    counter, _ = QueueCounter.objects.get_or_create(date=today)
    counter = QueueCounter.objects.select_for_update().get(pk=counter.pk)
    counter.number += 1
    counter.save(update_fields=['number'])
    return QueueEntry.objects.create(appointment=appt, date=today, number=counter.number)


@roles('receptionist', 'admin')
@require_http_methods(['GET', 'POST'])
def queue(request):
    if request.method == 'POST':
        with transaction.atomic():
            # Match cancellation/check-in lock order: appointment then queue entry.
            entry_id = request.POST.get('entry', '')
            if not entry_id.isdecimal() or len(entry_id) > 18:
                from django.http import Http404
                raise Http404
            entry = get_object_or_404(QueueEntry, pk=int(entry_id))
            appt = Appointment.objects.select_for_update().get(pk=entry.appointment_id)
            entry = QueueEntry.objects.select_for_update().get(pk=entry.pk)
            target = request.POST.get('status')
            transitions = {'waiting': {'called', 'cancelled'}, 'called': {'completed', 'cancelled'}}
            if target not in transitions.get(entry.status, set()) or appt.status == 'cancelled':
                messages.error(request, 'This queue transition is unavailable.')
            else:
                entry.status = target
                entry.save(update_fields=['status', 'updated'])
                audit(request.user, 'queue.'+target, entry.pk)
                messages.success(request, 'Queue updated.')
        return redirect('queue')
    return render(request, 'care/queue.html', {'entries': QueueEntry.objects.filter(date=timezone.localdate()).select_related('appointment__patient', 'appointment__slot__doctor')})


@roles('pharmacist', 'admin')
def movements(request):
    return render(request, 'care/movements.html', {'movements': StockMovement.objects.select_related('medicine', 'actor', 'prescription')[:200]})
