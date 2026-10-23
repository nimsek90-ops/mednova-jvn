"""Explicit MySQL acceptance suite: manage.py test care.mysql_acceptance.

Requires MEDNOVA_TEST_MYSQL=1 and a dedicated disposable MYSQL_DATABASE.
Django creates test_<database>; never point this at production credentials.
Not included in SQLite discovery because SQLite cannot verify row locking.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from . import tests as fixtures
from .models import User, Slot, Appointment
from .services import book, change_status, BookingError


class MySQLBookingAcceptance(TransactionTestCase):
    def test_simultaneous_support_retries_create_one_case(self):
        import uuid
        from django.test import Client
        from django.urls import reverse
        from .models import SupportCase
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(fixtures.Workflows.patient)
        payload = {'category':'technical','summary':'Synthetic concurrent support submission',
                   'consent':'on','request_key':str(uuid.uuid4())}
        def submit(client):
            response = client.post(reverse('support_create'), payload)
            self.assertEqual(response.status_code, 302)
        self.assertEqual(self.race([lambda c=c:submit(c) for c in clients]), ['ok','ok'])
        self.assertEqual(SupportCase.objects.count(), 1)

    def test_concurrent_review_submissions_update_one_appointment_review(self):
        from .models import AppointmentReview
        from .reviews import save_review
        appointment = fixtures.Workflows.appt
        Appointment.objects.filter(pk=appointment.pk).update(status='completed')
        patient_id = fixtures.Workflows.patient.pk
        results = self.race([
            lambda rating=rating: save_review(User.objects.get(pk=patient_id), appointment.pk, rating=rating)
            for rating in [4, 5]
        ])
        self.assertEqual(results, ['ok', 'ok'])
        self.assertEqual(AppointmentReview.objects.filter(appointment=appointment).count(), 1)

    def setUp(self):
        if connection.vendor != "mysql":
            self.fail("This acceptance suite requires a dedicated MySQL test database.")
        fixtures.Workflows.setUpTestData()

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
        slot_id = fixtures.Workflows.slot2.pk
        patients = [fixtures.Workflows.patient.pk, fixtures.Workflows.other.pk]
        results = self.race([
            lambda pk=pk: book(User.objects.get(pk=pk), slot_id, "in_person", "Synthetic concurrency test")
            for pk in patients
        ])
        self.assertCountEqual(results, ["ok", "unavailable"])
        self.assertEqual(Appointment.objects.filter(slot_id=slot_id).exclude(status="cancelled").count(), 1)
        self.assertTrue(Slot.objects.get(pk=slot_id).booked)

    def test_cancellation_racing_reschedule_keeps_slot_flags_consistent(self):
        patient_id, appointment_id, slot_id = fixtures.Workflows.patient.pk, fixtures.Workflows.appt.pk, fixtures.Workflows.slot2.pk
        self.race([
            lambda: book(User.objects.get(pk=patient_id), slot_id, "video", "Synthetic reschedule", Appointment.objects.get(pk=appointment_id)),
            lambda: change_status(Appointment.objects.get(pk=appointment_id), User.objects.get(pk=patient_id), "cancelled"),
        ])
        appt = Appointment.objects.get(pk=appointment_id)
        self.assertEqual(appt.status, "cancelled")
        for slot in Slot.objects.filter(pk__in=[fixtures.Workflows.slot.pk, slot_id]):
            self.assertEqual(slot.booked, Appointment.objects.filter(slot=slot).exclude(status="cancelled").exists())

    def test_simultaneous_dispense_has_one_deduction(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Medicine, Prescription, PrescriptionItem, StockMovement
        from .services import dispense
        medicine = Medicine.objects.create(name='Synthetic concurrency item',batch='QA',expiry=timezone.localdate()+timedelta(days=30),stock=10,price=1)
        rx = Prescription.objects.create(appointment=fixtures.Workflows.appt,instructions='Synthetic')
        PrescriptionItem.objects.create(prescription=rx,medicine=medicine,dose='Synthetic',quantity=2)
        result = self.race([lambda: dispense(Prescription.objects.get(pk=rx.pk),User.objects.get(pk=fixtures.Workflows.pharmacist.pk)) for _ in range(2)])
        self.assertCountEqual(result,['ok','unavailable'])
        medicine.refresh_from_db()
        self.assertEqual(medicine.stock,8)
        self.assertEqual(StockMovement.objects.filter(prescription=rx).count(),1)

    def test_simultaneous_daily_queue_tokens_are_unique(self):
        from .product import enqueue
        from .models import QueueEntry
        second = book(fixtures.Workflows.other,fixtures.Workflows.slot2.pk,'in_person','Synthetic queue test')
        def add(pk):
            from django.db import transaction
            with transaction.atomic():
                appt = Appointment.objects.select_for_update().get(pk=pk)
                enqueue(appt)
        result=self.race([lambda: add(fixtures.Workflows.appt.pk),lambda: add(second.pk)])
        self.assertEqual(result,['ok','ok'])
        self.assertEqual(set(QueueEntry.objects.values_list('number',flat=True)),{1,2})

    def test_simultaneous_partial_issues_cannot_overdispense(self):
        import uuid
        from datetime import timedelta
        from django.utils import timezone
        from .models import Medicine, Prescription, PrescriptionItem, DispensingEvent
        from .hospital_services import partial_dispense
        med=Medicine.objects.create(name='Synthetic partial race',batch='QA',expiry=timezone.localdate()+timedelta(days=30),stock=10,price=1)
        rx=Prescription.objects.create(appointment=fixtures.Workflows.appt,instructions='Synthetic')
        item=PrescriptionItem.objects.create(prescription=rx,medicine=med,dose='Synthetic',quantity=5)
        result=self.race([lambda:partial_dispense(item.pk,4,uuid.uuid4(),fixtures.Workflows.pharmacist) for _ in range(2)])
        self.assertCountEqual(result,['ok','unavailable'])
        med.refresh_from_db();item.refresh_from_db()
        self.assertEqual((med.stock,item.dispensed_quantity),(6,4))
        self.assertEqual(DispensingEvent.objects.filter(item=item).count(),1)

    def test_simultaneous_same_receipt_only_adds_stock_once(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Medicine, Supplier, PurchaseOrder, GoodsReceipt
        from .hospital_services import receive_purchase
        med=Medicine.objects.create(name='Synthetic receipt race',batch='QA',expiry=timezone.localdate()+timedelta(days=30),stock=0,price=1)
        supplier=Supplier.objects.create(name='Synthetic race supplier')
        order=PurchaseOrder.objects.create(supplier=supplier,medicine=med,quantity=10,status='approved',requested_by=fixtures.Workflows.pharmacist,approved_by=fixtures.Workflows.admin)
        result=self.race([lambda:receive_purchase(order.pk,10,'SYNTHETIC-RACE-GRN',fixtures.Workflows.pharmacist) for _ in range(2)])
        self.assertEqual(result,['ok','ok'])
        med.refresh_from_db();self.assertEqual(med.stock,10)
        self.assertEqual(GoodsReceipt.objects.filter(order=order).count(),1)

    def test_simultaneous_bed_allocation_has_one_winner(self):
        from .models import Bed, Admission
        from .hospital_services import update_admission
        bed=Bed.objects.create(label='Synthetic race bed',ward='QA',room_type='General')
        requests=[Admission.objects.create(patient=p,doctor=fixtures.Workflows.doctor,department=fixtures.Workflows.department) for p in [fixtures.Workflows.patient,fixtures.Workflows.other]]
        result=self.race([lambda pk=a.pk:update_admission(pk,'allocate',fixtures.Workflows.reception,bed.pk) for a in requests])
        self.assertCountEqual(result,['ok','unavailable'])
        self.assertEqual(Admission.objects.filter(bed=bed).count(),1)

    def test_simultaneous_distinct_slots_respect_daily_cap(self):
        from datetime import timedelta
        profile=fixtures.Workflows.doctor.doctor_profile
        profile.daily_limit=2
        profile.save()
        patient=User.objects.create_user('synthetic-cap-race@example.test','Synthetic-Cap-Password-928!',name='Synthetic cap patient')
        third=Slot.objects.create(doctor=fixtures.Workflows.doctor,start=fixtures.Workflows.slot2.start+timedelta(minutes=12))
        result=self.race([lambda:book(fixtures.Workflows.other,fixtures.Workflows.slot2.pk,'in_person','Synthetic cap race'),
            lambda:book(patient,third.pk,'in_person','Synthetic cap race')])
        self.assertCountEqual(result,['ok','unavailable'])
        self.assertEqual(Appointment.objects.count(),2)
