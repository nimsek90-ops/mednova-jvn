import uuid
from datetime import timedelta, datetime, time
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError, transaction
from . import tests as fixtures
from .models import *
from .services import book, dispense, BookingError
from .scheduling import publish_schedule, add_block, available_slots, day_bounds
from .hospital_services import partial_dispense, receive_purchase, update_admission


class HospitalUpgrade(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)

    def future_day(self):
        return timezone.localdate()+timedelta(days=5)

    def rx(self):
        med = Medicine.objects.create(name='Synthetic medicine',batch='UPGRADE',expiry=timezone.localdate()+timedelta(days=90),stock=20,price=10)
        rx = Prescription.objects.create(appointment=self.appt,instructions='Synthetic clinician instructions')
        item = PrescriptionItem.objects.create(prescription=rx,medicine=med,dose='Synthetic dose',quantity=8)
        return rx,item,med

    def test_multiple_weekly_sessions_duration_buffer_and_break(self):
        day=self.future_day()
        for start,end in [(time(9),time(10)),(time(17),time(18))]:
            ScheduleSession.objects.create(doctor=self.doctor,weekday=day.weekday(),start=start,end=end,duration=15,buffer=5,capacity=3)
        start=timezone.make_aware(datetime.combine(day,time(9,20)))
        add_block(self.doctor,start,start+timedelta(minutes=20),'break')
        self.assertEqual(publish_schedule(self.doctor,day,day),5)
        first,last=day_bounds(day)
        slots=list(available_slots(self.doctor).filter(start__gte=first,start__lt=last))
        self.assertEqual(len(slots),5)
        self.assertEqual([timezone.localtime(s.start).strftime('%H:%M') for s in slots],['09:00','09:40','17:00','17:20','17:40'])
        self.assertTrue(all(s.duration==15 and s.buffer==5 for s in slots))
        self.assertEqual(publish_schedule(self.doctor,day,day),0)

    def test_blocked_manual_slot_is_hidden_and_rechecked(self):
        add_block(self.doctor,self.slot2.start,self.slot2.start+timedelta(minutes=20),'leave')
        self.assertFalse(available_slots(self.doctor).filter(pk=self.slot2.pk).exists())
        with self.assertRaises(BookingError):
            book(self.other,self.slot2.pk,'video','Synthetic booking')

    def test_booked_visit_prevents_leave(self):
        with self.assertRaises(BookingError):
            add_block(self.doctor,self.slot.start,self.slot.start+timedelta(hours=1),'leave')
        self.assertFalse(ScheduleBlock.objects.exists())

    def test_buffer_overlap_daily_limit_and_mode(self):
        # Keep both visits on the same hospital day, including runs near midnight.
        self.slot.start=timezone.make_aware(datetime.combine(timezone.localdate()+timedelta(days=1),time(9)))
        self.slot.save()
        self.slot2.start=self.slot.start+timedelta(minutes=12)
        self.slot2.save()
        self.slot.duration,self.slot.buffer=15,5
        self.slot.save()
        with self.assertRaises(BookingError):
            book(self.other,self.slot2.pk,'video','Overlap in buffer')
        free=Slot.objects.create(doctor=self.doctor,start=self.slot.start+timedelta(hours=2),consultation_type='in_person')
        with self.assertRaises(BookingError):
            book(self.other,free.pk,'video','Wrong mode')
        profile=self.doctor.doctor_profile
        profile.daily_limit=1
        profile.save()
        self.assertFalse(available_slots(self.doctor).filter(pk=free.pk).exists())
        with self.assertRaises(BookingError):
            book(self.other,free.pk,'in_person','Daily limit')

    def test_session_capacity_and_urgent_booking(self):
        day=self.future_day()
        session=ScheduleSession.objects.create(doctor=self.doctor,weekday=day.weekday(),start=time(9),end=time(10),capacity=1,visit_type='urgent')
        publish_schedule(self.doctor,day,day)
        slot=Slot.objects.filter(session=session).first()
        self.assertFalse(available_slots(self.doctor).filter(session=session).exists())
        with self.assertRaises(BookingError):
            book(self.patient,slot.pk,'in_person','Urgent slot')
        book(self.patient,slot.pk,'in_person','Reception authorized booking',actor=self.reception)
        other=Slot.objects.filter(session=session,booked=False).first()
        with self.assertRaises(BookingError):
            book(self.other,other.pk,'in_person','Session limit',actor=self.reception)

    def test_schedule_permissions_and_overlap_form(self):
        path=reverse('schedule_rules')
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.doctor)
        data={'action':'session','weekday':1,'start':'09:00','end':'12:00','duration':15,'buffer':5,'mode':'both','visit_type':'new','capacity':10}
        self.assertEqual(self.client.post(path,data).status_code,302)
        data['start']='11:00'
        self.assertContains(self.client.post(path,data),'may not overlap')
        self.assertEqual(ScheduleSession.objects.count(),1)
        session=ScheduleSession.objects.get()
        self.assertEqual(self.client.post(path,{'action':'disable','session':session.pk}).status_code,302)
        session.refresh_from_db();self.assertFalse(session.active)
        self.assertEqual(self.client.post(path,{'action':'enable','session':session.pk}).status_code,302)
        session.refresh_from_db();self.assertTrue(session.active)

    def test_partial_dispensing_and_idempotent_retry(self):
        rx,item,med=self.rx()
        key=uuid.uuid4()
        first=partial_dispense(item.pk,3,key,self.pharmacist)
        self.assertEqual(partial_dispense(item.pk,3,key,self.pharmacist).pk,first.pk)
        med.refresh_from_db();item.refresh_from_db();rx.refresh_from_db()
        self.assertEqual((med.stock,item.remaining,rx.dispensed),(17,5,False))
        dispense(rx,self.pharmacist)
        med.refresh_from_db();item.refresh_from_db();rx.refresh_from_db()
        self.assertEqual((med.stock,item.remaining,rx.dispensed),(12,0,True))
        self.assertEqual(DispensingEvent.objects.count(),2)
        with self.assertRaises(BookingError):
            partial_dispense(item.pk,1,uuid.uuid4(),self.pharmacist)

    def test_quarantine_recall_expiry_and_wrong_role_deny(self):
        rx,item,med=self.rx()
        for status in ['quarantined','recalled','damaged']:
            med.safety_status=status;med.save()
            with self.assertRaises(BookingError):
                partial_dispense(item.pk,1,uuid.uuid4(),self.pharmacist)
            with self.assertRaises(BookingError):
                dispense(rx,self.pharmacist)
        med.safety_status='available';med.expiry=timezone.localdate()-timedelta(days=1);med.save()
        with self.assertRaises(BookingError):
            partial_dispense(item.pk,1,uuid.uuid4(),self.pharmacist)
        with self.assertRaises(BookingError):
            partial_dispense(item.pk,1,uuid.uuid4(),self.reception)
        med.refresh_from_db();self.assertEqual(med.stock,20)

    def test_purchase_receipt_approval_cap_and_duplicate_reference(self):
        rx,item,med=self.rx()
        supplier=Supplier.objects.create(name='Synthetic supplier')
        order=PurchaseOrder.objects.create(supplier=supplier,medicine=med,quantity=10,requested_by=self.pharmacist)
        with self.assertRaises(BookingError):receive_purchase(order.pk,5,'QA-GRN',self.pharmacist)
        order.status='approved';order.approved_by=self.admin;order.save()
        receipt=receive_purchase(order.pk,5,'QA-GRN',self.pharmacist)
        self.assertEqual(receive_purchase(order.pk,5,'QA-GRN',self.pharmacist).pk,receipt.pk)
        with self.assertRaises(BookingError):receive_purchase(order.pk,6,'QA-GRN-OVER',self.pharmacist)
        receive_purchase(order.pk,5,'QA-GRN-2',self.pharmacist)
        med.refresh_from_db();order.refresh_from_db()
        self.assertEqual((med.stock,order.received,order.status),(30,10,'received'))

    def test_admission_bed_exclusivity_and_clinical_discharge_authority(self):
        bed=Bed.objects.create(label='QA-A',ward='Synthetic ward',room_type='General')
        admission=Admission.objects.create(patient=self.patient,doctor=self.doctor,department=self.department)
        second=Admission.objects.create(patient=self.other,doctor=self.doctor,department=self.department)
        update_admission(admission.pk,'allocate',self.reception,bed.pk)
        with self.assertRaises(BookingError):update_admission(second.pk,'allocate',self.reception,bed.pk)
        with self.assertRaises(BookingError):update_admission(admission.pk,'discharge',self.reception)
        with self.assertRaises(BookingError):update_admission(admission.pk,'ready',self.doctor2)
        update_admission(admission.pk,'ready',self.doctor)
        update_admission(admission.pk,'discharge',self.reception)
        admission.refresh_from_db();self.assertIsNone(admission.bed)
        self.assertTrue(admission.last_bed)
        update_admission(second.pk,'allocate',self.reception,bed.pk)

    def test_mrn_card_ownership_and_immutable_identifier(self):
        first=PatientRegistration.objects.get(patient=self.patient)
        self.assertNotEqual(first.mrn,PatientRegistration.objects.get(patient=self.other).mrn)
        self.client.force_login(self.other)
        path=reverse('registration_card',args=[self.patient.pk])
        self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.reception)
        self.assertEqual(self.client.post(path,{'emergency_name':'Synthetic contact','consent':'on'}).status_code,302)
        first.refresh_from_db();self.assertTrue(first.consent)
        self.assertNotEqual(str(first.mrn),'')

    def test_clinical_draft_private_result_once_and_acknowledgment(self):
        self.slot.start=timezone.now()-timedelta(minutes=1);self.slot.save()
        self.appt.status='confirmed';self.appt.save()
        path=reverse('clinical_work',args=[self.appt.pk])
        self.client.force_login(self.reception)
        self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.doctor)
        data={'action':'draft','complaint':'SYNTHETIC PRIVATE DRAFT','plan':'Synthetic plan','expected_revision':0}
        self.assertEqual(self.client.post(path,data).status_code,302)
        self.assertContains(self.client.post(path,data),'Draft changed')
        self.assertEqual(self.client.post(path,{'action':'order','category':'lab','name':'Synthetic test'}).status_code,302)
        order=Investigation.objects.get(appointment=self.appt)
        self.client.post(path,{'action':'result','investigation':order.pk,'result':'Synthetic verified result','critical':'on'})
        self.client.post(path,{'action':'result','investigation':order.pk,'result':'Attempt overwrite'})
        order.refresh_from_db();self.assertEqual(order.result,'Synthetic verified result')
        self.client.post(path,{'action':'acknowledge','investigation':order.pk})
        order.refresh_from_db();self.assertIsNotNone(order.acknowledged_at)
        self.client.force_login(self.patient)
        self.assertNotContains(self.client.get(path),'SYNTHETIC PRIVATE DRAFT')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(path).status_code,404)

    def test_assistant_uses_real_slots_and_explicit_booking(self):
        path=reverse('assistant')
        self.client.force_login(self.other)
        response=self.client.post(path,{'topic':'doctors','question':'Test Doctor'})
        self.assertContains(response,'Confirm appointment request')
        response=self.client.post(path,{'action':'book','slot':self.slot2.pk,'mode':'in_person','reason':'Synthetic assistant request','consent':'on'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(Appointment.objects.filter(patient=self.other,slot=self.slot2).exists())
        response=self.client.post(path,{'action':'book','slot':self.slot2.pk,'mode':'in_person','reason':'Retry','consent':'on'})
        self.assertContains(response,'no longer available')

    def test_assistant_privacy_emergency_faq_and_handoff(self):
        path=reverse('assistant')
        HospitalFAQ.objects.create(question='SYNTHETIC UNAPPROVED',answer='Not public',approved=False)
        response=self.client.post(path,{'topic':'appointments','question':''})
        self.assertNotContains(response,self.appt.short_id)
        self.assertNotContains(response,'SYNTHETIC UNAPPROVED')
        response=self.client.post(path,{'topic':'doctors','question':'chest pain emergency'})
        self.assertContains(response,'112')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.post(path,{'topic':'appointments','question':''}),self.appt.short_id)
        for _ in range(2):self.client.post(path,{'topic':'support','question':'SYNTHETIC RAW QUESTION'})
        self.assertEqual(AssistantEscalation.objects.filter(patient=self.other).count(),1)

    def test_video_consent_waiting_room_admission_and_expiry(self):
        Payment.objects.filter(appointment=self.appt).update(status="paid", received_by=self.reception)
        self.slot.start=timezone.now();self.slot.save()
        self.appt.status='confirmed';self.appt.save()
        room=reverse('video',args=[self.appt.pk]);signal=reverse('signal',args=[self.appt.pk])
        self.client.force_login(self.patient)
        self.assertContains(self.client.get(room),'Enter waiting room')
        self.assertEqual(self.client.get(signal).json()['signals'],[])
        self.assertEqual(self.client.post(signal,{'kind':'ready','payload':{}},content_type='application/json').status_code,409)
        self.client.post(room,{'action':'consent','consent':'on'})
        self.assertEqual(self.client.post(room,{'action':'admit'}).status_code,403)
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.post(room,{'action':'admit'}).status_code,302)
        self.client.force_login(self.patient)
        self.assertEqual(self.client.post(signal,{'kind':'ready','payload':{}},content_type='application/json').status_code,200)
        self.client.force_login(self.doctor)
        self.client.post(room,{'action':'close'})
        self.assertEqual(self.client.get(signal).status_code,404)

    def test_new_role_pages_render_and_cross_role_denial(self):
        pages={'schedule_rules':self.doctor,'worklist':self.reception,'admissions':self.patient,
            'purchasing':self.pharmacist,'assistant_admin':self.admin,'bed_catalogue':self.admin}
        for name,user in pages.items():
            self.client.force_login(user)
            response=self.client.get(reverse(name))
            self.assertEqual(response.status_code,200,name)
            import re
            ids=re.findall(r'\bid="([^"]+)"',response.content.decode())
            self.assertEqual(len(ids),len(set(ids)),name)
        self.client.force_login(self.reception)
        exported=self.client.get(reverse('worklist')+'?export=csv')
        self.assertEqual(exported['Content-Type'],'text/csv; charset=utf-8')
        self.assertNotIn(self.patient.email,exported.content.decode())
        self.client.force_login(self.patient)
        for name in ['purchasing','assistant_admin','bed_catalogue','worklist','schedule_rules']:
            self.assertEqual(self.client.get(reverse(name)).status_code,403,name)

    def test_waiting_list_cancelled_slot_notification_and_ownership(self):
        path=reverse('waiting_list')
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(path,{'doctor':self.doctor.pk,'mode':'video'}).status_code,302)
        entry=WaitingList.objects.get(patient=self.other)
        self.client.force_login(self.patient)
        self.assertEqual(self.client.post(path,{'action':'leave','entry':entry.pk}).status_code,404)
        from .services import change_status
        change_status(self.appt,self.patient,'cancelled',reason='Synthetic patient request')
        self.appt.refresh_from_db();self.assertEqual(self.appt.cancellation_reason,'Synthetic patient request')
        self.assertTrue(Notification.objects.filter(recipient=self.other,message__contains='may now be available').exists())
        self.assertTrue(available_slots(self.doctor).filter(pk=self.slot.pk).exists())

    def test_no_show_requires_start_and_closes_queue(self):
        from .services import change_status
        self.appt.status='confirmed';self.appt.save()
        with self.assertRaises(BookingError):change_status(self.appt,self.doctor,'no_show')
        self.slot.start=timezone.now()-timedelta(minutes=15);self.slot.save()
        queue=QueueEntry.objects.create(appointment=self.appt,date=timezone.localdate(),number=1,status='in_consultation')
        change_status(self.appt,self.reception,'no_show')
        self.appt.refresh_from_db();queue.refresh_from_db()
        self.assertEqual((self.appt.status,queue.status),('no_show','cancelled'))

    def test_duplicate_registration_requires_identity_review(self):
        from .forms import ReceptionPatientForm
        self.patient.phone='9999912345';self.patient.save()
        data={'name':'Synthetic different patient','email':'synthetic-duplicate-review@example.test','phone':self.patient.phone,
            'role':'patient','password1':'Synthetic-Registration-928!','password2':'Synthetic-Registration-928!','consent':'on'}
        form=ReceptionPatientForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('Possible duplicate',str(form.errors))
        data['duplicate_reviewed']='on'
        form=ReceptionPatientForm(data)
        self.assertTrue(form.is_valid(),form.errors)
        user=form.save()
        self.assertNotEqual(user.pk,self.patient.pk)
        self.assertTrue(PatientRegistration.objects.filter(patient=user).exists())

    def test_draft_review_populates_finalization_without_exposing_to_patient(self):
        self.slot.start=timezone.now()-timedelta(minutes=2);self.slot.save()
        self.appt.status='confirmed';self.appt.save()
        ClinicalDraft.objects.create(appointment=self.appt,author=self.doctor,complaint='PRIVATE DRAFT REVIEW',plan='Synthetic plan')
        self.client.force_login(self.doctor)
        path=reverse('notes',args=[self.appt.pk])+'?draft=1'
        self.assertContains(self.client.get(path),'PRIVATE DRAFT REVIEW')
        self.client.force_login(self.patient)
        self.assertNotContains(self.client.get(path),'PRIVATE DRAFT REVIEW')

    def test_configured_reorder_threshold_is_shared_by_dashboard_and_inventory(self):
        Medicine.objects.create(name='Synthetic threshold check',batch='QA-THRESHOLD',stock=12,
            reorder_level=15,price=1,expiry=timezone.localdate()+timedelta(days=60))
        self.client.force_login(self.pharmacist)
        response=self.client.get(reverse('dashboard'))
        self.assertEqual(dict(response.context['stats'])['Low stock'],1)
        self.assertEqual(self.client.get(reverse('inventory')).context['low_stock_count'],1)
