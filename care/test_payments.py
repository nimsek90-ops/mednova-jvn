import io
import tempfile
from datetime import timedelta
from unittest.mock import patch
from PIL import Image
from django import forms
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from . import tests as fixtures
from .models import Appointment, Hospital, Notification, Payment, PaymentProof
from .payments import send_proof_email, verify_payment
from .services import book, BookingError, change_status


def screenshot(name='receipt.png'):
    data = io.BytesIO()
    Image.new('RGB', (80, 120), 'white').save(data, format='PNG')
    return SimpleUploadedFile(name, data.getvalue(), content_type='image/png')


class PaymentVerificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)
        cls.appt.status = 'confirmed'
        cls.appt.save(update_fields=['status'])

    def setUp(self):
        self.files = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.files.name, EMAIL_HOST='', RAZORPAY_KEY_ID='', RAZORPAY_KEY_SECRET='')
        self.override.enable()
        self.addCleanup(self.files.cleanup)
        self.addCleanup(self.override.disable)
        self.client.force_login(self.patient)
        self.path = reverse('appointment_payment', args=[self.appt.pk])
        self.decision = reverse('payment_verification_detail', args=[self.appt.pk])

    def submit(self, **extra):
        return self.client.post(self.path, {'method': 'online', 'screenshot': screenshot(), **extra})

    def payment(self):
        return Payment.objects.get(appointment=self.appt)

    def test_video_upload_stays_unpaid_until_assigned_doctor_confirms(self):
        self.slot.start = timezone.now()
        self.slot.save(update_fields=['start'])
        room = reverse('video', args=[self.appt.pk])
        signal = reverse('signal', args=[self.appt.pk])
        self.assertEqual(self.client.get(room).status_code, 404)
        self.assertRedirects(self.submit(), self.path)
        payment = self.payment()
        self.assertEqual((payment.status, payment.method, payment.received_by_id), ('awaiting', 'online', None))
        self.assertEqual(self.client.get(room).status_code, 404)
        self.assertEqual(self.client.post(signal, {'kind': 'ready', 'payload': {}}, content_type='application/json').status_code, 404)
        self.assertEqual(self.client.post(room, {'action': 'consent', 'consent': 'on'}).status_code, 404)
        self.client.force_login(self.doctor)
        self.assertContains(self.client.get('/dashboard/'), 'Confirm / reject')
        self.assertRedirects(self.client.post(self.decision, {'action': 'confirm', 'version': payment.verification_version}), reverse('payment_verification'))
        payment = self.payment()
        self.assertEqual((payment.status, payment.received_by_id), ('paid', self.doctor.pk))
        self.assertIsNotNone(payment.verified_at)
        self.assertEqual(Appointment.objects.get(pk=self.appt.pk).status, 'confirmed')
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(room).status_code, 200)
        self.assertTrue(Notification.objects.filter(recipient=self.patient, message__startswith='Payment confirmed').exists())

    def test_offline_visit_can_submit_online_and_reception_verify(self):
        Appointment.objects.filter(pk=self.appt.pk).update(mode='in_person')
        self.assertEqual(self.submit().status_code, 302)
        payment = self.payment()
        self.client.force_login(self.reception)
        queue = self.client.get(reverse('payment_verification'))
        for value in [self.patient.name, self.doctor.name, '250.00', 'Online Payment', 'View payment screenshot']:
            self.assertContains(queue, value)
        self.client.post(self.decision, {'action': 'confirm', 'version': payment.verification_version})
        self.assertEqual(self.payment().status, 'paid')

    def test_offline_payment_no_screenshot_only_reception_can_confirm(self):
        Appointment.objects.filter(pk=self.appt.pk).update(mode='in_person')
        self.assertRedirects(self.client.post(self.path, {'method': 'offline'}), self.path)
        payment = self.payment()
        self.assertEqual((payment.status, payment.method), ('unpaid', 'offline'))
        self.assertFalse(PaymentProof.objects.exists())
        with self.assertRaises(forms.ValidationError):
            verify_payment(self.doctor, self.appt.pk, action='confirm', version=payment.verification_version)
        verify_payment(self.reception, self.appt.pk, action='confirm', version=payment.verification_version)
        self.assertEqual(self.payment().status, 'paid')

    def test_video_cannot_choose_offline_and_online_requires_image(self):
        for data in [{'method': 'offline'}, {'method': 'online'}]:
            response = self.client.post(self.path, data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(self.payment().status, 'unpaid')
        self.assertFalse(PaymentProof.objects.exists())

    def test_invalid_images_and_size_limits(self):
        for raw in [b'<svg><script>test</script></svg>', b'%PDF-not-an-image', b'not an image']:
            response = self.client.post(self.path, {'method': 'online', 'screenshot': SimpleUploadedFile('receipt.png', raw, content_type='image/png')})
            self.assertTrue(response.context['form'].errors)
        with override_settings(REPORT_MAX_BYTES=10):
            self.assertTrue(self.submit().context['form'].errors)
        self.assertFalse(PaymentProof.objects.exists())

    def test_payment_and_proof_identity_is_server_derived(self):
        self.submit(patient=self.other.pk, doctor=self.doctor2.pk, amount='1', status='paid')
        proof = PaymentProof.objects.get()
        self.assertEqual(proof.amount, self.appt.fee)
        self.assertEqual(proof.payment.appointment.patient_id, self.patient.pk)
        self.assertEqual(self.payment().status, 'awaiting')
        self.assertNotIn('receipt', proof.image.name)
        with proof.image.open('rb') as file:
            self.assertEqual(Image.open(file).format, 'PNG')

    def test_reject_notify_resubmit_and_stale_decision_denied(self):
        self.submit()
        payment = self.payment()
        with self.assertRaises(forms.ValidationError):
            verify_payment(self.doctor, self.appt.pk, action='reject', version=payment.verification_version)
        verify_payment(self.doctor, self.appt.pk, action='reject', version=payment.verification_version, reason='Transaction not found')
        self.assertContains(self.client.get(self.path), 'Transaction not found')
        self.assertTrue(Notification.objects.filter(recipient=self.patient, message__startswith='Payment rejected').exists())
        self.submit()
        self.assertEqual(PaymentProof.objects.count(), 2)
        self.assertEqual(self.payment().status, 'awaiting')
        with self.assertRaises(forms.ValidationError):
            verify_payment(self.reception, self.appt.pk, action='confirm', version=payment.verification_version)

    def test_duplicate_upload_and_confirmation_do_not_duplicate(self):
        self.submit()
        self.submit()
        self.assertEqual(PaymentProof.objects.count(), 1)
        payment = self.payment()
        verify_payment(self.reception, self.appt.pk, action='confirm', version=payment.verification_version)
        with self.assertRaises(forms.ValidationError):
            verify_payment(self.doctor, self.appt.pk, action='confirm', version=payment.verification_version)
        self.assertEqual(Notification.objects.filter(message__startswith='Payment confirmed').count(), 1)

    def test_ownership_roles_and_screenshot_access(self):
        self.submit()
        path = reverse('payment_screenshot', args=[PaymentProof.objects.get().pk])
        for user, expected in [(self.patient, 200), (self.doctor, 200), (self.reception, 200), (self.admin, 200), (self.other, 404), (self.doctor2, 404), (self.pharmacist, 403)]:
            self.client.force_login(user)
            response = self.client.get(path)
            self.assertEqual(response.status_code, expected)
            if expected == 200:
                self.assertIn('no-store', response['Cache-Control'])
                self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.path).status_code, 404)
        self.client.force_login(self.doctor2)
        self.assertEqual(self.client.get(self.decision).status_code, 404)
        for user in [self.patient, self.pharmacist, self.other]:
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.decision, {'action': 'confirm', 'version': 1}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(path).status_code, 302)

    def test_pending_cancelled_completed_cannot_submit_or_verify(self):
        for status in ['pending', 'cancelled', 'completed', 'no_show']:
            Appointment.objects.filter(pk=self.appt.pk).update(status=status)
            self.submit()
            self.assertFalse(PaymentProof.objects.exists())
            with self.assertRaises(forms.ValidationError):
                verify_payment(self.reception, self.appt.pk, action='confirm', version=0)

    def test_cancelled_after_upload_cannot_be_confirmed(self):
        self.submit()
        payment = self.payment()
        change_status(self.appt, self.doctor, 'cancelled')
        with self.assertRaises(forms.ValidationError):
            verify_payment(self.doctor, self.appt.pk, action='confirm', version=payment.verification_version)
        self.assertEqual(self.payment().status, 'awaiting')

    def test_video_payment_confirmed_still_requires_schedule_and_assigned_user(self):
        self.submit()
        verify_payment(self.doctor, self.appt.pk, action='confirm', version=self.payment().verification_version)
        room = reverse('video', args=[self.appt.pk])
        self.assertEqual(self.client.get(room).status_code, 404)  # Tomorrow, outside window.
        self.slot.start = timezone.now()
        self.slot.save()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(room).status_code, 404)

    @override_settings(EMAIL_HOST='synthetic', DEFAULT_FROM_EMAIL='hospital@example.test', EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_hospital_email_attachment_and_retry_idempotence(self):
        Hospital.objects.update(email='payments@example.test')
        with self.captureOnCommitCallbacks(execute=True):
            self.submit()
        proof = PaymentProof.objects.get()
        self.assertEqual(proof.email_status, 'sent')
        self.assertEqual(self.payment().status, 'awaiting')
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['payments@example.test'])
        self.assertEqual(message.attachments[0].mimetype, 'image/png')
        for value in [str(self.appt.pk), self.patient.name, self.doctor.name, '250.00', 'Video']:
            self.assertIn(value, message.body)
        self.assertNotIn(self.appt.reason, message.body)
        self.assertFalse(send_proof_email(proof.pk))
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_email_and_smtp_failure_preserve_unverified_proof(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.submit()
        proof = PaymentProof.objects.get()
        self.assertEqual(proof.email_status, 'unavailable')
        Hospital.objects.update(email='payments@example.test')
        with override_settings(EMAIL_HOST='synthetic', DEFAULT_FROM_EMAIL='hospital@example.test'):
            with patch('care.payments.EmailMessage.send', side_effect=OSError('test failure')):
                self.assertFalse(send_proof_email(proof.pk))
            proof.refresh_from_db()
            self.assertEqual(proof.email_status, 'failed')
            with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
                self.assertTrue(send_proof_email(proof.pk))
        self.assertEqual(self.payment().status, 'awaiting')

    def test_csrf_and_legacy_payment_path_cannot_bypass(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.reception)
        self.assertEqual(client.post(self.decision, {'action': 'confirm', 'version': 0}).status_code, 403)
        self.client.force_login(self.reception)
        self.client.post(reverse('payment_record', args=[self.appt.pk]), {'method': 'cash', 'reference': 'test'})
        self.assertEqual(self.payment().status, 'unpaid')

    def test_reschedule_during_verification_blocked(self):
        self.submit()
        with self.assertRaises(BookingError):
            book(self.patient, self.slot2.pk, 'video', 'Synthetic reschedule', self.appt)

    def test_gateway_capture_still_needs_staff_for_video(self):
        Payment.objects.filter(appointment=self.appt).update(status='paid', method='razorpay', provider_id='pay_synthetic')
        self.slot.start = timezone.now()
        self.slot.save()
        room = reverse('video', args=[self.appt.pk])
        self.assertEqual(self.client.get(room).status_code, 404)
        verify_payment(self.doctor, self.appt.pk, action='confirm', version=0)
        self.assertEqual(self.client.get(room).status_code, 200)

    def test_cash_paid_visit_cannot_be_rescheduled_into_video(self):
        Appointment.objects.filter(pk=self.appt.pk).update(mode='in_person')
        Payment.objects.filter(appointment=self.appt).update(status='paid', method='offline', received_by=self.reception)
        with self.assertRaises(BookingError):
            book(self.patient, self.slot2.pk, 'video', 'Synthetic mode change', self.appt)

    def test_status_refreshes_do_not_consume_submission_limit(self):
        for _ in range(18):
            self.assertEqual(self.client.get(self.path).status_code, 200)
        self.assertEqual(self.submit().status_code, 302)
        for _ in range(14):
            self.client.post(self.path, {'method': 'online'})
        self.assertEqual(self.client.post(self.path, {'method': 'online'}).status_code, 429)
