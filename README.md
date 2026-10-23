> Current hospital upgrade (23 October): [implemented workflows, migrations, tests and remaining scope](docs/HOSPITAL_UPGRADE_REPORT.md). Primary MySQL now has46 tables; older reports are historical.

> VS Code folder delivery: [OPEN_IN_VSCODE.md](OPEN_IN_VSCODE.md), [database viewer guide](docs/VSCODE_DATABASE.md), and [login/delivery report](docs/LOGIN_AND_FOLDER_DELIVERY.md).

> Latest22 October transformation: [PRODUCT_TRANSFORMATION_REPORT.md](docs/PRODUCT_TRANSFORMATION_REPORT.md). Editable Figma system, new directory/schema explorer,116 SQLite tests and120 tests each on MySQL/PostgreSQL. Primary MySQL is preserved; PostgreSQL migration rehearsed locally. Supabase/Vercel targets and complete design sign-off remain blocked/outstanding.

> Latest final audit: [FINAL_SYSTEM_REPORT.md](docs/FINAL_SYSTEM_REPORT.md). The running local app now uses actual MySQL `mednova_local` (31 tables). 111 SQLite tests,115 MySQL tests,8 HTTP scenarios and261 responsive checks passed. Human administrator provisioning and hosted production verification remain blocked. Earlier counts below are historical.

> UI redesign: see [UI_REDESIGN_REPORT.md](docs/UI_REDESIGN_REPORT.md) for the shared design system, all screen coverage,129 responsive checks and104 passing regression tests.

> Current product expansion: see docs/PRODUCT_IMPLEMENTATION_REPORT.md. New additive migrations0003/0004; 108 MySQL tests and104 SQLite tests passed, including four real MySQL race tests. Older counts and statements below describe earlier checkpoints. Production deployment remains blocked.

# MedNova | Python + MySQL hospital portal

A locally reviewable replacement for the supplied React/localStorage prototype. Frontend: HTML templates, CSS and vanilla JavaScript. Backend: Django 5.2.18 / Python. Database: MySQL. No Node.js, React, Firebase, Google sign-in or OTP login is required.

**Start here:** `START_HERE.md`. Public homepage: `/`; workspaces: `/dashboard/` after login. Read `docs/REPAIR_AND_VERCEL_REPORT.md` for the current diagnosis/results and `docs/VERCEL_DEPLOYMENT.md` for the selected deployment target. No production site has been published.

## Implemented

- Email/password registration and login with Argon2 password hashing, password changes, optional SMTP password resets, server-side sessions and logout.
- Patient, Doctor, Receptionist, Pharmacist and Admin workspaces. Roles are read from the database, never accepted from a login selector.
- Staff registration starts pending. Doctors enter qualifications, department, registration number, experience, bio and consultation fee. Admin accepts or denies their application. Editing professional details requires a new review.
- Department directory, approved doctor directory, 12-minute availability slots, appointment request/confirmation, cancellation, rescheduling and history. Fees are stored at booking. Transactional checks reject duplicate and overlapping bookings.
- Private appointment-linked report uploads/downloads. JPEG and PNG are re-encoded; PDF upload fails closed until antivirus scanning is configured. Patients and assigned doctors can retrieve reports; receptionists, pharmacists and application admins cannot retrieve clinical files.
- Doctor-issued prescriptions; a dispensing queue with stock validation, expiry validation and transactional inventory updates. Clinical notes remain hidden from pharmacists. Issued prescriptions are retained unchanged.
- Configurable medicine batches, prices at entry and stock adjustments with audit records.
- Consultation payment records for verified cash/bank receipts and manually completed refunds. Optional Razorpay order creation, hosted Checkout, signed callback verification and captured-payment webhook handling.
- Appointment-specific WebRTC video calls with participant authorization, appointment time windows, camera/microphone controls, and optional authenticated TURN relay. No recording feature.
- Blue/teal/white split login, responsive layouts, self-hosted fonts, accessible form labels, focus states and restrained buttons. The original logo is reused; no synthetic patient photographs, reviews or metrics are included.
- English, Marathi and Hindi navigation, login, major labels and actions. Names and medical notes stay in the language entered. Some detailed validation, setup and legal text remains English; full professional language review is outstanding.
- Privacy and Terms pages, configurable hospital contacts and ambulance phone action. Hospital identity/contact/policy fields start empty rather than inventing details.

## Status and verification

Updated audit (21 October 2026): see `docs/PROJECT_AUDIT.md`, `docs/FIXES_APPLIED.md`, `docs/TEST_REPORT.md`, `docs/DATABASE_SETUP.md`, `docs/DEPLOYMENT.md` and `docs/PRODUCTION_READINESS.md`. Latest verification: 87 regression tests and eight actual HTTP scenarios passed; main authenticated browser journeys, including prescriptions/dispensing and report upload/download, were executed. Production MySQL, the explicit MySQL concurrency suite, real provider integrations and Vercel deployment remain UNVERIFIED. Vercel project creation was blocked by account permission (HTTP 403). No production-readiness claim is made. Earlier verification artifacts are historical.

Read `docs/SECURITY_REVIEW.md` for exact test results, scope and remaining checks. This is a review build, **not a claim of production readiness or a completed independent penetration test**. No production dataset is included in the source artifact; existing local records are preserved in ignored private databases. The target MySQL server, Windows installer, live email, real two-device video, payment provider and mobile/desktop browser rendering require target-environment verification.

## Source map

- `templates/care/`: HTML pages and shared layout
- `static/css/app.css`: responsive styling
- `static/js/`: interface, video and payment JavaScript
- `care/models.py`, `forms.py`, `views.py`, `services.py`: Python application
- `care/security.py`, `middleware.py`: access control, limits and headers
- `care/migrations/`: MySQL schema migrations
- `care/templatetags/translate.py`: interface translations
- `care/tests.py`: isolated workflow and security regression tests
- `mednova/settings.py`: environment-based configuration
- `database/README.md`: schema and database account guidance
- `docs/INTEGRATIONS.md`: email, video and payment setup
- `docs/DEPLOYMENT.md`: later deployment requirements

The supplied ZIP had no Python backend, live database, `.env` file or `.git` history. Existing browser-local sample records are not migrated into patient records.
