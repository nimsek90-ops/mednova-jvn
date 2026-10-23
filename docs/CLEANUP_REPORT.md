# MedNova safe cleanup report

Completed 23 October 2026 on branch `cleanup/safe-2026-10-23`. This is a cleanup of the existing Django project, not a replacement application.

## Recovery point and scope

The full non-ignored source state, including the unfinished receptionist changes, was saved before cleanup in commit **`0fba6e5`** (`Checkpoint current hospital work before safe cleanup`). The starting branch was `master`. A private-value scan of the 334 source files found no private configuration values eligible for staging. `.runtime`, `.venv`, local databases, uploads, dumps and private keys were not included in the checkpoint.

No files were removed before a recoverable source checkpoint existed. Private database backup files remain under ignored `.runtime/backups/`; they were never placed in Git or an ordinary source backup.

## Initial findings

- Runtime: Django 5.2.18, Python, server-rendered templates and plain JavaScript. The prepared laptop uses MySQL through restricted runtime credentials, with Waitress on loopback port 8000. PostgreSQL is an additional configuration/rehearsal, not a duplicate replacement for MySQL. No npm build is used.
- Entry points: `manage.py` for management/tests; `mednova/wsgi.py` for serving/deployment; `tools/local_mysql.py serve` and `Start-MedNova.ps1` for the prepared machine. CMD/PowerShell wrappers and VS Code tasks target different supported startup/setup uses.
- Models/routes/services cover the five roles, reception, scheduling, reports, pharmacy, purchasing, admissions, billing, video, assistant and restricted support cases. Dynamic Django discovery makes apparently empty package files, migrations, templates and management commands necessary.
- Canonical runtime assets are in `static/`. Collected `staticfiles/` assets serve a separate generated/deployment role. Font weights/licenses, public TLS CA files and editable Figma construction sources are intentional resources, not interchangeable copies.
- Most similarly named reports contain different historical scope/results. Only byte-identical verification outputs were candidates for content consolidation, with database environments kept separate.
- The interrupted reception upgrade had two unapplied migrations and four baseline test problems. Those are recorded below; cleanup did not create new hospital functionality.

## Removed files and evidence

Ten redundant files were removed, totaling **8,471 bytes of original file content**. New audit evidence/report files mean this is not a claim that the entire folder shrank by that amount.

| Removed | Retained source of truth / reason |
|---|---|
| `care/catalogue.py` | Its catalogue literal exactly matches frozen migration `care/migrations/0012_seed_possible_specialties.py`. The runtime helper had no imports/callers; all live catalogue screens query the database. The frozen migration remains unchanged. |
| `docs/verification/current-http.txt` | Identical to `final-http-mysql.txt` |
| `docs/verification/product-http.txt` | Identical to `final-http-mysql.txt` |
| `docs/verification/redesign-http.txt` | Identical to `final-http-mysql.txt` |
| `docs/verification/repair-http.txt` | Identical to `final-http-mysql.txt` |
| `docs/verification/login-delivery-mysql-http.txt` | Identical to `upgrade-mysql-http.txt` |
| `docs/verification/transformation-mysql-http.txt` | Identical to `upgrade-mysql-http.txt` |
| `docs/verification/login-delivery-postgres-http.txt` | Identical to `upgrade-postgres-http.txt` |
| `docs/verification/transformation-postgres-http.txt` | Identical to `upgrade-postgres-http.txt` |
| `docs/verification/upgrade-baseline-mysql-tests.txt` | Identical to `login-delivery-mysql-tests.txt` |

Every log comparison was checked byte for byte before deletion. Markdown references were updated. [Evidence aliases](verification/EVIDENCE_INDEX.md) preserve the old filenames/checkpoint associations without pretending that these old runs were executed again. MySQL and PostgreSQL canonical files remain separate even when their bytes match. Exact original hashes, destinations and reasons are in [cleanup-removals.json](verification/cleanup-removals.json).

No patient data, uploaded files, migrations, actual database tables, runtime credentials, fonts/images or source CSS were deleted. No directories were recursively purged.

## Consolidation and organization

- Added `care/http.py` for the existing positive-integer parser, pagination helper and common database-error-page decorator. `care.views.integer_id` and `care.views.paged` remain available as imported compatibility exports, so existing callers retain their interface.
- Reception no longer imports the views module merely to use HTTP helpers. Support and reception share error handling while keeping their original templates/status codes; support retains `Retry-After: 60`, reception retains its prior response contract.
- Test modules import the fixture module rather than exposing an imported TestCase class. All **179 regular test IDs are unchanged**, verified by `cleanup-test-discovery.json`; no test coverage was removed.
- Patient search pagination now retains explicit `name, pk` ordering after duplicate/MRN query combinations. This fixes the observed unordered-pagination warning without changing permissions or search results.
- Replaced the README's competing historical “current/latest” notices with one run path, source map and documentation index. Historical reports remain linked rather than being presented as current deployment claims. Setup/reset safeguards and integration configuration guides are preserved.
- Refreshed the public source integrity manifest after changes. No source folders or role-specific business controllers were merged into an oversized module.

## Intentionally retained

The per-file classification is in [cleanup-inventory.json](verification/cleanup-inventory.json). Important retention decisions:

- All migration files and package `__init__.py` files: framework schema/history and discovery contracts.
- Both database adapters, public CA certificates and engine-specific acceptance tests: required environment compatibility.
- Requirements file **and** lockfile: direct pins and resolved environment, not competing package managers.
- `.env.example`, Git/deployment ignore files, VS Code settings/tasks and Windows wrappers: distinct configuration/platform purposes.
- Legacy assistant POST templates and the patient-template compatibility alias: live compatibility behavior and direct/dynamic template lookups.
- Separate CSS layers, responsive overrides, weights/licenses and assets: repeated leaf-rule text is not enough to prove that cascade/media behavior is redundant. No CSS or image/font asset was removed. Literal template static references all resolve.
- Historical schema/role matrices/screenshots and Figma sources: distinct verification/design records.
- `.runtime/`, `.venv/`, `private_uploads/`, `.git/`, `staticfiles/` and the ignored legacy SQLite file: private operational state, installed runtime, generated serving assets or uncertain data provenance. A test-like filename was not treated as permission to delete a database.

## Dependency review

**No dependencies were removed or upgraded.** All ten direct requirements have a purpose: Django; mysqlclient and psycopg database adapters; Argon2 password hashing; Pillow report/image validation; requests payment HTTP; WhiteNoise static serving; Waitress serving; django-storages and boto3 optional private S3 storage. Configuration-based/dynamic imports are required even when a direct Python import is absent. Transitive lockfile entries remain intact. `pip check` reports no broken requirements.

## Pre-existing failures repaired

The baseline `cleanup-baseline-sqlite-tests.txt` discovered 179 tests, ran 167 because one class setup failed, and reported **3 failures plus 1 setup error**:

1. Chatbot fixture referenced `Department` without importing it. Added the missing import.
2. Department-count assertion expected exactly one department before the already-authored catalogue migration. It now verifies the actual department count.
3. Schema-search assertion excluded the new specialty/department join table. It now verifies both legitimate matching tables.
4. Daily-cap test added two hours to the current clock; near midnight this placed the candidate on a different hospital day, where the cap correctly did not apply. The fixture now explicitly places both visits on the same future day. The booking rule itself was not weakened.

No baseline failures were hidden or skipped, and no tests were deleted.

## Database protection and pending source setup

The checkpoint already contained receptionist migrations **0011** and **0012**, but the working MySQL database was still at 0010. Leaving the source/schema mismatched would leave the newly authored desk/catalogue pages broken. After isolated SQL verification, the existing backup-first migration helper applied only those already-authored migrations. Cleanup authored no new migration.

They add the specialty table and two relation tables, the optional registration address column, and possible-service reference catalogue entries. They do not assign doctors, create patient accounts, rewrite qualifications or replace appointments. Unpublished catalogue departments do not claim that services are available. The working database now has **51 tables**.

The private backup SHA256 is `a5e8078830c4e483d632107bbd44d65e00c8430b9436f261d84b0b3e3746fee4`. A private pre/post comparison hashed every original row using its original columns. Every original row is unchanged across **46 non-transient tables**; sessions and rate-limit counters were excluded because normal requests may update them. Reference catalogue rows/migration registrations may be appended. Row contents and private hashes were not exported to public reports. See `cleanup-data-preservation.json`, `cleanup-pending-migrations.txt` and `cleanup-schema.json`; schema foreign-key checks found no orphan rows. No database credentials or engine settings were changed.

## Tests actually executed

| Batch | Actual result |
|---|---|
| Baseline SQLite full suite | 179 discovered; 167 ran; 3 failures + 1 setup error, documented above |
| HTTP-helper/refactoring and repaired fixture checks | 158 focused tests passed |
| After duplicate module/log removals | 28 focused tests passed |
| Final full SQLite suite | **179 passed** |
| Final full MySQL suite | **188 passed**, including 9 SQL concurrency acceptance cases |
| Final full PostgreSQL suite | **188 passed**, including engine/locking compatibility cases |
| Test discovery preservation | All 179 regular test IDs identical before/after |
| Role/route matrix | **498 probes per engine**: 83 routes × anonymous/five roles; no unexpected server failures |
| Live HTTP, separate synthetic SQLite QA on 8003 | **9 checks passed**: all five logins/dashboards; reception registration page → selected patient → doctor profile → real booking form; authenticated report API; inventory/schema/empty specialty/permission/CSRF checks; health |
| Working MySQL server after restart | Seven read-only routes returned 200: health, login, assistant, doctors, specialties, departments, assistant API |
| Framework/migrations/dependencies | `check`, `makemigrations --check --dry-run`, `migrate --check`, `collectstatic --noinput`, `pip check` passed |
| JavaScript/static references | `node --check` passed for all five JS files; all literal template static references resolve |
| Source integrity | `git diff --check` and source manifest verification passed |

Raw final outputs are `docs/verification/cleanup-{sqlite,mysql,postgres}-tests.txt` with engine-specific route matrices. Live checks are in `cleanup-http.json` and `cleanup-working-server.json`. SQL tests used disposable test databases; live HTTP mutations/login state used an isolated synthetic QA database, not working patient data.

Actual commands included:

```powershell
.\.venv\Scripts\python.exe manage.py test care.test_reception care.test_transformation care.test_chatbot --noinput --verbosity 1
.\.venv\Scripts\python.exe .runtime\run_cleanup_checks.py sqlite
.\.venv\Scripts\python.exe .runtime\run_cleanup_checks.py mysql
.\.venv\Scripts\python.exe .runtime\run_cleanup_checks.py postgres
.\.venv\Scripts\python.exe .runtime\cleanup_http.py
.\.venv\Scripts\python.exe tools\local_mysql.py check
.\.venv\Scripts\python.exe tools\local_mysql.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe tools\local_mysql.py migrate --check
.\.venv\Scripts\python.exe tools\local_mysql.py collectstatic --noinput
.\.venv\Scripts\python.exe -m pip check
```

The ignored `.runtime` runners load the already configured isolated local test environments; they are not portable credentials or source-package setup requirements. A portable basic test command remains `manage.py test care --noinput`; engine locking suites require their explicit disposable SQL configuration.

## Limits and remaining risks

Browser automation failed to attach (webview timeout/debugger detached). Therefore no fresh rendered desktop/mobile or screenshot acceptance is claimed for this cleanup. Actual HTTP and role/security tests passed; existing distinct visual evidence was preserved. Real SMTP, financial transactions, external storage, camera/media, production hosting and hosted Supabase were not exercised. The separate historical PostgreSQL runtime rehearsal was retained rather than migrated/deployed; its current-source features still require the documented migration/private-schema procedure before use there. Disposable PostgreSQL tests passed independently.

No claim of an independent security audit, clinical validation or production readiness is made. Uncertain private/runtime files were kept rather than discarded for a smaller file count.

## Run and restore

The working application remains running at http://127.0.0.1:8000/ . To run later from this project folder:

```powershell
.\.venv\Scripts\python.exe tools\local_mysql.py serve
```

Use `git log --oneline` on `cleanup/safe-2026-10-23` to identify the final cleanup commit. Revert that specific cleanup commit to undo file cleanup while retaining the checkpointed receptionist/assistant work. For a single removed file, inspect or restore it from `0fba6e5`, for example:

```powershell
git show 0fba6e5:care/catalogue.py
git restore --source=0fba6e5 -- care/catalogue.py
```

Save any newer edits before restoring/reverting. Do not use `reset --hard`, database reset commands or destructive blanket restores. Source rollback does not require reversing the additive database migrations: the checkpoint already contains those migrations. Database backup recovery, if ever necessary, is a separate deliberate operator action; cleanup did not restore/overwrite any database.
