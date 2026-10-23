# MedNova patient assistant — implementation and verification

23 October 2026. Existing project: `MedNova-Python-MySQL`. Main application: http://127.0.0.1:8000/assistant/ . Patient/staff cases: http://127.0.0.1:8000/support/ .

## Root causes addressed

The first assistant searched whole questions literally and required a topic dropdown. The subsequent conversational version improved doctor search but still returned the same appointment summary for reports, prescriptions and billing. Its topic-only escalation could not carry an issue summary, route staff access, provide a case reference, receive a reply or track status. There was no patient-reviewed sharing workflow.

The assistant now recognizes supported service intents locally and calls the existing hospital models and services. Responses contain actual authorized data. It does not depend on an external generative model or fabricate missing facts.

## Supported patient journey

Patients can search approved doctors by specialty/name, ask for tomorrow morning, a weekday, an ISO date, video/in-person mode or times after 5 pm, and follow up about the same doctor. Doctor cards distinguish registration from available slots. Actual schedules, leave/breaks, duration, buffer, capacity and occupied intervals are checked through the shared availability service. A selected time opens the existing booking form preselected; the patient supplies visit details and consent and explicitly submits the real booking service. Rescheduling and cancellation likewise finish on existing secure confirmation screens. Chat never reports a successful mutation before that backend completes.

Private service responses now show their own actual data:

- Appointments: doctor, department, time, status, stored room/location, recorded cancellation reason and links to permitted actions. Upcoming visits can be requested. No unsupported attribution of who cancelled a visit is inferred.
- Reports: uploaded-file metadata and secure download links; investigations show their recorded Ordered, Resulted or Acknowledged status. File upload and investigation result are not treated as equivalent. No completion ETA or diagnosis is invented.
- Prescriptions: clinician-recorded instructions, recorded dose/route/frequency/duration, dispensing progress and links to the prescription. No new prescription, dose change or treatment recommendation is generated.
- Billing: actual consultation payment states, recorded outstanding non-cancelled consultation charges and receipts. Online payment is linked only when the existing payment integration is configured. Refunds and insurance approvals are never simulated.
- Queue: the patient's own token/status today; no invented wait-time estimate.
- Admissions: recorded admission/bed status. Published preparation and hospital policies come from approved FAQs/settings. Missing instructions are explicitly unavailable.
- Support: actual saved cases, status, portal conversation and replies.

Compound requests such as “my prescription and outstanding bill” retrieve the relevant tools separately. Short service follow-ups such as “it has been pending for four days” retain the report context. Ambiguous times without AM/PM prompt clarification. Unsupported questions offer a useful next step rather than a generic welcome response.

See [the intent catalogue](PATIENT_ASSISTANT_INTENTS.md) for tools, permissions, error outcomes and escalation conditions.

## Persistent human handoff

1. For unresolved download/booking/billing problems, safety/privacy concerns or explicit human requests, the assistant prepares a draft. It labels the original issue as the patient's report, with a message timestamp and verified appointment reference only when unambiguous.
2. A human-support follow-up retains the preceding unresolved issue. Credential/payment-secret phrases are omitted from the prepared summary.
3. The patient opens **Review summary and create support case**, edits the category/summary/appointment and explicitly consents to sharing with the selected hospital team.
4. Only the successful POST creates a persistent UUID case and returns its reference. A unique request key plus an identity row lock prevents simultaneous retry submissions from creating duplicate cases.
5. Assigned clinicians handle clinical/report cases. Pharmacy staff handle pharmacy cases. Reception/admin handle appointment, billing and technical cases. Privacy cases are restricted to administrators.
6. Clinical/report cases with an eligible linked doctor are assigned to that doctor. Otherwise they await administrator routing. Administrators can view medical/pharmacy routing metadata and assign eligible staff, but cannot read those summaries, messages or linked clinical reference through this dashboard.
7. Staff can reply in the authenticated portal, add internal notes, set priority/status and, for administrators, assign an eligible worker. Internal notes are hidden from patients. Patients receive portal notifications for staff replies and status changes; no email, SMS or external live-transfer claim is made.
8. Existing conversations cannot be routed into a weaker access group. Moving between operational, clinical, pharmacy and privacy access groups requires a new patient-consented case. This prevents staff reassignment from exposing the original conversation to a different audience.

Statuses: Open, Assigned, In Progress, Waiting for Patient, Escalated, Resolved, Closed. A patient reply to a waiting/resolved/closed case reopens it. The most recent 100 conversation entries are displayed, with the reviewed summary always visible. Support records are persistent; clearing chat does not delete saved cases.

This is a real hospital portal queue, **not live chat**. There is no promise that a staff member is currently online or has read a case. Staff must operate the queue. There is no separate laboratory role in the existing schema, so report support is routed to an assigned clinician rather than granting reception unrestricted medical access. Account identity is shared only after consent; phone/email details are not copied into the conversation or exposed unnecessarily.

## APIs, schema and safe migration

| Route | Operation |
|---|---|
| `GET /api/assistant/` | Greeting and limited public service history |
| `POST /api/assistant/` | JSON `{"message":"My reports"}`; structured text/cards/links/suggestions |
| `POST /api/assistant/` | JSON `{"action":"clear"}` clears context and draft |
| `GET /support/` | Authorized patient/team case queue and status filter |
| `GET/POST /support/new/` | Patient review and consent; idempotent persistent case creation |
| `GET/POST /support/<uuid>/` | Authorized conversation/replies/internal notes/routing/status |

Existing booking, appointment-action, report-download, prescription, billing, video, admission and notification routes remain the source of truth. No alternate booking or clinical-record store was created.

Migration `0010_patient_support_cases` adds only `care_supportcase` and `care_supportmessage`, with protected foreign keys, a unique submission key and a category/status index. The working MySQL database grew from **46 to 48 tables**. All original column definitions are unchanged; metadata orphan checks found **0** foreign-key orphans. The migration contains no reset/delete/data replacement operations.

The existing migration helper made a private backup before applying it. Backup SHA256: `f7866ae8932e13f1b70c0b17437cfb7c54db6cb34a1136a10ff2b74c81337f90`. The backup remains under ignored `.runtime/backups/`; it is not included in public artifacts. Runtime credentials were not changed. See `docs/verification/patient-assistant-mysql-migration.txt`, before/after schema snapshots and `patient-assistant-schema-preservation.json`.

## Authentication, privacy and reliability

- Existing Django login, session expiry, approved roles, CSRF and ownership checks are reused. Private queries always use `request.user`; browser-supplied patient IDs are not trusted.
- Patient-only tools reject staff accounts rather than granting broad patient-record searches. Each linked record endpoint enforces its existing authorization again.
- Support-case access is checked on reads and again under the case lock before writes. Administrator metadata access does not authorize reading a clinical conversation or replying into it.
- Case creation, messages, portal notifications and status changes use transactions. Audit entries contain action names/record references, not raw clinical conversation text.
- Chat accepts 1–500 characters, caps payload size and limits requests to 40/minute. Support creation and updates have separate limits. Structured API errors and a retryable support-unavailable page do not expose connection strings or stack traces.
- Queries prefetch related data, cap displayed results and restrict availability evaluation to the returned doctors. Time comparisons use the configured hospital timezone and aware day boundaries.
- Chat does not persist raw ordinary questions or private result cards. An unresolved issue/draft may temporarily remain in the private server session for up to 30 minutes for continuity. Clear removes that context and draft; login/logout and expiry isolate accounts. Expired session records should be cleaned through the existing session-maintenance process.
- Saved case summaries/messages remain hospital support records and require the hospital's retention/access policy. No new automatic deletion of existing data was introduced.
- Browser messages use `textContent`; Django templates escape case text. No external provider receives credentials, patient records or conversations.
- Emergency triggers take priority over routine tools and do not create tickets instead of urgent guidance. The published India emergency number is sourced from the [Ministry of Home Affairs ERSS description](https://www.mha.gov.in/en/commoncontent/emergency-response-support-system-erss). Chat explicitly says it has not contacted emergency services. These triggers are safeguards, not a validated clinical triage system.

## Files created or changed

New: `care/patient_assistant.py`, `care/support.py`, `care/migrations/0010_patient_support_cases.py`, `care/test_patient_assistant.py`, `templates/care/support_create.html`, `support_detail.html`, `support_queue.html`, `support_unavailable.html`, this report and the intent catalogue.

Updated: `care/chatbot.py`, `care/models.py`, `care/scheduling.py`, `care/product.py`, `care/mysql_acceptance.py`, `care/test_chatbot.py`, `care/test_product.py`, `mednova/urls.py`, `templates/care/chatbot.html`, `templates/care/components/navigation.html`.

The existing conversational UI uses `static/js/chatbot.js` and `static/css/chatbot.css`; existing assistant POST compatibility remains in `care/hospital_views.py` and `templates/care/assistant.html`.

## Tests actually executed

- Full isolated MySQL suite: **177 tests passed** (including existing booking/dispensing/bed/stock concurrency cases and the new concurrent support retry case). See `docs/verification/patient-assistant-mysql-tests.txt` and role matrix.
- Focused SQLite assistant tests: **27 passed**. Includes consent, draft continuity, wrong-patient record/case IDs, report/prescription/billing privacy, restricted clinical summaries, hidden internal notes, staff replies/status notifications, restricted reassignment, secret redaction, expired draft, CSRF, rate limit, database rollback/recovery, emergency priority, after-time clarification and sensitive routing.
- Live browser tests used a **separate synthetic SQLite database** on port 8003, not the working MySQL patient database. Verified patient login → actual report/investigation/prescription/billing answers → unresolved report issue → editable consent summary → saved assigned case → assigned doctor queue → doctor reply/status update → patient reads reply without internal notes.
- Twenty responsive checks: sixteen patient-page checks (assistant, case creation, queue and detail) plus four administrator case checks at 320/390/768/1280; no document overflow or duplicate IDs. The administrator browser check confirmed that the clinical summary and reply were hidden. Browser evidence: `docs/verification/patient-assistant-browser.json` and `patient-assistant-handoff.jpg`. Viewport was restored.
- Django system checks, migration drift check, JavaScript syntax check and `git diff --check` passed.
- No external AI dependency is configured; an AI-provider outage cannot disable these local tools. This is not a claim that a live provider was tested. Real payment/refund transactions, email/SMS delivery and real camera/audio sessions were not executed.

## Environment and local commands

No new environment variable or external service is required. The existing MySQL/Django private configuration is reused. Do not paste passwords or API keys into source.

In VS Code PowerShell, from the project folder:

```powershell
.\.venv\Scripts\python.exe tools\local_mysql.py serve
```

Open http://127.0.0.1:8000/assistant/ . This prepared working copy already has migration 0010 applied. A different configured installation must first back up and migrate using its authorized database operator:

```powershell
.\.venv\Scripts\python.exe tools\migrate_mysql.py --apply
.\.venv\Scripts\python.exe tools\local_mysql.py collectstatic --noinput
.\.venv\Scripts\python.exe tools\local_mysql.py check
```

The migration helper prompts for the authorized migration operator; web serving continues to use the existing restricted runtime account. Do not initialize/reset a new database to run this upgrade. The separate historical PostgreSQL rehearsal is not a Supabase deployment; migrate and apply its existing private-schema protections before using new support tables there.

For isolated focused tests (Django creates/disposes a test database, not patient data):

```powershell
.\.venv\Scripts\python.exe manage.py test care.test_patient_assistant care.test_chatbot --noinput
```

## Manual end-to-end verification

1. Open the assistant anonymously and ask “heart specialist tomorrow morning”. Results must reflect the installed records; an empty specialty must not create fictional doctors. Ask “My reports”; use the sign-in action.
2. Sign in with your own approved patient account. Ask “My appointments”, “My reports”, “Prescription help”, and “My prescription and outstanding bill”. Inspect only your actual records or truthful empty states.
3. Search a doctor, select a slot and review its preselected time in the existing booking form. Enter details/consent and submit once. Verify the actual appointment. Use the visit page to confirm rescheduling/cancellation under existing rules.
4. Ask “I cannot download my report”, then “I want to talk to a real person”. Review the prepared summary, select the relevant appointment if ambiguous and confirm sharing. Verify the returned case reference/status.
5. Sign in as the assigned doctor for clinical/report cases, pharmacy staff for pharmacy cases, or reception for operational cases. Open the support queue, read the permitted summary, add a portal reply and update status. An administrator must see only routing metadata for medical cases.
6. Return as the patient, open Support cases and Notifications, read the actual reply and respond. Internal staff notes must not appear. Clear chat and verify the saved case remains accessible.

## Remaining limits

The language layer is task-specific, not an unrestricted generative model. Unknown phrasing may require clarification. Subspecialties, preparation instructions, policies, laboratory completion estimates, insurance decisions and wait-time estimates are available only if existing records/approved content contain them. Booking and financial actions finish in the secure existing portal screens. Support is asynchronous and needs staff to work the queue. No live external transfer or external emergency dispatch exists. Existing sessions/retention operations remain the hospital operator's responsibility.
