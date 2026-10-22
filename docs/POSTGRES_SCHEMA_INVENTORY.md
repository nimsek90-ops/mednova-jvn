# PostgreSQL rehearsal schema inventory

PASS locally: actual PostgreSQL18.6, database mednova_pg_rehearsal, private mednova schema. This is **not a hosted Supabase schema**. Supabase project selection/creation is blocked. All31 tables have RLS enabled and forced; browser/API roles have no private-schema grants. The backend policy permits only the dedicated Django runtime role; per-user authorization remains in Django.

Counts below are exact table counts at the verified backup snapshot, not patient statistics. Later synthetic tests may add records. Full metadata: [JSON](verification/postgres-rehearsal-schema.json); migration results: [log](verification/postgres-migrations.txt); backup/restore: [evidence](verification/postgres-backup-restore.json). No record contents are exported here.

## auth_group

Purpose: Django permission groups, distinct from the custom hospital role. Model: auth.Group. Snapshot rows: 0. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | int | integer | NO | — |
| name | varchar(150) | character varying(150) | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| auth_group_id_not_null | id | Constraint |
| auth_group_pkey | id | Primary key |
| auth_group_name_key | name | Unique |
| auth_group_name_not_null | name | Constraint |
| auth_group_name_a6ea08ec_like | name | Index |

## auth_group_permissions

Purpose/model: auth.Group_permissions. Snapshot rows: 0. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| group_id | int | integer | NO | — |
| permission_id | int | integer | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| auth_group_permissions_id_not_null | id | Constraint |
| auth_group_permissions_group_id_not_null | group_id | Constraint |
| auth_group_permissions_permission_id_not_null | permission_id | Constraint |
| auth_group_permissions_pkey | id | Primary key |
| auth_group_permissions_group_id_permission_id_0cd325b0_uniq | group_id, permission_id | Unique |
| auth_group_permissions_group_id_b120cbf9_fk_auth_group_id | group_id | Foreign key → auth_group.id |
| auth_group_permissio_permission_id_84c5c92e_fk_auth_perm | permission_id | Foreign key → auth_permission.id |
| auth_group_permissions_group_id_b120cbf9 | group_id | Index |
| auth_group_permissions_permission_id_84c5c92e | permission_id | Index |

## auth_permission

Purpose: Django content-type permission definitions. Model: auth.Permission. Snapshot rows: 108. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | int | integer | NO | — |
| name | varchar(255) | character varying(255) | NO | — |
| content_type_id | int | integer | NO | — |
| codename | varchar(100) | character varying(100) | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| auth_permission_id_not_null | id | Constraint |
| auth_permission_content_type_id_not_null | content_type_id | Constraint |
| auth_permission_codename_not_null | codename | Constraint |
| auth_permission_pkey | id | Primary key |
| auth_permission_content_type_id_codename_01ab375a_uniq | content_type_id, codename | Unique |
| auth_permission_content_type_id_2f476e4b_fk_django_co | content_type_id | Foreign key → django_content_type.id |
| auth_permission_name_not_null | name | Constraint |
| auth_permission_content_type_id_2f476e4b | content_type_id | Index |

## care_appointment

Purpose: Patient, doctor slot, consultation mode, status and fee snapshot. Model: care.Appointment. Snapshot rows: 14. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | char(32) | uuid | NO | — |
| mode | varchar(10) | character varying(10) | NO | — |
| status | varchar(12) | character varying(12) | NO | — |
| reason | varchar(400) | character varying(400) | NO | — |
| fee | decimal(8,2) | numeric(8,2) | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| patient_id | bigint | bigint | NO | — |
| slot_id | bigint | bigint | NO | — |
| checked_in_at | datetime(6) | timestamp with time zone | YES | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_appointment_id_not_null | id | Constraint |
| care_appointment_mode_not_null | mode | Constraint |
| care_appointment_status_not_null | status | Constraint |
| care_appointment_reason_not_null | reason | Constraint |
| care_appointment_fee_not_null | fee | Constraint |
| care_appointment_created_not_null | created | Constraint |
| care_appointment_patient_id_not_null | patient_id | Constraint |
| care_appointment_pkey | id | Primary key |
| care_appointment_slot_id_not_null | slot_id | Constraint |
| care_appointment_slot_id_0e47ae40_fk_care_slot_id | slot_id | Foreign key → care_slot.id |
| care_appointment_patient_id_b4175725_fk_care_user_id | patient_id | Foreign key → care_user.id |
| care_appointment_patient_id_b4175725 | patient_id | Index |
| care_appointment_slot_id_0e47ae40 | slot_id | Index |

## care_auditevent

Purpose: Recorded security and administrative events. Model: care.AuditEvent. Snapshot rows: 236. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| action | varchar(100) | character varying(100) | NO | — |
| target | varchar(120) | character varying(120) | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| actor_id | bigint | bigint | YES | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_auditevent_id_not_null | id | Constraint |
| care_auditevent_action_not_null | action | Constraint |
| care_auditevent_target_not_null | target | Constraint |
| care_auditevent_created_not_null | created | Constraint |
| care_auditevent_pkey | id | Primary key |
| care_auditevent_actor_id_66dff823_fk_care_user_id | actor_id | Foreign key → care_user.id |
| care_auditevent_actor_id_66dff823 | actor_id | Index |

## care_clinicalnote

Purpose: Private appointment-scoped clinical documentation. Model: care.ClinicalNote. Snapshot rows: 2. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| complaint | longtext | text | NO | — |
| examination | longtext | text | NO | — |
| assessment | longtext | text | NO | — |
| plan | longtext | text | NO | — |
| follow_up | longtext | text | NO | — |
| correction_reason | varchar(300) | character varying(300) | NO | — |
| version | int unsigned | integer | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| appointment_id | char(32) | uuid | NO | — |
| author_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_clinicalnote_version_check | version | Check |
| care_clinicalnote_id_not_null | id | Constraint |
| care_clinicalnote_complaint_not_null | complaint | Constraint |
| care_clinicalnote_examination_not_null | examination | Constraint |
| care_clinicalnote_assessment_not_null | assessment | Constraint |
| care_clinicalnote_plan_not_null | plan | Constraint |
| care_clinicalnote_follow_up_not_null | follow_up | Constraint |
| care_clinicalnote_correction_reason_not_null | correction_reason | Constraint |
| care_clinicalnote_version_not_null | version | Constraint |
| care_clinicalnote_created_not_null | created | Constraint |
| care_clinicalnote_appointment_id_not_null | appointment_id | Constraint |
| care_clinicalnote_author_id_not_null | author_id | Constraint |
| care_clinicalnote_pkey | id | Primary key |
| clinical_note_version | appointment_id, version | Unique |
| care_clinicalnote_appointment_id_f5da14e4_fk_care_appo | appointment_id | Foreign key → care_appointment.id |
| care_clinicalnote_author_id_91e035dd_fk_care_user_id | author_id | Foreign key → care_user.id |
| care_clinicalnote_appointment_id_f5da14e4 | appointment_id | Index |
| care_clinicalnote_author_id_91e035dd | author_id | Index |

## care_deliveryoutbox

Purpose: Durable deduplicated notification delivery attempts and outcome. Model: care.DeliveryOutbox. Snapshot rows: 45. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| dedupe_key | varchar(120) | character varying(120) | NO | — |
| status | varchar(12) | character varying(12) | NO | — |
| attempts | smallint unsigned | smallint | NO | — |
| lease_until | datetime(6) | timestamp with time zone | YES | — |
| next_attempt | datetime(6) | timestamp with time zone | NO | — |
| sent_at | datetime(6) | timestamp with time zone | YES | — |
| last_error | varchar(120) | character varying(120) | NO | — |
| notification_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_deliveryoutbox_attempts_check | attempts | Check |
| care_deliveryoutbox_id_not_null | id | Constraint |
| care_deliveryoutbox_dedupe_key_not_null | dedupe_key | Constraint |
| care_deliveryoutbox_status_not_null | status | Constraint |
| care_deliveryoutbox_attempts_not_null | attempts | Constraint |
| care_deliveryoutbox_next_attempt_not_null | next_attempt | Constraint |
| care_deliveryoutbox_last_error_not_null | last_error | Constraint |
| care_deliveryoutbox_notification_id_not_null | notification_id | Constraint |
| care_deliveryoutbox_pkey | id | Primary key |
| care_deliveryoutbox_dedupe_key_key | dedupe_key | Unique |
| care_deliveryoutbox_notification_id_key | notification_id | Unique |
| care_deliveryoutbox_notification_id_831511e8_fk_care_noti | notification_id | Foreign key → care_notification.id |
| care_deliveryoutbox_dedupe_key_d8aa0118_like | dedupe_key | Index |

## care_department

Purpose: Published clinical-service catalog and active status. Model: care.Department. Snapshot rows: 2. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| name | varchar(100) | character varying(100) | NO | — |
| description | varchar(400) | character varying(400) | NO | — |
| active | tinyint(1) | boolean | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_department_id_not_null | id | Constraint |
| care_department_name_not_null | name | Constraint |
| care_department_description_not_null | description | Constraint |
| care_department_active_not_null | active | Constraint |
| care_department_pkey | id | Primary key |
| care_department_name_key | name | Unique |
| care_department_name_f38d6ea8_like | name | Index |

## care_doctorprofile

Purpose: Doctor qualifications, registration, department and consultation fee. Model: care.DoctorProfile. Snapshot rows: 4. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| qualification | varchar(200) | character varying(200) | NO | — |
| registration_number | varchar(100) | character varying(100) | NO | — |
| experience | smallint unsigned | smallint | NO | — |
| bio | longtext | text | NO | — |
| fee | decimal(8,2) | numeric(8,2) | NO | — |
| department_id | bigint | bigint | YES | — |
| user_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_doctorprofile_experience_check | experience | Check |
| care_doctorprofile_id_not_null | id | Constraint |
| care_doctorprofile_qualification_not_null | qualification | Constraint |
| care_doctorprofile_registration_number_not_null | registration_number | Constraint |
| care_doctorprofile_experience_not_null | experience | Constraint |
| care_doctorprofile_bio_not_null | bio | Constraint |
| care_doctorprofile_fee_not_null | fee | Constraint |
| care_doctorprofile_user_id_not_null | user_id | Constraint |
| care_doctorprofile_pkey | id | Primary key |
| care_doctorprofile_registration_number_key | registration_number | Unique |
| care_doctorprofile_user_id_key | user_id | Unique |
| care_doctorprofile_department_id_82a25853_fk_care_department_id | department_id | Foreign key → care_department.id |
| care_doctorprofile_user_id_86bd5dae_fk_care_user_id | user_id | Foreign key → care_user.id |
| care_doctorprofile_department_id_82a25853 | department_id | Index |
| care_doctorprofile_registration_number_9f242fd6_like | registration_number | Index |

## care_healthassessment

Purpose: Saved educational lifestyle questionnaire responses. Model: care.HealthAssessment. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| answers | json | jsonb | NO | — |
| result | json | jsonb | NO | — |
| patient_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_healthassessment_id_not_null | id | Constraint |
| care_healthassessment_created_not_null | created | Constraint |
| care_healthassessment_answers_not_null | answers | Constraint |
| care_healthassessment_result_not_null | result | Constraint |
| care_healthassessment_patient_id_not_null | patient_id | Constraint |
| care_healthassessment_pkey | id | Primary key |
| care_healthassessment_patient_id_97a9f22a_fk_care_user_id | patient_id | Foreign key → care_user.id |
| care_healthassessment_patient_id_97a9f22a | patient_id | Index |

## care_hospital

Purpose: Verified hospital identity, contacts, hours, policies and emergency contact. Model: care.Hospital. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| name | varchar(120) | character varying(120) | NO | — |
| address | longtext | text | NO | — |
| phone | varchar(20) | character varying(20) | NO | — |
| ambulance | varchar(20) | character varying(20) | NO | — |
| email | varchar(254) | character varying(254) | NO | — |
| privacy_email | varchar(254) | character varying(254) | NO | — |
| legal_name | varchar(200) | character varying(200) | NO | — |
| retention_days | int unsigned | integer | NO | — |
| cancellation_policy | longtext | text | NO | — |
| cancellation_notice_minutes | int unsigned | integer | NO | — |
| opening_hours | varchar(600) | character varying(600) | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_hospital_retention_days_check | retention_days | Check |
| care_hospital_id_not_null | id | Constraint |
| care_hospital_name_not_null | name | Constraint |
| care_hospital_address_not_null | address | Constraint |
| care_hospital_phone_not_null | phone | Constraint |
| care_hospital_ambulance_not_null | ambulance | Constraint |
| care_hospital_email_not_null | email | Constraint |
| care_hospital_privacy_email_not_null | privacy_email | Constraint |
| care_hospital_legal_name_not_null | legal_name | Constraint |
| care_hospital_retention_days_not_null | retention_days | Constraint |
| care_hospital_cancellation_policy_not_null | cancellation_policy | Constraint |
| care_hospital_pkey | id | Primary key |
| care_hospital_cancellation_notice_minutes_not_null | cancellation_notice_minutes | Constraint |
| care_hospital_cancellation_notice_minutes_check | cancellation_notice_minutes | Check |
| care_hospital_opening_hours_not_null | opening_hours | Constraint |

## care_medicine

Purpose: Medicine catalog batches, expiry, stock balance and price. Model: care.Medicine. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| name | varchar(150) | character varying(150) | NO | — |
| batch | varchar(60) | character varying(60) | NO | — |
| expiry | date | date | NO | — |
| stock | int unsigned | integer | NO | — |
| price | decimal(8,2) | numeric(8,2) | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_medicine_stock_check | stock | Check |
| care_medicine_id_not_null | id | Constraint |
| care_medicine_name_not_null | name | Constraint |
| care_medicine_batch_not_null | batch | Constraint |
| care_medicine_expiry_not_null | expiry | Constraint |
| care_medicine_stock_not_null | stock | Constraint |
| care_medicine_price_not_null | price | Constraint |
| care_medicine_pkey | id | Primary key |
| unique_medicine_batch | name, batch | Unique |

## care_notification

Purpose: Private user account/appointment updates and read state. Model: care.Notification. Snapshot rows: 83. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| message | varchar(200) | character varying(200) | NO | — |
| read | tinyint(1) | boolean | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| appointment_id | char(32) | uuid | YES | — |
| recipient_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_notification_id_not_null | id | Constraint |
| care_notification_message_not_null | message | Constraint |
| care_notification_read_not_null | read | Constraint |
| care_notification_created_not_null | created | Constraint |
| care_notification_recipient_id_not_null | recipient_id | Constraint |
| care_notification_pkey | id | Primary key |
| care_notification_recipient_id_cbd51a5f_fk_care_user_id | recipient_id | Foreign key → care_user.id |
| care_notification_appointment_id_48aa7bec_fk_care_appo | appointment_id | Foreign key → care_appointment.id |
| care_notification_appointment_id_48aa7bec | appointment_id | Index |
| care_notification_recipient_id_cbd51a5f | recipient_id | Index |

## care_payment

Purpose: Appointment payment, provider verification and refund state. Model: care.Payment. Snapshot rows: 14. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| amount | decimal(8,2) | numeric(8,2) | NO | — |
| status | varchar(16) | character varying(16) | NO | — |
| method | varchar(12) | character varying(12) | NO | — |
| order_id | varchar(100) | character varying(100) | NO | — |
| provider_id | varchar(100) | character varying(100) | NO | — |
| reference | varchar(120) | character varying(120) | NO | — |
| updated | datetime(6) | timestamp with time zone | NO | — |
| appointment_id | char(32) | uuid | NO | — |
| received_by_id | bigint | bigint | YES | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_payment_id_not_null | id | Constraint |
| care_payment_amount_not_null | amount | Constraint |
| care_payment_status_not_null | status | Constraint |
| care_payment_method_not_null | method | Constraint |
| care_payment_order_id_not_null | order_id | Constraint |
| care_payment_provider_id_not_null | provider_id | Constraint |
| care_payment_reference_not_null | reference | Constraint |
| care_payment_updated_not_null | updated | Constraint |
| care_payment_appointment_id_not_null | appointment_id | Constraint |
| care_payment_pkey | id | Primary key |
| care_payment_appointment_id_key | appointment_id | Unique |
| care_payment_appointment_id_eb858144_fk_care_appointment_id | appointment_id | Foreign key → care_appointment.id |
| care_payment_received_by_id_926e2a05_fk_care_user_id | received_by_id | Foreign key → care_user.id |
| care_payment_received_by_id_926e2a05 | received_by_id | Index |

## care_prescription

Purpose: Doctor-issued appointment prescription retained after issue. Model: care.Prescription. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | char(32) | uuid | NO | — |
| instructions | longtext | text | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| dispensed | tinyint(1) | boolean | NO | — |
| dispensed_at | datetime(6) | timestamp with time zone | YES | — |
| appointment_id | char(32) | uuid | NO | — |
| dispensed_by_id | bigint | bigint | YES | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_prescription_id_not_null | id | Constraint |
| care_prescription_instructions_not_null | instructions | Constraint |
| care_prescription_created_not_null | created | Constraint |
| care_prescription_dispensed_not_null | dispensed | Constraint |
| care_prescription_appointment_id_not_null | appointment_id | Constraint |
| care_prescription_pkey | id | Primary key |
| care_prescription_appointment_id_key | appointment_id | Unique |
| care_prescription_appointment_id_6bcdfad5_fk_care_appo | appointment_id | Foreign key → care_appointment.id |
| care_prescription_dispensed_by_id_550e91d1_fk_care_user_id | dispensed_by_id | Foreign key → care_user.id |
| care_prescription_dispensed_by_id_550e91d1 | dispensed_by_id | Index |

## care_prescriptionitem

Purpose: Medicine/dose/quantity lines of a prescription. Model: care.PrescriptionItem. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| dose | varchar(200) | character varying(200) | NO | — |
| quantity | smallint unsigned | smallint | NO | — |
| medicine_id | bigint | bigint | NO | — |
| prescription_id | char(32) | uuid | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_prescriptionitem_quantity_check | quantity | Check |
| care_prescriptionitem_id_not_null | id | Constraint |
| care_prescriptionitem_dose_not_null | dose | Constraint |
| care_prescriptionitem_quantity_not_null | quantity | Constraint |
| care_prescriptionitem_medicine_id_not_null | medicine_id | Constraint |
| care_prescriptionitem_prescription_id_not_null | prescription_id | Constraint |
| care_prescriptionitem_pkey | id | Primary key |
| care_prescriptionitem_medicine_id_078b2732_fk_care_medicine_id | medicine_id | Foreign key → care_medicine.id |
| care_prescriptionite_prescription_id_c40868da_fk_care_pres | prescription_id | Foreign key → care_prescription.id |
| care_prescriptionitem_medicine_id_078b2732 | medicine_id | Index |
| care_prescriptionitem_prescription_id_c40868da | prescription_id | Index |

## care_queuecounter

Purpose: Locked date-specific queue token allocator. Model: care.QueueCounter. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| date | date | date | NO | — |
| number | int unsigned | integer | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_queuecounter_number_check | number | Check |
| care_queuecounter_id_not_null | id | Constraint |
| care_queuecounter_date_not_null | date | Constraint |
| care_queuecounter_number_not_null | number | Constraint |
| care_queuecounter_pkey | id | Primary key |
| care_queuecounter_date_key | date | Unique |

## care_queueentry

Purpose: Checked-in appointment queue number and operational state. Model: care.QueueEntry. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| date | date | date | NO | — |
| number | int unsigned | integer | NO | — |
| status | varchar(12) | character varying(12) | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| updated | datetime(6) | timestamp with time zone | NO | — |
| appointment_id | char(32) | uuid | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_queueentry_number_check | number | Check |
| care_queueentry_id_not_null | id | Constraint |
| care_queueentry_date_not_null | date | Constraint |
| care_queueentry_number_not_null | number | Constraint |
| care_queueentry_status_not_null | status | Constraint |
| care_queueentry_created_not_null | created | Constraint |
| care_queueentry_updated_not_null | updated | Constraint |
| care_queueentry_appointment_id_not_null | appointment_id | Constraint |
| care_queueentry_pkey | id | Primary key |
| care_queueentry_appointment_id_key | appointment_id | Unique |
| queue_daily_token | date, number | Unique |
| care_queueentry_appointment_id_b3b1fbc1_fk_care_appointment_id | appointment_id | Foreign key → care_appointment.id |

## care_ratebucket

Purpose: Private abuse/rate-limit counters. Model: care.RateBucket. Snapshot rows: 118. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| key | varchar(64) | character varying(64) | NO | — |
| count | int unsigned | integer | NO | — |
| expires | datetime(6) | timestamp with time zone | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_ratebucket_count_check | count | Check |
| care_ratebucket_id_not_null | id | Constraint |
| care_ratebucket_key_not_null | key | Constraint |
| care_ratebucket_count_not_null | count | Constraint |
| care_ratebucket_expires_not_null | expires | Constraint |
| care_ratebucket_pkey | id | Primary key |
| care_ratebucket_key_key | key | Unique |
| care_ratebucket_key_9452b5f5_like | key | Index |

## care_report

Purpose: Authorized medical upload metadata and private object keys. Model: care.Report. Snapshot rows: 1. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | char(32) | uuid | NO | — |
| title | varchar(120) | character varying(120) | NO | — |
| extension | varchar(5) | character varying(5) | NO | — |
| file | varchar(100) | character varying(100) | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| appointment_id | char(32) | uuid | NO | — |
| uploaded_by_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_report_id_not_null | id | Constraint |
| care_report_title_not_null | title | Constraint |
| care_report_extension_not_null | extension | Constraint |
| care_report_file_not_null | file | Constraint |
| care_report_created_not_null | created | Constraint |
| care_report_appointment_id_not_null | appointment_id | Constraint |
| care_report_uploaded_by_id_not_null | uploaded_by_id | Constraint |
| care_report_pkey | id | Primary key |
| care_report_appointment_id_d1306e85_fk_care_appointment_id | appointment_id | Foreign key → care_appointment.id |
| care_report_uploaded_by_id_ccabd984_fk_care_user_id | uploaded_by_id | Foreign key → care_user.id |
| care_report_appointment_id_d1306e85 | appointment_id | Index |
| care_report_uploaded_by_id_ccabd984 | uploaded_by_id | Index |

## care_signal

Purpose: Short-lived authorized WebRTC signaling payloads. Model: care.Signal. Snapshot rows: 0. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| kind | varchar(12) | character varying(12) | NO | — |
| payload | json | jsonb | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| appointment_id | char(32) | uuid | NO | — |
| sender_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_signal_id_not_null | id | Constraint |
| care_signal_kind_not_null | kind | Constraint |
| care_signal_payload_not_null | payload | Constraint |
| care_signal_created_not_null | created | Constraint |
| care_signal_appointment_id_not_null | appointment_id | Constraint |
| care_signal_sender_id_not_null | sender_id | Constraint |
| care_signal_pkey | id | Primary key |
| care_signal_appointment_id_2c345e47_fk_care_appointment_id | appointment_id | Foreign key → care_appointment.id |
| care_signal_sender_id_b00c5bf3_fk_care_user_id | sender_id | Foreign key → care_user.id |
| care_signal_appointment_id_2c345e47 | appointment_id | Index |
| care_signal_sender_id_b00c5bf3 | sender_id | Index |

## care_slot

Purpose: Published doctor consultation start, mode and active/booked state. Model: care.Slot. Snapshot rows: 22. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| start | datetime(6) | timestamp with time zone | NO | — |
| booked | tinyint(1) | boolean | NO | — |
| active | tinyint(1) | boolean | NO | — |
| doctor_id | bigint | bigint | NO | — |
| consultation_type | varchar(10) | character varying(10) | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_slot_id_not_null | id | Constraint |
| care_slot_start_not_null | start | Constraint |
| care_slot_booked_not_null | booked | Constraint |
| care_slot_active_not_null | active | Constraint |
| care_slot_doctor_id_not_null | doctor_id | Constraint |
| care_slot_pkey | id | Primary key |
| unique_doctor_slot | doctor_id, start | Unique |
| care_slot_doctor_id_0ea3cf91_fk_care_user_id | doctor_id | Foreign key → care_user.id |
| care_slot_consultation_type_not_null | consultation_type | Constraint |
| care_slot_doctor_id_0ea3cf91 | doctor_id | Index |

## care_stockmovement

Purpose: Reasoned stock changes, actor, prescription link and resulting balance. Model: care.StockMovement. Snapshot rows: 4. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| quantity | int | integer | NO | — |
| balance | int unsigned | integer | NO | — |
| reason | varchar(120) | character varying(120) | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| actor_id | bigint | bigint | NO | — |
| medicine_id | bigint | bigint | NO | — |
| prescription_id | char(32) | uuid | YES | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_stockmovement_balance_check | balance | Check |
| care_stockmovement_id_not_null | id | Constraint |
| care_stockmovement_quantity_not_null | quantity | Constraint |
| care_stockmovement_balance_not_null | balance | Constraint |
| care_stockmovement_reason_not_null | reason | Constraint |
| care_stockmovement_created_not_null | created | Constraint |
| care_stockmovement_actor_id_not_null | actor_id | Constraint |
| care_stockmovement_medicine_id_not_null | medicine_id | Constraint |
| care_stockmovement_pkey | id | Primary key |
| care_stockmovement_actor_id_bc85711e_fk_care_user_id | actor_id | Foreign key → care_user.id |
| care_stockmovement_medicine_id_7e30d52f_fk_care_medicine_id | medicine_id | Foreign key → care_medicine.id |
| care_stockmovement_prescription_id_12ea9f64_fk_care_pres | prescription_id | Foreign key → care_prescription.id |
| care_stockmovement_actor_id_bc85711e | actor_id | Index |
| care_stockmovement_medicine_id_7e30d52f | medicine_id | Index |
| care_stockmovement_prescription_id_12ea9f64 | prescription_id | Index |

## care_user

Purpose: Account identity, five-role/approval state and sensitive credential hashes. Model: care.User. Snapshot rows: 22. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| password | varchar(128) | character varying(128) | NO | — |
| last_login | datetime(6) | timestamp with time zone | YES | — |
| is_superuser | tinyint(1) | boolean | NO | — |
| first_name | varchar(150) | character varying(150) | NO | — |
| last_name | varchar(150) | character varying(150) | NO | — |
| is_staff | tinyint(1) | boolean | NO | — |
| is_active | tinyint(1) | boolean | NO | — |
| date_joined | datetime(6) | timestamp with time zone | NO | — |
| email | varchar(254) | character varying(254) | NO | — |
| name | varchar(120) | character varying(120) | NO | — |
| phone | varchar(20) | character varying(20) | NO | — |
| role | varchar(20) | character varying(20) | NO | — |
| approval | varchar(12) | character varying(12) | NO | — |
| review_note | varchar(300) | character varying(300) | NO | — |
| date_of_birth | date | date | YES | — |
| must_change_password | tinyint(1) | boolean | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_user_id_not_null | id | Constraint |
| care_user_password_not_null | password | Constraint |
| care_user_is_superuser_not_null | is_superuser | Constraint |
| care_user_first_name_not_null | first_name | Constraint |
| care_user_last_name_not_null | last_name | Constraint |
| care_user_is_staff_not_null | is_staff | Constraint |
| care_user_is_active_not_null | is_active | Constraint |
| care_user_date_joined_not_null | date_joined | Constraint |
| care_user_email_not_null | email | Constraint |
| care_user_name_not_null | name | Constraint |
| care_user_phone_not_null | phone | Constraint |
| care_user_role_not_null | role | Constraint |
| care_user_approval_not_null | approval | Constraint |
| care_user_review_note_not_null | review_note | Constraint |
| care_user_pkey | id | Primary key |
| care_user_email_key | email | Unique |
| care_user_must_change_password_not_null | must_change_password | Constraint |
| care_user_email_a1268be6_like | email | Index |

## care_user_groups

Purpose/model: care.User_groups. Snapshot rows: 0. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| user_id | bigint | bigint | NO | — |
| group_id | int | integer | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_user_groups_id_not_null | id | Constraint |
| care_user_groups_user_id_not_null | user_id | Constraint |
| care_user_groups_group_id_not_null | group_id | Constraint |
| care_user_groups_pkey | id | Primary key |
| care_user_groups_user_id_group_id_1eda340c_uniq | user_id, group_id | Unique |
| care_user_groups_user_id_41d4ff38_fk_care_user_id | user_id | Foreign key → care_user.id |
| care_user_groups_group_id_453e3af7_fk_auth_group_id | group_id | Foreign key → auth_group.id |
| care_user_groups_group_id_453e3af7 | group_id | Index |
| care_user_groups_user_id_41d4ff38 | user_id | Index |

## care_user_user_permissions

Purpose/model: care.User_user_permissions. Snapshot rows: 0. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| user_id | bigint | bigint | NO | — |
| permission_id | int | integer | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_user_user_permissions_id_not_null | id | Constraint |
| care_user_user_permissions_user_id_not_null | user_id | Constraint |
| care_user_user_permissions_permission_id_not_null | permission_id | Constraint |
| care_user_user_permissions_pkey | id | Primary key |
| care_user_user_permissions_user_id_permission_id_a4bcbb7c_uniq | user_id, permission_id | Unique |
| care_user_user_permissions_user_id_81986f5f_fk_care_user_id | user_id | Foreign key → care_user.id |
| care_user_user_permi_permission_id_db02c1d5_fk_auth_perm | permission_id | Foreign key → auth_permission.id |
| care_user_user_permissions_permission_id_db02c1d5 | permission_id | Index |
| care_user_user_permissions_user_id_81986f5f | user_id | Index |

## care_wellnessentry

Purpose: Patient/date lifestyle observations and non-clinical indicator. Model: care.WellnessEntry. Snapshot rows: 2. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| date | date | date | NO | — |
| sleep | decimal(4,1) | numeric(4,1) | NO | — |
| water | decimal(4,1) | numeric(4,1) | NO | — |
| exercise_days | smallint unsigned | smallint | NO | — |
| stress | smallint unsigned | smallint | NO | — |
| score | smallint unsigned | smallint | NO | — |
| updated | datetime(6) | timestamp with time zone | NO | — |
| patient_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_wellnessentry_exercise_days_check | exercise_days | Check |
| care_wellnessentry_stress_check | stress | Check |
| care_wellnessentry_score_check | score | Check |
| care_wellnessentry_id_not_null | id | Constraint |
| care_wellnessentry_date_not_null | date | Constraint |
| care_wellnessentry_sleep_not_null | sleep | Constraint |
| care_wellnessentry_water_not_null | water | Constraint |
| care_wellnessentry_exercise_days_not_null | exercise_days | Constraint |
| care_wellnessentry_stress_not_null | stress | Constraint |
| care_wellnessentry_score_not_null | score | Constraint |
| care_wellnessentry_updated_not_null | updated | Constraint |
| care_wellnessentry_patient_id_not_null | patient_id | Constraint |
| care_wellnessentry_pkey | id | Primary key |
| wellness_patient_date | patient_id, date | Unique |
| care_wellnessentry_patient_id_42b3bcb5_fk_care_user_id | patient_id | Foreign key → care_user.id |
| care_wellnessentry_patient_id_42b3bcb5 | patient_id | Index |

## care_wellnessrevision

Purpose: Wellness entry change history. Model: care.WellnessRevision. Snapshot rows: 3. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| values | json | jsonb | NO | — |
| created | datetime(6) | timestamp with time zone | NO | — |
| entry_id | bigint | bigint | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| care_wellnessrevision_id_not_null | id | Constraint |
| care_wellnessrevision_values_not_null | values | Constraint |
| care_wellnessrevision_created_not_null | created | Constraint |
| care_wellnessrevision_entry_id_not_null | entry_id | Constraint |
| care_wellnessrevision_pkey | id | Primary key |
| care_wellnessrevisio_entry_id_70499e0a_fk_care_well | entry_id | Foreign key → care_wellnessentry.id |
| care_wellnessrevision_entry_id_70499e0a | entry_id | Index |

## django_content_type

Purpose: Django model/content-type registry. Model: contenttypes.ContentType. Snapshot rows: 27. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | int | integer | NO | — |
| app_label | varchar(100) | character varying(100) | NO | — |
| model | varchar(100) | character varying(100) | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| django_content_type_id_not_null | id | Constraint |
| django_content_type_app_label_not_null | app_label | Constraint |
| django_content_type_model_not_null | model | Constraint |
| django_content_type_pkey | id | Primary key |
| django_content_type_app_label_model_76bd3d3b_uniq | app_label, model | Unique |

## django_migrations

Purpose/model: Django schema migration history. Snapshot rows: 20. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| id | bigint | bigint | NO | — |
| app | varchar(255) | character varying(255) | NO | — |
| name | varchar(255) | character varying(255) | NO | — |
| applied | datetime(6) | timestamp with time zone | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| django_migrations_id_not_null | id | Constraint |
| django_migrations_app_not_null | app | Constraint |
| django_migrations_name_not_null | name | Constraint |
| django_migrations_applied_not_null | applied | Constraint |
| django_migrations_pkey | id | Primary key |

## django_session

Purpose: Sensitive server-side authentication session records. Model: sessions.Session. Snapshot rows: 57. RLS: enabled=True, forced=True.

| Column | Source MySQL type | Actual PostgreSQL type | Nullable | Default |
|---|---|---|---|---|
| session_key | varchar(40) | character varying(40) | NO | — |
| session_data | longtext | text | NO | — |
| expire_date | datetime(6) | timestamp with time zone | NO | — |

| Key / constraint | Columns | Definition |
|---|---|---|
| django_session_session_key_not_null | session_key | Constraint |
| django_session_session_data_not_null | session_data | Constraint |
| django_session_expire_date_not_null | expire_date | Constraint |
| django_session_pkey | session_key | Primary key |
| django_session_expire_date_a5c62663 | expire_date | Index |
| django_session_session_key_c0390e0f_like | session_key | Index |
