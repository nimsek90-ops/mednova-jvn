import uuid
from unittest.mock import patch
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db import OperationalError
from . import tests as fixtures
from .models import SupportCase, SupportMessage, Report, Investigation, Prescription, Payment, QueueEntry, Notification, HospitalFAQ


class PatientAssistantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)
        Report.objects.create(appointment=cls.appt, uploaded_by=cls.doctor, title='SYNTHETIC BLOOD REPORT', extension='.pdf', file='reports/synthetic.pdf')
        Investigation.objects.create(appointment=cls.appt, ordered_by=cls.doctor, category='lab', name='SYNTHETIC BLOOD TEST', status='ordered')
        Prescription.objects.create(appointment=cls.appt, instructions='SYNTHETIC CLINICIAN INSTRUCTIONS')

    def ask(self, message):
        return self.client.post(reverse('assistant_api'), {'message':message}, content_type='application/json')

    def create_case(self, category='reports', patient=None):
        return SupportCase.objects.create(patient=patient or self.patient, category=category, summary='PRIVATE SUPPORT ISSUE',
            appointment=self.appt if not patient else None, assigned_to=self.doctor if category in ('reports','clinical') else None,
            consented_at=timezone.now(), request_key=uuid.uuid4())

    def test_reports_status_and_secure_links_are_own_only(self):
        self.client.force_login(self.patient)
        result = self.ask('Is my blood report ready?').json()
        self.assertIn('SYNTHETIC BLOOD REPORT', str(result))
        self.assertIn('Ordered', str(result))
        self.assertNotIn('ready tomorrow', str(result))
        self.assertTrue(any('Secure report download' == a['label'] for c in result['cards'] for a in c['links']))
        self.client.force_login(self.other)
        self.assertNotIn('SYNTHETIC BLOOD', str(self.ask('My reports').json()))
        for role in [self.doctor,self.reception,self.pharmacist,self.admin]:
            self.client.force_login(role)
            self.assertNotIn('SYNTHETIC BLOOD', str(self.ask('My reports').json()))

    def test_prescription_and_bill_are_actual_and_private(self):
        self.client.force_login(self.patient)
        result = self.ask('My prescription and outstanding bill').json()
        self.assertIn('SYNTHETIC CLINICIAN INSTRUCTIONS', str(result))
        self.assertIn('₹250.00', result['text'])
        self.assertIn('Payment Pending', str(result))
        self.client.force_login(self.other)
        result = self.ask('My prescription and outstanding bill').json()
        self.assertNotIn('SYNTHETIC CLINICIAN', str(result))
        self.assertIn('₹0.00', result['text'])

    def test_no_policy_or_waiting_time_invented(self):
        response = self.ask('What should I bring for my appointment?')
        self.assertIn('not been published', response.json()['text'])
        self.client.force_login(self.patient)
        QueueEntry.objects.create(appointment=self.appt, date=timezone.localdate(), number=7)
        response = self.ask('I have been waiting for a long time').json()
        self.assertIn('Your token 7', str(response))
        self.assertIn('not stored', response['text'])
        self.assertIn('support_draft', self.client.session)

    def test_handoff_retains_issue_and_requires_consent(self):
        self.client.force_login(self.patient)
        self.ask('I cannot download my report')
        self.ask('I want to talk to a real person')
        draft = self.client.session['support_draft']
        self.assertIn('cannot download my report', draft['summary'])
        self.assertEqual(draft['category'], 'reports')
        self.assertEqual(SupportCase.objects.count(), 0)
        page = self.client.get(reverse('support_create'))
        self.assertContains(page, 'cannot download my report')
        payload = {'category':'reports','summary':draft['summary'], 'request_key':draft['request_key'], 'appointment':self.appt.pk}
        self.assertEqual(self.client.post(reverse('support_create'),payload).status_code,200)
        self.assertEqual(SupportCase.objects.count(),0)
        payload['consent']='on'
        result = self.client.post(reverse('support_create'),payload)
        self.assertEqual(result.status_code,302)
        case = SupportCase.objects.get()
        self.assertEqual(case.assigned_to,self.doctor)
        self.client.post(reverse('support_create'),payload)
        self.assertEqual(SupportCase.objects.count(),1)
        self.assertIn(case.reference,str(self.ask('My case status').json()))

    def test_case_id_and_appointment_manipulation_denied(self):
        case = self.create_case()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('support_case',args=[case.pk])).status_code,404)
        response=self.client.post(reverse('support_create'), {'category':'reports','summary':'A test issue','appointment':self.appt.pk,'request_key':uuid.uuid4(),'consent':'on'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(SupportCase.objects.count(),1)

    def test_clinical_summary_hidden_from_admin_and_other_staff(self):
        case = self.create_case()
        SupportMessage.objects.create(case=case,author=self.doctor,text='PRIVATE CLINICAL NOTE',internal=True)
        path=reverse('support_case',args=[case.pk])
        self.client.force_login(self.admin)
        result=self.client.get(path)
        self.assertEqual(result.status_code,200)
        self.assertNotContains(result,'PRIVATE SUPPORT ISSUE')
        self.assertNotContains(result,'PRIVATE CLINICAL NOTE')
        for user in [self.reception,self.pharmacist,self.doctor2]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(path).status_code,404)
        self.client.force_login(self.doctor)
        self.assertContains(self.client.get(path),'PRIVATE SUPPORT ISSUE')
        self.assertContains(self.client.get(path),'PRIVATE CLINICAL NOTE')
        self.client.force_login(self.patient)
        self.assertNotContains(self.client.get(path),'PRIVATE CLINICAL NOTE')

    def test_staff_reply_patient_followup_and_status_notification(self):
        case=self.create_case('billing')
        path=reverse('support_case',args=[case.pk])
        self.client.force_login(self.reception)
        self.assertEqual(self.client.post(path,{'action':'reply','text':'Your billing query is being reviewed.'}).status_code,302)
        self.assertTrue(Notification.objects.filter(recipient=self.patient,message__contains='support case').exists())
        self.client.post(path,{'action':'route','category':'billing','status':'waiting_for_patient','priority':'routine','assigned_to':self.reception.pk})
        case.refresh_from_db();self.assertEqual(case.status,'waiting_for_patient')
        self.client.force_login(self.patient)
        self.assertContains(self.client.get(path),'Your billing query is being reviewed.')
        self.client.post(path,{'action':'reply','text':'Here is my clarification.','internal':'on'})
        case.refresh_from_db();self.assertEqual(case.status,'open')
        self.assertFalse(case.messages.get(text='Here is my clarification.').internal)

    def test_routing_cannot_weaken_medical_access(self):
        case=self.create_case()
        path=reverse('support_case',args=[case.pk])
        self.client.force_login(self.admin)
        response=self.client.post(path,{'action':'route','category':'technical','status':'open','priority':'routine','assigned_to':''})
        self.assertContains(response,'different access group')
        case.refresh_from_db();self.assertEqual(case.category,'reports')
        self.client.post(path,{'action':'route','category':'reports','status':'assigned','priority':'routine','assigned_to':self.doctor2.pk})
        case.refresh_from_db();self.assertEqual(case.assigned_to,self.doctor2)
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(path).status_code,404)

    def test_draft_clear_expiry_and_secret_redaction(self):
        self.client.force_login(self.patient)
        self.ask('human support password should-not-be-stored')
        self.assertNotIn('should-not-be-stored',str(self.client.session.get('support_draft')))
        self.client.post(reverse('assistant_api'),{'action':'clear'},content_type='application/json')
        self.assertNotIn('support_draft',self.client.session)
        session=self.client.session;session['support_draft']={'summary':'EXPIRED PRIVATE DRAFT','updated':0};session.save()
        self.assertNotContains(self.client.get(reverse('support_create')),'EXPIRED PRIVATE DRAFT')

    def test_emergency_precedes_record_queries_and_handoff(self):
        self.client.force_login(self.patient)
        result=self.ask('chest pain and my report is missing').json()
        self.assertIn('112',result['text'])
        self.assertEqual(SupportCase.objects.count(),0)
        self.assertNotIn('support_draft',self.client.session)

    def test_after_time_filter_and_same_doctor_context(self):
        self.ask('Test Doctor')
        result=self.ask('I want to book with the same doctor after 5 pm').json()
        self.assertTrue(result['cards'])
        self.assertNotIn('Other Doctor',str(result))
        self.assertIn('AM or PM',self.ask('Who is available after 5?').json()['text'])

    def test_case_csrf_and_route_roles(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('support_create'),{}).status_code,403)
        for user in [self.doctor,self.reception,self.pharmacist,self.admin]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('support_create')).status_code,403)
            self.assertEqual(self.client.get(reverse('support_queue')).status_code,200)

    def test_database_failure_rolls_back_case_and_safely_recovers(self):
        self.client.force_login(self.patient)
        with patch('care.support.SupportCase.objects.create', side_effect=OperationalError('private secret')):
            response=self.client.post(reverse('support_create'),{'category':'technical','summary':'Synthetic failure','request_key':uuid.uuid4(),'consent':'on'})
        self.assertEqual(response.status_code,503)
        self.assertNotContains(response,'private secret',status_code=503)
        self.assertEqual(SupportCase.objects.count(),0)

    def test_report_followup_and_multi_record_reference_clarification(self):
        self.client.force_login(self.patient)
        self.ask('I cannot download my report')
        result=self.ask('It has been pending for four days').json()
        self.assertIn('SYNTHETIC BLOOD',str(result))
        summary=self.client.session['support_draft']['summary']
        self.assertIn('cannot download',summary)
        self.assertIn('four days',summary)

    def test_sensitive_routing_prepares_only_correct_team(self):
        self.client.force_login(self.patient)
        for question, category in [('This is not my report','privacy'),('I want to report abuse','clinical'),('Can you diagnose me?','clinical'),('My medication caused a reaction','pharmacy')]:
            with self.subTest(question=question):
                response=self.ask(question)
                self.assertEqual(response.status_code,200)
                self.assertEqual(self.client.session['support_draft']['category'],category)
                self.assertEqual(SupportCase.objects.count(),0)
