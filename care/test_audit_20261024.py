"""Reproducible storage outage checks; no external provider or hospital data."""
from unittest.mock import patch
from botocore.exceptions import EndpointConnectionError
from django.test import TestCase, override_settings
from django.urls import reverse
from . import tests as fixtures
from .models import Appointment, Payment, PaymentProof, Report
from .test_payments import screenshot


class AuditStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)
        Appointment.objects.filter(pk=cls.appt.pk).update(status='confirmed')

    def setUp(self):
        self.client.force_login(self.patient)
        self.client.raise_request_exception = False

    def test_payment_upload_storage_outage_preserves_pending_payment(self):
        with patch('django.db.models.fields.files.FieldFile.save', side_effect=EndpointConnectionError(endpoint_url='https://storage.example.test')):
            response = self.client.post(reverse('appointment_payment', args=[self.appt.pk]), {'method': 'online', 'screenshot': screenshot()})
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'storage is temporarily unavailable', status_code=503)
        self.assertFalse(PaymentProof.objects.exists())
        self.assertEqual(Payment.objects.get(appointment=self.appt).status, 'unpaid')

    def test_payment_screenshot_storage_outage_is_retryable(self):
        proof = PaymentProof.objects.create(payment=self.appt.payment, image='synthetic.png', amount=self.appt.fee)
        with patch('django.db.models.fields.files.FieldFile.open', side_effect=EndpointConnectionError(endpoint_url='https://storage.example.test')):
            response = self.client.get(reverse('payment_screenshot', args=[proof.pk]))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '60')
        self.assertNotContains(response, 'storage.example.test', status_code=503)

    def test_invalid_storage_endpoint_does_not_crash_payment_submission(self):
        with patch('django.db.models.fields.files.FieldFile.save', side_effect=ValueError('Invalid endpoint: private-provider-setting')):
            response = self.client.post(reverse('appointment_payment', args=[self.appt.pk]), {'method': 'online', 'screenshot': screenshot()})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '60')
        self.assertNotContains(response, 'private-provider-setting', status_code=503)
        self.assertFalse(PaymentProof.objects.exists())
        self.assertEqual(Payment.objects.get(appointment=self.appt).status, 'unpaid')

    def test_invalid_storage_endpoint_does_not_crash_report_submission(self):
        with patch('django.db.models.fields.files.FieldFile.save', side_effect=ValueError('Invalid endpoint: private-provider-setting')):
            response = self.client.post(reverse('upload', args=[self.appt.pk]), {'title': 'Synthetic report', 'file': screenshot()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report storage is unavailable')
        self.assertNotContains(response, 'private-provider-setting')
        self.assertFalse(Report.objects.exists())

    def test_report_storage_outage_is_retryable(self):
        report = Report.objects.create(appointment=self.appt, uploaded_by=self.patient, title='Synthetic report', extension='.png', file='synthetic.png')
        with patch('django.db.models.fields.files.FieldFile.open', side_effect=OSError('synthetic unavailable')):
            response = self.client.get(reverse('download', args=[report.pk]))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '60')

    @override_settings(PRIVATE_STORAGE_BACKEND='s3')
    def test_report_signed_url_failure_is_retryable(self):
        report = Report.objects.create(appointment=self.appt, uploaded_by=self.patient, title='Synthetic report', extension='.png', file='synthetic.png')
        storage = Report._meta.get_field('file').storage
        with patch.object(storage, 'url', side_effect=EndpointConnectionError(endpoint_url='https://storage.example.test')):
            response = self.client.get(reverse('download', args=[report.pk]))
        self.assertEqual(response.status_code, 503)

    def test_private_download_authorization_precedes_storage(self):
        proof = PaymentProof.objects.create(payment=self.appt.payment, image='synthetic.png', amount=self.appt.fee)
        self.client.force_login(self.other)
        with patch('django.db.models.fields.files.FieldFile.open') as opened:
            self.assertEqual(self.client.get(reverse('payment_screenshot', args=[proof.pk])).status_code, 404)
            opened.assert_not_called()


class AuditNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)

    def test_head_probes_preserve_readiness_and_do_not_return_bodies(self):
        for path in ('/', '/health/'):
            response = self.client.head(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b'')
            self.assertEqual(self.client.post(path).status_code, 405)
        from django.db import DatabaseError
        with patch('django.db.connection.cursor', side_effect=DatabaseError('private connection detail')):
            response = self.client.head('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.content, b'')

    def test_booking_links_match_role_permissions(self):
        for user in [self.doctor, self.admin, self.pharmacist]:
            self.client.force_login(user)
            for path in [reverse('doctors'), reverse('doctor_detail', args=[self.doctor.pk])]:
                self.assertNotContains(self.client.get(path), 'href="/book/')
        for user in [self.patient, self.reception]:
            self.client.force_login(user)
            self.assertContains(self.client.get(reverse('doctors')), f'href="/book/{self.doctor.pk}/')

    def test_pharmacist_directory_does_not_link_to_forbidden_appointments(self):
        self.client.force_login(self.pharmacist)
        self.assertNotContains(self.client.get(reverse('doctors')), 'href="/appointments/"')
