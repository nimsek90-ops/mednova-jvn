# MedNova website audit — 24 October 2026

**Final score: 81/100. Overall status: Not Ready for Deployment.**

The main local workflows pass after repairs. The production launch gate fails because required hospital/domain, email and TURN configuration is missing. No production data, existing accounts or clinical records were overwritten. All test mutations used the separate `mednova_audit_20261024` MySQL schema or disposable test databases. The working `mednova_local` database received read-only HTTP and metadata checks. The primary site remains running on port 8000; the isolated audit server is stopped.

## Weighted score

| Category | Earned / weight | Evidence and deductions |
| --- | ---: | --- |
| Core functionality and user workflows | 23 / 25 | Five-role browser login, real registration/profile/logout/booking, reception, prescribing/dispensing, purchasing, admissions and reviews. Not every possible form/input combination was exercised. |
| Backend, APIs and database | 18 / 20 | Real MySQL CRUD and readback, 53 tables, zero orphan rows, concurrency acceptance and malformed API input checks. Optional PostgreSQL/remote production database not exercised in this audit. |
| Authentication and security | 18 / 20 | Six-role route matrix, object ownership, CSRF, active throttling, protected files/config URLs, security headers and dependency remediation. Not an exhaustive independent penetration test. |
| UI/UX and responsiveness | 8 / 10 | 239 rendered links/assets pass; desktop and 375px mobile checks; no captured browser console errors. Partial translation coverage and incomplete cross-browser/accessibility coverage remain. |
| Appointment, payment and video workflows | 7 / 10 | Actual booking/cancellation, both payment choices, screenshot/rejection/resubmission, staff confirmation, consent/admission and synthetic signalling. Real gateway transactions, email and cross-device media are blocked. |
| Error handling and reliability | 4 / 5 | Four reproduced storage failures repaired and retested with retryable responses. Load, recovery and prolonged provider-failure behavior not established. |
| Build and deployment readiness | 3 / 10 | Production Django security checks, static collection and WSGI import pass. Launch gate fails; remote services and a hosted artifact/deployment remain unverified. |
| **Total** | **81 / 100** | |

This is an evidence-weighted readiness assessment, not a code-coverage percentage. Points reflect demonstrated paths and deductions for blocked or unsampled boundaries; untested services receive no full-functionality credit. A high local functionality score does not override the failed deployment gate.

## Test totals and evidence

| Check set | Result |
| --- | --- |
| Final automated MySQL suite | **225 passed, 0 failed**; includes seven new audit regressions |
| Role matrix, inside the automated suite | 88 routes × six roles = **528 requests**; no server errors, expected access restrictions |
| Live end-to-end HTTP scenario groups | **22 passed**: eight core, six hospital, four payment, three clinical/review/security groups and one signalling exchange; repeated standalone login checks excluded from this count |
| Rendered UI links and assets | **239 checked, 0 broken/forbidden** after fixes |
| Browser | All five authenticated roles signed in; no captured JavaScript errors; desktop and 375px mobile inspected without horizontal overflow |
| Main-site read-only smoke/security checks | Nine passed, including denied private/config paths |
| Source checks | 82 Python syntax checks and five JavaScript syntax checks passed; `git diff --check` passed |
| Dependency checks | `pip check` passes; OSV queried 26 installed distributions, **zero advisory matches after repair** |
| Production build/preflight | Static collection, WSGI import and `check --deploy --fail-level WARNING` pass; **`launch_check` fails** on missing required configuration |
| Blocked external-service groups | **6**, itemized below |
| Additional audit scopes not tested | **4**, itemized below |

These sets overlap and are not summed into one inflated test count. The route-matrix requests are assertions within the 225 tests. The dependency scan is a registry-advisory check, not a guarantee that every dependency or native component is vulnerability-free. A focused secret-pattern scan of nonignored source found no matches; ignored private credentials were not published or included in it.

Evidence files use the `verification/audit-20261024-*` prefix. Key records: [final suite](verification/audit-20261024-mysql-tests.txt), [role matrix](verification/audit-20261024-mysql-role-matrix.json), [core HTTP](verification/audit-20261024-core-http.txt), [hospital HTTP](verification/audit-20261024-hospital-http.txt), [payments](verification/audit-20261024-payment-http.json), [clinical/reviews](verification/audit-20261024-clinical-reviews-http.json), [signalling/localization](verification/audit-20261024-signalling-locale.json), [database readback](verification/audit-20261024-database-readback.json), [schema](verification/audit-20261024-schema.json), [crawl](verification/audit-20261024-link-crawl.json), [browser](verification/audit-20261024-browser.json), [build](verification/audit-20261024-build.json), [primary smoke](verification/audit-20261024-primary-http.json).

## Issues found and repaired

| Priority | Finding | Fix and retest |
| --- | --- | --- |
| High | Pillow 12.3.0 matched 39 advisory records in one dependency. Its default image detection includes affected unsupported decoders before the previous post-open format check. | Pinned and installed Pillow 13.0.0 in both requirement files; restricted report/payment `Image.open` to PNG/JPEG before detection. Final full suite and package consistency pass; advisory scan falls to zero matches. No denial-of-service exploit was executed against the running service. |
| Medium | Payment upload, payment screenshot read, report read and signed-report URL failures produced unhandled 500 responses. Four new tests reproduced them. | Added safe storage-outage responses with HTTP 503/Retry-After and no provider details; failed payment uploads remain unconfirmed. Cleanup failure no longer masks the original storage error. Four previously failing checks now pass; authorization remains before file access. |
| Medium | Seven staff-facing directory links led to 403: booking links offered to non-booking roles, and pharmacist “My appointments”. | Directory/profile actions now follow existing role permissions. No backend permissions expanded. Two regressions failed before repair and pass afterward; expanded crawl passes all 239 links/assets. |

Maintainer evidence for the dependency change: [Pillow image-detection advisory](https://github.com/python-pillow/Pillow/security/advisories/GHSA-xgh8-jp6q-p5x8) and [Pillow 13.0.0 release](https://github.com/python-pillow/Pillow/releases/tag/13.0.0). Before/after advisory outputs, storage regressions, navigation regressions and the initial failed crawl are retained beside the final evidence.

Files changed: `care/forms.py`, `care/payments.py`, `care/views.py`, new `care/private_storage.py`, new `care/test_audit_20261024.py`, `templates/care/doctors.html`, `templates/care/doctor_detail.html`, `requirements.txt`, `requirements.lock.txt`. Documentation/index/manifest and audit evidence were updated. No schema migration, new feature, new dependency family or UI redesign was introduced.

## Remaining issues, blocked services and untested scope

**Critical: none identified in the tested scope.** Remaining high-priority items are launch blockers, not concealed test passes:

| External group | Status / impact / required configuration |
| --- | --- |
| B1 — SMTP and hospital recipient | **Blocked, High.** `EMAIL_HOST`, `DEFAULT_FROM_EMAIL` and the hospital email are blank. Real password-reset, proof-attachment and notification delivery cannot be established. In-memory mail tests pass; that is not real SMTP success. |
| B2 — Payment gateway | **Blocked, Medium, optional while disabled.** Razorpay credentials/webhook secret are absent. Captured-payment handling has mocked tests, but no real sandbox capture/webhook was performed and no money was sent. Manual screenshot/staff verification flows pass. |
| B3 — Cross-device video/TURN | **Blocked, High for video launch.** `TURN_URL` and `TURN_SECRET` are absent. Eligibility, consent, admission and synthetic offer/answer API exchange pass; actual camera/microphone media across networks was not tested. |
| B4 — Private cloud storage | **Blocked, High for Vercel launch.** Local filesystem storage works; S3 credentials/bucket are not configured. Real private object upload and signed URL behavior are untested; fault injection does not establish provider availability. |
| B5 — Hosted build/deployment/domain | **Blocked, High.** Vercel CLI is absent, no `.vercel/project.json` link exists, no verified public HTTPS origin is configured, and hospital identity/contact/policy fields are incomplete. No hosted build artifact, deployment, public TLS or production smoke test is claimed. |
| B6 — Managed production database | **Blocked, High for hosted launch.** The running MySQL database is loopback-only. Managed remote connectivity, production TLS and production privilege configuration were not tested. Local MySQL and isolated CRUD/concurrency tests pass. |

**Low:** Payment/review localization is incomplete. An actual Marathi session retained the English payment heading; core tasks remain usable. This is recorded rather than claimed fully translated.

**Not tested: four additional scope groups.** (N1) sustained load/stress and long-duration reliability; (N2) a full WCAG/manual assistive-technology and cross-browser/device matrix; (N3) an independent comprehensive penetration test beyond the specific authorization/input/header/advisory checks performed; (N4) a fresh production backup-restore/disaster-recovery drill. Existing private backups were preserved, not restored over any database.

Only existing features were exercised. The hospital assistant is local intent/FAQ logic, not an external generative model; no model-provider test is claimed. No Node frontend build is applicable to this Django template application, and no new lint framework was installed. No real patients were contacted, real payments sent or hardware permissions requested.

## Exact next steps before deployment

1. In **Admin → Hospital settings**, enter verified hospital identity, address, phone, hospital/privacy email and cancellation/refund policy. Complete the remaining translation keys before a fully localized release.
2. Configure production environment values using [the existing deployment guide](VERCEL_DEPLOYMENT.md): `APP_ENV=production`, a verified HTTPS `PUBLIC_ORIGIN`, exact `ALLOWED_HOSTS`, a private stable `DJANGO_SECRET_KEY`, remote `MYSQL_*` with certificate verification (or the supported PostgreSQL configuration), and durable private `PRIVATE_STORAGE_BACKEND=s3` settings. Do not deploy local test flags, fixture accounts, `.runtime` or local database credentials.
3. Configure and test the real SMTP sender/recipient and authenticated TURN relay. Keep Razorpay disabled unless the complete sandbox credentials and webhook can be tested. Verify real private object access and remote database connectivity.
4. With the intended production environment active, run the following from the project folder. Back up before any pending production migration; this audit adds no migration:

```powershell
python manage.py migrate --plan
python manage.py check --deploy --fail-level WARNING
python manage.py launch_check
python manage.py collectstatic --noinput
python manage.py send_payment_proofs
```

5. Link/configure a preview deployment using the existing guide, run the actual hosting build there, and repeat the five-role smoke tests against that protected preview. Verify a sandbox payment, real email, two-device video, private cloud files and a backup restore before production release. Re-score only after recording those results.

Local startup remains:

```powershell
.venv\Scripts\python.exe tools/local_mysql.py serve
```
