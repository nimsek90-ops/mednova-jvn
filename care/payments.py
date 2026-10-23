"""Manual payment proof and staff verification using existing payment records."""
import io
from datetime import timedelta
from PIL import Image, UnidentifiedImageError
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .delivery import publish
from .http import paged
from .models import Appointment, Hospital, Payment, PaymentProof, User
from .security import audit, roles, limited

PAYMENT_NUMBER = '9373084858'


class PaymentForm(forms.Form):
    method = forms.ChoiceField(choices=[('online', 'Online Payment'), ('offline', 'Offline Payment at Reception')])
    screenshot = forms.FileField(required=False, label='Payment screenshot (PNG or JPEG)', widget=forms.ClearableFileInput(attrs={'accept': 'image/png,image/jpeg'}))

    def __init__(self, *args, appointment, **kwargs):
        super().__init__(*args, **kwargs)
        if appointment.mode == 'video':
            self.fields['method'].choices = [('online', 'Online Payment')]
            self.fields['method'].initial = 'online'
        self.fields['screenshot'].help_text = f'Online payment requires a screenshot, up to {settings.REPORT_MAX_BYTES // (1024 * 1024)} MB. Uploading does not confirm payment.'

    def clean_screenshot(self):
        upload = self.cleaned_data.get('screenshot')
        if not upload:
            return None
        if upload.size > settings.REPORT_MAX_BYTES:
            raise forms.ValidationError('The screenshot exceeds the upload size limit.')
        try:
            with Image.open(io.BytesIO(upload.read())) as image:
                if image.format not in ('PNG', 'JPEG') or image.width * image.height > 20000000:
                    raise ValueError()
                image.load()
                output = io.BytesIO()
                image.convert('RGB').save(output, format='PNG')
                if output.tell() > settings.REPORT_MAX_BYTES:
                    raise ValueError()
                return ContentFile(output.getvalue(), name='payment.png')
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise forms.ValidationError('Upload a valid PNG or JPEG screenshot within the size limit.')

    def clean(self):
        data = super().clean()
        if data.get('method') == 'online' and not data.get('screenshot') and 'screenshot' not in self.errors:
            self.add_error('screenshot', 'Upload your payment screenshot for staff verification.')
        if data.get('method') == 'offline' and data.get('screenshot'):
            self.add_error('screenshot', 'Choose online payment to submit a screenshot, or leave this empty for reception payment.')
        return data


def eligible(payment):
    return payment.appointment.status == 'confirmed' and payment.amount > 0


@transaction.atomic
def verify_payment(actor, appointment_id, *, action, version, reason=''):
    actor = User.objects.get(pk=actor.pk)
    appt = get_object_or_404(Appointment.objects.select_for_update(), pk=appointment_id)
    doctor_id = appt.slot.doctor_id
    if not actor.is_active or actor.approval != 'approved' or not (
        actor.role in ('receptionist', 'admin') or (actor.role == 'doctor' and actor.pk == doctor_id)
    ):
        raise forms.ValidationError('You cannot verify this payment.')
    payment = Payment.objects.select_for_update().get(appointment=appt)
    if not eligible(payment) or payment.verification_version != version or action not in ('confirm', 'reject'):
        raise forms.ValidationError('This payment changed or is no longer eligible. Reload before reviewing it.')
    captured_gateway = payment.method == 'razorpay' and payment.status == 'paid' and payment.received_by_id is None and payment.provider_id
    if captured_gateway and action == 'reject':
        raise forms.ValidationError('This gateway payment was captured. Use the existing refund process if a refund is needed.')
    online = (payment.method == 'online' and payment.status == 'awaiting' and payment.current_proof_id) or captured_gateway
    offline = payment.method == 'offline' and payment.status == 'unpaid' and appt.mode == 'in_person' and actor.role in ('receptionist', 'admin')
    if not (online or offline):
        raise forms.ValidationError('No eligible payment is waiting for your verification.')
    if action == 'reject' and (not reason.strip() or len(reason) > 300):
        raise forms.ValidationError('Enter a rejection reason of up to 300 characters.')
    payment.status = 'paid' if action == 'confirm' else 'rejected'
    payment.received_by = actor
    payment.verified_at = timezone.now()
    payment.rejection_reason = reason.strip() if action == 'reject' else ''
    payment.verification_version += 1
    payment.save()
    publish(appt.patient, 'Payment confirmed. Review your appointment details.' if action == 'confirm' else 'Payment rejected. Open your appointment to review the reason and next steps.',
            f'payment:{payment.pk}:{payment.verification_version}', appt)
    audit(actor, 'payment.confirmed' if action == 'confirm' else 'payment.rejected', payment.pk)
    # Confirmation remains confirmed: billing never reopens a cancelled/completed visit.
    return payment


def submit_payment(patient, appointment_id, form):
    saved_file = None
    try:
        with transaction.atomic():
            appt = get_object_or_404(Appointment.objects.select_for_update(), pk=appointment_id, patient=patient)
            payment = Payment.objects.select_for_update().get(appointment=appt)
            if not eligible(payment) or payment.status not in ('unpaid', 'rejected'):
                raise forms.ValidationError('This payment is already submitted or no longer eligible.')
            method = form.cleaned_data['method']
            if appt.mode == 'video' and method != 'online':
                raise forms.ValidationError('Video appointments require online payment.')
            payment.method = method
            payment.status = 'awaiting' if method == 'online' else 'unpaid'
            payment.received_by = None
            payment.verified_at = None
            payment.rejection_reason = ''
            payment.current_proof = None
            payment.order_id = ''
            payment.verification_version += 1
            if method == 'online':
                proof = PaymentProof(payment=payment, amount=payment.amount)
                proof.image.save('payment.png', form.cleaned_data['screenshot'], save=False)
                saved_file = proof.image
                proof.save()
                payment.current_proof = proof
                transaction.on_commit(lambda: send_proof_email(proof.pk), robust=True)
            payment.save()
            audit(patient, 'payment.proof_submitted' if method == 'online' else 'payment.reception_selected', payment.pk)
            return payment
    except Exception:
        if saved_file:
            saved_file.delete(save=False)
        raise


def send_proof_email(proof_id):
    """Retryable delivery. SMTP success does not change payment verification status."""
    now = timezone.now()
    with transaction.atomic():
        proof = PaymentProof.objects.select_for_update().get(pk=proof_id)
        if proof.email_status == 'sent' or (proof.email_lease_until and proof.email_lease_until > now):
            return False
        hospital = Hospital.objects.first()
        if not hospital or not hospital.email or not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:
            proof.email_status = 'unavailable'
            proof.save(update_fields=['email_status'])
            return False
        recipient = hospital.email
        proof.email_status = 'sending'
        proof.email_attempts += 1
        proof.email_lease_until = now + timedelta(minutes=5)
        proof.save(update_fields=['email_status', 'email_attempts', 'email_lease_until'])
    try:
        appt = proof.payment.appointment
        body = (f'Payment proof submitted for staff review. A screenshot is not confirmation of payment.\n'
                f'Submission: {proof.pk}\nSubmitted: {proof.submitted_at.isoformat()}\n'
                f'Appointment: {appt.pk}\nPatient: {appt.patient.name}\nDoctor: {appt.slot.doctor.name}\n'
                f'Type: {appt.get_mode_display()}\nAppointment time: {timezone.localtime(appt.slot.start).isoformat()}\n'
                f'Amount due: INR {proof.amount}\nMethod: Online Payment\n'
                'Sign in to the hospital payment verification queue to compare the transaction against actual received funds.')
        message = EmailMessage('MedNova payment proof: ' + appt.short_id, body, settings.DEFAULT_FROM_EMAIL, [recipient])
        with proof.image.open('rb') as image:
            message.attach('payment-proof.png', image.read(), 'image/png')
        if message.send(fail_silently=False) != 1:
            raise OSError('Email not accepted')
    except Exception:
        PaymentProof.objects.filter(pk=proof_id).update(email_status='failed', email_lease_until=None)
        return False
    PaymentProof.objects.filter(pk=proof_id).update(email_status='sent', emailed_at=timezone.now(), email_lease_until=None)
    return True


def retry_proof_emails(limit=2):
    ids = list(PaymentProof.objects.exclude(email_status='sent').order_by('email_attempts', 'submitted_at').values_list('pk', flat=True)[:limit])
    return sum(send_proof_email(pk) for pk in ids)


def staff_payments(user):
    qs = Payment.objects.select_related('appointment__patient', 'appointment__slot__doctor', 'current_proof', 'received_by')
    if user.role == 'doctor':
        return qs.filter(appointment__slot__doctor=user)
    return qs if user.role in ('receptionist', 'admin') else qs.none()


def verification_queue(user):
    payments = staff_payments(user).filter(appointment__status='confirmed').filter(Q(status='awaiting') | Q(status='unpaid', method='offline') | Q(status='paid', method='razorpay', received_by__isnull=True)).order_by('updated', 'pk')
    return payments.filter(method__in=['online', 'razorpay']) if user.role == 'doctor' else payments


@roles('patient')
@require_http_methods(['GET', 'POST'])
def instructions(request, pk):
    if request.method == 'POST' and limited(f'payment-proof-submit:{request.user.pk}', 15, 600):
        response = HttpResponse('Too many payment submissions. Please try again later.', status=429)
        response['Retry-After'] = '600'
        return response
    appt = get_object_or_404(Appointment.objects.select_related('slot__doctor', 'payment__current_proof'), pk=pk, patient=request.user)
    payment = appt.payment
    form = PaymentForm(request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None,
                       appointment=appt, initial={'method': payment.method or 'online'})
    can_submit = eligible(payment) and payment.status in ('unpaid', 'rejected')
    if request.method == 'POST':
        if not can_submit:
            form.add_error(None, 'This payment is already submitted or no longer eligible.')
        elif form.is_valid():
            try:
                submit_payment(request.user, pk, form)
            except forms.ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, 'Payment instructions saved. Staff must confirm receipt before payment is confirmed.')
                return redirect('appointment_payment', pk=pk)
    return render(request, 'care/payment_instructions.html', {'appt': appt, 'payment': payment, 'form': form, 'can_submit': can_submit, 'payment_number': PAYMENT_NUMBER})


@roles('receptionist', 'doctor', 'admin')
@require_http_methods(['GET', 'POST'])
def verification(request, pk=None):
    if pk:
        payment = get_object_or_404(staff_payments(request.user), appointment_id=pk)
        error = ''
        if request.method == 'POST':
            try:
                version = int(request.POST.get('version', ''))
                verify_payment(request.user, pk, action=request.POST.get('action'), version=version, reason=request.POST.get('reason', ''))
            except (ValueError, forms.ValidationError) as exc:
                error = '; '.join(exc.messages) if isinstance(exc, forms.ValidationError) else 'Reload the payment before verifying it.'
                payment.refresh_from_db()
            else:
                messages.success(request, 'Payment decision saved and patient notified.')
                return redirect('payment_verification')
        return render(request, 'care/payment_verification_detail.html', {'payment': payment, 'error': error})
    if request.method == 'POST':
        raise Http404()
    payments = verification_queue(request.user)
    return render(request, 'care/payment_verification.html', {'payments': paged(request, payments), 'pagination': paged(request, payments)})


@roles('patient', 'receptionist', 'doctor', 'admin')
@require_http_methods(['GET'])
def screenshot(request, pk):
    proof = get_object_or_404(PaymentProof.objects.select_related('payment__appointment__slot'), pk=pk)
    appt = proof.payment.appointment
    user = request.user
    if not (user.role in ('receptionist', 'admin') or (user.role == 'patient' and appt.patient_id == user.pk) or (user.role == 'doctor' and appt.slot.doctor_id == user.pk)):
        raise Http404()
    try:
        response = FileResponse(proof.image.open('rb'), content_type='image/png', filename='payment-proof.png')
    except OSError:
        raise Http404('Payment screenshot is unavailable. Contact the hospital.')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
