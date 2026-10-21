# Verification report â€” 21 October 2026

Windows, Python 3.14.6, Django 5.2.18; dependencies repaired/installed into project .venv. SQLite used only for isolated verification. All fixture users/registrations are synthetic with reserved example.test emails. No real patient data, MySQL credentials or external service account was supplied.

| Execution | Exact result |
|---|---|
| Initial imports | Failed: Pillow _imaging missing; repaired environment |
| Initial existing suite inside sandbox | 55 executed: 53 passed, 2 temporary-directory permission errors |
| Existing suite with temporary filesystem access | 55 passed, 0 failures, 0 skips |
| First expanded suite | 70 passed, 0 failures, 0 skips |
| Full expanded suite: python manage.py test care --verbosity 1 | 76 passed, 0 failures, 0 skips, 4.972 seconds |
| Real HTTP Waitress acceptance: python tools/http_acceptance.py | 8 scenarios passed, 0 failed |
| Explicit MySQL concurrency suite: care.mysql_acceptance | 2 tests supplied, NOT RUN: no dedicated MySQL service/credentials |
| Django system checks | 0 issues |
| Production check --deploy --fail-level WARNING using synthetic host/secret configuration | 0 issues; no actual deployment/DB/provider validation implied |
| makemigrations --check --dry-run | No changes detected |
| Isolated SQLite migrate | auth/contenttypes/care 0001 + 0002/sessions applied |
| collectstatic --noinput | Initial 8 copied; subsequent CSS update 1 copied, 7 unchanged |
| compileall -q care mednova | Passed |
| pip check | No broken requirements found |
| Browser public doctor directory/filter | DB-backed profiles rendered; availability checkbox GET filtered to doctor with a free slot |
| Browser authenticated sign-in | BLOCKED: in-app browser sends Origin: null; CSRF correctly returns 403 |

The regression suite covers hashing, registration/approval, normalized login/email, forged roles/fees, reset mail via in-memory email backend and single-use tokens, password change/session invalidation, logout, rate limiting, CSRF/XSS/security headers, private paths/uploads/downloads, object permissions, sequential booking duplicates/overlaps/cancellations/rescheduling, pharmacy expiry/atomicity/idempotency, payment receipts/signed webhook fixtures, signaling/time windows, templates and role pages. Added tests cover service authorization, stale slot flags, doctor overlaps, consultation type, cancellation notice, notifications, check-in, patient lookup/registration, user deactivation, department editing, slot editing and day/week/month calendars. Mocked provider payloads and in-memory email are tests, not verified integrations.

The eight real HTTP scenarios use Waitress on loopback, a separate on-disk SQLite database, real cookies and CSRF tokens with same-origin headers. They assert registration/profile/logout/relogin; doctor publishes and retrieves slots; directory/slot selection/saved booking; duplicate rejection and object 404; doctor confirmation/patient cancellation/released availability; reception/pharmacy boundaries; administrator pages; health/inbox/actual CSRF rejection. These are HTTP acceptance results, not browser acceptance results.

## Browser acceptance Aâ€“L

| Workflow | Result and limitation |
|---|---|
| A registration/login/profile | Automated + HTTP PASS; browser UNVERIFIED |
| B doctor schedule | Automated + HTTP PASS; browser UNVERIFIED |
| C discovery/booking | Public directory/filter browser PASS; booking HTTP + automated PASS; authenticated browser UNVERIFIED |
| D second patient same slot | HTTP/sequential automated PASS; concurrent MySQL and browser UNVERIFIED |
| E doctor status | HTTP confirmation + automated transitions PASS; browser UNVERIFIED |
| F patient status/cancel/reschedule | HTTP status/cancel + automated reschedule PASS; browser UNVERIFIED |
| G reception | Automated registration/check-in + HTTP lookup/role boundaries PASS; browser scheduling UNVERIFIED |
| H pharmacy | Automated dispense/stock/access + HTTP page/access PASS; browser dispense UNVERIFIED |
| I administration | Automated approval/users/departments + HTTP pages PASS; browser approval UNVERIFIED |
| J reset/errors/access | In-memory reset/token + DB outage health + HTTP CSRF/access PASS; real SMTP/browser reset UNVERIFIED |
| K persistence | On-disk SQLite fixtures survived server restarts; HTTP profile survived logout/login. Production MySQL/deployment persistence UNVERIFIED |
| L desktop/mobile | Public directory inspected at default viewport and 390Ã—844; GET filter verified. Authenticated dashboards/full accessibility UNVERIFIED |

## Outstanding verification

Run the explicit two-thread MySQL suite using DATABASE_SETUP.md. SQLite select_for_update does not lock rows; local regression results do not prove MySQL concurrency. The two explicit tests fail on unexpected DB errors/deadlocks rather than silently skipping. Add staging stress coverage for pharmacy, payment/cancellation, approval changes and multi-doctor reschedules.

Use normal desktop/mobile browser profiles with a non-null same origin for Aâ€“L. The sole connected in-app browser cannot complete form submissions; security was not disabled to accommodate it. Real SMTP, TURN, Razorpay sandbox, ClamAV, production startup, public health, TLS, backups and restore drills remain UNVERIFIED. Existing static-analysis JSON is historical; no fresh independent penetration/compliance audit was performed.

Final rerun: 76/76 regression tests passed in 4.972 seconds; 8/8 HTTP scenarios passed after the test-only SQLite transaction change. One intermediate repeat encountered SQLite database-is-locked during login; test SQLite now uses IMMEDIATE transactions with a 20-second timeout. Production MySQL settings were not changed. Raw results: docs/verification/current-tests.txt and current-http.txt. Mobile filter repair was visually rechecked at 390×844 with no horizontal overflow.

For the HTTP harness, set APP_ENV=local, MEDNOVA_TESTING=1 and MEDNOVA_TEST_DB=browser_acceptance.sqlite3 in both server and client environments. The harness refuses other client settings. It requires synthetic Workflows fixtures; never seed or target production.
