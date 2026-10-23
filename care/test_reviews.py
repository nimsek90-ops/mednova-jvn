from datetime import timedelta
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from . import tests as fixtures
from .models import Appointment, AppointmentReview
from .reviews import save_review


class ReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)
        cls.appt.status = 'completed'
        cls.appt.save(update_fields=['status'])
        cls.slot.start = timezone.now() - timedelta(days=1)
        cls.slot.save(update_fields=['start'])

    def setUp(self):
        self.client.force_login(self.patient)
        self.url = reverse('appointment_review', args=[self.appt.pk])

    def test_rating_only_submission_and_public_retrieval(self):
        response = self.client.post(self.url, {'rating': '5'})
        self.assertRedirects(response, reverse('appointment', args=[self.appt.pk]))
        review = AppointmentReview.objects.get()
        self.assertEqual((review.rating, review.comment, review.patient_id, review.doctor_id, review.appointment_id),
                         (5, '', self.patient.pk, self.doctor.pk, self.appt.pk))
        self.assertIsNotNone(review.submitted_at)
        public = Client().get(reverse('doctor_detail', args=[self.doctor.pk]))
        self.assertContains(public, '5.0 / 5')
        self.assertContains(public, 'Verified patient')
        self.assertNotContains(public, self.patient.email)
        self.assertNotContains(public, self.appt.reason)
        self.assertNotContains(public, str(self.appt.pk))

    def test_edit_and_repeated_submission_keep_one_review_and_submission_date(self):
        self.client.post(self.url, {'rating': 2, 'comment': 'First feedback'})
        original = AppointmentReview.objects.get()
        response = self.client.get(self.url)
        self.assertContains(response, 'First feedback')
        self.assertContains(response, 'value="2"')
        self.client.post(self.url, {'rating': 4, 'comment': 'Updated feedback'})
        self.client.post(self.url, {'rating': 4, 'comment': ''})
        review = AppointmentReview.objects.get()
        self.assertEqual(review.pk, original.pk)
        self.assertEqual(review.submitted_at, original.submitted_at)
        self.assertEqual((review.rating, review.comment), (4, ''))
        self.assertGreaterEqual(review.updated_at, original.updated_at)
        self.assertContains(self.client.get(reverse('appointment', args=[self.appt.pk])), 'Edit your review')

    def test_invalid_ratings_and_long_comments_are_rejected(self):
        for rating in ['', '0', '6', '-1', '2.5', 'five']:
            response = self.client.post(self.url, {'rating': rating})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.client.post(self.url, {'rating': 3, 'comment': 'x' * 2001})
        self.assertFalse(AppointmentReview.objects.exists())

    def test_only_owner_patient_can_submit(self):
        for user, status in [(self.other, 404), (self.doctor, 403), (self.reception, 403), (self.admin, 403), (self.pharmacist, 403)]:
            self.client.force_login(user)
            for method in [self.client.get, self.client.post]:
                self.assertEqual(method(self.url, {'rating': 5}).status_code, status)
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {'rating': 5}).status_code, 302)
        self.assertFalse(AppointmentReview.objects.exists())

    def test_non_completed_appointments_do_not_offer_or_accept_reviews(self):
        for status in ['pending', 'confirmed', 'cancelled', 'no_show']:
            Appointment.objects.filter(pk=self.appt.pk).update(status=status)
            self.assertEqual(self.client.post(self.url, {'rating': 5}).status_code, 403)
            self.assertNotContains(self.client.get(reverse('appointment', args=[self.appt.pk])), 'Rate your appointment')
        self.assertFalse(AppointmentReview.objects.exists())

    def test_completed_appointment_offers_review_and_five_required_stars(self):
        self.assertContains(self.client.get(reverse('appointment', args=[self.appt.pk])), 'Rate your appointment')
        response = self.client.get(self.url)
        self.assertContains(response, 'type="radio"', count=5)
        self.assertContains(response, 'Additional feedback (optional)')
        self.assertNotIn('required', response.context['form']['comment'].as_widget())

    def test_identity_spoofing_ignored_and_comments_escaped(self):
        comment = '<script>alert("test")</script>'
        self.client.post(self.url, {'rating': 3, 'comment': comment, 'patient': self.other.pk,
                                   'doctor': self.doctor2.pk, 'appointment': 'invalid'})
        review = AppointmentReview.objects.get()
        self.assertEqual((review.patient_id, review.doctor_id), (self.patient.pk, self.doctor.pk))
        public = Client().get(reverse('doctor_detail', args=[self.doctor.pk]))
        self.assertContains(public, '&lt;script&gt;')
        self.assertNotContains(public, comment)
        self.assertNotContains(Client().get(reverse('doctor_detail', args=[self.doctor2.pk])), '&lt;script&gt;')

    def test_database_enforces_unique_appointment_and_rating_range(self):
        review = save_review(self.patient, self.appt.pk, rating=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AppointmentReview.objects.create(appointment=self.appt, patient=self.patient, doctor=self.doctor, rating=5)
        for rating in [0, 6]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                AppointmentReview.objects.filter(pk=review.pk).update(rating=rating)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.patient)
        self.assertEqual(client.post(self.url, {'rating': 5}).status_code, 403)
        self.assertFalse(AppointmentReview.objects.exists())
