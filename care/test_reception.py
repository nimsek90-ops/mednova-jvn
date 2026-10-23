from unittest.mock import patch
from django.test import TestCase,Client
from django.db import OperationalError
from django.urls import reverse
from . import tests as fixtures
from .models import User,PatientRegistration,Appointment,Department,Specialty,DoctorProfile,QueueEntry


class ReceptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.Workflows.setUpTestData.__func__(cls)
        cls.specialty=Specialty.objects.create(name='Synthetic Specialist',normalized_name='synthetic specialist')
        cls.specialty.departments.add(cls.department)
        cls.doctor.doctor_profile.specialties.add(cls.specialty)

    def setUp(self):
        self.client.force_login(self.reception)

    def payload(self,**updates):
        data={'name':'Synthetic New Patient','email':'new-desk@example.test','phone':'+91 98765 43210','address':'Synthetic address','emergency_name':'Synthetic contact','emergency_phone':'9876543211','consent':'on'}
        data.update(updates);return data

    def test_register_patient_mrn_success_actions_no_staff_password(self):
        response=self.client.post(reverse('reception_register'),self.payload())
        self.assertEqual(response.status_code,302)
        user=User.objects.get(email='new-desk@example.test')
        self.assertEqual(user.role,'patient');self.assertFalse(user.has_usable_password())
        self.assertEqual(user.phone,'9876543210')
        self.assertEqual(user.registration.address,'Synthetic address')
        page=self.client.get(response.url)
        self.assertContains(page,user.registration.display_mrn)
        self.assertContains(page,f'/doctors/?patient={user.pk}')

    def test_duplicate_email_and_phone_safe_selection(self):
        self.patient.phone='98765 43210';self.patient.save()
        original=self.patient.name
        response=self.client.post(reverse('reception_register'),self.payload(email=self.patient.email))
        self.assertContains(response,'existing account')
        self.assertEqual(User.objects.filter(email=self.patient.email).count(),1)
        response=self.client.post(reverse('reception_register'),self.payload())
        self.assertContains(response,'Use existing record')
        self.assertFalse(User.objects.filter(email='new-desk@example.test').exists())
        self.patient.refresh_from_db();self.assertEqual(self.patient.name,original)
        response=self.client.post(reverse('reception_register'),self.payload(duplicate_reviewed='on'))
        self.assertEqual(response.status_code,302)

    def test_name_and_mrn_duplicate_review_does_not_overwrite(self):
        response=self.client.post(reverse('reception_register'),self.payload(name=self.patient.name))
        self.assertContains(response,'Possible existing patient')
        response=self.client.post(reverse('reception_register'),self.payload(existing_mrn=self.patient.registration.display_mrn,duplicate_reviewed='on'))
        self.assertContains(response,'Use patient search')
        self.assertFalse(User.objects.filter(email='new-desk@example.test').exists())

    def test_validation_fields_and_database_error(self):
        for change in [{'phone':'abc123'},{'phone':'12345'},{'email':'invalid'},{'name':'1234'},{'name':''},{'consent':''}]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post(reverse('reception_register'),self.payload(**change)).status_code,200)
                self.assertFalse(User.objects.filter(email='new-desk@example.test').exists())
        with patch('care.reception.User.objects.create_user',side_effect=OperationalError('private database details')):
            response=self.client.post(reverse('reception_register'),self.payload())
        self.assertEqual(response.status_code,503)
        self.assertNotContains(response,'private database details',status_code=503)

    def test_search_mrn_and_formatted_phone(self):
        self.patient.phone='98765 43210';self.patient.save()
        for query in [self.patient.name,self.patient.email,self.patient.registration.display_mrn,'+91 9876543210']:
            with self.subTest(query=query):
                self.assertContains(self.client.get(reverse('patients'),{'q':query}),self.patient.name)
                self.assertContains(self.client.get(reverse('reception_booking'),{'q':query}),self.patient.name)

    def test_new_patient_to_real_booking_and_retry(self):
        self.client.post(reverse('reception_register'),self.payload())
        user=User.objects.get(email='new-desk@example.test')
        response=self.client.get(reverse('doctors'),{'patient':user.pk,'department':self.department.pk,'specialty':self.specialty.pk})
        self.assertContains(response,'Booking for Synthetic New Patient')
        self.assertContains(response,self.doctor.name)
        self.assertNotContains(response,self.doctor2.name)
        path=reverse('booking',args=[self.doctor.pk])+f'?patient={user.pk}'
        response=self.client.get(path)
        self.assertContains(response,f'<option value="{user.pk}" selected>')
        data={'patient':user.pk,'slot':self.slot2.pk,'mode':'in_person','reason':'Synthetic receptionist booking','consent':'on'}
        response=self.client.post(path,data)
        self.assertEqual(response.status_code,302)
        self.assertTrue(Appointment.objects.filter(patient=user,slot=self.slot2).exists())
        self.client.post(path,data)
        self.assertEqual(Appointment.objects.filter(patient=user,slot=self.slot2).count(),1)

    def test_doctor_catalogue_no_fake_profiles_or_services(self):
        self.assertGreaterEqual(Specialty.objects.count(),100)
        for name in ['Dermatology','Dentistry','General Surgery','Cardiology','Clinical Genetics']:
            self.assertTrue(Specialty.objects.filter(name=name).exists())
        self.assertEqual(DoctorProfile.objects.count(),2)
        self.assertFalse(Department.objects.get(name='Dermatology').active)
        self.assertContains(self.client.get(reverse('specialty_catalogue'),{'q':'Dermatology'}),'No doctors currently listed')
        empty=Specialty.objects.get(name='Dermatology')
        response=self.client.get(reverse('doctors'),{'specialty':empty.pk})
        self.assertContains(response,'No matching doctors')

    def test_admin_specialty_edit_assign_and_deactivate(self):
        self.client.force_login(self.admin)
        path=reverse('doctor_specialties',args=[self.doctor2.pk])
        self.assertEqual(self.client.post(path,{'specialties':[self.specialty.pk]}).status_code,302)
        self.assertTrue(self.doctor2.doctor_profile.specialties.filter(pk=self.specialty.pk).exists())
        self.client.post(reverse('specialty_edit',args=[self.specialty.pk]),{'name':self.specialty.name,'departments':[self.department.pk]})
        self.specialty.refresh_from_db();self.assertFalse(self.specialty.active)
        self.client.logout()
        self.assertNotContains(self.client.get(reverse('doctor_detail',args=[self.doctor.pk])),self.specialty.name)

    def test_invalid_department_assignment_and_spelling_duplicate(self):
        self.client.force_login(self.admin)
        other=Specialty.objects.get(name='Dermatology')
        response=self.client.post(reverse('doctor_specialties',args=[self.doctor.pk]),{'specialties':[other.pk]})
        self.assertEqual(response.status_code,200)
        self.assertFalse(self.doctor.doctor_profile.specialties.filter(pk=other.pk).exists())
        response=self.client.post(reverse('specialty_create'),{'name':'  orthopaedics ','departments':[self.department.pk],'active':'on'})
        self.assertContains(response,'already exists')

    def test_role_denials_and_csrf(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('reception_register'),self.payload()).status_code,403)
        for user in [self.patient,self.doctor,self.pharmacist]:
            self.client.force_login(user)
            for route in ['reception_desk','reception_register','reception_booking']:
                self.assertEqual(self.client.get(reverse(route)).status_code,403)
        self.client.force_login(self.reception)
        self.assertEqual(self.client.get(reverse('specialty_create')).status_code,403)
        self.assertEqual(self.client.get(reverse('doctor_specialties',args=[self.doctor.pk])).status_code,403)
        self.assertEqual(self.client.get(reverse('schedule_rules')).status_code,403)

    def test_reception_dashboard_and_no_clinical_reason(self):
        response=self.client.get(reverse('dashboard'))
        self.assertContains(response,'+ Register New Patient')
        self.assertContains(response,'Receptionist Desk')
        self.assertNotContains(self.client.get(reverse('reception_patient',args=[self.patient.pk])),'A private clinical reason')
