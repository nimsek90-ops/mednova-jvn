from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock
import hashlib, hmac, json
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.urls import reverse
from django.template.loader import get_template
from pathlib import Path
from .models import *
from .services import book, BookingError, dispense, change_status
from .forms import UploadForm, RegisterForm
from .security import limited


class Workflows(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.patient = User.objects.create_user(
            "patient@example.test", "Correct-Hospital-Pass12", name="Test Patient"
        )
        cls.other = User.objects.create_user(
            "other@example.test", "Correct-Hospital-Pass12", name="Other Patient"
        )
        cls.doctor = User.objects.create_user(
            "doctor@example.test",
            "Correct-Hospital-Pass12",
            name="Test Doctor",
            role="doctor",
        )
        cls.doctor2 = User.objects.create_user(
            "doctor2@example.test",
            "Correct-Hospital-Pass12",
            name="Other Doctor",
            role="doctor",
        )
        cls.admin = User.objects.create_superuser(
            "admin@example.test", "Correct-Hospital-Pass12", name="Hospital Admin"
        )
        cls.reception = User.objects.create_user(
            "reception@example.test",
            "Correct-Hospital-Pass12",
            name="Reception",
            role="receptionist",
        )
        cls.pharmacist = User.objects.create_user(
            "pharmacy@example.test",
            "Correct-Hospital-Pass12",
            name="Pharmacy",
            role="pharmacist",
        )
        cls.pending = User.objects.create_user(
            "pending@example.test",
            "Correct-Hospital-Pass12",
            name="Pending Doctor",
            role="doctor",
            approval="pending",
        )
        cls.department = Department.objects.create(name="Test department")
        for i, u in enumerate([cls.doctor, cls.doctor2]):
            DoctorProfile.objects.create(
                user=u,
                department=cls.department,
                qualification="Test qualification",
                registration_number=f"TEST-{i}",
                fee=250,
            )
        cls.slot = Slot.objects.create(
            doctor=cls.doctor, start=timezone.now() + timedelta(days=1)
        )
        cls.slot2 = Slot.objects.create(
            doctor=cls.doctor, start=timezone.now() + timedelta(days=1, minutes=12)
        )
        cls.appt = book(cls.patient, cls.slot.pk, "video", "A private clinical reason")
        Hospital.objects.create()

    def sign(self, user):
        self.client.force_login(user)

    def test_password_is_argon2_hash(self):
        self.assertTrue(self.patient.password.startswith("argon2$"))
        self.assertNotIn("Correct", self.patient.password)

    def test_email_password_login_and_role_from_database(self):
        r = self.client.post(
            "/login/",
            {
                "email": "PATIENT@EXAMPLE.TEST",
                "password": "Correct-Hospital-Pass12",
                "role": "admin",
            },
        )
        self.assertRedirects(r, "/dashboard/")
        self.assertEqual(self.client.get("/admin/staff/").status_code, 403)

    def test_registration_cannot_create_admin(self):
        f = RegisterForm(
            {
                "name": "Attack",
                "email": "new@example.test",
                "role": "admin",
                "password1": "Correct-Hospital-Pass12",
                "password2": "Correct-Hospital-Pass12",
                "consent": True,
            }
        )
        self.assertFalse(f.is_valid())

    def test_staff_registration_pending(self):
        f = RegisterForm(
            {
                "name": "New Doctor",
                "email": "new@example.test",
                "role": "doctor",
                "password1": "Good-New-Doctor-Pass19",
                "password2": "Good-New-Doctor-Pass19",
                "consent": True,
            }
        )
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.save().approval, "pending")

    def test_simple_patient_registration(self):
        self.client.post(
            "/register/",
            {
                "name": "New Patient",
                "email": "new@example.test",
                "role": "patient",
                "password1": "Good-New-Patient-Pass19",
                "password2": "Good-New-Patient-Pass19",
                "consent": "on",
            },
        )
        u = User.objects.get(email="new@example.test")
        self.assertEqual(u.approval, "approved")
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)

    def test_pending_staff_blocked(self):
        self.sign(self.pending)
        self.assertRedirects(self.client.get("/availability/"), "/dashboard/")
        self.assertContains(self.client.get("/dashboard/"), "Account awaiting review")

    def test_admin_approval_requires_doctor_profile(self):
        self.sign(self.admin)
        self.client.post(
            "/admin/staff/", {"user": self.pending.pk, "action": "approved"}
        )
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.approval, "pending")

    def test_admin_approves_doctor(self):
        DoctorProfile.objects.create(
            user=self.pending,
            department=self.department,
            qualification="Test",
            registration_number="PENDING-1",
        )
        self.sign(self.admin)
        self.client.post(
            "/admin/staff/", {"user": self.pending.pk, "action": "approved"}
        )
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.approval, "approved")

    def test_patient_cannot_read_other_patient_appointment(self):
        self.sign(self.other)
        self.assertEqual(
            self.client.get(reverse("appointment", args=[self.appt.pk])).status_code,
            404,
        )

    def test_other_doctor_cannot_read_appointment(self):
        self.sign(self.doctor2)
        self.assertEqual(
            self.client.get(reverse("appointment", args=[self.appt.pk])).status_code,
            404,
        )

    def test_reception_cannot_see_clinical_reason(self):
        self.sign(self.reception)
        self.assertNotContains(
            self.client.get(reverse("appointment", args=[self.appt.pk])),
            "A private clinical reason",
        )

    def test_admin_cannot_see_clinical_reason(self):
        self.sign(self.admin)
        self.assertNotContains(
            self.client.get(reverse("appointment", args=[self.appt.pk])),
            "A private clinical reason",
        )

    def test_duplicate_slot_is_rejected(self):
        with self.assertRaises(BookingError):
            book(self.other, self.slot.pk, "in_person", "Test")

    def test_patient_overlapping_doctors_rejected(self):
        s = Slot.objects.create(doctor=self.doctor2, start=self.slot.start)
        with self.assertRaises(BookingError):
            book(self.patient, s.pk, "in_person", "Test")

    def test_reschedule_releases_old_slot(self):
        book(self.patient, self.slot2.pk, "video", "Changed", self.appt)
        self.slot.refresh_from_db()
        self.slot2.refresh_from_db()
        self.appt.refresh_from_db()
        self.assertFalse(self.slot.booked)
        self.assertTrue(self.slot2.booked)
        self.assertEqual(self.appt.status, "pending")

    def test_cancellation_releases_slot_and_marks_refund(self):
        Payment.objects.filter(appointment=self.appt).update(status="paid")
        change_status(self.appt, self.patient, "cancelled")
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.booked)
        self.assertEqual(
            Payment.objects.get(appointment=self.appt).status, "refund_due"
        )

    def test_patient_cannot_confirm(self):
        self.sign(self.patient)
        r = self.client.post(
            reverse("appointment_action", args=[self.appt.pk]), {"action": "confirmed"}
        )
        self.assertEqual(r.status_code, 403)

    def test_get_cannot_mutate(self):
        self.sign(self.patient)
        self.assertEqual(
            self.client.get(
                reverse("appointment_action", args=[self.appt.pk])
            ).status_code,
            405,
        )

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.patient)
        self.assertEqual(
            c.post(
                reverse("appointment_action", args=[self.appt.pk]),
                {"action": "cancelled"},
            ).status_code,
            403,
        )

    def test_weak_password_rejected(self):
        f = RegisterForm(
            {
                "name": "New",
                "email": "new@example.test",
                "role": "patient",
                "password1": "12345678",
                "password2": "12345678",
                "consent": True,
            }
        )
        self.assertFalse(f.is_valid())

    def test_xss_escaped_in_profile_and_appointment(self):
        self.patient.name = "<script>alert(1)</script>"
        self.patient.save()
        self.sign(self.patient)
        r = self.client.get("/dashboard/")
        self.assertNotContains(r, "<script>alert(1)</script>")
        self.assertContains(r, "&lt;script&gt;")

    def test_security_headers_and_no_cors(self):
        r = self.client.get("/login/")
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", r["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", r)
        self.assertIn("no-store", r["Cache-Control"])

    def test_rate_limiter(self):
        self.assertFalse(limited("unique", 2, 60))
        self.assertFalse(limited("unique", 2, 60))
        self.assertTrue(limited("unique", 2, 60))

    def test_private_paths_not_exposed(self):
        for url in [
            "/.env",
            "/.git/config",
            "/private_uploads/anything",
            "/manage.py",
            "/settings.py",
        ]:
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_unapproved_doctor_not_public(self):
        self.assertNotContains(self.client.get("/doctors/"), "Pending Doctor")

    def test_localized_login(self):
        for lang, word in [("mr", "प्रवेश करा"), ("hi", "लॉग इन करें")]:
            self.client.post("/language/", {"language": lang})
            self.assertContains(self.client.get("/login/"), word)

    def test_all_role_dashboards_render(self):
        for u in [
            self.patient,
            self.doctor,
            self.reception,
            self.pharmacist,
            self.admin,
        ]:
            self.sign(u)
            self.assertEqual(self.client.get("/dashboard/").status_code, 200)

    def test_relevant_pages_render(self):
        matrix = [
            (
                self.admin,
                [
                    "/admin/staff/",
                    "/admin/departments/",
                    "/admin/settings/",
                    "/admin/audit/",
                    "/inventory/",
                    "/appointments/",
                ],
            ),
            (
                self.patient,
                [
                    "/doctors/",
                    "/profile/",
                    "/password/",
                    "/prescriptions/",
                    "/appointments/",
                    reverse("booking", args=[self.doctor.pk]),
                    reverse("appointment", args=[self.appt.pk]),
                    reverse("upload", args=[self.appt.pk]),
                ],
            ),
            (self.doctor, ["/availability/", "/profile/", "/prescriptions/"]),
            (self.pharmacist, ["/inventory/", "/prescriptions/"]),
        ]
        for u, paths in matrix:
            self.sign(u)
            for path in paths:
                self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_all_templates_compile(self):
        for path in Path(__file__).parent.parent.joinpath("templates").rglob("*.html"):
            get_template(
                str(path.relative_to(Path(__file__).parent.parent / "templates"))
            )

    def test_forged_image_rejected(self):
        f = UploadForm(
            {"title": "Test"},
            {
                "file": SimpleUploadedFile(
                    "file.jpg", b"<script>malicious</script>", content_type="image/jpeg"
                )
            },
        )
        self.assertFalse(f.is_valid())

    def test_pdf_fails_closed_without_scanner(self):
        f = UploadForm(
            {"title": "Test"},
            {"file": SimpleUploadedFile("file.pdf", b"%PDF-1.5 fake")},
        )
        self.assertFalse(f.is_valid())

    def test_uploaded_image_private_download(self):
        img = BytesIO()
        Image.new("RGB", (16, 16), "white").save(img, format="PNG")
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            self.sign(self.patient)
            r = self.client.post(
                reverse("upload", args=[self.appt.pk]),
                {
                    "title": "A report",
                    "file": SimpleUploadedFile("report.png", img.getvalue()),
                },
            )
            self.assertEqual(r.status_code, 302)
            report = Report.objects.get()
            self.assertTrue(report.file.name.endswith(".jpg"))
            self.sign(self.other)
            self.assertEqual(
                self.client.get(reverse("download", args=[report.pk])).status_code, 404
            )
            self.sign(self.reception)
            self.assertEqual(
                self.client.get(reverse("download", args=[report.pk])).status_code, 403
            )
            self.sign(self.doctor)
            r = self.client.get(reverse("download", args=[report.pk]))
            self.assertEqual(r.status_code, 200)
            self.assertIn("attachment", r["Content-Disposition"])
            r.close()

    def medicine_and_rx(self):
        med = Medicine.objects.create(
            name="Test medicine",
            batch="TEST",
            expiry=timezone.localdate() + timedelta(days=100),
            stock=10,
            price=20,
        )
        rx = Prescription.objects.create(
            appointment=self.appt, instructions="Private clinical instructions"
        )
        PrescriptionItem.objects.create(
            prescription=rx, medicine=med, dose="Test dose", quantity=3
        )
        return med, rx

    def test_dispensing_atomic_and_idempotent(self):
        med, rx = self.medicine_and_rx()
        dispense(rx, self.pharmacist)
        med.refresh_from_db()
        self.assertEqual(med.stock, 7)
        with self.assertRaises(BookingError):
            dispense(rx, self.pharmacist)
        med.refresh_from_db()
        self.assertEqual(med.stock, 7)

    def test_insufficient_stock_does_not_dispense(self):
        med, rx = self.medicine_and_rx()
        med.stock = 1
        med.save()
        with self.assertRaises(BookingError):
            dispense(rx, self.pharmacist)
        rx.refresh_from_db()
        self.assertFalse(rx.dispensed)

    def test_pharmacist_does_not_read_clinical_notes(self):
        self.medicine_and_rx()
        self.sign(self.pharmacist)
        self.assertNotContains(
            self.client.get("/prescriptions/"), "Private clinical instructions"
        )

    def test_video_only_assigned_participants_at_time(self):
        self.appt.status = "confirmed"
        self.appt.save()
        self.slot.start = timezone.now()
        self.slot.save()
        self.sign(self.patient)
        self.assertEqual(
            self.client.get(reverse("video", args=[self.appt.pk])).status_code, 200
        )
        self.sign(self.other)
        self.assertEqual(
            self.client.get(reverse("video", args=[self.appt.pk])).status_code, 404
        )
        self.sign(self.reception)
        self.assertEqual(
            self.client.get(reverse("video", args=[self.appt.pk])).status_code, 403
        )

    def test_video_before_window_blocked(self):
        self.appt.status = "confirmed"
        self.appt.save()
        self.sign(self.patient)
        self.assertEqual(
            self.client.get(reverse("video", args=[self.appt.pk])).status_code, 404
        )

    def test_patient_cannot_send_doctor_offer(self):
        self.appt.status = "confirmed"
        self.appt.save()
        self.slot.start = timezone.now()
        self.slot.save()
        self.sign(self.patient)
        r = self.client.post(
            reverse("signal", args=[self.appt.pk]),
            json.dumps({"kind": "offer", "payload": {}}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_signal_exchange_authorized(self):
        self.appt.status = "confirmed"
        self.appt.save()
        self.slot.start = timezone.now()
        self.slot.save()
        self.sign(self.doctor)
        path = reverse("signal", args=[self.appt.pk])
        self.assertEqual(
            self.client.post(
                path,
                json.dumps(
                    {"kind": "offer", "payload": {"type": "offer", "sdp": "test"}}
                ),
                content_type="application/json",
            ).status_code,
            200,
        )
        self.sign(self.patient)
        self.assertEqual(len(self.client.get(path).json()["signals"]), 1)

    def test_forged_payment_rejected(self):
        self.sign(self.patient)
        r = self.client.post(
            reverse("payment_verify", args=[self.appt.pk]),
            json.dumps(
                {"razorpay_payment_id": "pay_fake", "razorpay_signature": "fake"}
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Payment.objects.get(appointment=self.appt).status, "unpaid")

    def test_unsigned_webhook_rejected(self):
        with override_settings(RAZORPAY_WEBHOOK_SECRET="test-webhook-secret"):
            self.assertEqual(
                self.client.post(
                    "/api/payments/webhook/", b"{}", content_type="application/json"
                ).status_code,
                403,
            )

    def test_payment_receipt_recorded_by_reception(self):
        self.sign(self.reception)
        self.client.post(
            reverse("payment_record", args=[self.appt.pk]),
            {"method": "cash", "reference": "TEST-RECEIPT"},
        )
        p = Payment.objects.get(appointment=self.appt)
        self.assertEqual(p.status, "paid")
        self.assertEqual(p.received_by, self.reception)

    def test_patient_cannot_record_payment(self):
        self.sign(self.patient)
        self.assertEqual(
            self.client.post(
                reverse("payment_record", args=[self.appt.pk]),
                {"method": "cash", "reference": "fake"},
            ).status_code,
            403,
        )

    def test_password_change_invalidates_old_session(self):
        other_client = Client()
        other_client.force_login(self.patient)
        self.sign(self.patient)
        self.client.post(
            "/password/",
            {
                "old_password": "Correct-Hospital-Pass12",
                "new_password1": "Even-Better-Password45",
                "new_password2": "Even-Better-Password45",
            },
        )
        self.assertEqual(other_client.get("/dashboard/").status_code, 302)

    def test_no_default_demo_credentials(self):
        self.assertFalse(
            self.client.login(username="admin@mednova.com", password="admin123")
        )

    def test_malformed_booking_identifiers_return_404(self):
        self.sign(self.patient)
        self.assertEqual(
            self.client.get(
                reverse("booking", args=[self.doctor.pk]) + "?reschedule=invalid"
            ).status_code,
            404,
        )
        r = self.client.post(
            reverse("booking", args=[self.doctor.pk]),
            {"slot": "invalid", "mode": "video", "reason": "Test", "consent": "on"},
        )
        self.assertEqual(r.status_code, 404)

    def test_booking_ignores_client_supplied_fee(self):
        self.sign(self.patient)
        r = self.client.post(
            reverse("booking", args=[self.doctor.pk]),
            {
                "slot": self.slot2.pk,
                "mode": "video",
                "reason": "Test",
                "consent": "on",
                "fee": "0",
                "patient": self.other.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        appt = Appointment.objects.get(slot=self.slot2)
        self.assertEqual(appt.patient, self.patient)
        self.assertEqual(appt.fee, Decimal("250.00"))

    def test_forged_upload_path_not_used(self):
        im = BytesIO()
        Image.new("RGB", (16, 16), "white").save(im, format="PNG")
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            self.sign(self.patient)
            self.client.post(
                reverse("upload", args=[self.appt.pk]),
                {
                    "title": "Test",
                    "file": SimpleUploadedFile("../../settings.py", im.getvalue()),
                },
            )
            report = Report.objects.get()
            self.assertTrue(report.file.name.startswith("reports/"))
            self.assertNotIn("settings", report.file.name)

    def test_signed_webhook_wrong_amount_not_paid(self):
        p = Payment.objects.get(appointment=self.appt)
        p.order_id = "order_test"
        p.save()
        payload = json.dumps(
            {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "order_id": "order_test",
                            "amount": 1,
                            "currency": "INR",
                            "status": "captured",
                            "id": "pay_test",
                        }
                    }
                },
            }
        ).encode()
        with override_settings(RAZORPAY_WEBHOOK_SECRET="test-secret"):
            signature = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
            r = self.client.post(
                "/api/payments/webhook/",
                payload,
                content_type="application/json",
                HTTP_X_RAZORPAY_SIGNATURE=signature,
            )
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, "unpaid")

    def test_signed_webhook_capture_idempotent(self):
        p = Payment.objects.get(appointment=self.appt)
        p.order_id = "order_test"
        p.save()
        payload = json.dumps(
            {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "order_id": "order_test",
                            "amount": 25000,
                            "currency": "INR",
                            "status": "captured",
                            "id": "pay_test",
                        }
                    }
                },
            }
        ).encode()
        with override_settings(RAZORPAY_WEBHOOK_SECRET="test-secret"):
            sig = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
            for i in range(2):
                self.client.post(
                    "/api/payments/webhook/",
                    payload,
                    content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=sig,
                )
        p.refresh_from_db()
        self.assertEqual(p.status, "paid")
        self.assertEqual(AuditEvent.objects.filter(action="payment.webhook").count(), 1)

    def test_doctor_profile_edits_need_review_again(self):
        self.sign(self.doctor)
        self.client.post(
            "/profile/",
            {
                "name": self.doctor.name,
                "phone": "",
                "department": self.department.pk,
                "qualification": "Updated qualification",
                "registration_number": "TEST-0",
                "experience": 2,
                "bio": "",
                "fee": "250",
            },
        )
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.approval, "pending")

    def test_expired_medicine_not_dispensed(self):
        med, rx = self.medicine_and_rx()
        med.expiry = timezone.localdate() - timedelta(days=1)
        med.save()
        with self.assertRaises(BookingError):
            dispense(rx, self.pharmacist)

    def test_availability_never_creates_overlapping_slots(self):
        self.sign(self.doctor)
        day = timezone.localdate() + timedelta(days=3)
        self.client.post(
            "/availability/", {"date": str(day), "start": "09:00", "end": "10:00"}
        )
        self.client.post(
            "/availability/", {"date": str(day), "start": "09:05", "end": "10:05"}
        )
        values = list(
            Slot.objects.filter(doctor=self.doctor, start__date=day)
            .order_by("start")
            .values_list("start", flat=True)
        )
        self.assertEqual(len(values), 5)
        self.assertTrue(
            all(b - a >= timedelta(minutes=12) for a, b in zip(values, values[1:]))
        )

    def test_approved_doctor_can_issue_prescription_after_start(self):
        med = Medicine.objects.create(
            name="Test medicine",
            batch="T1",
            expiry=timezone.localdate() + timedelta(days=1),
            stock=10,
            price=20,
        )
        self.appt.status = "confirmed"
        self.appt.save()
        self.slot.start = timezone.now() - timedelta(minutes=2)
        self.slot.save()
        self.sign(self.doctor)
        r = self.client.post(
            reverse("prescribe", args=[self.appt.pk]),
            {
                "instructions": "A clinical instruction",
                "medicine_1": med.pk,
                "dose_1": "Test dose",
                "quantity_1": 2,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Prescription.objects.count(), 1)

    def test_paid_appointment_cannot_switch_doctor(self):
        Payment.objects.filter(appointment=self.appt).update(status="paid")
        slot = Slot.objects.create(doctor=self.doctor2, start=self.slot2.start)
        with self.assertRaises(BookingError):
            book(self.patient, slot.pk, "video", "Test", self.appt)

    def test_service_rejects_forged_reschedule_owner(self):
        with self.assertRaises(BookingError):
            book(self.other, self.slot2.pk, "video", "Test", self.appt)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.slot_id, self.slot.pk)

    def test_service_rejects_invalid_mode_and_reason(self):
        for mode, reason in [("fake", "Test"), ("video", ""), ("video", "x" * 401)]:
            with self.assertRaises(BookingError):
                book(self.other, self.slot2.pk, mode, reason)
        self.assertFalse(Appointment.objects.filter(slot=self.slot2).exists())

    def test_service_enforces_status_actor_permissions(self):
        for actor, status in [(self.other, "cancelled"), (self.doctor2, "confirmed"), (self.patient, "confirmed"), (self.pharmacist, "cancelled")]:
            with self.assertRaises(BookingError):
                change_status(self.appt, actor, status)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, "pending")

    def test_slot_consultation_type_enforced(self):
        self.slot2.consultation_type = "in_person"
        self.slot2.save()
        with self.assertRaises(BookingError):
            book(self.other, self.slot2.pk, "video", "Test")
        self.assertEqual(book(self.other, self.slot2.pk, "in_person", "Test").mode, "in_person")

    def test_stale_slot_flag_does_not_allow_double_booking(self):
        Slot.objects.filter(pk=self.slot.pk).update(booked=False)
        with self.assertRaises(BookingError):
            book(self.other, self.slot.pk, "video", "Test")

    def test_overlapping_doctor_slots_rejected(self):
        slot = Slot.objects.create(doctor=self.doctor, start=self.slot.start + timedelta(minutes=5))
        with self.assertRaises(BookingError):
            book(self.other, slot.pk, "video", "Test")

    def test_cancellation_notice_enforced(self):
        Hospital.objects.update(cancellation_notice_minutes=2880)
        with self.assertRaises(BookingError):
            change_status(self.appt, self.patient, "cancelled")
        with self.assertRaises(BookingError):
            book(self.patient, self.slot2.pk, "video", "Test", self.appt)

    def test_dispensing_requires_approved_pharmacist(self):
        med, rx = self.medicine_and_rx()
        with self.assertRaises(BookingError):
            dispense(rx, self.patient)
        self.appt.status = "cancelled"
        self.appt.save()
        with self.assertRaises(BookingError):
            dispense(rx, self.pharmacist)
        med.refresh_from_db()
        self.assertEqual(med.stock, 10)

    def test_notifications_are_private_and_persistent(self):
        self.assertEqual(Notification.objects.filter(recipient=self.patient).count(), 1)
        self.sign(self.other)
        self.assertNotContains(self.client.get('/notifications/'), 'Appointment requested.')
        self.sign(self.patient)
        self.assertContains(self.client.get('/notifications/'), 'Appointment requested.')
        self.client.post('/notifications/')
        self.assertFalse(Notification.objects.filter(recipient=self.patient, read=False).exists())

    def test_check_in_permission_and_idempotency(self):
        self.appt.status = 'confirmed'
        self.appt.mode = 'in_person'
        self.appt.save()
        self.slot.start = timezone.now()
        self.slot.save()
        url = reverse('check_in', args=[self.appt.pk])
        self.sign(self.patient)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.sign(self.reception)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.appt.refresh_from_db()
        first = self.appt.checked_in_at
        self.assertIsNotNone(first)
        self.client.post(url)
        self.appt.refresh_from_db()
        self.assertEqual(first, self.appt.checked_in_at)

    def test_health_readiness_handles_database_failure(self):
        from django.db import OperationalError
        self.assertEqual(self.client.get('/health/').json(), {'status': 'ok'})
        with patch('django.db.backends.utils.CursorWrapper.execute', side_effect=OperationalError('secret connection data')):
            response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'secret', response.content)

    @override_settings(EMAIL_HOST='test.invalid', DEFAULT_FROM_EMAIL='test@example.test', PUBLIC_ORIGIN='https://hospital.example.test', EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_reset_email_token_and_single_use(self):
        from django.core import mail
        self.client.post('/forgot-password/', {'email': self.patient.email})
        self.assertEqual(len(mail.outbox), 1)
        url = mail.outbox[0].body.split('https://hospital.example.test')[1].split()[0]
        response = self.client.post(url, {'new_password1': 'New-Private-Password-123', 'new_password2': 'New-Private-Password-123'})
        self.assertEqual(response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.check_password('New-Private-Password-123'))
        self.assertContains(self.client.get(url), 'Reset link expired')
        self.client.post('/forgot-password/', {'email': 'absent@example.test'})
        self.assertEqual(len(mail.outbox), 1)

    def test_email_normalization_on_save(self):
        self.other.email = ' MIXED@Example.Test '
        self.other.save()
        self.other.refresh_from_db()
        self.assertEqual(self.other.email, 'mixed@example.test')

    def test_directory_department_and_availability_filters(self):
        self.assertContains(self.client.get('/doctors/?available=1'), self.doctor.name)
        self.assertNotContains(self.client.get('/doctors/?available=1'), self.doctor2.name)
        department = Department.objects.create(name='Another test department')
        self.assertNotContains(self.client.get(f'/doctors/?department={department.pk}'), self.doctor.name)

    def test_availability_rejects_past_and_short_ranges(self):
        from .forms import AvailabilityForm
        form = AvailabilityForm({'date': str(timezone.localdate() + timedelta(days=1)), 'start': '09:00', 'end': '09:05'})
        self.assertFalse(form.is_valid())

    def test_reception_registers_patient_without_role_escalation(self):
        self.sign(self.reception)
        data = {'name': 'Synthetic Reception Patient', 'email': 'reception-patient@example.test', 'role': 'patient', 'password1': 'Synthetic-Patient-Password-198', 'password2': 'Synthetic-Patient-Password-198', 'consent': 'on'}
        self.assertEqual(self.client.post('/patients/', data).status_code, 302)
        self.assertEqual(User.objects.get(email=data['email']).role, 'patient')
        data.update(email='forged@example.test', role='admin')
        self.assertEqual(self.client.post('/patients/', data).status_code, 200)
        self.assertFalse(User.objects.filter(email=data['email']).exists())
        self.assertContains(self.client.get('/patients/?q=reception-patient'), 'Synthetic Reception Patient')
        self.assertEqual(self.client.get('/admin/users/').status_code, 403)

    def test_admin_deactivation_invalidates_access_and_booking(self):
        self.sign(self.admin)
        self.assertEqual(self.client.post('/admin/users/', {'user': self.other.pk, 'action': 'deactivate'}).status_code, 302)
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_active)
        with self.assertRaises(BookingError):
            book(self.other, self.slot2.pk, 'video', 'Test')
        self.assertEqual(self.client.post('/admin/users/', {'user': self.admin.pk, 'action': 'deactivate'}).status_code, 403)
        self.assertContains(self.client.get('/admin/operations/'), 'pending: 1')

    def test_department_edit_blocks_discovery_and_booking(self):
        self.sign(self.admin)
        self.assertEqual(self.client.post(reverse('department_edit', args=[self.department.pk]), {'name': self.department.name, 'description': 'Test'}).status_code, 302)
        with self.assertRaises(BookingError):
            book(self.other, self.slot2.pk, 'video', 'Test')
        self.assertNotContains(self.client.get('/doctors/'), self.doctor.name)

    def test_slot_edit_enforces_ownership_overlap_and_booked_state(self):
        self.sign(self.doctor2)
        url = reverse('edit_slot', args=[self.slot2.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.sign(self.doctor)
        start = timezone.localtime(self.slot.start + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M')
        self.assertContains(self.client.post(url, {'start': start, 'consultation_type': 'video'}), 'overlaps another slot')
        start = timezone.localtime(self.slot.start + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        self.assertEqual(self.client.post(url, {'start': start, 'consultation_type': 'video'}).status_code, 302)
        self.assertEqual(self.client.get(reverse('edit_slot', args=[self.slot.pk])).status_code, 403)

    def test_calendar_day_week_month(self):
        self.sign(self.doctor)
        day = str(timezone.localdate(self.slot.start))
        for period in ('day', 'week', 'month'):
            response = self.client.get(f'/availability/?date={day}&period={period}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context['slots']), 2)

    def test_complete_patient_doctor_journey(self):
        self.sign(self.other)
        response = self.client.post(reverse('booking', args=[self.doctor.pk]), {'slot': self.slot2.pk, 'mode': 'in_person', 'reason': 'Synthetic acceptance visit', 'consent': 'on'})
        self.assertEqual(response.status_code, 302)
        appt = Appointment.objects.get(slot=self.slot2)
        self.client.post('/logout/')
        self.client.post('/login/', {'email': self.other.email, 'password': 'Correct-Hospital-Pass12'})
        self.assertContains(self.client.get(response.url), 'Synthetic acceptance visit')
        self.sign(self.doctor)
        self.client.post(reverse('appointment_action', args=[appt.pk]), {'action': 'confirmed'})
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'confirmed')
        self.sign(self.other)
        self.assertContains(self.client.get(response.url), 'Confirmed')
        self.client.post(reverse('appointment_action', args=[appt.pk]), {'action': 'cancelled'})
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'cancelled')

    def test_home_and_public_navigation_are_available_without_login(self):
        response = self.client.get('/')
        self.assertContains(response, 'Your care, connected.')
        for path in ('/departments/', '/doctors/', '/contact/', '/login/', '/register/'):
            self.assertContains(response, f'href="{path}"')
        self.assertContains(self.client.get('/departments/'), self.department.name)
        self.assertContains(self.client.get(reverse('doctor_detail', args=[self.doctor.pk])), 'TEST-0')
        self.assertEqual(self.client.get(reverse('doctor_detail', args=[self.pending.pk])).status_code, 404)

    def test_browser_form_security_header_and_real_csrf_login(self):
        c = Client(enforce_csrf_checks=True)
        response = c.get('/login/')
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        token = c.cookies['csrftoken'].value
        data = {'email': self.patient.email, 'password': 'Correct-Hospital-Pass12', 'csrfmiddlewaretoken': token}
        self.assertEqual(c.post('/login/', data, HTTP_ORIGIN='https://attacker.invalid').status_code, 403)
        self.assertEqual(c.post('/login/', data, HTTP_ORIGIN='null').status_code, 403)
        self.assertEqual(c.post('/login/', data, HTTP_ORIGIN='http://testserver').status_code, 302)
        self.assertEqual(c.get('/dashboard/').status_code, 200)

    def test_login_returns_to_booking_without_open_redirect(self):
        url = reverse('booking', args=[self.doctor.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=', response.url)
        response = self.client.post('/login/', {'email': self.patient.email, 'password': 'Correct-Hospital-Pass12', 'next': url})
        self.assertEqual(response.url, url)
        self.client.post('/logout/')
        response = self.client.post('/login/', {'email': self.patient.email, 'password': 'Correct-Hospital-Pass12', 'next': 'https://attacker.invalid'})
        self.assertEqual(response.url, '/dashboard/')

    def test_language_keeps_current_public_page_and_rejects_external_next(self):
        response = self.client.post('/language/', {'language': 'mr', 'next': '/doctors/?available=1'})
        self.assertEqual(response.url, '/doctors/?available=1')
        response = self.client.post('/language/', {'language': 'en', 'next': 'https://attacker.invalid'})
        self.assertEqual(response.url, '/')

    def test_receipt_is_object_scoped(self):
        url = reverse('receipt', args=[self.appt.pk])
        self.sign(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.sign(self.patient)
        self.assertContains(self.client.get(url), '250.00')
        self.sign(self.pharmacist)
        self.assertEqual(self.client.get(url).status_code, 403)

    @override_settings(PRIVATE_STORAGE_BACKEND='s3')
    def test_private_s3_download_signs_only_after_authorization(self):
        report = Report.objects.create(appointment=self.appt, uploaded_by=self.patient, title='Synthetic private report', extension='.jpg', file='reports/synthetic.jpg')
        with patch.object(Report._meta.get_field('file'), 'storage') as report_storage:
            sign_url = report_storage.url
            sign_url.return_value = 'https://private.example.test/reports/synthetic.jpg?signature=test'
            self.sign(self.other)
            self.assertEqual(self.client.get(reverse('download', args=[report.pk])).status_code, 404)
            sign_url.assert_not_called()
            self.sign(self.patient)
            response = self.client.get(reverse('download', args=[report.pk]))
            self.assertEqual(response.status_code, 302)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(sign_url.call_args.kwargs['expire'], 60)

    @override_settings(REPORT_MAX_BYTES=3 * 1024 * 1024)
    def test_vercel_upload_limit_is_enforced_before_storage(self):
        form = UploadForm({'title': 'Synthetic'}, {'file': SimpleUploadedFile('oversize.jpg', b'x' * (3 * 1024 * 1024 + 1))})
        self.assertFalse(form.is_valid())
        self.assertIn('3 MB', str(form.errors))

    @override_settings(CRON_SECRET='synthetic-cron-secret')
    def test_cleanup_endpoint_requires_bearer_secret(self):
        self.assertEqual(self.client.get('/api/maintenance/cleanup/').status_code, 403)
        self.assertEqual(self.client.get('/api/maintenance/cleanup/', HTTP_AUTHORIZATION='Bearer wrong').status_code, 403)
        with patch('django.core.management.call_command') as command:
            response = self.client.get('/api/maintenance/cleanup/', HTTP_AUTHORIZATION='Bearer synthetic-cron-secret')
        self.assertEqual(response.status_code, 200)
        command.assert_called_once()

    def test_vercel_configuration_fails_closed_for_missing_services(self):
        from mednova.hosting import storage_config, validate_vercel
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            validate_vercel({})
        with self.assertRaises(ImproperlyConfigured):
            storage_config({}, vercel=True)
        with self.assertRaises(ImproperlyConfigured):
            storage_config({'PRIVATE_STORAGE_BACKEND': 's3', 'S3_BUCKET_NAME': 'synthetic', 'S3_REGION_NAME': 'test', 'AWS_ACCESS_KEY_ID': 'synthetic-test-key', 'AWS_SECRET_ACCESS_KEY': 'synthetic-test-secret', 'S3_ENDPOINT_URL': 'http://unsafe.invalid'})
        backend, storages = storage_config({'PRIVATE_STORAGE_BACKEND': 's3', 'S3_BUCKET_NAME': 'synthetic', 'S3_REGION_NAME': 'test', 'AWS_ACCESS_KEY_ID': 'synthetic-test-key', 'AWS_SECRET_ACCESS_KEY': 'synthetic-test-secret'}, vercel=True)
        options = storages['default']['OPTIONS']
        self.assertEqual(backend, 's3')
        self.assertIsNone(options['default_acl'])
        self.assertTrue(options['verify'])
        self.assertTrue(options['querystring_auth'])
        self.assertEqual(options['querystring_expire'], 60)

    def test_clinical_buttons_match_consultation_time_and_existing_prescription(self):
        self.appt.status = 'confirmed'
        self.appt.save()
        self.sign(self.doctor)
        url = reverse('appointment', args=[self.appt.pk])
        self.assertNotContains(self.client.get(url), 'Issue prescription')
        self.assertNotContains(self.client.get(url), 'Complete consultation')
        self.slot.start = timezone.now() - timedelta(minutes=1)
        self.slot.save()
        self.assertContains(self.client.get(url), 'Issue prescription')
        Prescription.objects.create(appointment=self.appt, instructions='Synthetic test note')
        self.assertNotContains(self.client.get(url), 'Issue prescription')
        self.assertContains(self.client.get(url), 'Complete consultation')

    def test_storage_failure_never_reports_upload_success(self):
        img = BytesIO()
        Image.new('RGB', (16, 16), 'white').save(img, format='PNG')
        self.sign(self.patient)
        with patch('django.core.files.storage.filesystem.FileSystemStorage._save', side_effect=OSError('Synthetic storage outage')):
            response = self.client.post(reverse('upload', args=[self.appt.pk]), {'title': 'Synthetic outage report', 'file': SimpleUploadedFile('test.png', img.getvalue())})
        self.assertContains(response, 'Report storage is unavailable.')
        self.assertFalse(Report.objects.exists())
