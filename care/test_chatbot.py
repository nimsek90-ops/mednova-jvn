from datetime import datetime, time, timedelta
from unittest.mock import patch
from django.db import OperationalError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from . import tests as fixtures
from .models import Appointment, Department, ScheduleBlock, HospitalFAQ, AssistantEscalation


class ChatbotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)
        cls.department, _ = Department.objects.get_or_create(name='Cardiology')
        cls.department.active = True
        cls.department.save()
        from .models import DoctorProfile
        DoctorProfile.objects.filter(user__in=[cls.doctor,cls.doctor2]).update(department=cls.department)
        cls.slot2.start = timezone.make_aware(datetime.combine(timezone.localdate()+timedelta(days=1), time(9)))
        cls.slot2.save()

    def ask(self, text):
        return self.client.post(reverse('assistant_api'), {'message': text}, content_type='application/json')

    def test_specialty_synonyms_typos_and_context(self):
        for text in ['heart specialist', 'Show cardiologists', 'cardiolgy doctor', 'Who treats heart problems?']:
            with self.subTest(text=text):
                result = self.ask(text).json()
                self.assertEqual(len(result['cards']), 2)
        result = self.ask('Which one is available tomorrow morning?').json()
        self.assertTrue(any('09:00 AM' in d for c in result['cards'] for d in c['details']))

    def test_no_fabricated_specialty_or_today_slots(self):
        self.assertEqual(self.ask('skin doctor').json()['cards'], [])
        result = self.ask('cardiologist available today').json()
        self.assertEqual(len(result['cards']), 2)
        self.assertTrue(all(any('no verified slots' in d for d in c['details']) for c in result['cards']))

    def test_leave_not_listed_and_no_mutation(self):
        ScheduleBlock.objects.create(doctor=self.doctor, start=self.slot2.start-timedelta(minutes=1), end=self.slot2.start+timedelta(hours=1), reason='leave')
        result = self.ask('heart doctor tomorrow morning').json()
        self.assertFalse(any('Available:' in d for c in result['cards'] for d in c['details']))
        self.slot2.refresh_from_db()
        self.assertFalse(self.slot2.booked)

    def test_own_records_and_no_private_history(self):
        self.assertIn('Sign in', self.ask('my reports').json()['text'])
        self.client.force_login(self.other)
        self.assertNotIn(self.appt.short_id, str(self.ask('my appointments').json()))
        self.client.force_login(self.patient)
        self.assertIn(self.appt.short_id, str(self.ask('my appointments').json()))
        self.assertNotIn(self.appt.short_id, str(self.client.session.get('hospital_chat')))

    def test_approved_faq_only(self):
        HospitalFAQ.objects.create(question='Parking policy', answer='Approved parking information', approved=True)
        HospitalFAQ.objects.create(question='Parking policy', answer='SECRET DRAFT', approved=False)
        text = str(self.ask('parking policy').json())
        self.assertIn('Approved parking information', text)
        self.assertNotIn('SECRET DRAFT', text)

    def test_emergency_and_handoff(self):
        self.assertIn('112', self.ask('chest pain').json()['text'])
        self.client.force_login(self.patient)
        self.ask('human support'); self.ask('human support')
        self.assertEqual(AssistantEscalation.objects.filter(patient=self.patient).count(), 0)
        self.assertIn('support_draft', self.client.session)

    def test_validation_csrf_and_errors(self):
        self.assertEqual(self.ask('').status_code, 400)
        self.assertEqual(self.ask('x'*501).status_code, 400)
        self.assertEqual(self.client.post(reverse('assistant_api'), '[]', content_type='application/json').status_code, 400)
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('assistant_api'), {'message':'doctors'}, content_type='application/json').status_code, 403)
        with patch('care.chatbot.answer', side_effect=OperationalError('private connection secret')):
            result = self.ask('doctors')
        self.assertEqual(result.status_code, 503)
        self.assertNotIn('secret', result.content.decode())

    def test_clear_and_question_not_retained(self):
        self.ask('heart specialist PRIVATEQUESTION')
        self.assertNotIn('PRIVATEQUESTION', str(self.client.session.get('hospital_chat')))
        self.client.post(reverse('assistant_api'), {'action':'clear'}, content_type='application/json')
        self.assertNotIn('hospital_chat', self.client.session)

    def test_ui_and_real_links(self):
        self.assertContains(self.client.get(reverse('assistant')), 'chat-compose')
        result = self.ask('Find doctors').json()
        for card in result['cards']:
            self.assertEqual(self.client.get(card['links'][0]['url']).status_code, 200)

    def test_slot_selection_requires_confirmation_and_prevents_duplicate(self):
        self.client.force_login(self.other)
        result = self.ask('heart specialist tomorrow morning').json()
        selected = [a for c in result['cards'] for a in c['links'] if a['label'].startswith('Select ')][0]
        response = self.client.get(selected['url'])
        self.assertContains(response, f'value="{self.slot2.pk}" data-label=')
        self.assertEqual(Appointment.objects.filter(slot=self.slot2).count(), 0)
        payload = {'slot':self.slot2.pk, 'mode':'in_person', 'reason':'Synthetic chatbot confirmation', 'consent':'on'}
        self.assertEqual(self.client.post(selected['url'], payload).status_code, 302)
        self.client.post(selected['url'], payload)
        self.assertEqual(Appointment.objects.filter(slot=self.slot2).count(), 1)

    def test_rate_limit_and_stock_authorization(self):
        self.assertIn('restricted', self.ask('medicine stock').json()['text'])
        with patch('care.chatbot.limited', return_value=True):
            response = self.ask('doctors')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '60')

    def test_overlapping_unbooked_slot_is_not_advertised(self):
        self.slot2.start = self.slot.start + timedelta(minutes=1)
        self.slot2.save()
        result = self.ask('Find doctors').json()
        self.assertFalse(any('Available:' in d for c in result['cards'] for d in c['details']))
