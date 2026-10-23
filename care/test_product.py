from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from . import tests as fixtures
from .models import *
from .product import wellness_score
from .services import dispense, change_status
from .delivery import reminders, process_outbox


class ProductWorkflows(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)

    def login(self, user):
        self.client.force_login(user)

    def test_formula_boundaries(self):
        self.assertEqual(wellness_score(8, 8, 5, 0), 100)
        self.assertEqual(wellness_score(0, 0, 0, 10), 0)
        self.assertEqual(wellness_score(24, 30, 7, 0), 100)
        self.assertEqual(wellness_score(4, 0, 0, 10), 13)

    def test_wellness_save_correct_and_isolation(self):
        self.login(self.patient)
        data = dict(date=timezone.localdate(), sleep=8, water=8, exercise_days=5, stress=0)
        self.assertEqual(self.client.post(reverse('wellness'), data).status_code, 302)
        entry = WellnessEntry.objects.get(patient=self.patient)
        self.assertEqual(entry.score, 100)
        data.update(stress=10)
        self.client.post(reverse('wellness'), data)
        entry.refresh_from_db()
        self.assertEqual(entry.score, 70)
        self.assertEqual(entry.revisions.count(), 2)
        self.assertContains(self.client.get(reverse('wellness')), '70/100')
        WellnessEntry.objects.create(patient=self.patient,date=timezone.localdate()-timedelta(days=8),sleep=0,water=8,exercise_days=0,stress=10,score=20)
        response=self.client.get(reverse('wellness'))
        self.assertEqual(response.context['previous_week'],20)
        self.assertEqual(response.context['weekly'],70)
        self.assertEqual(response.context['pagination'].paginator.count,2)
        self.login(self.other)
        self.assertContains(self.client.get(reverse('wellness')), 'No entries yet.')

    def test_wellness_rejects_invalid_ranges_and_date(self):
        self.login(self.patient)
        valid = dict(date=timezone.localdate(), sleep=8, water=8, exercise_days=5, stress=0)
        for key, value in [('sleep', -1), ('sleep', 25), ('water', 31), ('exercise_days', 8), ('stress', 11), ('stress', '1.5'), ('date', timezone.localdate()+timedelta(days=1))]:
            self.assertEqual(self.client.post(reverse('wellness'), {**valid, key: value}).status_code, 200)
        self.assertFalse(WellnessEntry.objects.exists())

    def test_questionnaire_saves_actual_answers(self):
        self.login(self.patient)
        answers = dict(sleep_quality='poor', hydration='low', activity='little', balanced_meals='rarely', stress=9)
        self.assertEqual(self.client.post(reverse('health_hub'), answers).status_code, 302)
        assessment = HealthAssessment.objects.get()
        self.assertEqual(assessment.answers['stress'], 9)
        self.assertEqual(len(assessment.result), 5)
        self.login(self.other)
        self.assertContains(self.client.get(reverse('health_hub')), 'No assessments saved.')

    def test_symptom_emergency_overrides_routine(self):
        for symptom in ['chest', 'breathing', 'stroke', 'bleeding', 'unconscious']:
            response = self.client.post(reverse('symptoms'), dict(symptoms=[symptom, 'other'], duration='minutes', severity='mild'))
            self.assertContains(response, 'Seek emergency help now')
            self.assertNotContains(response, '>Find a doctor<')
        response = self.client.post(reverse('symptoms'), dict(symptoms=['other'], duration='days', severity='mild'))
        self.assertContains(response, 'Find a doctor')
        self.assertFalse(HealthAssessment.objects.exists())

    def test_symptom_invalid_input(self):
        response = self.client.post(reverse('symptoms'), dict(symptoms=['unknown'], duration='forever', severity='none'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['result'])

    def test_notes_finalize_correct_stale_and_permissions(self):
        self.appt.slot.start = timezone.now()-timedelta(minutes=2)
        self.appt.slot.save()
        self.appt.status = 'confirmed'
        self.appt.save()
        url = reverse('notes', args=[self.appt.pk])
        self.login(self.doctor)
        data = dict(complaint='Synthetic complaint', examination='', assessment='', plan='Synthetic plan', follow_up='', expected_version=0)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 200)
        data['expected_version'] = 1
        self.assertEqual(self.client.post(url, data).status_code, 200)
        data.update(correction_reason='Synthetic correction', plan='Corrected synthetic plan')
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.appt.notes.count(), 2)
        self.assertEqual(self.appt.notes.get(version=1).plan, 'Synthetic plan')
        for user, expected in [(self.patient, 200), (self.other, 403), (self.doctor2, 403), (self.reception, 403), (self.admin, 403), (self.pharmacist, 403)]:
            self.login(user)
            self.assertEqual(self.client.get(url).status_code, expected)
            self.assertEqual(self.client.post(url, data).status_code, 403)

    def test_notes_block_before_start_and_cancelled(self):
        self.login(self.doctor)
        self.assertEqual(self.client.post(reverse('notes', args=[self.appt.pk]), {}).status_code, 403)

    def test_timeline_care_scope(self):
        url = reverse('timeline', args=[self.patient.pk])
        for user, expected in [(self.patient,200),(self.other,403),(self.doctor,200),(self.doctor2,403),(self.reception,403),(self.admin,403),(self.pharmacist,403)]:
            self.login(user)
            self.assertEqual(self.client.get(url).status_code, expected)

    def test_queue_checkin_idempotency_and_transitions(self):
        self.appt.slot.start = timezone.now()+timedelta(minutes=5)
        self.appt.slot.save()
        self.appt.mode = 'in_person'
        self.appt.status = 'confirmed'
        self.appt.save()
        self.login(self.reception)
        url = reverse('check_in', args=[self.appt.pk])
        self.client.post(url)
        self.client.post(url)
        entry = QueueEntry.objects.get()
        self.assertEqual(entry.number,1)
        self.client.post(reverse('queue'), dict(entry=entry.pk,status='called'))
        entry.refresh_from_db()
        self.assertEqual(entry.status,'called')
        self.client.post(reverse('queue'), dict(entry=entry.pk,status='waiting'))
        entry.refresh_from_db()
        self.assertEqual(entry.status,'called')
        change_status(self.appt,self.reception,'cancelled')
        entry.refresh_from_db()
        self.assertEqual(entry.status,'cancelled')

    def test_stock_movement_and_duplicate_dispense(self):
        medicine = Medicine.objects.create(name='Synthetic item',batch='SYN',expiry=timezone.localdate()+timedelta(days=30),stock=10,price=1)
        rx = Prescription.objects.create(appointment=self.appt,instructions='Synthetic')
        PrescriptionItem.objects.create(prescription=rx,medicine=medicine,dose='Synthetic',quantity=2)
        dispense(rx,self.pharmacist)
        movement = StockMovement.objects.get()
        self.assertEqual((movement.quantity,movement.balance),(-2,8))
        self.assertEqual(movement.prescription,rx)
        self.login(self.pharmacist)
        self.assertContains(self.client.get(reverse('movements')),'Synthetic item')

    def test_new_route_role_matrix(self):
        matrix = {'wellness': {'patient'}, 'queue': {'receptionist','admin'}, 'movements': {'pharmacist','admin'}}
        users = [self.patient,self.doctor,self.reception,self.pharmacist,self.admin]
        for route,allowed in matrix.items():
            self.client.logout()
            self.assertEqual(self.client.get(reverse(route)).status_code,302)
            for user in users:
                self.login(user)
                self.assertEqual(self.client.get(reverse(route)).status_code,200 if user.role in allowed else 403)
        for route in ['about','pharmacy_info','health_hub','symptoms']:
            self.client.logout()
            self.assertEqual(self.client.get(reverse(route)).status_code,200)
            for user in users:
                self.login(user)
                self.assertEqual(self.client.get(reverse(route)).status_code,200)

    @override_settings(EMAIL_HOST='')
    def test_email_unconfigured_not_claimed_sent(self):
        self.assertEqual(process_outbox(),0)
        self.assertFalse(DeliveryOutbox.objects.filter(status='sent').exists())
        self.assertTrue(DeliveryOutbox.objects.filter(status='unavailable').exists())

    @override_settings(EMAIL_HOST='synthetic',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_outbox_send_and_reminder_deduplication(self):
        self.appt.status='confirmed'
        self.appt.save()
        reminders()
        reminders()
        self.assertEqual(DeliveryOutbox.objects.filter(dedupe_key__startswith='reminder:').count(),1)
        expected=DeliveryOutbox.objects.count()
        self.assertEqual(process_outbox(),expected)
        self.assertEqual(process_outbox(),0)
        from django.core import mail
        self.assertEqual(len(mail.outbox),expected)
        self.assertNotIn('A private clinical reason',mail.outbox[0].body)

    @override_settings(EMAIL_HOST='synthetic')
    @patch('care.delivery.send_mail',side_effect=RuntimeError('synthetic failure'))
    def test_email_failure_recorded(self, sender):
        self.assertEqual(process_outbox(),0)
        self.assertTrue(DeliveryOutbox.objects.filter(status='failed').exists())

    def test_complete_route_matrix(self):
        import uuid, json, os
        from django.urls import get_resolver
        all_roles = {'patient','doctor','receptionist','pharmacist','admin'}
        policy = {
            'reception_desk':{'receptionist','admin'},'reception_register':{'receptionist','admin'},'reception_booking':{'receptionist'},'reception_patient':{'receptionist','admin'},'specialty_create':{'admin'},'specialty_edit':{'admin'},'doctor_specialties':{'admin'},
            'support_create':{'patient'},'support_queue':all_roles,'support_case':all_roles,
            'waiting_list':{'patient','receptionist'},'worklist':{'doctor','receptionist','pharmacist','admin'},'schedule_rules':{'doctor'},'registration_card':{'patient','receptionist','admin'},'admissions':{'patient','doctor','receptionist','admin'},'bed_catalogue':{'admin'},'purchasing':{'pharmacist','admin'},'partial_issue':{'pharmacist'},'batch_safety':{'pharmacist','admin'},'clinical_work':{'patient','doctor'},'assistant_admin':{'admin'},
            'schema_explorer':{'admin'},'data_management':{'admin'},'notifications':all_roles,'patients':{'receptionist','admin'},'users':{'admin'},'operations':{'admin'},
            'edit_slot':{'doctor'},'department_edit':{'admin'},'check_in':{'receptionist','admin'},
            'receipt':{'patient','receptionist','admin'},'password':all_roles,'dashboard':all_roles,'profile':all_roles,
            'availability':{'doctor'},'remove_slot':{'doctor'},'booking':{'patient','receptionist'},
            'appointments':{'patient','doctor','receptionist','admin'},'appointment':{'patient','doctor','receptionist','admin'},
            'appointment_action':{'patient','doctor','receptionist','admin'},'upload':{'patient','doctor'},'download':{'patient','doctor'},
            'prescribe':{'doctor'},'prescriptions':{'patient','doctor','pharmacist'},'dispense':{'pharmacist'},
            'inventory':{'pharmacist','admin'},'stock':{'pharmacist','admin'},'staff':{'admin'},'departments':{'admin'},
            'settings':{'admin'},'audit':{'admin'},'payment_record':{'receptionist','admin'},'pay':{'patient'},
            'payment_verify':{'patient'},'video':{'patient','doctor'},'signal':{'patient','doctor'},
            'wellness':{'patient'},'notes':{'patient','doctor'},'timeline':{'patient','doctor'},
            'queue':{'receptionist','admin'},'movements':{'pharmacist','admin'},
        }
        rows=[]
        users=[None,self.patient,self.doctor,self.reception,self.pharmacist,self.admin]
        for pattern in get_resolver().url_patterns:
            name=pattern.name
            kwargs={}
            for key,converter in pattern.pattern.converters.items():
                if key=='patient_id': value=self.patient.pk
                elif key=='doctor_id': value=self.doctor.pk
                elif key in ('medicine_id','item_id'): value=1
                elif key=='kind': value='privacy'
                elif key=='uid': value='invalid'
                elif key=='token': value='invalid'
                elif key=='pk':
                    value=self.appt.pk if converter.__class__.__name__=='UUIDConverter' else (self.department.pk if name=='department_edit' else self.slot.pk)
                else: raise AssertionError(key)
                kwargs[key]=value
            url=reverse(name,kwargs=kwargs)
            for user in users:
                if user: self.login(user)
                else: self.client.logout()
                response=self.client.get(url)
                status=response.status_code
                role=user.role if user else 'anonymous'
                rows.append({'name':name,'url':url,'role':role,'status':status})
                self.assertLess(status,500,(name,role,status))
                if name in policy:
                    if not user:
                        self.assertIn(status,(302,405),(name,role,status))
                    elif role not in policy[name]:
                        self.assertIn(status,(403,404,405),(name,role,status))
        destination=os.getenv('MEDNOVA_MATRIX_OUTPUT')
        if destination:
            from pathlib import Path
            Path(destination).write_text(json.dumps(rows,indent=2))
        self.assertEqual(len(rows),len(get_resolver().url_patterns)*6)

    def test_core_product_translations(self):
        from .templatetags.translate import t
        for language in ['mr','hi']:
            for label in ['Wellness tracking','Medical timeline','Health Hub','Clinical notes','Save questionnaire']:
                self.assertNotEqual(t(label,language),label)
        self.login(self.patient)
        for language in ['en','mr','hi']:
            self.client.post(reverse('language'),{'language':language,'next':'/wellness/'})
            response=self.client.get(reverse('wellness'))
            self.assertEqual(response.status_code,200)
            self.assertContains(response,t('Wellness tracking',language))
