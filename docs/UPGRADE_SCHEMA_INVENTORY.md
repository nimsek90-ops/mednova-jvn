# Current MySQL schema — hospital upgrade

Actual primary: mednova_local, MySQL8.4.13, 46 tables. Metadata only; no record values. Migrations care0001–0009 are applied. Historical schema reports describe the earlier31-table state.

## auth_group

auth.Group

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | int | NO | PRI |
| name | varchar(150) | NO | UNI |

Constraints and indexes:

- name: {"columns": ["name"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## auth_group_permissions

auth.Group_permissions

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| group_id | int | NO | MUL |
| permission_id | int | NO | MUL |

Constraints and indexes:

- auth_group_permissio_permission_id_84c5c92e_fk_auth_perm: {"columns": ["permission_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["auth_permission", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- auth_group_permissions_group_id_b120cbf9_fk_auth_group_id: {"columns": ["group_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["auth_group", "id"]}
- auth_group_permissions_group_id_permission_id_0cd325b0_uniq: {"columns": ["group_id", "permission_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## auth_permission

auth.Permission

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | int | NO | PRI |
| name | varchar(255) | NO |  |
| content_type_id | int | NO | MUL |
| codename | varchar(100) | NO |  |

Constraints and indexes:

- auth_permission_content_type_id_2f476e4b_fk_django_co: {"columns": ["content_type_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["django_content_type", "id"]}
- auth_permission_content_type_id_codename_01ab375a_uniq: {"columns": ["content_type_id", "codename"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_admission

care.Admission

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| status | varchar(16) | NO |  |
| last_bed | varchar(200) | NO |  |
| created | datetime(6) | NO |  |
| updated | datetime(6) | NO |  |
| department_id | bigint | NO | MUL |
| doctor_id | bigint | NO | MUL |
| patient_id | bigint | NO | MUL |
| bed_id | bigint | YES | UNI |

Constraints and indexes:

- bed_id: {"columns": ["bed_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_admission_bed_id_fecf2e36_fk_care_bed_id: {"columns": ["bed_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_bed", "id"]}
- care_admission_department_id_a690c14f_fk_care_department_id: {"columns": ["department_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_department", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_admission_doctor_id_b52f18e7_fk_care_user_id: {"columns": ["doctor_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_admission_patient_id_e820bc3b_fk_care_user_id: {"columns": ["patient_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_appointment

care.Appointment

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | char(32) | NO | PRI |
| mode | varchar(10) | NO |  |
| status | varchar(12) | NO |  |
| reason | varchar(400) | NO |  |
| fee | decimal(8,2) | NO |  |
| created | datetime(6) | NO |  |
| patient_id | bigint | NO | MUL |
| slot_id | bigint | NO | MUL |
| checked_in_at | datetime(6) | YES |  |
| cancellation_reason | varchar(300) | NO |  |

Constraints and indexes:

- care_appointment_patient_id_b4175725_fk_care_user_id: {"columns": ["patient_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_appointment_slot_id_0e47ae40_fk_care_slot_id: {"columns": ["slot_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_slot", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_assistantescalation

care.AssistantEscalation

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| topic | varchar(24) | NO |  |
| resolved | tinyint(1) | NO |  |
| created | datetime(6) | NO |  |
| patient_id | bigint | NO | MUL |

Constraints and indexes:

- care_assistantescalation_patient_id_2c05a23b_fk_care_user_id: {"columns": ["patient_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_auditevent

care.AuditEvent

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| action | varchar(100) | NO |  |
| target | varchar(120) | NO |  |
| created | datetime(6) | NO |  |
| actor_id | bigint | YES | MUL |

Constraints and indexes:

- care_auditevent_actor_id_66dff823_fk_care_user_id: {"columns": ["actor_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_bed

care.Bed

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| label | varchar(80) | NO | UNI |
| ward | varchar(100) | NO |  |
| room_type | varchar(100) | NO |  |
| active | tinyint(1) | NO |  |

Constraints and indexes:

- label: {"columns": ["label"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_clinicaldraft

care.ClinicalDraft

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| complaint | longtext | NO |  |
| examination | longtext | NO |  |
| assessment | longtext | NO |  |
| plan | longtext | NO |  |
| follow_up | longtext | NO |  |
| revision | int unsigned | NO |  |
| updated | datetime(6) | NO |  |
| appointment_id | char(32) | NO | UNI |
| author_id | bigint | NO | MUL |

Constraints and indexes:

- appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_clinicaldraft_appointment_id_198e23b1_fk_care_appo: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_appointment", "id"]}
- care_clinicaldraft_author_id_4eff61f6_fk_care_user_id: {"columns": ["author_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_clinicaldraft_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_clinicalnote

care.ClinicalNote

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| complaint | longtext | NO |  |
| examination | longtext | NO |  |
| assessment | longtext | NO |  |
| plan | longtext | NO |  |
| follow_up | longtext | NO |  |
| correction_reason | varchar(300) | NO |  |
| version | int unsigned | NO |  |
| created | datetime(6) | NO |  |
| appointment_id | char(32) | NO | MUL |
| author_id | bigint | NO | MUL |

Constraints and indexes:

- care_clinicalnote_appointment_id_f5da14e4_fk_care_appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_appointment", "id"]}
- care_clinicalnote_author_id_91e035dd_fk_care_user_id: {"columns": ["author_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_clinicalnote_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- clinical_note_version: {"columns": ["appointment_id", "version"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_deliveryoutbox

care.DeliveryOutbox

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| dedupe_key | varchar(120) | NO | UNI |
| status | varchar(12) | NO |  |
| attempts | smallint unsigned | NO |  |
| lease_until | datetime(6) | YES |  |
| next_attempt | datetime(6) | NO |  |
| sent_at | datetime(6) | YES |  |
| last_error | varchar(120) | NO |  |
| notification_id | bigint | NO | UNI |

Constraints and indexes:

- care_deliveryoutbox_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_deliveryoutbox_notification_id_831511e8_fk_care_noti: {"columns": ["notification_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_notification", "id"]}
- dedupe_key: {"columns": ["dedupe_key"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- notification_id: {"columns": ["notification_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_department

care.Department

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| name | varchar(100) | NO | UNI |
| description | varchar(400) | NO |  |
| active | tinyint(1) | NO |  |

Constraints and indexes:

- name: {"columns": ["name"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_dispensingevent

care.DispensingEvent

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| key | char(32) | NO | UNI |
| quantity | smallint unsigned | NO |  |
| created | datetime(6) | NO |  |
| item_id | bigint | NO | MUL |
| pharmacist_id | bigint | NO | MUL |

Constraints and indexes:

- care_dispensingevent_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_dispensingevent_item_id_bb96344c_fk_care_pres: {"columns": ["item_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_prescriptionitem", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_dispensingevent_pharmacist_id_21d9d1a2_fk_care_user_id: {"columns": ["pharmacist_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- key: {"columns": ["key"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_doctorprofile

care.DoctorProfile

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| qualification | varchar(200) | NO |  |
| registration_number | varchar(100) | NO | UNI |
| experience | smallint unsigned | NO |  |
| bio | longtext | NO |  |
| fee | decimal(8,2) | NO |  |
| department_id | bigint | YES | MUL |
| user_id | bigint | NO | UNI |
| daily_limit | smallint unsigned | NO |  |
| location | varchar(160) | NO |  |

Constraints and indexes:

- care_doctorprofile_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_doctorprofile_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_doctorprofile_department_id_82a25853_fk_care_department_id: {"columns": ["department_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_department", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_doctorprofile_user_id_86bd5dae_fk_care_user_id: {"columns": ["user_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- registration_number: {"columns": ["registration_number"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- user_id: {"columns": ["user_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_goodsreceipt

care.GoodsReceipt

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| reference | varchar(120) | NO | UNI |
| quantity | int unsigned | NO |  |
| created | datetime(6) | NO |  |
| received_by_id | bigint | NO | MUL |
| order_id | bigint | NO | MUL |

Constraints and indexes:

- care_goodsreceipt_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_goodsreceipt_order_id_6a376b81_fk_care_purchaseorder_id: {"columns": ["order_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_purchaseorder", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_goodsreceipt_received_by_id_526f1d87_fk_care_user_id: {"columns": ["received_by_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- reference: {"columns": ["reference"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_healthassessment

care.HealthAssessment

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| created | datetime(6) | NO |  |
| answers | json | NO |  |
| result | json | NO |  |
| patient_id | bigint | NO | MUL |

Constraints and indexes:

- care_healthassessment_patient_id_97a9f22a_fk_care_user_id: {"columns": ["patient_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_hospital

care.Hospital

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| name | varchar(120) | NO |  |
| address | longtext | NO |  |
| phone | varchar(20) | NO |  |
| ambulance | varchar(20) | NO |  |
| email | varchar(254) | NO |  |
| privacy_email | varchar(254) | NO |  |
| legal_name | varchar(200) | NO |  |
| retention_days | int unsigned | NO |  |
| cancellation_policy | longtext | NO |  |
| cancellation_notice_minutes | int unsigned | NO |  |
| opening_hours | varchar(600) | NO |  |

Constraints and indexes:

- care_hospital_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_hospital_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_hospitalfaq

care.HospitalFAQ

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| question | varchar(200) | NO |  |
| answer | longtext | NO |  |
| language | varchar(2) | NO |  |
| approved | tinyint(1) | NO |  |
| updated | datetime(6) | NO |  |

Constraints and indexes:

- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_investigation

care.Investigation

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| category | varchar(12) | NO |  |
| name | varchar(180) | NO |  |
| status | varchar(12) | NO |  |
| result | longtext | NO |  |
| critical | tinyint(1) | NO |  |
| acknowledged_at | datetime(6) | YES |  |
| created | datetime(6) | NO |  |
| appointment_id | char(32) | NO | MUL |
| ordered_by_id | bigint | NO | MUL |

Constraints and indexes:

- care_investigation_appointment_id_80a3dcca_fk_care_appo: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_appointment", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_investigation_ordered_by_id_b7e67b80_fk_care_user_id: {"columns": ["ordered_by_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_medicine

care.Medicine

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| name | varchar(150) | NO | MUL |
| batch | varchar(60) | NO |  |
| expiry | date | NO |  |
| stock | int unsigned | NO |  |
| price | decimal(8,2) | NO |  |
| barcode | varchar(100) | NO |  |
| dosage_form | varchar(80) | NO |  |
| generic_name | varchar(150) | NO |  |
| location | varchar(120) | NO |  |
| manufacturer | varchar(150) | NO |  |
| purchase_price | decimal(8,2) | NO |  |
| reorder_level | int unsigned | NO |  |
| safety_status | varchar(12) | NO |  |
| strength | varchar(80) | NO |  |

Constraints and indexes:

- care_medicine_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_medicine_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- unique_medicine_batch: {"columns": ["name", "batch"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}

## care_notification

care.Notification

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| message | varchar(200) | NO |  |
| read | tinyint(1) | NO |  |
| created | datetime(6) | NO |  |
| appointment_id | char(32) | YES | MUL |
| recipient_id | bigint | NO | MUL |

Constraints and indexes:

- care_notification_appointment_id_48aa7bec_fk_care_appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_appointment", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_notification_recipient_id_cbd51a5f_fk_care_user_id: {"columns": ["recipient_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_patientregistration

care.PatientRegistration

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| mrn | char(32) | NO | UNI |
| emergency_name | varchar(120) | NO |  |
| emergency_phone | varchar(20) | NO |  |
| guardian | varchar(120) | NO |  |
| consent | tinyint(1) | NO |  |
| created | datetime(6) | NO |  |
| patient_id | bigint | NO | UNI |

Constraints and indexes:

- care_patientregistration_patient_id_92f99ed7_fk_care_user_id: {"columns": ["patient_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- mrn: {"columns": ["mrn"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- patient_id: {"columns": ["patient_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_payment

care.Payment

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| amount | decimal(8,2) | NO |  |
| status | varchar(16) | NO |  |
| method | varchar(12) | NO |  |
| order_id | varchar(100) | NO |  |
| provider_id | varchar(100) | NO |  |
| reference | varchar(120) | NO |  |
| updated | datetime(6) | NO |  |
| appointment_id | char(32) | NO | UNI |
| received_by_id | bigint | YES | MUL |

Constraints and indexes:

- appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_payment_appointment_id_eb858144_fk_care_appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_appointment", "id"]}
- care_payment_received_by_id_926e2a05_fk_care_user_id: {"columns": ["received_by_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_prescription

care.Prescription

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | char(32) | NO | PRI |
| instructions | longtext | NO |  |
| created | datetime(6) | NO |  |
| dispensed | tinyint(1) | NO |  |
| dispensed_at | datetime(6) | YES |  |
| appointment_id | char(32) | NO | UNI |
| dispensed_by_id | bigint | YES | MUL |

Constraints and indexes:

- appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_prescription_appointment_id_6bcdfad5_fk_care_appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_appointment", "id"]}
- care_prescription_dispensed_by_id_550e91d1_fk_care_user_id: {"columns": ["dispensed_by_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_prescriptionitem

care.PrescriptionItem

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| dose | varchar(200) | NO |  |
| quantity | smallint unsigned | NO |  |
| medicine_id | bigint | NO | MUL |
| prescription_id | char(32) | NO | MUL |
| dispensed_quantity | smallint unsigned | NO |  |
| duration_text | varchar(100) | NO |  |
| frequency | varchar(100) | NO |  |
| route | varchar(60) | NO |  |

Constraints and indexes:

- care_prescriptionite_prescription_id_c40868da_fk_care_pres: {"columns": ["prescription_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_prescription", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_prescriptionitem_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_prescriptionitem_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_prescriptionitem_medicine_id_078b2732_fk_care_medicine_id: {"columns": ["medicine_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_medicine", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- issue_not_above_prescribed: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_purchaseorder

care.PurchaseOrder

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| quantity | int unsigned | NO |  |
| received | int unsigned | NO |  |
| status | varchar(12) | NO |  |
| created | datetime(6) | NO |  |
| approved_by_id | bigint | YES | MUL |
| medicine_id | bigint | NO | MUL |
| requested_by_id | bigint | NO | MUL |
| supplier_id | bigint | NO | MUL |

Constraints and indexes:

- care_purchaseorder_approved_by_id_a278bb6a_fk_care_user_id: {"columns": ["approved_by_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_purchaseorder_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_purchaseorder_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_purchaseorder_medicine_id_c7277a1b_fk_care_medicine_id: {"columns": ["medicine_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_medicine", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_purchaseorder_requested_by_id_f36839c1_fk_care_user_id: {"columns": ["requested_by_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_purchaseorder_supplier_id_602fdae7_fk_care_supplier_id: {"columns": ["supplier_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_supplier", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- receipt_not_above_order: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}

## care_queuecounter

care.QueueCounter

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| date | date | NO | UNI |
| number | int unsigned | NO |  |

Constraints and indexes:

- care_queuecounter_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- date: {"columns": ["date"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_queueentry

care.QueueEntry

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| date | date | NO | MUL |
| number | int unsigned | NO |  |
| status | varchar(20) | NO |  |
| created | datetime(6) | NO |  |
| updated | datetime(6) | NO |  |
| appointment_id | char(32) | NO | UNI |

Constraints and indexes:

- appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_queueentry_appointment_id_b3b1fbc1_fk_care_appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_appointment", "id"]}
- care_queueentry_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- queue_daily_token: {"columns": ["date", "number"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}

## care_ratebucket

care.RateBucket

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| key | varchar(64) | NO | UNI |
| count | int unsigned | NO |  |
| expires | datetime(6) | NO |  |

Constraints and indexes:

- care_ratebucket_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- key: {"columns": ["key"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_report

care.Report

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | char(32) | NO | PRI |
| title | varchar(120) | NO |  |
| extension | varchar(5) | NO |  |
| file | varchar(100) | NO |  |
| created | datetime(6) | NO |  |
| appointment_id | char(32) | NO | MUL |
| uploaded_by_id | bigint | NO | MUL |

Constraints and indexes:

- care_report_appointment_id_d1306e85_fk_care_appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_appointment", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_report_uploaded_by_id_ccabd984_fk_care_user_id: {"columns": ["uploaded_by_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_scheduleblock

care.ScheduleBlock

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| start | datetime(6) | NO |  |
| end | datetime(6) | NO |  |
| reason | varchar(120) | NO |  |
| doctor_id | bigint | NO | MUL |

Constraints and indexes:

- care_scheduleblock_doctor_id_1e9fa32e_fk_care_user_id: {"columns": ["doctor_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- schedule_positive_block: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}

## care_schedulesession

care.ScheduleSession

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| weekday | smallint unsigned | NO |  |
| start | time(6) | NO |  |
| end | time(6) | NO |  |
| duration | smallint unsigned | NO |  |
| buffer | smallint unsigned | NO |  |
| mode | varchar(10) | NO |  |
| visit_type | varchar(12) | NO |  |
| capacity | smallint unsigned | NO |  |
| active | tinyint(1) | NO |  |
| doctor_id | bigint | NO | MUL |

Constraints and indexes:

- care_schedulesession_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_schedulesession_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_schedulesession_chk_3: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_schedulesession_chk_4: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_schedulesession_doctor_id_73794033_fk_care_user_id: {"columns": ["doctor_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- schedule_doctor_day_start: {"columns": ["doctor_id", "weekday", "start"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC", "ASC"], "index_type": "BTREE"}
- schedule_positive_session: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- schedule_valid_limits: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}

## care_signal

care.Signal

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| kind | varchar(12) | NO |  |
| payload | json | NO |  |
| created | datetime(6) | NO |  |
| appointment_id | char(32) | NO | MUL |
| sender_id | bigint | NO | MUL |

Constraints and indexes:

- care_signal_appointment_id_2c345e47_fk_care_appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_appointment", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_signal_sender_id_b00c5bf3_fk_care_user_id: {"columns": ["sender_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_slot

care.Slot

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| start | datetime(6) | NO |  |
| booked | tinyint(1) | NO |  |
| active | tinyint(1) | NO |  |
| doctor_id | bigint | NO | MUL |
| consultation_type | varchar(10) | NO |  |
| buffer | smallint unsigned | NO |  |
| duration | smallint unsigned | NO |  |
| session_id | bigint | YES | MUL |

Constraints and indexes:

- care_slot_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_slot_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_slot_doctor_id_0ea3cf91_fk_care_user_id: {"columns": ["doctor_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- care_slot_session_id_e0272692_fk_care_schedulesession_id: {"columns": ["session_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_schedulesession", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- unique_doctor_slot: {"columns": ["doctor_id", "start"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}

## care_stockmovement

care.StockMovement

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| quantity | int | NO |  |
| balance | int unsigned | NO |  |
| reason | varchar(120) | NO |  |
| created | datetime(6) | NO |  |
| actor_id | bigint | NO | MUL |
| medicine_id | bigint | NO | MUL |
| prescription_id | char(32) | YES | MUL |

Constraints and indexes:

- care_stockmovement_actor_id_bc85711e_fk_care_user_id: {"columns": ["actor_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_stockmovement_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_stockmovement_medicine_id_7e30d52f_fk_care_medicine_id: {"columns": ["medicine_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_medicine", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_stockmovement_prescription_id_12ea9f64_fk_care_pres: {"columns": ["prescription_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_prescription", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_supplier

care.Supplier

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| name | varchar(150) | NO | UNI |
| contact | varchar(160) | NO |  |
| active | tinyint(1) | NO |  |

Constraints and indexes:

- name: {"columns": ["name"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_user

care.User

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| password | varchar(128) | NO |  |
| last_login | datetime(6) | YES |  |
| is_superuser | tinyint(1) | NO |  |
| first_name | varchar(150) | NO |  |
| last_name | varchar(150) | NO |  |
| is_staff | tinyint(1) | NO |  |
| is_active | tinyint(1) | NO |  |
| date_joined | datetime(6) | NO |  |
| email | varchar(254) | NO | UNI |
| name | varchar(120) | NO |  |
| phone | varchar(20) | NO |  |
| role | varchar(20) | NO |  |
| approval | varchar(12) | NO |  |
| review_note | varchar(300) | NO |  |
| date_of_birth | date | YES |  |
| must_change_password | tinyint(1) | NO |  |

Constraints and indexes:

- email: {"columns": ["email"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_user_groups

care.User_groups

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| user_id | bigint | NO | MUL |
| group_id | int | NO | MUL |

Constraints and indexes:

- care_user_groups_group_id_453e3af7_fk_auth_group_id: {"columns": ["group_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["auth_group", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_user_groups_user_id_41d4ff38_fk_care_user_id: {"columns": ["user_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- care_user_groups_user_id_group_id_1eda340c_uniq: {"columns": ["user_id", "group_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_user_user_permissions

care.User_user_permissions

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| user_id | bigint | NO | MUL |
| permission_id | int | NO | MUL |

Constraints and indexes:

- care_user_user_permi_permission_id_db02c1d5_fk_auth_perm: {"columns": ["permission_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["auth_permission", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_user_user_permissions_user_id_81986f5f_fk_care_user_id: {"columns": ["user_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- care_user_user_permissions_user_id_permission_id_a4bcbb7c_uniq: {"columns": ["user_id", "permission_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_videoattendance

care.VideoAttendance

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| patient_consented_at | datetime(6) | YES |  |
| admitted_at | datetime(6) | YES |  |
| ended_at | datetime(6) | YES |  |
| appointment_id | char(32) | NO | UNI |

Constraints and indexes:

- appointment_id: {"columns": ["appointment_id"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_videoattendance_appointment_id_f33b37fa_fk_care_appo: {"columns": ["appointment_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_appointment", "id"]}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## care_waitinglist

care.WaitingList

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| mode | varchar(10) | NO |  |
| active | tinyint(1) | NO |  |
| created | datetime(6) | NO |  |
| doctor_id | bigint | NO | MUL |
| patient_id | bigint | NO | MUL |

Constraints and indexes:

- care_waitinglist_doctor_id_bb065168_fk_care_user_id: {"columns": ["doctor_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_user", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- care_waitinglist_patient_id_32d307f8_fk_care_user_id: {"columns": ["patient_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- waiting_patient_doctor_mode: {"columns": ["patient_id", "doctor_id", "mode"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC", "ASC"], "index_type": "BTREE"}

## care_wellnessentry

care.WellnessEntry

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| date | date | NO |  |
| sleep | decimal(4,1) | NO |  |
| water | decimal(4,1) | NO |  |
| exercise_days | smallint unsigned | NO |  |
| stress | smallint unsigned | NO |  |
| score | smallint unsigned | NO |  |
| updated | datetime(6) | NO |  |
| patient_id | bigint | NO | MUL |

Constraints and indexes:

- care_wellnessentry_chk_1: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_wellnessentry_chk_2: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_wellnessentry_chk_3: {"columns": [], "primary_key": false, "unique": false, "index": false, "check": true, "foreign_key": null}
- care_wellnessentry_patient_id_42b3bcb5_fk_care_user_id: {"columns": ["patient_id"], "primary_key": false, "unique": false, "index": false, "check": false, "foreign_key": ["care_user", "id"]}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- wellness_patient_date: {"columns": ["patient_id", "date"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}

## care_wellnessrevision

care.WellnessRevision

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| values | json | NO |  |
| created | datetime(6) | NO |  |
| entry_id | bigint | NO | MUL |

Constraints and indexes:

- care_wellnessrevision_entry_id_70499e0a_fk_care_wellnessentry_id: {"columns": ["entry_id"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": ["care_wellnessentry", "id"], "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## django_content_type

contenttypes.ContentType

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | int | NO | PRI |
| app_label | varchar(100) | NO | MUL |
| model | varchar(100) | NO |  |

Constraints and indexes:

- django_content_type_app_label_model_76bd3d3b_uniq: {"columns": ["app_label", "model"], "primary_key": false, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC", "ASC"], "index_type": "BTREE"}
- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## django_migrations

Django schema migration history

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| id | bigint | NO | PRI |
| app | varchar(255) | NO |  |
| name | varchar(255) | NO |  |
| applied | datetime(6) | NO |  |

Constraints and indexes:

- PRIMARY: {"columns": ["id"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}

## django_session

sessions.Session

| Column | SQL type | Nullable | Key |
|---|---|---|---|
| session_key | varchar(40) | NO | PRI |
| session_data | longtext | NO |  |
| expire_date | datetime(6) | NO | MUL |

Constraints and indexes:

- PRIMARY: {"columns": ["session_key"], "primary_key": true, "unique": true, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
- django_session_expire_date_a5c62663: {"columns": ["expire_date"], "primary_key": false, "unique": false, "index": true, "check": false, "foreign_key": null, "type": "idx", "orders": ["ASC"], "index_type": "BTREE"}
