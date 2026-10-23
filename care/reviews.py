"""Verified appointment reviews, with identity derived exclusively on the server."""
from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .models import Appointment, AppointmentReview
from .security import audit, roles


class ReviewForm(forms.Form):
    rating = forms.TypedChoiceField(choices=[(n, f'{n} star' if n == 1 else f'{n} stars') for n in range(1, 6)], coerce=int, widget=forms.RadioSelect)
    comment = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={'rows': 5, 'maxlength': 2000}), label='Additional feedback (optional)')


@transaction.atomic
def save_review(patient, appointment_id, *, rating, comment=''):
    appointment = get_object_or_404(Appointment.objects.select_for_update(), pk=appointment_id, patient=patient)
    if appointment.status != 'completed':
        raise forms.ValidationError('Reviews are available after your appointment is completed.')
    form = ReviewForm({'rating': rating, 'comment': comment})
    if not form.is_valid():
        raise forms.ValidationError('Choose a rating from 1 to 5 and keep feedback within 2,000 characters.')
    review, created = AppointmentReview.objects.update_or_create(
        appointment=appointment,
        defaults={'patient': patient, 'doctor_id': appointment.slot.doctor_id, **form.cleaned_data},
    )
    audit(patient, 'review_created' if created else 'review_updated', review.pk)
    return review


@roles('patient')
@require_http_methods(['GET', 'POST'])
def edit(request, pk):
    appointment = get_object_or_404(Appointment.objects.select_related('slot__doctor'), pk=pk, patient=request.user)
    if appointment.status != 'completed':
        return HttpResponseForbidden('Reviews are available after your appointment is completed.')
    review = AppointmentReview.objects.filter(appointment=appointment).first()
    form = ReviewForm(request.POST if request.method == 'POST' else None,
                      initial={'rating': review.rating, 'comment': review.comment} if review else None)
    if request.method == 'POST' and form.is_valid():
        try:
            save_review(request.user, pk, **form.cleaned_data)
        except forms.ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Your review has been saved. Thank you for your feedback.')
            return redirect('appointment', pk=pk)
    return render(request, 'care/review_form.html', {'appt': appointment, 'form': form, 'review': review})
