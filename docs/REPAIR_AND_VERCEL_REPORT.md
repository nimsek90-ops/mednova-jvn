> Current product expansion: see PRODUCT_IMPLEMENTATION_REPORT.md. New additive migrations0003/0004; 108 MySQL tests and104 SQLite tests passed, including four real MySQL race tests. Older counts and statements below describe earlier checkpoints. Production deployment remains blocked.

# MedNova repair and functional verification — 21 October 2026

## Outcome

The existing Django project was repaired without a rewrite. Public pages and the main role-based workflows now work in the local browser with CSRF enabled and database persistence. The local app remains running at http://127.0.0.1:8000/ using a clearly labelled isolated synthetic database.

Vercel deployment is BLOCKED, not complete: the connected account's create-project request returned HTTP 403 forbidden. No existing projects were visible, no authenticated local CLI fallback was found, and no production MySQL/bucket credentials were supplied. No production database was contacted, seeded, reset or migrated.

## Root cause

care/middleware.py set Referrer-Policy: no-referrer, causing native browser form POSTs to send Origin: null and fail Django CSRF verification. Correcting it to same-origin made login and language forms work in the same browser. CSRF remains enabled; null/hostile origins are rejected by regression tests. The earlier conclusion that this was a browser limitation was incorrect and is superseded.

The root route also deliberately rendered the login view, and public navigation did not expose a complete hospital website. Added public home, departments and approved doctor profiles, while retaining authenticated workspaces. LOGIN_PREVIEW_DIAGNOSIS.md contains the prioritized defect table and evidence.

## Main files changed and purpose

| Files | Purpose |
|---|---|
| care/middleware.py | Correct form-compatible referrer policy without disabling CSRF |
| care/views.py, mednova/urls.py | Public pages, safe next redirects, page-preserving language change, receipts, private signed downloads, storage-outage error, authenticated maintenance endpoint |
| care/security.py | Preserve login destination and use branded permission errors |
| care/forms.py | Hosting-aware upload size validation/help |
| care/context.py | Explicit local synthetic-workspace label |
| mednova/settings.py, mednova/hosting.py | Remote MySQL TLS/connection lifecycle, private S3 configuration, exact hosts/origins, fail-closed Vercel validation |
| templates/care/home.html, public_departments.html, doctor_detail.html, receipt.html | Real ORM-backed public pages and authorized payment record |
| templates/care/base.html, login.html, appointment.html, doctors.html, error.html | Navigation, login destination, language path, receipt links, time-eligible clinical controls, useful errors and favicon |
| List templates | Remove duplicate pagination inclusions; keep shared base controls |
| static/css/app.css | Responsive public navigation/homepage styles preserving existing identity |
| .python-version, pyproject.toml, vercel.json, .vercelignore | Documented Python 3.14 / Django WSGI deployment configuration and exclusion rules |
| requirements.txt, requirements.lock.txt, .env.example, .gitignore | Pinned private-storage dependencies, placeholder setting names and artifact exclusions |
| care/tests.py, tools/http_acceptance.py | New regressions and stable fixture-specific HTTP doctor selection |
| docs/ | Diagnosis, final evidence, setup, deployment limitations and rollback guidance |

No new model schema change was needed in this repair. Existing migrations 0001 and 0002 remain unchanged. A local Git checkpoint was created before edits: 1196fba.

## Executed checks

| Check | Actual result |
|---|---|
| Final Django regression suite | 87 passed, 0 failed, 0 skipped; 5.318 seconds |
| Final real HTTP acceptance against Waitress | 8 scenarios passed, 0 failed |
| Django system checks | 0 issues |
| Production/Vercel check --deploy --fail-level WARNING | 0 issues using synthetic configuration only; no external DB/bucket contacted |
| Import/source compilation | Passed for care, mednova and tools |
| Route/template URL scan | 48 routes mapped; all literal template URL names resolved; 28 Python source files parsed |
| Migration consistency | No changes detected |
| Existing isolated database migration status | All 17 migration entries applied, including care 0001 and 0002 |
| Fresh database migrations | Executed by the isolated regression test runner |
| Static collection | Successful; 8 assets retained |
| pip check | No broken requirements found |
| git diff --check | Passed; line-ending notices only |
| Actual connected browser | Public and authenticated workflow below executed; desktop and 390×844 appointment layout inspected with no horizontal overflow |
| Browser console on final completed patient page | No captured error/warning entries |
| MySQL concurrency suite | Two explicit threaded tests exist; NOT RUN, no dedicated MySQL service/credentials |
| Actual Vercel project/deployment | Project creation failed HTTP 403; no deployment/build ran |

Raw results: docs/verification/repair-tests.txt, repair-http.txt and repair-route-map.json. A production settings check is not evidence of a real deployment, TLS connection or S3 operation.

Intermediate failures were investigated: the first sandbox run hit two existing upload-test temporary-directory permission errors; rerunning with required access resolved them. The first new S3 test mocked the shared filesystem URL method and also intercepted static URLs; its mock was narrowed to the Report file field. An HTTP rerun initially chose a newly added browser-test doctor instead of its own fixture; the harness now selects the intended Test Doctor identity. Final suites passed after these corrections. A standalone persistence diagnostic initially omitted its SQLite file setting and queried an empty in-memory DB; rerunning with the explicit isolated file passed. These were not hidden or counted as successful checks.

## Actual browser acceptance

The following were performed through forms/navigation, not inferred from page status codes. Data is synthetic, using reserved example.test emails and clearly labelled non-clinical records.

1. Administrator created Synthetic Browser QA department and saved labelled test hospital settings. Real legal/address/contact fields remained unconfigured.
2. A new synthetic doctor registered, submitted professional details and saw Account awaiting review; privileged doctor navigation was unavailable while pending.
3. Administrator approved that exact test account after the user explicitly authorized it. Automatic approval review initially blocked this access change; the action was not bypassed.
4. The doctor logged in and created three future in-person slots through availability management; all appeared in the schedule.
5. A new patient registered, opened the doctor directory and booked an actual available slot.
6. The assigned doctor opened the saved appointment from the dashboard and confirmed it. The patient logged in again and saw Confirmed.
7. The patient updated their profile. A different patient attempted the private appointment URL and received the branded 404 without the clinical record.
8. The second patient booked a different slot, rescheduled it to a third slot and cancelled it. The saved appointment showed the new time and then Cancelled. Server duplicate rejection was also exercised by the eight-scenario HTTP suite; concurrent MySQL contention remains UNVERIFIED.
9. Receptionist checked in the confirmed visit and saved a clearly synthetic cash receipt reference. Its page omitted clinical notes. The receptionist was denied administrator user management.
10. After the actual appointment start time, the assigned doctor issued a synthetic prescription and completed the consultation. No time-validation bypass or database timestamp adjustment was used.
11. Pharmacist saw the dispensing queue without the private instruction note, dispensed two synthetic item units and saw Dispensed. Inventory changed from 10 to 8.
12. The patient logged in again, saw Completed and the saved prescription, uploaded a synthetic PNG report and downloaded the authorized re-encoded JPEG. The downloaded image was checked as JPEG, 480×100.
13. The patient saw the saved Paid receipt/reference. Hindi and English language POSTs kept the current receipt page.
14. Waitress was stopped and restarted. After a fresh login, the browser returned to the receipt and displayed the completed appointment, prescription and uploaded report. An independent ORM check confirmed the saved profile, paid status, dispensed prescription, report count and stock of 8.

Public home/navigation and the patient appointment were inspected at desktop/mobile sizes. This is local browser evidence. Full browser coverage of every edge case, independent accessibility/language review and the entire deployed staging workflow remain UNVERIFIED. SMTP, real video, payment capture, antivirus and actual cloud-object operations were not simulated as working integrations.

## Remaining actions and release gates

1. Account owner: grant Vercel project-creation/deployment permission to the connected integration or provide an accessible existing project in the intended team. The observed error was an account/API permission denial, not an application build failure.
2. Configure separate Preview/Production remote MySQL, verified CA/TLS, restricted credentials and private object storage. Enter secrets directly in Vercel/approved secret management. The full variable-name checklist and exact deployment commands are in VERCEL_DEPLOYMENT.md.
3. Verify the actual Vercel Linux build, including mysqlclient native libraries, then execute MySQL migrations/concurrency tests on isolated staging infrastructure. Do not treat SQLite locking results as MySQL proof.
4. Verify real S3 writes/private downloads, encryption, public-access blocking and restore. Review the explicit 3 MiB Vercel form-upload cap versus 5 MiB local uploads. Full 5 MiB Vercel direct-to-quarantine upload/finalization is not implemented.
5. Configure and verify SMTP, TURN, optional Razorpay sandbox and a cloud-compatible antivirus scanner before enabling their corresponding features. A laptop clamscan path is not a cloud scanner. No automatic refund transfer is implemented.
6. Supply verified hospital identity/contact information later, as requested. Approve actual clinician/staff credentials before real patient access. No credentials or legal identity were invented.
7. Complete deployed staging acceptance, protected storage/backup restoration, monitoring, cron frequency/retention review, language/accessibility review and production sign-off.

Backups and rollback: DATABASE_SETUP.md documents consistent MySQL/private-file backups and isolated restore verification. VERCEL_DEPLOYMENT.md documents compatible code rollback and explains that Vercel rollback does not restore data. Never reverse/drop clinical tables, overwrite a live database or delete reports without explicit approval and a verified backup.

Status: local repair and main browser journeys VERIFIED; production MySQL, provider integrations and Vercel deployment UNVERIFIED/BLOCKED. The application is not declared production-ready.
