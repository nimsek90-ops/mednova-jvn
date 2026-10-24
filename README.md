# MedNova Smart Hospital

## Authoritative live architecture

Vercel (`deployment/vercel`) proxies same-origin requests to Render (`Dockerfile.render` → `deployment/render/start.py` → Django WSGI). **Aiven MySQL is the one authoritative live database.** Cloudflare R2 stores private upload objects; Django sessions and `care.User` provide authentication. Supabase is not part of the active live deployment.

PostgreSQL helpers and the root direct-Django Vercel configuration are optional, tested compatibility paths, not a second live backend or database. Do not run a data-copy or deployment helper without selecting its target explicitly. Local fixtures, restore databases and historical audit evidence are not production sources.

See [restructuring evidence](docs/RESTRUCTURE_2026-10-24.md) for the current workflow repairs and deployment status.


Django templates and plain JavaScript, served by Waitress. MySQL is the working database. No npm build or separate frontend server is required.

## Run the existing project

From this project folder in VS Code PowerShell:

```powershell
.\.venv\Scripts\python.exe tools\local_mysql.py serve
```

Open http://127.0.0.1:8000/ . Keep the terminal running. If the app is already open, use that server instead of starting another one.

This laptop uses its ignored private MySQL configuration; do not initialize or reset a database to run it. [OPEN_IN_VSCODE.md](OPEN_IN_VSCODE.md) explains existing-data setup, a fresh machine and authorized admin recovery. There is no default password. [START_HERE.md](START_HERE.md) covers first-time installation and troubleshooting.

## Current modules

- Five approved-account workspaces: patient, doctor, receptionist, pharmacist and administrator.
- Patient registration/MRN lookup, the reception desk, department/specialty catalogue, doctor profiles and published schedules.
- Booking, rescheduling, cancellation, check-in and queues, with transactional conflict and capacity checks.
- Private reports, clinical records, prescriptions, inventory/dispensing, purchasing, billing and admissions.
- Hospital assistant, authorized patient-service tools, reviewed support handoff and restricted staff case queues.
- Optional email, payments, private cloud storage and WebRTC video. These integrations require their own configuration and verification; local tests do not establish production readiness.

The catalogue lists possible services, not proof that a hospital provides them. No doctors or credentials are generated for catalogue entries. No chatbot response diagnoses, prescribes or claims an external transfer succeeded.

## Project map

| Location | Purpose |
|---|---|
| `mednova/` | Settings, URL routing, WSGI, database and hosting configuration |
| `care/` | Models, forms, role-specific views, service transactions, security and tests |
| `care/http.py` | Small shared HTTP helpers; permissions remain in the existing security layer |
| `care/migrations/` | Required schema history and frozen reference data; retain every migration |
| `templates/care/` | Shared layout, accessible fields and role-specific pages |
| `static/` | Canonical CSS, JavaScript, images and self-hosted fonts |
| `tools/` | Explicit local database/startup, migration and HTTP verification tools |
| `docs/` | Current guides, historical reports, design records and verification evidence |
| `design/figma/` | Editable design construction sources; not an application build step |

`.runtime/`, `.venv/`, `private_uploads/`, local databases and `staticfiles/` are operational or generated directories. They are not disposable source duplicates. Do not copy private data or credentials into Git or a source archive.

## Checks

```powershell
.\.venv\Scripts\python.exe manage.py test care --noinput
.\.venv\Scripts\python.exe tools\local_mysql.py check
.\.venv\Scripts\python.exe tools\local_mysql.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m pip check
```

Django's ordinary test command uses an isolated test database. Real SQL locking acceptance requires the explicitly configured disposable SQL test database described in the verification report; never aim tests at working patient data. Dependency versions remain pinned in `requirements.txt` and `requirements.lock.txt`.

## Documentation

- [Latest complete website audit — 24 October 2026](docs/WEBSITE_AUDIT_2026-10-24.md)
- [Appointment payment verification and email setup](docs/APPOINTMENT_PAYMENTS.md)
- [Patient reviews and verification](docs/PATIENT_REVIEWS.md)
- [Cleanup audit, recovery checkpoint and verification](docs/CLEANUP_REPORT.md)
- [Documentation and historical evidence index](docs/README.md)
- [Patient assistant and support-case behavior](docs/PATIENT_ASSISTANT_REPORT.md)
- [Hospital scheduling, pharmacy and admission workflows](docs/HOSPITAL_UPGRADE_REPORT.md)
- [Database operations](docs/MYSQL_OPERATIONS.md) and [VS Code database viewer](docs/VSCODE_DATABASE.md)
- [External integrations](docs/INTEGRATIONS.md) and [deployment requirements](docs/VERCEL_DEPLOYMENT.md)

Historical reports record their own checkpoint counts and limitations; they are not current deployment claims. The active local schema has 53 tables after the payment proof verification migration. No hosted production deployment is verified by this cleanup.
