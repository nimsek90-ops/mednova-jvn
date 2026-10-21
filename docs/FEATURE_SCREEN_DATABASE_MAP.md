# Feature, screen, backend and permission inventory

58 registered routes, one Django care app, 23 concrete care models, five roles and five additive care migrations. This is a workflow-level table map: related notification/audit writes are included where relevant; shared Hospital/context/session reads apply to HTML pages. JSON lists source file/line and all directly referenced templates. Object authorization is tested separately from role entry.

| Feature / route | Screen | Backend | Workflow tables | Role entry |
|---|---|---|---|---|
| `admin/data/` | data_management.html | `care.product.data_management` | user, doctorprofile, department, medicine, appointment, payment, auditevent | admin |
| `about/` | information.html | `care.product.public_information` | department, doctorprofile, user, slot, hospital | public / special token policy |
| `pharmacy/` | information.html | `care.product.public_information` | department, doctorprofile, user, slot, hospital | public / special token policy |
| `health-hub/` | health_hub.html, form.html | `care.product.health_hub` | healthassessment | public / special token policy |
| `symptom-information/` | symptoms.html | `care.product.symptoms` | Educational content; no saved symptom rows | public / special token policy |
| `wellness/` | wellness.html, form.html | `care.product.wellness` | wellnessentry, wellnessrevision, healthassessment | patient |
| `appointments/<uuid:pk>/notes/` | notes.html | `care.product.notes` | appointment, clinicalnote, report, prescription, prescriptionitem, medicine, auditevent | doctor, patient |
| `patients/<int:patient_id>/timeline/` | timeline.html | `care.product.timeline` | appointment, clinicalnote, report, prescription, prescriptionitem, medicine, auditevent | doctor, patient |
| `queue/` | queue.html | `care.product.queue` | appointment, queuecounter, queueentry, auditevent | admin, receptionist |
| `inventory/movements/` | movements.html | `care.product.movements` | medicine, stockmovement, prescription, prescriptionitem, auditevent | admin, pharmacist |
| `api/maintenance/cleanup/` | JSON/file/action redirect; shared destination screen | `care.views.cleanup` | signal, ratebucket, notification, deliveryoutbox | public / special token policy |
| `health/` | JSON/file/action redirect; shared destination screen | `care.views.health` | Database connectivity probe; no clinical rows | public / special token policy |
| `notifications/` | notifications.html | `care.views.notifications` | notification | admin, doctor, patient, pharmacist, receptionist |
| `patients/` | patients.html | `care.views.patients` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin, receptionist |
| `admin/users/` | users.html | `care.views.users` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin |
| `admin/operations/` | operations.html | `care.views.operational_report` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin |
| `availability/<int:pk>/edit/` | form.html | `care.views.edit_slot` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | doctor |
| `admin/departments/<int:pk>/` | form.html | `care.views.department_edit` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin |
| `appointments/<uuid:pk>/check-in/` | JSON/file/action redirect; shared destination screen | `care.views.check_in` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | admin, receptionist |
| `/` | home.html | `care.views.home` | department, doctorprofile, user, slot, hospital | public / special token policy |
| `departments/` | public_departments.html | `care.views.public_departments` | department, doctorprofile, user, slot, hospital | public / special token policy |
| `doctors/<int:pk>/` | doctor_detail.html | `care.views.doctor_detail` | department, doctorprofile, user, slot, hospital | public / special token policy |
| `appointments/<uuid:pk>/receipt/` | receipt.html | `care.views.receipt` | appointment, payment, auditevent | admin, patient, receptionist |
| `login/` | login.html | `care.views.sign_in` | user, ratebucket, auditevent | public / special token policy |
| `register/` | form.html | `care.views.register` | user, ratebucket, auditevent | public / special token policy |
| `logout/` | JSON/file/action redirect; shared destination screen | `care.views.sign_out` | user, ratebucket, auditevent | public / special token policy |
| `language/` | JSON/file/action redirect; shared destination screen | `care.views.language` | user, ratebucket, auditevent | public / special token policy |
| `forgot-password/` | forgot.html | `care.views.forgot` | user, ratebucket, auditevent | public / special token policy |
| `reset/<str:uid>/<str:token>/` | form.html | `care.views.reset` | user, ratebucket, auditevent | public / special token policy |
| `password/` | form.html | `care.views.password` | user, ratebucket, auditevent | admin, doctor, patient, pharmacist, receptionist |
| `dashboard/` | dashboard.html, pending.html | `care.views.dashboard` | user, doctorprofile, appointment, slot, medicine, prescription, notification, wellnessentry | admin, doctor, patient, pharmacist, receptionist |
| `profile/` | form.html | `care.views.profile` | user, ratebucket, auditevent | admin, doctor, patient, pharmacist, receptionist |
| `doctors/` | doctors.html | `care.views.doctors` | department, doctorprofile, user, slot, hospital | public / special token policy |
| `availability/` | availability.html | `care.views.availability` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | doctor |
| `availability/<int:pk>/remove/` | JSON/file/action redirect; shared destination screen | `care.views.remove_slot` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | doctor |
| `book/<int:doctor_id>/` | booking.html | `care.views.booking` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | patient, receptionist |
| `appointments/` | appointments.html | `care.views.appointments` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | admin, doctor, patient, receptionist |
| `appointments/<uuid:pk>/` | appointment.html | `care.views.appointment` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | admin, doctor, patient, receptionist |
| `appointments/<uuid:pk>/action/` | JSON/file/action redirect; shared destination screen | `care.views.appointment_action` | appointment, slot, user, doctorprofile, payment, notification, deliveryoutbox, auditevent | admin, doctor, patient, receptionist |
| `appointments/<uuid:pk>/upload/` | form.html | `care.views.upload` | appointment, clinicalnote, report, prescription, prescriptionitem, medicine, auditevent | doctor, patient |
| `reports/<uuid:pk>/download/` | JSON/file/action redirect; shared destination screen | `care.views.download` | appointment, clinicalnote, report, prescription, prescriptionitem, medicine, auditevent | doctor, patient |
| `appointments/<uuid:pk>/prescribe/` | prescribe.html | `care.views.prescribe` | appointment, clinicalnote, report, prescription, prescriptionitem, medicine, auditevent | doctor |
| `prescriptions/` | prescriptions.html | `care.views.prescriptions` | appointment, clinicalnote, report, prescription, prescriptionitem, medicine, auditevent | doctor, patient, pharmacist |
| `prescriptions/<uuid:pk>/dispense/` | JSON/file/action redirect; shared destination screen | `care.views.dispense_rx` | appointment, clinicalnote, report, prescription, prescriptionitem, medicine, auditevent | pharmacist |
| `inventory/` | inventory.html | `care.views.inventory` | medicine, stockmovement, prescription, prescriptionitem, auditevent | admin, pharmacist |
| `inventory/<int:pk>/adjust/` | JSON/file/action redirect; shared destination screen | `care.views.stock` | medicine, stockmovement, prescription, prescriptionitem, auditevent | admin, pharmacist |
| `admin/staff/` | staff.html | `care.views.staff` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin |
| `admin/departments/` | form.html | `care.views.departments` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin |
| `admin/settings/` | form.html | `care.views.hospital_settings` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin |
| `admin/audit/` | audit.html | `care.views.audit_log` | user, doctorprofile, department, hospital, appointment, payment, auditevent | admin |
| `appointments/<uuid:pk>/payment-record/` | payment_record.html | `care.views.payment_record` | appointment, payment, auditevent | admin, receptionist |
| `appointments/<uuid:pk>/pay/` | pay.html, form.html | `care.views.pay` | appointment, payment, auditevent | patient |
| `api/payments/<uuid:pk>/verify/` | JSON/file/action redirect; shared destination screen | `care.views.payment_verify` | appointment, payment, auditevent | patient |
| `api/payments/webhook/` | JSON/file/action redirect; shared destination screen | `care.views.webhook` | appointment, payment, auditevent | public / special token policy |
| `appointments/<uuid:pk>/video/` | video.html, form.html | `care.views.video` | appointment, signal, ratebucket, auditevent | doctor, patient |
| `api/appointments/<uuid:pk>/signals/` | JSON/file/action redirect; shared destination screen | `care.views.signal` | appointment, signal, ratebucket, auditevent | doctor, patient |
| `legal/<str:kind>/` | legal.html | `care.views.legal` | department, doctorprofile, user, slot, hospital | public / special token policy |
| `contact/` | contact.html | `care.views.contact` | department, doctorprofile, user, slot, hospital | public / special token policy |

## Verification boundaries

PASS: current MySQL suite exercised every route as anonymous and each of five roles (348 GET probes), then explicit workflow tests covered writes, CSRF, ownership, invalid inputs and concurrent operations. GET probes alone do not establish a full write workflow. See FINAL_SYSTEM_REPORT.md and test sources for the distinction.

Public health-information screens return educational rules/content, not a diagnosis. Patient history/notes/reports require the patient or an assigned doctor; administrators and receptionists receive operational scheduling data only. Pharmacists receive the dispensing minimum, not clinical notes/reports. Payment webhook uses signature authentication; maintenance requires its bearer secret; reset requires Django token. Failed provider configuration is surfaced rather than returning fake success.

The curated data portal has eight fixed entity types with search/sort and links to existing validated/paginated workflows. It deliberately has no arbitrary SQL, general record editor or hard-delete interface. Users are deactivated; clinical/audit/payment records are retained.