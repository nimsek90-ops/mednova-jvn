# Actual MySQL schema inventory

PASS — introspected from `mednova_local`, MySQL 8.4.13. All 31 tables use InnoDB. Counts are optimizer estimates at capture time, not patient statistics. No row contents are included. Full DDL, column defaults and constraints: [JSON evidence](verification/final-mysql-schema.json). All checked foreign-key orphan counts were zero.

## auth_group

Purpose/model: auth.Group. Approximate rows: 0.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | int | NO | — | auto_increment |
| name | varchar(150) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| name | name | UNIQUE |
| PRIMARY | id | PRIMARY KEY |

## auth_group_permissions

Purpose/model: auth.Group_permissions. Approximate rows: 0.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| group_id | int | NO | — | — |
| permission_id | int | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| auth_group_permissions_group_id_permission_id_0cd325b0_uniq | group_id, permission_id | UNIQUE |
| auth_group_permissions_group_id_b120cbf9_fk_auth_group_id | group_id | FOREIGN KEY → auth_group.id |
| auth_group_permissio_permission_id_84c5c92e_fk_auth_perm | permission_id | FOREIGN KEY → auth_permission.id |

## auth_permission

Purpose/model: auth.Permission. Approximate rows: 108.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | int | NO | — | auto_increment |
| name | varchar(255) | NO | — | — |
| content_type_id | int | NO | — | — |
| codename | varchar(100) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| auth_permission_content_type_id_codename_01ab375a_uniq | content_type_id, codename | UNIQUE |
| auth_permission_content_type_id_2f476e4b_fk_django_co | content_type_id | FOREIGN KEY → django_content_type.id |

## care_appointment

Purpose/model: care.Appointment. Approximate rows: 10.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | char(32) | NO | — | — |
| mode | varchar(10) | NO | — | — |
| status | varchar(12) | NO | — | — |
| reason | varchar(400) | NO | — | — |
| fee | decimal(8,2) | NO | — | — |
| created | datetime(6) | NO | — | — |
| patient_id | bigint | NO | — | — |
| slot_id | bigint | NO | — | — |
| checked_in_at | datetime(6) | YES | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_appointment_patient_id_b4175725_fk_care_user_id | patient_id | FOREIGN KEY → care_user.id |
| care_appointment_slot_id_0e47ae40_fk_care_slot_id | slot_id | FOREIGN KEY → care_slot.id |

## care_auditevent

Purpose/model: care.AuditEvent. Approximate rows: 173.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| action | varchar(100) | NO | — | — |
| target | varchar(120) | NO | — | — |
| created | datetime(6) | NO | — | — |
| actor_id | bigint | YES | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_auditevent_actor_id_66dff823_fk_care_user_id | actor_id | FOREIGN KEY → care_user.id |

## care_clinicalnote

Purpose/model: care.ClinicalNote. Approximate rows: 2.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| complaint | longtext | NO | — | — |
| examination | longtext | NO | — | — |
| assessment | longtext | NO | — | — |
| plan | longtext | NO | — | — |
| follow_up | longtext | NO | — | — |
| correction_reason | varchar(300) | NO | — | — |
| version | int unsigned | NO | — | — |
| created | datetime(6) | NO | — | — |
| appointment_id | char(32) | NO | — | — |
| author_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| clinical_note_version | appointment_id, version | UNIQUE |
| care_clinicalnote_appointment_id_f5da14e4_fk_care_appointment_id | appointment_id | FOREIGN KEY → care_appointment.id |
| care_clinicalnote_author_id_91e035dd_fk_care_user_id | author_id | FOREIGN KEY → care_user.id |
| care_clinicalnote_chk_1 | version | CHECK |

## care_deliveryoutbox

Purpose/model: care.DeliveryOutbox. Approximate rows: 20.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| dedupe_key | varchar(120) | NO | — | — |
| status | varchar(12) | NO | — | — |
| attempts | smallint unsigned | NO | — | — |
| lease_until | datetime(6) | YES | — | — |
| next_attempt | datetime(6) | NO | — | — |
| sent_at | datetime(6) | YES | — | — |
| last_error | varchar(120) | NO | — | — |
| notification_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| dedupe_key | dedupe_key | UNIQUE |
| notification_id | notification_id | UNIQUE |
| care_deliveryoutbox_notification_id_831511e8_fk_care_noti | notification_id | FOREIGN KEY → care_notification.id |
| care_deliveryoutbox_chk_1 | attempts | CHECK |

## care_department

Purpose/model: care.Department. Approximate rows: 2.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| name | varchar(100) | NO | — | — |
| description | varchar(400) | NO | — | — |
| active | tinyint(1) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| name | name | UNIQUE |
| PRIMARY | id | PRIMARY KEY |

## care_doctorprofile

Purpose/model: care.DoctorProfile. Approximate rows: 4.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| qualification | varchar(200) | NO | — | — |
| registration_number | varchar(100) | NO | — | — |
| experience | smallint unsigned | NO | — | — |
| bio | longtext | NO | — | — |
| fee | decimal(8,2) | NO | — | — |
| department_id | bigint | YES | — | — |
| user_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| registration_number | registration_number | UNIQUE |
| user_id | user_id | UNIQUE |
| care_doctorprofile_department_id_82a25853_fk_care_department_id | department_id | FOREIGN KEY → care_department.id |
| care_doctorprofile_user_id_86bd5dae_fk_care_user_id | user_id | FOREIGN KEY → care_user.id |
| care_doctorprofile_chk_1 | experience | CHECK |

## care_healthassessment

Purpose/model: care.HealthAssessment. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| created | datetime(6) | NO | — | — |
| answers | json | NO | — | — |
| result | json | NO | — | — |
| patient_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_healthassessment_patient_id_97a9f22a_fk_care_user_id | patient_id | FOREIGN KEY → care_user.id |

## care_hospital

Purpose/model: care.Hospital. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| name | varchar(120) | NO | — | — |
| address | longtext | NO | — | — |
| phone | varchar(20) | NO | — | — |
| ambulance | varchar(20) | NO | — | — |
| email | varchar(254) | NO | — | — |
| privacy_email | varchar(254) | NO | — | — |
| legal_name | varchar(200) | NO | — | — |
| retention_days | int unsigned | NO | — | — |
| cancellation_policy | longtext | NO | — | — |
| cancellation_notice_minutes | int unsigned | NO | — | — |
| opening_hours | varchar(600) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_hospital_chk_1 | retention_days | CHECK |
| care_hospital_chk_2 | cancellation_notice_minutes | CHECK |

## care_medicine

Purpose/model: care.Medicine. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| name | varchar(150) | NO | — | — |
| batch | varchar(60) | NO | — | — |
| expiry | date | NO | — | — |
| stock | int unsigned | NO | — | — |
| price | decimal(8,2) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| unique_medicine_batch | name, batch | UNIQUE |
| care_medicine_chk_1 | stock | CHECK |

## care_notification

Purpose/model: care.Notification. Approximate rows: 58.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| message | varchar(200) | NO | — | — |
| read | tinyint(1) | NO | — | — |
| created | datetime(6) | NO | — | — |
| appointment_id | char(32) | YES | — | — |
| recipient_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_notification_appointment_id_48aa7bec_fk_care_appointment_id | appointment_id | FOREIGN KEY → care_appointment.id |
| care_notification_recipient_id_cbd51a5f_fk_care_user_id | recipient_id | FOREIGN KEY → care_user.id |

## care_payment

Purpose/model: care.Payment. Approximate rows: 10.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| amount | decimal(8,2) | NO | — | — |
| status | varchar(16) | NO | — | — |
| method | varchar(12) | NO | — | — |
| order_id | varchar(100) | NO | — | — |
| provider_id | varchar(100) | NO | — | — |
| reference | varchar(120) | NO | — | — |
| updated | datetime(6) | NO | — | — |
| appointment_id | char(32) | NO | — | — |
| received_by_id | bigint | YES | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| appointment_id | appointment_id | UNIQUE |
| care_payment_appointment_id_eb858144_fk_care_appointment_id | appointment_id | FOREIGN KEY → care_appointment.id |
| care_payment_received_by_id_926e2a05_fk_care_user_id | received_by_id | FOREIGN KEY → care_user.id |

## care_prescription

Purpose/model: care.Prescription. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | char(32) | NO | — | — |
| instructions | longtext | NO | — | — |
| created | datetime(6) | NO | — | — |
| dispensed | tinyint(1) | NO | — | — |
| dispensed_at | datetime(6) | YES | — | — |
| appointment_id | char(32) | NO | — | — |
| dispensed_by_id | bigint | YES | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| appointment_id | appointment_id | UNIQUE |
| care_prescription_appointment_id_6bcdfad5_fk_care_appointment_id | appointment_id | FOREIGN KEY → care_appointment.id |
| care_prescription_dispensed_by_id_550e91d1_fk_care_user_id | dispensed_by_id | FOREIGN KEY → care_user.id |

## care_prescriptionitem

Purpose/model: care.PrescriptionItem. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| dose | varchar(200) | NO | — | — |
| quantity | smallint unsigned | NO | — | — |
| medicine_id | bigint | NO | — | — |
| prescription_id | char(32) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_prescriptionitem_medicine_id_078b2732_fk_care_medicine_id | medicine_id | FOREIGN KEY → care_medicine.id |
| care_prescriptionite_prescription_id_c40868da_fk_care_pres | prescription_id | FOREIGN KEY → care_prescription.id |
| care_prescriptionitem_chk_1 | quantity | CHECK |

## care_queuecounter

Purpose/model: care.QueueCounter. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| date | date | NO | — | — |
| number | int unsigned | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| date | date | UNIQUE |
| care_queuecounter_chk_1 | number | CHECK |

## care_queueentry

Purpose/model: care.QueueEntry. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| date | date | NO | — | — |
| number | int unsigned | NO | — | — |
| status | varchar(12) | NO | — | — |
| created | datetime(6) | NO | — | — |
| updated | datetime(6) | NO | — | — |
| appointment_id | char(32) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| appointment_id | appointment_id | UNIQUE |
| queue_daily_token | date, number | UNIQUE |
| care_queueentry_appointment_id_b3b1fbc1_fk_care_appointment_id | appointment_id | FOREIGN KEY → care_appointment.id |
| care_queueentry_chk_1 | number | CHECK |

## care_ratebucket

Purpose/model: care.RateBucket. Approximate rows: 100.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| key | varchar(64) | NO | — | — |
| count | int unsigned | NO | — | — |
| expires | datetime(6) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| key | key | UNIQUE |
| care_ratebucket_chk_1 | count | CHECK |

## care_report

Purpose/model: care.Report. Approximate rows: 1.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | char(32) | NO | — | — |
| title | varchar(120) | NO | — | — |
| extension | varchar(5) | NO | — | — |
| file | varchar(100) | NO | — | — |
| created | datetime(6) | NO | — | — |
| appointment_id | char(32) | NO | — | — |
| uploaded_by_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_report_appointment_id_d1306e85_fk_care_appointment_id | appointment_id | FOREIGN KEY → care_appointment.id |
| care_report_uploaded_by_id_ccabd984_fk_care_user_id | uploaded_by_id | FOREIGN KEY → care_user.id |

## care_signal

Purpose/model: care.Signal. Approximate rows: 0.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| kind | varchar(12) | NO | — | — |
| payload | json | NO | — | — |
| created | datetime(6) | NO | — | — |
| appointment_id | char(32) | NO | — | — |
| sender_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_signal_appointment_id_2c345e47_fk_care_appointment_id | appointment_id | FOREIGN KEY → care_appointment.id |
| care_signal_sender_id_b00c5bf3_fk_care_user_id | sender_id | FOREIGN KEY → care_user.id |

## care_slot

Purpose/model: care.Slot. Approximate rows: 20.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| start | datetime(6) | NO | — | — |
| booked | tinyint(1) | NO | — | — |
| active | tinyint(1) | NO | — | — |
| doctor_id | bigint | NO | — | — |
| consultation_type | varchar(10) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| unique_doctor_slot | doctor_id, start | UNIQUE |
| care_slot_doctor_id_0ea3cf91_fk_care_user_id | doctor_id | FOREIGN KEY → care_user.id |

## care_stockmovement

Purpose/model: care.StockMovement. Approximate rows: 2.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| quantity | int | NO | — | — |
| balance | int unsigned | NO | — | — |
| reason | varchar(120) | NO | — | — |
| created | datetime(6) | NO | — | — |
| actor_id | bigint | NO | — | — |
| medicine_id | bigint | NO | — | — |
| prescription_id | char(32) | YES | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_stockmovement_actor_id_bc85711e_fk_care_user_id | actor_id | FOREIGN KEY → care_user.id |
| care_stockmovement_medicine_id_7e30d52f_fk_care_medicine_id | medicine_id | FOREIGN KEY → care_medicine.id |
| care_stockmovement_prescription_id_12ea9f64_fk_care_pres | prescription_id | FOREIGN KEY → care_prescription.id |
| care_stockmovement_chk_1 | balance | CHECK |

## care_user

Purpose/model: care.User. Approximate rows: 19.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| password | varchar(128) | NO | — | — |
| last_login | datetime(6) | YES | — | — |
| is_superuser | tinyint(1) | NO | — | — |
| first_name | varchar(150) | NO | — | — |
| last_name | varchar(150) | NO | — | — |
| is_staff | tinyint(1) | NO | — | — |
| is_active | tinyint(1) | NO | — | — |
| date_joined | datetime(6) | NO | — | — |
| email | varchar(254) | NO | — | — |
| name | varchar(120) | NO | — | — |
| phone | varchar(20) | NO | — | — |
| role | varchar(20) | NO | — | — |
| approval | varchar(12) | NO | — | — |
| review_note | varchar(300) | NO | — | — |
| date_of_birth | date | YES | — | — |
| must_change_password | tinyint(1) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| email | email | UNIQUE |

## care_user_groups

Purpose/model: care.User_groups. Approximate rows: 0.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| user_id | bigint | NO | — | — |
| group_id | int | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_user_groups_user_id_group_id_1eda340c_uniq | user_id, group_id | UNIQUE |
| care_user_groups_group_id_453e3af7_fk_auth_group_id | group_id | FOREIGN KEY → auth_group.id |
| care_user_groups_user_id_41d4ff38_fk_care_user_id | user_id | FOREIGN KEY → care_user.id |

## care_user_user_permissions

Purpose/model: care.User_user_permissions. Approximate rows: 0.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| user_id | bigint | NO | — | — |
| permission_id | int | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_user_user_permissions_user_id_permission_id_a4bcbb7c_uniq | user_id, permission_id | UNIQUE |
| care_user_user_permissions_user_id_81986f5f_fk_care_user_id | user_id | FOREIGN KEY → care_user.id |
| care_user_user_permi_permission_id_db02c1d5_fk_auth_perm | permission_id | FOREIGN KEY → auth_permission.id |

## care_wellnessentry

Purpose/model: care.WellnessEntry. Approximate rows: 2.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| date | date | NO | — | — |
| sleep | decimal(4,1) | NO | — | — |
| water | decimal(4,1) | NO | — | — |
| exercise_days | smallint unsigned | NO | — | — |
| stress | smallint unsigned | NO | — | — |
| score | smallint unsigned | NO | — | — |
| updated | datetime(6) | NO | — | — |
| patient_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| wellness_patient_date | patient_id, date | UNIQUE |
| care_wellnessentry_patient_id_42b3bcb5_fk_care_user_id | patient_id | FOREIGN KEY → care_user.id |
| care_wellnessentry_chk_1 | exercise_days | CHECK |
| care_wellnessentry_chk_2 | stress | CHECK |
| care_wellnessentry_chk_3 | score | CHECK |

## care_wellnessrevision

Purpose/model: care.WellnessRevision. Approximate rows: 3.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| values | json | NO | — | — |
| created | datetime(6) | NO | — | — |
| entry_id | bigint | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| care_wellnessrevision_entry_id_70499e0a_fk_care_wellnessentry_id | entry_id | FOREIGN KEY → care_wellnessentry.id |

## django_content_type

Purpose/model: contenttypes.ContentType. Approximate rows: 27.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | int | NO | — | auto_increment |
| app_label | varchar(100) | NO | — | — |
| model | varchar(100) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |
| django_content_type_app_label_model_76bd3d3b_uniq | app_label, model | UNIQUE |

## django_migrations

Purpose/model: Django schema migration history. Approximate rows: 20.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| id | bigint | NO | — | auto_increment |
| app | varchar(255) | NO | — | — |
| name | varchar(255) | NO | — | — |
| applied | datetime(6) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | id | PRIMARY KEY |

## django_session

Purpose/model: sessions.Session. Approximate rows: 39.

| Column | MySQL type | Nullable | Default | Extra |
|---|---|---|---|---|
| session_key | varchar(40) | NO | — | — |
| session_data | longtext | NO | — | — |
| expire_date | datetime(6) | NO | — | — |

| Constraint/index | Columns | Kind / referenced key |
|---|---|---|
| PRIMARY | session_key | PRIMARY KEY |
| django_session_expire_date_a5c62663 | expire_date | INDEX |
