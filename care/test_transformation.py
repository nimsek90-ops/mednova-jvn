from django.test import TestCase, SimpleTestCase
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from . import tests as fixtures
from mednova.database import postgres_database
from mednova.hosting import validate_vercel


class PostgreSQLConfiguration(SimpleTestCase):
    def test_production_requires_verified_tls_and_private_schema(self):
        env = dict(PGHOST='database.example.test', PGDATABASE='postgres',
                   PGUSER='mednova_runtime', PGPASSWORD='synthetic-test-only')
        with self.assertRaises(ImproperlyConfigured):
            postgres_database(env)
        env.update(PGSSLROOTCERT='/approved/provider-ca.pem')
        result = postgres_database(env)
        self.assertEqual(result['ENGINE'], 'django.db.backends.postgresql')
        self.assertIsNone(result['OPTIONS']['prepare_threshold'])
        self.assertEqual(result['CONN_MAX_AGE'], 0)
        self.assertIn('search_path=mednova ', result['OPTIONS']['options'])
        self.assertNotIn(',public', result['OPTIONS']['options'])
        self.assertTrue(result['DISABLE_SERVER_SIDE_CURSORS'])
        for schema in ['public', 'mednova; DROP SCHEMA public', '../private']:
            with self.assertRaises(ImproperlyConfigured):
                postgres_database(dict(env, PGSCHEMA=schema))

    def test_vercel_rejects_postgres_test_flag(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_vercel({'APP_ENV':'production','MEDNOVA_TEST_POSTGRES':'1'})


class ProductTransformation(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)

    def test_schema_explorer_permissions_and_no_record_contents(self):
        url = reverse('schema_explorer')
        self.assertEqual(self.client.get(url).status_code, 302)
        for user in [self.patient, self.doctor, self.reception, self.pharmacist]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        from unittest.mock import patch
        from django.db import connection
        from contextlib import nullcontext
        # SQLite constraint introspection uses PRAGMA, not a record sampler.
        guard = patch.object(connection.introspection, 'get_table_description', side_effect=AssertionError('Schema explorer must never sample private rows')) if connection.vendor in ('mysql','postgresql') else nullcontext()
        with guard:
            response = self.client.get(url, {'table':'care_user'})
        self.assertContains(response, 'must_change_password')
        self.assertNotContains(response, self.patient.email)
        self.assertNotContains(response, self.patient.password)
        self.assertEqual(self.client.get(url, {'table':'auth.users'}).status_code,404)
        self.assertEqual(self.client.post(url, {}).status_code,405)

    def test_schema_search_and_actual_directory_availability(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('schema_explorer'), {'q':'department'})
        self.assertEqual([t['name'] for t in response.context['tables']],['care_department','care_specialty_departments'])
        self.client.logout()
        response = self.client.get(reverse('doctors'))
        profile = next(doc for doc in response.context['doctors'] if doc.user_id==self.doctor.pk)
        self.assertIsNotNone(profile.next_slot)
        self.assertContains(response, 'Next published slot')

    def test_directory_never_advertises_slots_beyond_booking_window(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Slot
        Slot.objects.filter(doctor=self.doctor).update(active=False)
        Slot.objects.create(doctor=self.doctor,start=timezone.now()+timedelta(days=91))
        response=self.client.get(reverse('doctors'),{'available':'1'})
        self.assertNotIn(self.doctor.pk,[doc.user_id for doc in response.context['doctors']])
        response=self.client.get(reverse('doctors'))
        doctor=next(doc for doc in response.context['doctors'] if doc.user_id==self.doctor.pk)
        self.assertIsNone(doctor.next_slot)
