# MedNova fresh local audit and cleanup — 24 October 2026

## Outcome

**88/100 — Ready with issues; external integration sign-off remains required.**
This is a fresh verification of the existing project, not a claim that every possible defect has been excluded. Changes are local and uncommitted. No push, deployment, production record mutation, real payment or external email was performed.

## Confirmed bugs and fixes

New product bugs confirmed in this audit: **1 medium** (0 critical, 0 high, 0 low).

Payment-proof email retries selected actively leased messages before applying their bounded batch limit. Another worker could already be sending those messages; selecting them consumed the batch and delayed eligible pending/expired-lease messages. `care/payments.py` now excludes unexpired leases before limiting the query. The existing transactional send-time lease check remains intact. Expired leases remain retryable.

`care/test_payments.py` adds a regression covering an active lease, a pending message and an expired lease in a two-message batch. The new test failed against the original implementation, then passed after the fix. All 20 payment tests and the final full MySQL suite passed. No model changes or migrations were needed.

## Cleanup

Removed only the redundant download archives `.runtime/mysql-8.4.13-winx64.zip` and `.runtime/postgres-official.zip`: **665,775,229 bytes (634.9 MiB)**. Both extracted database executables were verified to exist. Startup helpers reference those extracted directories, not the ZIPs. Post-cleanup MySQL connectivity and full tests passed. PostgreSQL startup was not exercised.

Preserved database clusters, SQLite databases, private credentials, uploads, backups, extracted runtimes, deployment alternatives and historical audit evidence. No source files were removed speculatively. Deletions are ignored local artifacts and do not appear as tracked Git deletions. Details: `verification/fresh-audit-20261024-cleanup.json`.

## Final test results

| Check | Passed | Failed |
|---|---:|---:|
| Django tests against isolated MySQL | 229 | 0 |
| Frontend routing build tests | 2 | 0 |
| HTTP acceptance scenario groups | 8 | 0 |
| Payment HTTP scenario/login groups | 8 | 0 |
| Clinical/review HTTP scenario/login groups | 7 | 0 |
| Six-role rendered link and asset checks | 251 | 0 |
| Deployed public read-only HTTP checks | 10 | 0 |

**231 automated tests passed; 23 HTTP scenario groups, 251 link/asset checks and 10 public probes passed separately.** These checks overlap deliberately; they are not 515 independent unit tests. The 540 route/role assertions in the Django matrix are included in the 229 tests and not added again. No final failing accessible checks remain.

Backend startup on localhost:8003, database connectivity, Django system checks, migration drift check, unapplied migration check, `pip check` and `git diff --check` passed. Django deployment checks passed with production security flags explicitly supplied to the isolated local settings; this does not validate provider credentials. No lint/type-check tool is configured in pyproject.toml. The server-rendered Django frontend has no separate TypeScript build. The actual frontend production command, `node build.mjs` in deployment/vercel with the configured backend origin, passed.

## Workflow evidence

- Synthetic registration, profile update, logout/re-login and persistence; approved doctor availability publication; appointment booking, duplicate prevention, confirmation, cancellation and slot release.
- Patient, doctor, receptionist, pharmacist and administrator authenticated HTTP workflows; anonymous and cross-role boundaries; actual CSRF denials; schema metadata and health.
- Both appointment types, online proof upload, rejection/resubmission, reception offline payment, assigned-doctor/reception verification and patient notification. A screenshot alone leaves video room/signalling inaccessible; staff verification unlocks an otherwise eligible room. Screenshot ownership denial verified.
- Doctor prescription, pharmacist dispensing, patient retrieval; private image report upload/download and another-patient denial.
- Completed-visit rating without comment, public retrieval, editing/repeated submission, owner boundary; malformed assistant payloads rejected; sensitive file URL probes denied.
- Actual browser patient login and mobile completed-appointment/review navigation. Five rating radio controls, comment not required, saved edit values present. At the requested 390px mobile viewport the rendered client width and scroll width both measured 375px: no horizontal overflow. Desktop viewport restored afterward. Screenshot: `.runtime/fresh-audit-mobile.png`.
- Production was read-only: home, health, doctor directory, login, registration, contact and favicon returned 200; .env, .git/config and private upload probes returned expected 404. Authenticated production workflows were not repeated because this audit prohibits production mutations.

### Test-harness observations

The clinical HTTP script initially assumed a doctor's aggregate rating was exactly 5.0 and there was only one review. This fails against a reused isolated schema with earlier synthetic reviews. The temporary runner was corrected to assert the specific submitted feedback, and the complete flow passed. No product change was made for this test assumption.

An unnecessary repeat of the login-heavy HTTP runner hit the expected 429 rate limit. The synthetic audit schema's rate-limit windows were expired explicitly, then all eight acceptance groups passed. Production rate limits were untouched. This is test setup, not a product failure.

## Blocked / not run

Counted as **7 integration/tooling groups not verified**, not passed:

1. Hospital SMTP recipient/provider delivery: previous live audit found no hospital recipient; not changed or revalidated through real delivery here. Locmem email attachment/failure/idempotence tests pass, but cannot prove inbox delivery.
2. Fresh R2 cloud upload/read/deletion and production database writes: intentionally not run under the no-production-mutation constraint. Local private-file flow and outage tests pass; earlier live evidence remains historical.
3. Real Razorpay capture/refund: no real financial transaction or live provider credential exercise.
4. Two-device WebRTC media and TURN traversal: eligibility/signalling authorization covered, actual audio/video transport not exercised.
5. External PDF antivirus service: no real scanner integration verification.
6. Local Docker image rebuild: Docker CLI is unavailable. Frontend routing build passes; the earlier deployed container remains historical evidence.
7. Standalone lint/type-check and a fresh dependency vulnerability advisory scan: no configured lint/type-check command; pip consistency is not a vulnerability scan.

Admissions, procurement, staff approvals, scheduling and assistant behavior have existing automated coverage in the full suite; not every operational variant received a separate manual browser pass. No comprehensive penetration or sustained load test was performed.

## Evidence-based score

| Category | Award | Maximum | Reason for deductions |
|---|---:|---:|---|
| Core functionality/workflows | 23 | 25 | Broad automated and real HTTP coverage; not all operational variants manually exercised |
| Backend/API/database | 19 | 20 | MySQL persistence, isolation and migrations pass; no load test |
| Authentication/security | 18 | 20 | Role boundaries, ownership and CSRF pass; no comprehensive penetration/advisory scan |
| UI/responsiveness | 8 | 10 | Desktop login/navigation and mobile review checked; not every screen/device |
| Appointments/payment/video | 8 | 10 | Manual verification lock passes; provider payment/media transport unverified |
| Error handling/reliability | 4 | 5 | Retry defect fixed and outages covered; external delivery remains unverified |
| Build/deployment readiness | 8 | 10 | Frontend build and settings checks pass; Docker and live integration release checks outstanding |
| **Total** | **88** | **100** | Untested areas receive deductions |

## Remaining steps before release

1. Review the local code diff and regression, then authorize push/deployment if desired. The email retry fix is not live yet.
2. Configure/verify the existing hospital email recipient and SMTP settings privately; send a deliberately authorized synthetic proof and verify inbox delivery.
3. In an authorized staging environment, verify cloud storage, payment-provider sandbox capture/refund, two-device video/TURN and PDF scanning; build the container in Docker/CI.
4. Run a current dependency advisory scan and deployment smoke tests after an authorized release.

Changed application files: `care/payments.py`, `care/test_payments.py`. This report and `verification/fresh-audit-20261024-*` contain fresh evidence. Historical reports describe prior fixes and must not be treated as newly executed tests.
