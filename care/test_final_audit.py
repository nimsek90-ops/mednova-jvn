import json
import os
import secrets
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from . import tests as fixtures
from .models import User, Appointment

class FinalAuditWorkflows(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)

    def test_targeted_admin_is_idempotent_and_requires_change(self):
        first=secrets.token_urlsafe(28)
        email='synthetic-bootstrap-admin@example.test'
        log=StringIO()
        with patch.dict(os.environ,{'MEDNOVA_ADMIN_EMAIL':email,'MEDNOVA_ADMIN_PASSWORD':first}):
            call_command('ensure_admin',noinput=True,stdout=log)
        user=User.objects.get(email=email)
        self.assertTrue(user.is_staff and user.is_superuser and user.is_active and user.must_change_password)
        self.assertEqual((user.role,user.approval),('admin','approved'))
        self.assertTrue(user.check_password(first))
        original=user.password
        with patch.dict(os.environ,{'MEDNOVA_ADMIN_EMAIL':email,'MEDNOVA_ADMIN_PASSWORD':secrets.token_urlsafe(28)}):
            call_command('ensure_admin',noinput=True,stdout=log)
        user.refresh_from_db()
        self.assertEqual(user.password,original)
        self.assertEqual(User.objects.filter(email=email).count(),1)
        self.assertNotIn(first,log.getvalue())
        self.assertTrue(self.client.login(email=email,password=first))
        self.assertRedirects(self.client.get(reverse('data_management')),reverse('password'))
        self.assertRedirects(self.client.get(reverse('dashboard')),reverse('password'))
        replacement=secrets.token_urlsafe(28)
        response=self.client.post(reverse('password'),{'old_password':first,'new_password1':replacement,'new_password2':replacement})
        self.assertEqual(response.status_code,302)
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)
        self.assertTrue(user.check_password(replacement))
        self.assertEqual(self.client.get(reverse('data_management')).status_code,200)

    def test_admin_setup_never_promotes_conflicting_patient(self):
        original=self.patient.password
        with patch.dict(os.environ,{'MEDNOVA_ADMIN_EMAIL':self.patient.email,'MEDNOVA_ADMIN_PASSWORD':secrets.token_urlsafe(28)}):
            with self.assertRaises(CommandError):
                call_command('ensure_admin',noinput=True,stdout=StringIO())
        self.patient.refresh_from_db()
        self.assertEqual((self.patient.role,self.patient.password),('patient',original))
        self.assertFalse(self.patient.is_staff or self.patient.is_superuser)

    def test_admin_missing_identity_and_weak_password_fail(self):
        with patch.dict(os.environ,{'MEDNOVA_ADMIN_EMAIL':'','MEDNOVA_ADMIN_PASSWORD':''}):
            with self.assertRaises(CommandError): call_command('ensure_admin',noinput=True,stdout=StringIO())
        with patch.dict(os.environ,{'MEDNOVA_ADMIN_EMAIL':'synthetic-weak@example.test','MEDNOVA_ADMIN_PASSWORD':'123'}):
            with self.assertRaises(CommandError): call_command('ensure_admin',noinput=True,stdout=StringIO())
        self.assertFalse(User.objects.filter(email='synthetic-weak@example.test').exists())

    def test_data_portal_scoping_search_sort_and_no_clinical_data(self):
        for user in [self.patient,self.doctor,self.reception,self.pharmacist]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('data_management')).status_code,403)
        self.client.force_login(self.admin)
        response=self.client.get(reverse('data_management'),{'q':'Departments','sort':'count'})
        self.assertContains(response,'Departments')
        self.assertNotContains(response,self.appt.reason)
        self.assertEqual(self.client.post(reverse('data_management'),{}).status_code,405)
        self.assertEqual(len(response.context['entities']),1)
        from .models import Department
        self.assertEqual(response.context['entities'][0]['count'],Department.objects.count())

    def test_booking_date_groups_and_real_task_context(self):
        self.client.force_login(self.patient)
        response=self.client.get(reverse('booking',args=[self.doctor.pk]))
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['available_dates'])
        self.assertTrue(response.context['slot_days'])
        flattened=[slot.pk for _,slots in response.context['slot_days'] for slot in slots]
        self.assertEqual(set(flattened),{slot.pk for slot in response.context['slots']})
        self.assertContains(response,'Your visit details')
        dashboard=self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard.context['next_appointment'].pk,self.appt.pk)
        self.assertNotContains(dashboard,'A little more clarity.')

    def test_schema_inventory_uses_actual_backend_and_no_row_contents(self):
        with TemporaryDirectory() as folder:
            output=Path(folder)/'schema.json'
            if connection.vendor not in ('mysql','postgresql'):
                with self.assertRaises(CommandError):call_command('database_inventory',output=str(output),stdout=StringIO())
                self.assertFalse(output.exists())
            else:
                with patch.object(connection.introspection, 'get_table_description', side_effect=AssertionError('Metadata export must not sample records')):
                    call_command('database_inventory',output=str(output),stdout=StringIO())
                report=json.loads(output.read_text())
                self.assertEqual(report['engine'],connection.vendor)
                self.assertTrue(any(t['table']=='care_user' for t in report['tables']))
                self.assertNotIn(self.patient.email,output.read_text())
                self.assertNotIn(self.appt.reason,output.read_text())
                self.assertTrue(all(o['count']==0 for t in report['tables'] for o in t['orphan_counts']))

    def test_checkin_action_matches_backend_eligibility(self):
        from django.utils import timezone
        self.appt.status='confirmed'
        self.appt.mode='in_person'
        self.appt.save()
        self.client.force_login(self.reception)
        response=self.client.get(reverse('appointment',args=[self.appt.pk]))
        self.assertNotContains(response,'>Check in patient<')
        self.assertContains(response,'Check-in opens on the appointment date.')
        self.appt.slot.start=timezone.now()
        self.appt.slot.save()
        self.assertContains(self.client.get(reverse('appointment',args=[self.appt.pk])),'Check in patient')
