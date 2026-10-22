# Login repair and VS Code folder delivery — 22 October 2026

| Item | Status | Evidence / practical limit |
|---|---|---|
| Role-selection root cause | PASS | Login role labels were inert `<span>` elements, with no links or role-selection form field. The shared backend already authenticated by email and routed the dashboard from the stored User.role. Admin was present as tiny plain text, not a discoverable action. |
| Five role flows | PASS | Replaced inert labels with real server-rendered role links, selected state, 44px targets and a hidden submitted role. Explicit form action, safe next URL and preserved email on error. Matching logins succeed; 20 cross-role combinations deny authentication. Generic login remains supported. Role choice never changes permissions. |
| Inactive/missing role/invalid credentials | PASS | Generic invalid-or-inactive feedback; unsupported stored role denied. Pending staff still reach the existing approval screen. Existing CSRF, throttling, password replacement, logout and server-side authorization remain in force. JS duplicate-submit/loading handling remains active. |
| Intended admin recovery | BLOCKED on private terminal input | Read-only inspection found jayesh@gmail.com absent in actual primary MySQL. No human password or account was invented. Run Admin-MedNova.ps1 for secure hidden entry; existing ensure_admin is idempotent, refuses conflicting non-admin accounts and requires bootstrap password replacement. Existing synthetic provisioning tests passed. |
| Database identity/data preservation | PASS | Primary remains MySQL8.4.13, mednova_local,127.0.0.1:3307, restricted runtime. check_database confirms actual connection. PostgreSQL remains separate rehearsal. No schema migration/reset/bulk patient modification was needed. Only synthetic HTTP workflows mutate test records. |
| VS Code project | PASS | Workspace file, extension recommendations, interpreter configuration, three tasks and PowerShell setup/start/admin scripts added. All three scripts parsed successfully. Fresh-machine dependency installation and provisioning were not executed against a new machine. |
| Database table visibility | PASS documentation / NOT TESTED extension UI | Actual engine/connection, 31-table schema links, safe SELECTs, transactions and export guidance are in VSCODE_DATABASE.md. Oracle extension grid browsing is documented; no claim of installed extension or verified inline writeback. Password stays in ignored config or secure credential prompt. |
| Admin data tools | PASS existing verified implementation | Metadata-only schema explorer and whitelisted audited application forms retained. Search, pagination and role boundaries covered in existing tests. No arbitrary SQL endpoint or unrestricted clinical-table CRUD was added. |
| Full backend regression | PASS | 120 SQLite tests;124 MySQL tests;124 PostgreSQL tests. The SQL suites include four actual concurrency cases each. Four focused role tests pass. Counts overlap across engines. Logs: verification/login-delivery-*-tests.txt. |
| Real HTTP workflows | PASS | Eight scenarios pass on primary MySQL and restricted PostgreSQL runtime after restart, covering auth/profile, doctor availability, booking, denial, cancellation, reception/pharmacy, admin metadata and real CSRF rejection. |
| Responsive login | PASS selected checks | Actual browser widths320,375,390,430,768,1024,1280,1440,1600. Five links present; minimum link height44px; no page horizontal overflow. Doctor/Admin navigation visibly verified. See responsive JSON and screenshot. Previous207 checks across role/public pages are recorded separately in PRODUCT_TRANSFORMATION_REPORT.md; not rerun or claimed as new checks here. |
| Entire-screen premium redesign | NOT TESTED / incomplete | Existing shared premium layout, implemented directory and role dashboards retained. This delivery improves actual login; it does not claim every screen has been freshly redesigned or approved. Existing Figma workflow studies still need refinement. |
| Hosted integrations/production | BLOCKED / NOT TESTED | Supabase/Vercel targets and credentials remain unresolved. Real SMTP/payment/TURN/storage integrations and production readiness are not asserted. |
| Clean source ZIP | PASS after packaging verification | See the sibling MedNova-VSCode-Complete-2026-10-22.zip and its .verification.json for exact file count/hash and extraction checks. Excludes private config, databases/dumps/uploads, virtual environments, caches and Git metadata. Original history/data stay in the original repository. |

## Files changed

care/views.py; templates/care/login.html and base.html; static/css/product.css; care/tests.py; new care/test_login_delivery.py; .vscode settings/tasks/extensions; MedNova.code-workspace; Setup-MedNova.ps1, Start-MedNova.ps1 and Admin-MedNova.ps1; OPEN_IN_VSCODE.md; README/START_HERE pointers; this report, database guide, current test logs/matrices and login screenshot. No model migration or production credential was introduced.

## Exact commands on this laptop

```powershell
Set-Location 'C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Python-MySQL'
code .
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-MedNova.ps1
# In a separate terminal; enter a new password privately:
powershell -NoProfile -ExecutionPolicy Bypass -File .\Admin-MedNova.ps1 -Email 'jayesh@gmail.com'
```

Use the already running server instead of starting a duplicate. Fresh ZIP setup is documented in OPEN_IN_VSCODE.md. Do not copy local runtime data to external staging. Database backup/restore, full metadata and rollback-first UPDATE/INSERT/DELETE examples remain in MYSQL_OPERATIONS.md and linked schema inventories.
