# Follow-up repair

See LOGIN_PREVIEW_DIAGNOSIS.md and REPAIR_AND_VERCEL_REPORT.md for the current repair: corrected the application Referrer-Policy causing CSRF failures, added public navigation/pages, safe workflow redirects, receipts and private S3/Vercel configuration. Final verification: 87 regression tests, eight HTTP scenarios and actual browser journeys. Earlier browser limitations below were superseded by the confirmed header fix.

---

# Changes applied — 21 October 2026

The initial baseline is PROJECT_AUDIT.md. Existing visual identity, ORM persistence, role approval, private reports, prescriptions, payment and video implementations were retained.

| Confirmed defect / gap | Root cause | Files and change | Verification |
|---|---|---|---|
| Arbitrary service mode/reason and forged reschedule owner | Validation existed only in views/forms | care/services.py validates input and persisted owner | Regression tests |
| Concurrent cancellation/rescheduling lock mismatch | Appointment/slot locks acquired in differing orders | services.py locks patient, sorted doctor rows, then appointment/slot; ownership checked after patient lock | Sequential regressions pass; actual MySQL races UNVERIFIED |
| Stale slot flag / imported overlapping doctor slots | Relied on booked flag alone | services.py checks current appointment occupancy and doctor overlaps | Regression tests |
| Service status and dispensing lacked actor permissions | Relied on route decorators | services.py reloads actor and enforces role, approval, activity and ownership | Regression tests |
| Dispensing against cancelled consultation | No consultation check/lock | services.py locks appointment before prescription, rejects cancellation | Regression tests; MySQL race UNVERIFIED |
| Receipt/order operations used stale appointment status | Appointment read before payment transaction | views.py locks and reloads appointment before payment | Existing payment tests and source inspection; provider UNVERIFIED |
| Prescription eligibility could change before transaction | Only initial view check | views.py rechecks status/start after appointment lock | Prescription regression tests |
| Email normalization bypassed ordinary saves | Only manager/form normalized | models.py normalizes email on save | Regression test; bulk SQL is operator responsibility |
| Past or shorter-than-12-minute availability silently accepted | Form checked end > start only | forms.py rejects invalid future ranges | Regression test |
| Consultation mode control absent | Slots lacked consultation type | models/forms/views/services/templates and migration 0002 add either/in-person/video slots | Regression test and HTTP slot creation |
| Slot editing and calendar views absent | Only add/remove/list available | SlotEditForm, edit_slot and day/week/month filters | Ownership/overlap/booked-slot/calendar regressions |
| Cancellation policy was free text only | No configurable server cutoff | Hospital cancellation_notice_minutes, service enforcement | Regression test |
| Notifications disappeared after response | Flash messages only | Notification model, transactional booking/status notices, own-user inbox/read action | Regression and HTTP tests |
| Reception patient lookup/registration/check-in missing | Routes absent | patients/check_in views, forms, templates, routes | Role/registration/check-in regressions; HTTP lookup |
| Reception reschedule action hidden | Template allowed patient only | appointment.html exposes eligible reception reschedule link | Template compilation and service regression |
| User activation controls, department editing, operational totals absent | No management routes | users/department_edit/operational_report and templates | Regression and HTTP checks |
| Directory filtering/pagination incomplete | Text search only, unused department query | views/templates add department and free-slot filters; exclude non-doctor profile users | Regression, HTTP, mobile browser filter |
| Pagination controls absent on list pages | Pagination context existed without links | templates/context preserve filters and expose navigation | Template compilation; >30-page traversal not browser verified |
| Mobile filters cramped | Search bar forced multiple fields in one row | static/css/app.css wraps fields and gives mobile inputs full width | Browser visual inspection/recheck |
| No safe readiness endpoint | No health route | /health/ checks DB and schema, returns generic 503 | Success/failure regression + Waitress HTTP |
| Default CSRF error unhelpful | Django default failure page | csrf_failure returns branded 403, logs category only | Automated CSRF and actual HTTP rejection |
| MySQL tests impossible to select | TESTING unconditionally replaced MySQL | settings.py supports MEDNOVA_TEST_MYSQL=1, explicit mysql_acceptance.py | Suite supplied; execution blocked by absent MySQL |
| Private uploads tied to checkout | Hardcoded MEDIA_ROOT | PRIVATE_MEDIA_ROOT supports persistent private volume | Configuration inspection; production volume UNVERIFIED |
| Stale setup error / dependency lock | Referenced nonexistent setup.py; certifi lock differed from repaired env | settings.py points to configure.py; lock matches installed version | Import/pip/system checks |

Migration 0002 is additive and retains existing business records. It was applied only to isolated SQLite data. Back up and rehearse on a MySQL clone before a live migration. No production database was accessed, reset, seeded or migrated. No service credentials were added.

Test-environment fix: a repeated multi-threaded Waitress HTTP run exposed a SQLite lock-upgrade failure in rate limiting. The test-only SQLite backend now uses IMMEDIATE transactions and a 20-second busy timeout. Final regression and HTTP suites passed after this change; production MySQL row-lock semantics remain independently unverified. Production startup also refuses MEDNOVA_TESTING=1 outside the test command.
