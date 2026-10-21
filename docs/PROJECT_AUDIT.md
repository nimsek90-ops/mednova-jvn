> Current product expansion: see PRODUCT_IMPLEMENTATION_REPORT.md. New additive migrations0003/0004; 108 MySQL tests and104 SQLite tests passed, including four real MySQL race tests. Older counts and statements below describe earlier checkpoints. Production deployment remains blocked.

# Initial project audit — 21 October 2026

Scope: extracted Django project, not the historical React ZIP mentioned in README. Existing verification artifacts describe an earlier run and are not evidence of this environment. No .env, production database credentials or hosting target is provided. No production data has been modified.

Architecture: mednova/settings.py and urls.py configure Django, MySQL, sessions, CSRF and WhiteNoise. care/models.py defines email users, departments, doctor profiles, slots, appointments, payments, prescriptions/items, medicine batches, private reports, audit events, rate buckets, video signals and hospital settings. Forms validate browser input; views enforce route and object permissions; services perform transactional booking/status/dispensing operations. Templates use server queries, vanilla JS handles navigation, Razorpay and WebRTC. Migration 0001 creates the schema. Management commands check DB/configuration, create an administrator and clean transient records. No background worker or external notification queue exists.

| Feature | Current implementation | Backend status | Database status | Test result | Severity | Required fix |
|---|---|---|---|---|---|---|
| Email login/logout/password policy | Django auth, Argon2, POST logout, rate buckets | Partially working | Email unique; manager lowercases only | Not yet tested | Medium | Normalize all ordinary user saves |
| Registration and roles | Patient self-service; staff pending; admin excluded | Partially working | ORM writes | Not yet tested | Medium | Preserve approval boundary; regression tests |
| Password recovery | SMTP + expiring Django tokens | Blocked by configuration | Tokens tied to password/login | Not yet tested | Medium | Test delivery/token reuse; configure real SMTP |
| Profile and staff review | Professional changes return doctor to pending | Partially working | Transactional writes | Not yet tested | High | Concurrent approval changes versus booking require locking review |
| Doctor directory | Approved profiles + name/department text search | Partially working | ORM backed | Not yet tested | Low | Add department and availability filters; pagination |
| Availability | Fixed 12-minute ranges; remove unused slots | Partially working | Doctor lock + unique start | Not yet tested | Medium | Reject past/too-short ranges; add calendar filters; consultation mode absent |
| Booking/rescheduling | Patient/doctor row locks; slot flag | Broken | Atomic but cancellation uses different lock order | Not yet tested | High | Lock shared calendar consistently; validate service input/ownership and overlaps |
| Appointment status | View permissions + service transitions | Partially working | Atomic updates | Not yet tested | High | Service lacks actor authorization; stale patient cancellation check |
| Reception scheduling | Existing-patient selector, booking/status/payment | Partially working | ORM backed | Not yet tested | Medium | Reschedule link absent; lookup/registration/check-in missing |
| Prescriptions | Assigned doctor issuance, immutable once issued | Partially working | Appointment lock, items | Not yet tested | Medium | Verify all paths and authorization |
| Pharmacy | Queue, transactional dispensing, inventory adjustments | Partially working | Row locks and nonnegative stock | Not yet tested | High | Service permits unprivileged callers; cancelled prescription dispensing not rejected |
| Reports | Private downloads, image re-encoding, scanned PDF | Blocked by configuration | Metadata in DB, files private | Not yet tested | Medium | Configure scanner, persistent protected storage and backup |
| Payments | Cash/bank/refund records + Razorpay | Blocked by configuration | Payment row locks | Not yet tested | High | Verify capture/cancellation races; sandbox credentials unavailable |
| Video | Authorized time-window signaling + TURN WebRTC | Blocked by configuration | Short-lived signals | Not yet tested | Medium | Real two-device TURN verification required |
| Administration | Staff review/departments/settings/audit | Partially working | ORM backed | Not yet tested | Medium | General user management, department editing and operational reports missing |
| Notifications | Django flash messages only | Missing | No notification model | Not yet tested | Medium | Persistent notification workflow not implemented |
| Language/navigation/layout | EN/MR/HI core labels, responsive CSS | Partially working | Session language | Not yet tested | Low | Browser/mobile and language review |
| Error handling/security headers | Safe 500 fallback, CSP, cookies, private cache | Partially working | DB failure can prevent template context | Not yet tested | Medium | Readiness endpoint with safe DB failure |
| MySQL migrations/concurrency | MySQL config; tests always force SQLite | Broken verification setup | Production UNVERIFIED | Not yet tested | High | Opt-in dedicated MySQL tests; real concurrency gate |
| Production operations | Deployment checklist only | Partially working | No target configured | Not yet tested | High | Health endpoint, concrete commands, backup/restore and rollback guide |

Confirmed source defects: services.book accepts arbitrary mode/reason and an existing appointment belonging to another patient; services.change_status has no actor checks; services.dispense has no actor checks. Reproduce with direct service calls in isolated tests. Booking locks patient → doctor → slot → appointment, while cancellation locks appointment → slot: concurrent reschedule/cancel can release the wrong slot or deadlock. Production implications remain unverified until MySQL concurrency tests run.

Runtime baseline: Python 3.14.6. Initial dependency/import run failed with `ImportError: cannot import name '_imaging' from 'PIL'`; environment repair required before test results can be asserted. Existing static-analysis JSON reports five low subprocess findings; arguments are lists without shell execution, scanner executable is operator configuration. This is not a fresh security scan.

Full route inventory is mednova/urls.py; source inventory and SHA-256 audit snapshot are recorded in docs/verification/source-inventory.json. No deployment-readiness claim is made.
