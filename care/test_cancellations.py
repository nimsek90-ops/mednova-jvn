from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from . import tests as fixtures
from .models import Appointment, AppointmentCancellation, Slot, Notification
from .services import change_status, book, BookingError

class DoctorCancellationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)
        cls.appt.status='confirmed'
        cls.appt.save(update_fields=['status'])

    def cancel(self):
        change_status(self.appt,self.doctor,'cancelled',reason='Unavailable due to an emergency')

    def test_reason_required_and_transaction_preserves_visit(self):
        for reason in ['', '   ', 'abc', 'x'*301, None]:
            with self.assertRaises(BookingError):
                change_status(self.appt,self.doctor,'cancelled',reason=reason)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status,'confirmed')
        self.assertFalse(AppointmentCancellation.objects.exists())

    def test_snapshot_notification_and_repeated_click(self):
        self.cancel()
        event=AppointmentCancellation.objects.get()
        self.assertEqual((event.patient_id,event.doctor_id,event.cancelled_by_id,event.original_start),
                         (self.patient.pk,self.doctor.pk,self.doctor.pk,self.slot.start))
        self.assertEqual(event.kind,'cancelled_by_doctor')
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.active)
        self.assertFalse(self.slot.booked)
        notices=Notification.objects.filter(recipient=self.patient,message__contains='cancelled by the doctor')
        self.assertEqual(notices.count(),1)
        self.assertIn(event.reason,notices.get().message)
        with self.assertRaises(BookingError):self.cancel()
        self.assertEqual(AppointmentCancellation.objects.count(),1)
        self.assertEqual(notices.count(),1)

    def test_alternatives_are_owned_and_do_not_reopen_original(self):
        self.cancel()
        future=Slot.objects.create(doctor=self.doctor,start=timezone.now()+timedelta(days=3),consultation_type='video')
        self.client.force_login(self.patient)
        path=reverse('cancellation_alternatives',args=[self.appt.pk])
        response=self.client.get(path)
        self.assertEqual(response.status_code,200)
        self.assertIn(future,list(response.context['same_slots']))
        self.assertNotIn(self.slot,list(response.context['same_slots']))
        new=book(self.patient,future.pk,'video','Follow-up appointment')
        self.appt.refresh_from_db()
        self.assertNotEqual(new.pk,self.appt.pk)
        self.assertEqual(self.appt.status,'cancelled')
        self.assertTrue(AppointmentCancellation.objects.filter(appointment=self.appt).exists())
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(path).status_code,404)
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(path).status_code,403)

    def test_doctor_sees_patient_as_main_appointment_identity(self):
        self.client.force_login(self.doctor)
        response=self.client.get(reverse('appointment',args=[self.appt.pk]))
        self.assertContains(response,'<h2>'+self.patient.name+'</h2>',html=True)
        self.assertContains(response,'data-cancel-dialog')
        self.assertNotContains(response,'HEALTH &amp; WELLBEING')
        self.assertNotContains(response,'href="/wellness/"')
        self.client.force_login(self.patient)
        self.assertContains(self.client.get(reverse('appointment',args=[self.appt.pk])), '<h2>'+self.doctor.name+'</h2>',html=True)

    def test_other_doctor_cannot_cancel(self):
        with self.assertRaises(BookingError):
            change_status(self.appt,self.doctor2,'cancelled',reason='Unavailable due to emergency')
        self.assertFalse(AppointmentCancellation.objects.exists())

    def test_read_only_refresh_does_not_rewrite_session_every_request(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        self.client.force_login(self.patient)
        self.client.get('/health/')  # First activity refresh establishes the rolling window.
        with CaptureQueriesContext(connection) as queries:
            for _ in range(3):
                self.assertEqual(self.client.get('/health/').status_code,200)
        writes=[q['sql'] for q in queries if q['sql'].lstrip().upper().startswith('UPDATE') and 'django_session' in q['sql']]
        self.assertEqual(writes,[])

    def test_long_reason_and_doctor_name_persist_in_patient_notification(self):
        self.doctor.name='D'*self.doctor._meta.get_field('name').max_length
        self.doctor.save(update_fields=['name'])
        reason='Unavailable: '+('x'*280)
        change_status(self.appt,self.doctor,'cancelled',reason=reason)
        notice=Notification.objects.get(recipient=self.patient,message__contains='cancelled by the doctor')
        self.assertIn(reason,notice.message)
        self.assertGreater(len(notice.message),200)
        self.assertEqual(AppointmentCancellation.objects.get().reason,reason)
