"""Explicit MySQL acceptance suite: manage.py test care.mysql_acceptance.

Requires MEDNOVA_TEST_MYSQL=1 and a dedicated disposable MYSQL_DATABASE.
Django creates test_<database>; never point this at production credentials.
Not included in SQLite discovery because SQLite cannot verify row locking.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from .tests import Workflows
from .models import User, Slot, Appointment
from .services import book, change_status, BookingError


class MySQLBookingAcceptance(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "mysql":
            self.fail("This acceptance suite requires a dedicated MySQL test database.")
        Workflows.setUpTestData()

    def race(self, functions):
        barrier = Barrier(len(functions))

        def run(fn):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                fn()
                return "ok"
            except BookingError:
                return "unavailable"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(functions)) as executor:
            return list(executor.map(run, functions))

    def test_simultaneous_same_slot_has_one_winner(self):
        slot_id = Workflows.slot2.pk
        patients = [Workflows.patient.pk, Workflows.other.pk]
        results = self.race([
            lambda pk=pk: book(User.objects.get(pk=pk), slot_id, "in_person", "Synthetic concurrency test")
            for pk in patients
        ])
        self.assertCountEqual(results, ["ok", "unavailable"])
        self.assertEqual(Appointment.objects.filter(slot_id=slot_id).exclude(status="cancelled").count(), 1)
        self.assertTrue(Slot.objects.get(pk=slot_id).booked)

    def test_cancellation_racing_reschedule_keeps_slot_flags_consistent(self):
        patient_id, appointment_id, slot_id = Workflows.patient.pk, Workflows.appt.pk, Workflows.slot2.pk
        self.race([
            lambda: book(User.objects.get(pk=patient_id), slot_id, "video", "Synthetic reschedule", Appointment.objects.get(pk=appointment_id)),
            lambda: change_status(Appointment.objects.get(pk=appointment_id), User.objects.get(pk=patient_id), "cancelled"),
        ])
        appt = Appointment.objects.get(pk=appointment_id)
        self.assertEqual(appt.status, "cancelled")
        for slot in Slot.objects.filter(pk__in=[Workflows.slot.pk, slot_id]):
            self.assertEqual(slot.booked, Appointment.objects.filter(slot=slot).exclude(status="cancelled").exists())

    def test_simultaneous_dispense_has_one_deduction(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Medicine, Prescription, PrescriptionItem, StockMovement
        from .services import dispense
        medicine = Medicine.objects.create(name='Synthetic concurrency item',batch='QA',expiry=timezone.localdate()+timedelta(days=30),stock=10,price=1)
        rx = Prescription.objects.create(appointment=Workflows.appt,instructions='Synthetic')
        PrescriptionItem.objects.create(prescription=rx,medicine=medicine,dose='Synthetic',quantity=2)
        result = self.race([lambda: dispense(Prescription.objects.get(pk=rx.pk),User.objects.get(pk=Workflows.pharmacist.pk)) for _ in range(2)])
        self.assertCountEqual(result,['ok','unavailable'])
        medicine.refresh_from_db()
        self.assertEqual(medicine.stock,8)
        self.assertEqual(StockMovement.objects.filter(prescription=rx).count(),1)

    def test_simultaneous_daily_queue_tokens_are_unique(self):
        from .product import enqueue
        from .models import QueueEntry
        second = book(Workflows.other,Workflows.slot2.pk,'in_person','Synthetic queue test')
        def add(pk):
            from django.db import transaction
            with transaction.atomic():
                appt = Appointment.objects.select_for_update().get(pk=pk)
                enqueue(appt)
        result=self.race([lambda: add(Workflows.appt.pk),lambda: add(second.pk)])
        self.assertEqual(result,['ok','ok'])
        self.assertEqual(set(QueueEntry.objects.values_list('number',flat=True)),{1,2})
