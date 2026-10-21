# Product expansion and verification - 21 October 2026

Local application: http://127.0.0.1:8000/ . Production release: NOT READY.

The existing Django/MySQL application was preserved. No earlier React source was found; the additions are documented Django replacements based on the supplied specification. The original login-only route and same-origin form failure were repaired in the previous checkpoint (see LOGIN_PREVIEW_DIAGNOSIS.md). Checkpoint before this expansion: 4ff6d5d. No real patient records or production credentials were used.

## Feature matrix

| Feature | Implementation and executed evidence | Remaining limits |
|---|---|---|
| Public home, departments, doctor directory/profile, contact, legal, login/recovery | Existing repaired pages plus new About, Health Hub, Symptom Information and Pharmacy pages. All 57 routes exercised in role matrix. | Verified hospital identity/content still required. |
| Five roles and staff approval | Existing backend role/object checks retained. Expanded route matrix: anonymous plus five roles, 342 GET requests; targeted mutation/clinical permissions also tested. | Route matrix is route/method coverage, not exhaustive coverage of every input and object combination. |
| Appointments, 12-minute slots, rescheduling/cancellation | Existing transactional services retained. Actual MySQL competing booking and cancellation/reschedule races passed. | Managed MySQL TLS, capacity and staging remain unverified. |
| Wellness tracking | Server formula, bounds, per-patient/date uniqueness, persistent corrections and retained snapshots. Browser saved 100, corrected to 70; both versions and score survived restart. | Demonstration lifestyle score, not a clinical instrument. |
| Wellness trends | Rolling 7/30-day averages and preceding comparable periods, recorded days only; paginated daily history. Boundary, owner-isolation, previous-period and pagination-context tests executed. | No claim of disease prediction or validated health benefit. |
| Health Hub questionnaire | Five actual answers, timestamp, private assessment history and transparent educational rules. Browser saved poor/low/little/rarely/stress8 and displayed matching five reflections. | Not an examination or lab test; professional content review required. |
| Symptom information | Validated selections/duration/severity, ephemeral response, no symptom-history storage, warning signs override routine booking. Browser chest-pain selection displayed emergency guidance without routine booking recommendation. | Rule-based, not AI; incomplete emergency coverage; qualified clinical review required before real-world release. |
| Patient profile | Optional DOB, future-date validation, private account profile; existing name/phone editing retained. | No unnecessary demographic collection introduced. |
| Clinical notes | Assigned doctor only, after consultation starts, confirmed/completed only. Finalized append-only versions, required correction reason, optimistic version check plus appointment row lock. Browser finalized versions1/2 and retained original content. | App-level history is not a cryptographic electronic signature or tamper-proof database ledger. |
| Medical timeline | Patient's own recorded visits, prescriptions, report links and note versions. Doctor limited to their own assigned care episodes. Browser verified actual saved events after restart. | No hospital-wide doctor access, fabricated diagnoses, allergy negatives or inferred findings. |
| Reception queue | Check-in issues daily unique token, timestamps and constrained waiting/called/completed/cancelled transitions. One entry per appointment. Cancellation closes active queue entry. Browser issued token1 and advanced to Called. MySQL concurrent token test passed. | Queue completion is operational; it does not finalize clinical consultation. |
| Pharmacy | Existing catalog/batches/expiry/stock/pricing/dispensing retained; opening/adjustment/dispensing movements now record actor, quantity, balance, batch and RX reference. Low stock <=10, expired and next30-day expiry totals. MySQL simultaneous dispensing deducted once. | Historical movements before introduction are not reconstructed. Ordering/delivery/comparison not implemented or advertised. |
| Reports | Existing authenticated private upload/download and access audits retained. File and storage-failure tests passed on MySQL and SQLite. | Real S3 bucket, antivirus service, restore and deployed upload limits still need verification. Vercel form cap3MiB; local5MiB. |
| Notifications | Persistent inbox; registration, approval, appointment, prescription and payment events. Deduplicated upcoming reminders, durable email outbox, bounded processing, row claims/leases/retries and delivery status. Locmem success, failure and missing-config cases tested. | Real SMTP not configured; local processor accepted0 messages and marked unavailable. SMS provider/adapter is not implemented. SMTP retry is at-least-once and can duplicate after crash following acceptance. |
| Payments/video/recovery | Existing offline receipt/provider-verification/WebRTC/recovery code and regressions retained; earlier browser offline receipt verified. | Razorpay sandbox, SMTP inbox recovery and two-device TURN media test unverified without services. No automatic refund transfer. |
| Hospital settings | Optional opening-hours field added; displayed on About/Pharmacy/Contact. | Actual hospital details must be supplied and verified by operator. |
| Languages | Existing EN/MR/HI system plus translations for core new navigation, actions and common labels. Automated language-switch/render tests passed. | New long-form guidance, form choices and some operational text remain English; professional translation review required. |
| Vercel | Existing Django entrypoint, static collection, external MySQL/private S3 fail-closed config and authenticated cron retained. | Account returned403 on project creation. No deployment, managed DB/storage credentials or Linux driver build verification. |

## Executed tests and artifacts

- `APP_ENV=local python manage.py test care --verbosity 1`: 104 tests passed on SQLite, 33.154s, zero skipped/failures. `verification/product-sqlite-tests.txt`.
- `APP_ENV=local MEDNOVA_TESTING=1 MEDNOVA_TEST_MYSQL=1 python manage.py test care care.mysql_acceptance.MySQLBookingAcceptance --noinput --verbosity 1`: 108 tests passed on actual MySQL8.4.13, 48.928s, zero skipped/failures. `verification/product-mysql-tests.txt`.
- Four real MySQL race cases: same-slot booking, cancellation/reschedule, duplicate dispensing, daily token allocation. `verification/mysql-targeted-1.txt` also records the individual names.
- `verification/product-route-inventory.json`: complete route, view, source-file and line inventory.
- `verification/product-role-route-matrix.json`: 57 routes x anonymous/five roles =342 requests, forbidden-role and anonymous checks plus no500 assertions. POST mutation tests are separately covered in the suites.
- Fresh schema created by test runner; separate existing MySQL schema migrated from care0002 to care0004 with a historical hospital sentinel preserved. `verification/product-mysql-upgrade.txt`.
- Existing local synthetic SQLite migrated additively to care0004; no DB reset.
- Following history-pagination/trend refinements, focused wellness/questionnaire tests passed; `verification/product-trends-tests.txt`. Final follow-up checks are recorded beside this report.
- `manage.py check`, `makemigrations --check --dry-run`, `collectstatic --noinput`, Python compile, `pip check`, and `git diff --check` executed.
- The eight live HTTP scenarios passed again against the final running Waitress application; `verification/product-http.txt`.
- Earlier verified core flow evidence remains in REPAIR_AND_VERCEL_REPORT.md and repair-http.txt; it is historical evidence, not a new provider acceptance run.

MySQL setup: official portable8.4.13 Windows archive, MD5 matched vendor7b94489d5524dea9b27097068bea25a8. Isolated loopback3307, random password stored only in ignored .runtime, dedicated synthetic databases, no Windows service. This is not managed production connectivity or production TLS verification. The local test instance may be stopped after verification; files remain private/ignored for recovery.

A real MySQL run exposed two test-harness assumptions: a named-time-zone DATE lookup without imported MySQL timezone tables (replaced by equivalent aware day bounds), and closing a streaming response without consuming it inside Django TestCase (now consumes and checks the JPEG bytes). No failed business assertion was removed.

## Browser evidence

Executed through the Codex in-app browser against Waitress and the isolated synthetic database:

1. Patient login redirected to protected wellness path.
2. Save8h sleep/8glasses/5active days/stress0 ->100.
3. Correct same date to stress10 ->70, retain both snapshots.
4. Questionnaire saves actual selected answers and corresponding educational reflections.
5. Chest pain with mild severity -> emergency result, no routine booking CTA in result.
6. Previously approved synthetic doctor opens assigned completed appointment; finalizes synthetic note version1.
7. Doctor correction saves version2 with reason; original version1 remains visible.
8. Reception signs in, opens a prepared synthetic confirmed in-person appointment, checks in -> persistent token1.
9. Reception updates Waiting -> Called and sees timestamp/status. This appointment was prepared with the backend service for this queue test; this step is not claimed as a new browser booking test.
10. Application restarted; fresh patient session still sees score70 and both snapshots.
11. Patient timeline lists actual existing prescription/report and two clinical-note versions.
12. Narrow-layout queue screenshot inspected. New About page verified at390px with documentWidth=viewport=390; Marathi navigation switch preserved the path.
13. Pharmacist adjusted the synthetic item8->9->8 with reasons; movement history displayed both records, timestamps, actor and resulting balances.
14. Browser error/warning console was empty at final check. Viewport override reset and public homepage left open.

Browser state snapshots/screenshots were inspected in the tool output. No screenshot file is claimed where none was saved. Full deployed25-step acceptance and external service cases remain unverified.

## Migration, startup and operational instructions

New additive migrations: care0003 (wellness, revisions, questionnaire, clinical notes, queue, stock movements, DOB, opening hours) and care0004 (optional notification appointment and delivery outbox). Back up first; rehearse on a clone; run `python manage.py migrate --plan` then `python manage.py migrate --noinput`. Existing clinical data is not backfilled with fabricated notes or movements. Existing checked-in appointments can receive a token on a repeat valid check-in; completed historical visits are not retroactively queued.

Windows local synthetic preview (existing browser DB only):

```powershell
Set-Location C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Python-MySQL
$env:APP_ENV='local'
$env:MEDNOVA_TESTING='1'
$env:MEDNOVA_TEST_DB='browser_acceptance.sqlite3'
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:8000 mednova.wsgi:application
```

This is a labelled synthetic preview. Production must not set MEDNOVA_TESTING or use this database. Local TESTING uses a random process secret, so server restart invalidates sessions; production requires a stable strong secret. See DATABASE_SETUP.md for real MySQL setup and VERCEL_DEPLOYMENT.md for production variables, private storage, launch checks and backups.

Notification processing: `python manage.py process_notifications`. Existing authenticated `/api/maintenance/cleanup/` calls bounded cleanup plus reminder/outbox processing. With current daily cron, reminders are best effort and can be late/missed near a scheduling boundary. Production reminders require an approved sufficiently frequent scheduler, actual cron execution monitoring and provider acceptance testing. Do not advertise guaranteed or SMS delivery. Outbox emails contain a generic account notice and no appointment reason, notes or medicines.

## Release blockers, security, backup and rollback

- Vercel account/project authorization (actual403), managed MySQL/TLS credentials and private durable storage configuration are absent. No production URL exists.
- Linux mysqlclient native build, real storage access, encrypted backups/restore and deployed synthetic acceptance must pass.
- SMTP, TURN, payment sandbox and approved PDF malware-scanner configuration are missing/unverified. SMS integration is not implemented.
- Qualified clinical safety review, hospital identity/contacts/clinician verification, legal/privacy/retention decisions, professional translations and complete accessibility review remain gates. The symptom tool prominently discloses pending review.
- App-level append-only note/score histories do not protect against a privileged DB operator. Restrict DB access, audit infrastructure changes and retain encrypted backups.
- Use least-privilege runtime MySQL credentials; the isolated root test account is not a production example.
- Take consistent MySQL and private-object backups, enable approved object versioning, test restore into a new isolated environment and reconcile writes before any recovery. Never restore over live data without explicit authorization.
- Prefer code rollback compatible with additive schema. Do not unapply0003/0004 after real use: that drops newly recorded information. Keep database migrations and object backups separate from Git source checkpoints.

Official medical source pages used for the limited emergency rules: https://www.nhs.uk/conditions/heart-attack/ , https://www.nhs.uk/symptoms/shortness-of-breath/ , https://www.nhs.uk/conditions/stroke/symptoms/ , https://www.londonambulance.nhs.uk/our-services/emergency-care/calling-999/ . Source UK numbers are not substituted for verified local emergency contacts.

Official MySQL package listing: https://dev.mysql.com/downloads/mysql/8.4.html?os=3 . Vercel sources and exact environment checklist remain in VERCEL_DEPLOYMENT.md.
