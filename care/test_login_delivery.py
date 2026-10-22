from django.test import TestCase
from django.urls import reverse
from . import tests as workflow_fixtures
from .models import RateBucket, User


class RoleLoginDelivery(TestCase):
    @classmethod
    def setUpTestData(cls):
        workflow_fixtures.Workflows.setUpTestData.__func__(cls)

    def test_five_role_links_and_matching_login(self):
        accounts = [self.patient, self.doctor, self.reception, self.pharmacist, self.admin]
        for account in accounts:
            with self.subTest(role=account.role):
                self.client.logout()
                RateBucket.objects.all().delete()
                response = self.client.get(reverse('login'), {'role': account.role})
                self.assertEqual(response.context['selected_role'], account.role)
                self.assertContains(response, 'aria-current="page"')
                for role, label in User.ROLES:
                    self.assertContains(response, '?role=' + role)
                response = self.client.post(reverse('login'), {'email':account.email,
                    'password':'Correct-Hospital-Pass12','role':account.role})
                self.assertRedirects(response, reverse('dashboard'))
                self.assertEqual(int(self.client.session['_auth_user_id']), account.pk)
                self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_all_cross_role_submissions_denied(self):
        for account in [self.patient, self.doctor, self.reception, self.pharmacist, self.admin]:
            for role, label in User.ROLES:
                if role == account.role:
                    continue
                with self.subTest(account=account.role, selected=role):
                    RateBucket.objects.all().delete()
                    response = self.client.post(reverse('login'), {'email':account.email,
                        'password':'Correct-Hospital-Pass12','role':role})
                    self.assertContains(response, 'does not belong to the selected workspace')
                    self.assertNotIn('_auth_user_id', self.client.session)

    def test_invalid_inactive_missing_role_and_generic_login(self):
        for account in [self.patient, self.doctor, self.reception, self.pharmacist, self.admin]:
            response = self.client.post(reverse('login'), {'email':account.email,
                'password':'incorrect','role':account.role})
            self.assertContains(response, 'incorrect, or the account is inactive')
            self.assertNotIn('_auth_user_id', self.client.session)
        self.patient.is_active = False
        self.patient.save()
        response = self.client.post(reverse('login'), {'email':self.patient.email,
            'password':'Correct-Hospital-Pass12','role':'patient'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.doctor.role = 'invalid'
        self.doctor.save()
        response = self.client.post(reverse('login'), {'email':self.doctor.email,
            'password':'Correct-Hospital-Pass12'})
        self.assertContains(response, 'no supported workspace')
        response = self.client.post(reverse('login'), {'email':self.admin.email,
            'password':'Correct-Hospital-Pass12'})
        self.assertRedirects(response, reverse('dashboard'))

    def test_role_navigation_preserves_safe_destination_and_rejects_external(self):
        response = self.client.get(reverse('login'), {'role':'admin','next':'https://example.test'})
        self.assertEqual(response.context['next'], reverse('dashboard'))
        response = self.client.get(reverse('login'), {'role':'patient','next':reverse('appointments')})
        self.assertContains(response, 'name="next" value="' + reverse('appointments') + '"')
