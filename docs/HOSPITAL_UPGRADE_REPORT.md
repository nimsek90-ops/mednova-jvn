# MedNova hospital upgrade — 23 October 2026

**A working integrated upgrade is implemented and running locally. The entire large-hospital specification is not complete and this is not a production-readiness claim.** The existing Django application, five roles, email login, MySQL database, business records and history were retained. Start at http://127.0.0.1:8000/dashboard/ and use the role's worklist/navigation.

## Implemented and verified scope

| Requested area | Status | Actual implementation / limit |
|---|---|---|
| Audit and preservation | PASS | Clean Git baseline002920c; existing application files inspected; plan in MEDNOVA_IMPLEMENTATION_PLAN.md. Baseline124 MySQL tests passed before changes. Private backups taken before migration. |
| Authentication and roles | PASS | Existing five working role links/shared authentication preserved; stored roles authorize requests, not submitted labels. Existing cross-role, ownership, CSRF, inactive account and administrator provisioning tests retained. Browser signed into all five synthetic roles. No human credential was reset or bundled. |
| Doctor scheduling | PASS for core workflow | Weekly multi-session rules, new/follow-up/urgent session labels, mode, duration+buffer, per-session cap, per-doctor daily cap, blocks/leave/rounds/holidays, explicit date publishing, disable/enable and one-off availability. Existing12minute slots remain12minutes with zero buffer. Blocks reject overlaps with booked visits; staff must reschedule/cancel first. |
| Consistent booking | PASS | Directory, profiles, Patient/Reception booking and assistant use shared available_slots; book rechecks rules under patient/doctor/slot locks. Interval overlap includes buffers; daily/session caps and urgent restrictions are enforced at commit. Cancellation/rescheduling and slot reuse remain integrated. |
| Appointment operations | PASS core / PARTIAL broader scope | Existing calendar supports day/week/month; appointment list adds date-range/department filters, no-show state, cancellation reason, queue in-consultation state, waiting-list subscriptions and cancellation notifications. Formal linked follow-up episodes and proactive clinic-delay broadcasts are not implemented. |
| Doctor worklist and clinical notes | PASS core / PARTIAL EMR | Live assigned visits and recorded critical-result counts; private revision-checked drafts; explicit review into existing finalized versioned notes; immutable older finalized versions and correction reason retained. Full structured allergy/medication/vitals/diagnostic/problem lists are not implemented. |
| Investigations/referrals | PASS local record workflow / PARTIAL integration | Assigned doctor creates lab/radiology/referral orders, records a verified result once and acknowledges it; patient sees only their own orders/results, never private drafts. No laboratory/radiology staff role, instrument feed, specialist task routing, validated critical thresholds or external result feed is connected. |
| Reception registration | PASS core / PARTIAL extended scope | Stable full UUID MRN for existing/new patient identities; operational registration card, guardian/emergency contact and consent fields; print control; name/email/phone/MRN lookup; duplicate email rejection and phone-review check, never automatic merge. Advanced identity matching, MRN merge resolution, provisional unknown-patient emergency registration, dependant trees, label printers and registration-document upload workflows are not implemented. |
| Queue/check-in | PASS core | Existing check-in/token uniqueness preserved; waiting/called/in-consultation/completed/cancelled transitions and no-show closure. No fabricated waiting-time estimates. Department routing/clinical emergency escalation beyond operational registration is incomplete. |
| Admissions/beds | PASS core / PARTIAL IPD | Responsible doctor requests admission; reception/admin allocate or transfer an unoccupied bed transactionally; only responsible doctor authorizes discharge readiness; desk completion releases bed and preserves the last-bed label and audit action. No full ward/procedure/perioperative notes, signed discharge summary, nursing task system, clinical handover or emergency/ambulance module is implemented. |
| Pharmacy catalogue/safety | PASS core | Generic/strength/form/manufacturer/location/barcode/reorder/purchase-price fields, batch expiry, FEFO display ordering, quarantine/recall/damage states, admin-only release and audited changes. Both whole and partial dispensing reject expired/unavailable batches. FEFO does not automatically substitute clinically different products. |
| Partial dispensing | PASS | Remaining quantities, pharmacist/quantity/timestamp/batch issue events and idempotent request UUID; transactional stock movement, no negative stock or repeated completion; full dispensing safely finishes only remaining quantities. Historical completed prescriptions backfilled to prevent reissue. |
| Suppliers/purchasing | PASS core / PARTIAL procurement | Supplier records, purchase requisition, admin approval, verified partial/full GRN with unique delivery reference, outstanding quantity and transactional stock addition. Supplier credit notes/returns/invoices/payment reconciliation/reorder forecasting are not implemented. |
| Advanced pharmacy/compliance | NOT IMPLEMENTED / external validation needed | Ward/ICU/OT stock requests, multi-store transfers, stocktakes/returns, restricted/controlled medicine registers, cold-chain incidents and antimicrobial workflows remain incomplete. No validated allergy/interaction/duplicate-therapy dataset or regulatory certification is claimed. |
| Billing | PASS preserved / PARTIAL new scope | Existing consultation payment records/receipts, authorized manual payments and Razorpay integration structure preserved. No fake success. Pharmacy invoices/taxes/discount/refund approvals, TPA/insurance/cashier reconciliation and medicine billing linkage are not implemented. |
| Patient assistant | PASS core / PARTIAL AI/chat scope | Floating entry, responsive service page, real doctor/slot search, explicit confirmed booking through book(), own appointment/report/prescription/billing links, approved multilingual FAQs, private session reply history, topic-only support escalation and Admin resolution/FAQ approval. Raw questions are not stored. Cancellation/reschedule use the existing authorized visit screens. Not a free-form generative medical chatbot; no AI provider call/credential is required. Full English/Marathi/Hindi translation coverage is incomplete. |
| Emergency guidance | PASS selected deterministic tests | Defined emergency phrases immediately direct to urgent help/112 without questionnaire or payment. This is not validated clinical triage or a guarantee of recognizing all emergencies. National112 reference: https://112.gov.in/about . |
| Video privacy/workflow | PASS server tests / NOT TESTED real media | Existing authenticated native WebRTC/signaling extended with patient consent, private waiting room, doctor admission, room end state, device selectors and existing mute/camera/end/retry handling. TURN credentials are short-lived server-generated values; no recording. Repeated readiness no longer recreates a negotiating/connected peer. The browser tools exposed one shared-session in-app browser, without two independent media-capable device sessions. Real two-browser/device audio/video and cross-network reconnection were NOT verified; no decorative-panel success claim. |
| UI/accessibility | PASS selected checks / NOT TESTED full audit | Actual templates reuse shared brand, fonts, sidebar, forms, cards and controlled scrolling.198 browser checks across22 role/page combinations at nine widths passed overflow/heading/duplicate-ID checks. Duplicate schedule/purchase IDs found during testing were fixed; assistant button is hidden on its own screen. No full WCAG/Lighthouse/performance/real-device certification. |
| Schema/privacy | PASS local |46 actual tables; metadata-only Admin schema explorer includes new tables. Original values in all31 earlier tables preserved, with expected registry additions. Original uploads and runtime files retained locally. No unrestricted SQL or clinical listing added. |
| Hosted services/production | BLOCKED / NOT TESTED | No production/Supabase/Vercel release or new provider resources created. Hosting/provider credentials, hospital policy and independent clinical/privacy/security validation remain prerequisites. |

## Changed files

[Full modified/added file inventory](verification/upgrade-changed-files.json). Main additions: care/scheduling.py, hospital_services.py, hospital_forms.py, hospital_views.py, test_hospital_upgrade.py, migrations0006–0009, nine integrated templates and tools/migrate_mysql.py plus hospital_http.py. Existing models/services/forms/views/product/auth tests, URLs/navigation, video/app JavaScript and product styling were extended in place.

## Database migrations and preservation

Applied to primary MySQL and the separate local PostgreSQL rehearsal:

- 0006: additive workflow tables and optional/defaulted fields for sessions/blocks, MRN, admissions/beds, catalogue/partial issues, procurement, drafts/orders, FAQs/support and video attendance.
- 0007: checks for issue/order quantity bounds and valid session/block intervals/limits.
- 0008: new MRNs for existing patient users; fill the new issued-quantity field for previously completed prescriptions. No duplicate patient identities or fabricated historical issue-event records created. Reverse is deliberately a no-op for this preservation step.
- 0009: optional cancellation reason, no-show/queue choices and waiting-list table.

All24 Django migrations are applied; no pending model change detected. Before applying, a private logical backup and31-table original-column hash snapshot were taken. After applying and before synthetic HTTP mutations, all original rows/columns matched the snapshot. Content-type/permission/migration registries appended expected entries. Current MySQL remains mednova_local at127.0.0.1:3307 with DML-only mednova_local_app. The isolated PostgreSQL rehearsal remains on54329/private mednova; backend-only RLS was reapplied to all46 tables for restricted mednova_pg_runtime. It is not hosted Supabase and is not patient-level SQL isolation if the backend secret is compromised.

Metadata: [UPGRADE_SCHEMA_INVENTORY.md](UPGRADE_SCHEMA_INVENTORY.md), [MySQL JSON](verification/upgrade-mysql-schema.json), [PostgreSQL JSON](verification/upgrade-postgres-schema.json). Preservation evidence: [upgrade-data-preservation.json](verification/upgrade-data-preservation.json). Backups contain private information and remain in ignored .runtime/backups, outside deliverable archives. MySQL DDL is not generally transactional: recovery must use a rehearsed backup restored to a separate target, never an automatic destructive rollback of the user's live schema.

## Executed verification

- Baseline124 MySQL tests passed before modifications.
- Final full suite:141 SQLite tests;149 MySQL tests;149 PostgreSQL tests. The SQL suites include eight actual concurrency scenarios (same-slot booking, cancel/reschedule, whole dispensing, daily queue tokens, partial issues, duplicate GRN, competing bed allocation and daily booking cap). These counts overlap across engines, not separate unique tests.
- 21 focused upgrade tests passed, covering schedules/buffers/blocks/modes/caps/urgent rules, partial issues, safety, receipts, beds/discharge authority, MRN privacy, drafts/results, assistant ownership/emergency/booking, consent/admission/expiry, duplicate registration, waiting list/no-show shared reorder thresholds and unique form IDs.
- 71 routes ×6 identities =426 route/permission probes per full suite. Synthetic-role browser logins verified all five dashboards.
- Eight original real HTTP scenarios passed on each SQL-backed app. Six new real HTTP scenarios passed on each, covering persisted MRN, schedule→assistant booking, clinical denial, admissions, approved purchases/GRN/quarantine, waiting-list cancellation and metadata/emergency guidance. These are actual loopback requests, not mocked payments or external services.
- 198 current browser geometry checks: Doctor5, Reception5, Pharmacist4, Admin4, Patient4 pages, each at320/375/390/430/768/1024/1280/1440/1600px. No page overflow or duplicate IDs in the recorded final checks; browser error log empty. Media/device use, full screen-reader flows and every form at every width were not tested.
- System checks, migration consistency, collectstatic, JavaScript syntax and Git whitespace checks passed. Source/model-specific testing does not establish production performance or legal/clinical safety.

Logs are in verification/upgrade-*.txt; matrices and responsive evidence are adjacent JSON. Actual private orchestration commands executed: `.venv/Scripts/python.exe .runtime/run_upgrade_checks.py sqlite`, `mysql`, `postgres`; these invoke `manage.py test care` plus the appropriate explicit SQL acceptance class and obtain credentials from ignored local operator files. The private orchestration is excluded from source packages. Reproducible commands are below.

## Windows setup, migration and start

Prepared laptop, existing data (migrations already applied):

```powershell
Set-Location 'C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Python-MySQL'
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-MedNova.ps1
```

For a clean extracted source folder, first install Python3.12 x64 and MySQL, then run `Setup-MedNova.ps1` for pinned dependencies. Use `-ConfigureNewDatabase` only for a NEW empty database; it prompts securely, applies migrations and writes ignored local configuration. To connect an existing installation, securely configure .env from .env.example using the correct runtime identity; do not reinitialize it. Admin provisioning remains `Admin-MedNova.ps1 -Email 'jayesh@gmail.com'` with hidden password input; no password is included in source/archive. Original human Admin account was retained without credential changes.

For later pending migrations on an existing local MySQL database:

```powershell
.\.venv\Scripts\python.exe tools/local_mysql.py migrate --plan
.\.venv\Scripts\python.exe tools/migrate_mysql.py --apply
```

The new migration helper reads the selected existing local config, prompts for an authorized migration identity/password, requires mysqldump, takes a private backup, shows the plan and applies migrations. It never creates/resets/drops a database or changes runtime grants. The prepared-laptop execution used `--operator-config .runtime/mysql-test.json`, an existing private operator file; do not distribute it. External production migrations require the controlled deployment/backup runner, not this loopback helper.

Basic source regression:

```powershell
.\.venv\Scripts\python.exe manage.py test care --noinput
```

For real MySQL concurrency tests, use a separate terminal with an authorized local test operator (CREATE/DROP disposable test schema permissions), never the primary runtime identity:

```powershell
$env:APP_ENV='local'
$env:DATABASE_VENDOR='mysql'
$env:MEDNOVA_TEST_MYSQL='1'
$env:MYSQL_HOST='127.0.0.1'
$env:MYSQL_PORT='3307'
$env:MYSQL_DATABASE='mednova_qa'
$env:MYSQL_USER=Read-Host 'Local test operator username'
$testSecret=Read-Host 'Local test operator password' -AsSecureString
$env:MYSQL_PASSWORD=[System.Net.NetworkCredential]::new('', $testSecret).Password
.\.venv\Scripts\python.exe manage.py test care care.mysql_acceptance.MySQLBookingAcceptance --noinput
```

Django uses a separate test_mednova_qa database. Close this dedicated test terminal afterward; do not start the app from it. The separate PostgreSQL equivalent uses MEDNOVA_TEST_POSTGRES=1, DATABASE_VENDOR=postgresql, PGHOST=127.0.0.1, PGPORT=54329, PGDATABASE=mednova_pg_qa, PGSCHEMA=public, PGSSLMODE=disable and a privately entered local test-owner credential, then `manage.py test care care.postgres_acceptance.PostgreSQLBookingAcceptance --noinput`. These flags are for isolated loopback test databases, not hosted connections.

Real HTTP checks, only when the explicitly synthetic local fixture accounts already exist:

```powershell
.\.venv\Scripts\python.exe tools/local_mysql.py http_acceptance
.\.venv\Scripts\python.exe tools/local_mysql.py hospital_http
```

These create clearly labelled synthetic records in the designated LOCAL test workspace. They refuse unapproved remote targets and are not production acceptance tools. Fixtures/passwords are test-only; there is no default real administrator password. The PostgreSQL helper accepts the same commands for its separate rehearsal.

## How to review the new workflows

Doctor: My profile sets daily cap/location → Weekly schedule & leave adds morning/evening rules → Publish dates → review Availability. Book via a Patient/Reception screen or Hospital assistant. Doctor confirms. Use a current/past confirmed care episode for private draft, explicit finalization, prescriptions, orders/results and acknowledgment; other doctors/reception cannot read it.

Reception: Patients → Registration card shows stable MRN; duplicate-phone review never merges records. Book shared slots, check in today's confirmed in-person visits and progress the queue. A responsible doctor requests an admission; allocate/transfer a free bed; desk discharge remains unavailable until that doctor marks readiness.

Pharmacist: Inventory → catalogue/batch/safety; Prescriptions → partial issue with verification and quantity; supplier purchase → Admin approval → verified GRN. Stock movement and issue events persist with actor/time. Do not treat the synthetic QA items as medicines or use this unvalidated system for real dispensing.

Patient: Hospital assistant searches real published slots and requires explicit booking confirmation/consent. Own visits link to existing cancellation/rescheduling, report/prescription/payment screens. Waiting list sends saved availability notifications without reserving a slot. Anonymous chat never discloses private visits.

Admin: Data management/schema → actual metadata; Bed catalogue → verified ward resources; Suppliers/purchases → approve requests; Assistant knowledge → approve/unpublish FAQ and resolve topic-only support requests. No unrestricted SQL or clinical CRUD is available.

Video: Configure TURN_URL/TURN_SECRET on a real secure coturn relay and HTTPS for non-localhost access. Assigned patient consents → doctor admits → both start in separate browser profiles/devices → permit devices → verify actual audio/video, mute/camera, device switching after end, network interruption, retry and room closure. Real two-device media has not been verified here; do not present the panels/signaling tests as a successful call.

## External setup and incomplete work

Remaining code (not merely missing credentials): full structured EMR/allergy/vitals lists, complete IPD/ward/perioperative/discharge/handover, department delay broadcasts, advanced reception identity/dependants/emergency/visitor/ambulance/complaint desks, TPA/cashier/refund approvals, native PDF/XLSX reports, pharmacy ward stores/transfers/returns/controlled and cold-chain workflows, pharmacy billing/taxes/reconciliation, supplier credits/analytics, validated medication-safety knowledge, full translations and optional generative assistant adapter.

External/provider verification: SMTP (existing outbox must be processed), Razorpay/webhook credentials, TURN/HTTPS/two actual media-capable devices, private report storage/antivirus, barcode/label hardware and any lab/radiology interfaces. Hospital clinical leadership must validate prescribing/dispensing/triage policies; privacy, telemedicine and applicable Indian legal/security requirements need qualified review before any real-hospital use. No regulatory compliance certification is claimed.

Screenshots: [schedule desktop](design/screenshots/upgrade-schedule-desktop.jpg), [purchasing desktop](design/screenshots/upgrade-purchasing-desktop.jpg), [assistant mobile](design/screenshots/upgrade-assistant-mobile.jpg). Source archives intentionally omit databases/dumps/uploads, credentials, .env, .runtime, .venv, caches and Git internals. Original history/data remain in the original folder.

## Source deliverable

Verified clean ZIP: `C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Hospital-Upgrade-2026-10-23.zip`. Extracted folder: `C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Hospital-Upgrade-2026-10-23`. The adjacent `.verification.json` records CRC, SHA256, file-count, byte-comparison and extracted-source test evidence. Open MedNova.code-workspace in that folder. On this prepared laptop, continue using the ORIGINAL folder to retain its private database configuration. The ZIP is a source delivery requiring private setup on a new machine.
