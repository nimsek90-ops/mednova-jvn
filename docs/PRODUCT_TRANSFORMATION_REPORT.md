# MedNova product transformation — 22 October 2026

**Local implementation and PostgreSQL rehearsal passed. Hosted release remains BLOCKED.** The primary app at http://127.0.0.1:8000/ still uses the preserved MySQL mednova_local database. A separate local PostgreSQL rehearsal at http://127.0.0.1:8002/ uses mednova_pg_rehearsal/private mednova schema and restricted backend credentials. Neither is a Supabase deployment or public production URL.

## Delivery and acceptance status

| Requested proof | Status | Actual result / remaining work |
|---|---|---|
| Figma design system | PASS for editable foundations | [MedNova Product System](https://www.figma.com/design/3VZ4B2Z0G66KCRFAaGseNB):44 variables,5 text styles,24 component families,64 editable desktop/mobile screen studies and2 implementation-faithful directory variants. No complete-UI bitmap substitutes. |
| Complete high-fidelity Figma redesign/sign-off | NOT TESTED / incomplete | The directory is aligned to implemented code. Other64 screen variants are editable workflow studies, not a claim of fully approved, pixel-matched production designs. Further per-screen refinement/sign-off is required. |
| Desktop/mobile screenshots | PASS | Saved actual public-directory render references at1280px and390px, plus Figma component/study previews. Links below distinguish implementation screenshots from design specimens. |
| Actual repository changes | PASS | New directory comparison layout, database explorer, PostgreSQL configuration/security tools, preserved Django auth/services and tested cross-database workflows. No static replacement application. |
| Final architecture decision | PASS as a proposed target / BLOCKED hosted | Retain Django/templates/auth/business services; explicit PostgreSQL adapter for Supabase; Vercel WSGI; private persistent reports. Architecture/operations are documented in SUPABASE_MIGRATION_AND_OPERATIONS.md. |
| Actual Supabase project/schema | BLOCKED | Connected list_projects returned zero projects. Organization/region/intended project and actual cost confirmation remain unanswered. No hosted schema or bucket was created. |
| Supabase RLS/advisors | BLOCKED | Hosted security/performance advisors, JWT identities and Data API/storage tests cannot run without a target. Local private-schema/backend-only RLS and simulated API-role denial passed; these are not hosted advisor results. |
| Safe migration/data integrity | PASS locally / BLOCKED production | All20 migrations applied to PostgreSQL18.6;596 exported objects matched exactly across IDs, fields, relationships and password hashes; original MySQL retained.31-table PostgreSQL backup/restore passed. No live cutover. |
| Human administrator | BLOCKED | Intended email and local/staging destination are not unambiguous in available messages. No identity inferred from connected-tool email or patient data. Secure idempotent provisioning/forced password replacement passed in synthetic tests on all backends. |
| All five roles and backend | PASS in local test scope |116 regression tests on SQLite;120 on MySQL;120 on PostgreSQL. Each SQL backend includes four actual transaction races.354 route/role GET probes per backend, plus explicit write/ownership/security tests. |
| Actual HTTP flows | PASS locally | Eight PostgreSQL HTTP scenarios through the restricted RLS-enabled runtime; MySQL HTTP scenarios rerun for current source. Registration, login, saved profile, slot publishing, booking, confirmation/cancellation, duplicate rejection, role boundaries and CSRF. |
| Responsive/browser checks | PASS in recorded scope |207 page/width checks across anonymous and five roles at320/375/390/430/768/1024/1280/1440/1600px; no document overflow/missing h1. Directory filtering and schema search/detail verified. No browser JS errors reported. |
| Security/accessibility/performance | PASS for executed checks / NOT TESTED comprehensively | Private schema/RLS/grants, role/object authorization, existing CSRF/upload/payment/outbox tests, labels/focus and reduced-motion CSS. No independent penetration test, WCAG certification, Lighthouse/load benchmark or real-device certification. |
| Vercel preview/production/live URL | BLOCKED | Connected project list empty; previous creation403 remains unresolved. No project target, managed-service credentials, real Linux build or HTTPS preview acceptance. No production deployment or live URL claimed. |

The full acceptance criteria are not yet satisfied. In particular, hosted services/deployment and complete per-screen design approval remain outstanding. This report does not label the application production-ready.

## Design and implementation

The new doctor directory replaces the repeated tall-card grid with comparison rows: identity/department/qualifications, professional details, fee, next actual published slot and booking action. Search/department/availability filters retain their request contracts. Next availability is an ORM aggregate over active, unbooked future slots within the same90-day booking window; empty availability is explicitly shown. Counts come from the paginator, not fabricated metrics. Mobile rows stack into readable sections with full-width actions.

The new admin database explorer discovers the actual permitted application tables from the connected database and displays searchable metadata, exact SQL column types, nullability, primary/unique/foreign keys and indexes. It uses metadata-only catalog/PRAGMA queries and does not sample record bodies or permit SQL execution. Final review found Django's generic get_table_description() samples SELECT * LIMIT1; this helper and the MySQL constraint helper that delegates to it were replaced with catalog-only queries. Regression guards reject sampling helpers in both the explorer and schema export. SQLite constraint introspection uses metadata-only PRAGMA and remains allowed. Existing entity forms remain responsible for validated create/edit/stock/status operations and audit events; protected records are retained/deactivated rather than hard-deleted. The complete feature map now contains59 routes: [TRANSFORMATION_FEATURE_MAP.md](TRANSFORMATION_FEATURE_MAP.md), [source/table/permission JSON](verification/transformation-feature-inventory.json).

Django remains the only user/session/role system. PostgreSQL is selected only with DATABASE_VENDOR=postgresql; MySQL remains default. The adapter validates schema identifiers, requires verified TLS in production, disables persistent connections/prepared statements/server cursors, and bounds connection/statement times. Supabase is not treated as a drop-in MySQL server, nor are Django hashes reinterpreted as Supabase Auth identities. The S3 adapter now uses path-style addressing for custom endpoints; real Supabase Storage is still unverified.

Main source changes: mednova/database.py, settings.py, hosting.py; care/schema.py (catalog-only metadata), care/product.py, views.py, urls, schema/directory templates, shared base and product.css; secure_postgres/database_inventory commands; PostgreSQL concurrency and transformation tests; guarded local HTTP/rehearsal helpers; requirements/environment/deployment exclusions. Existing migrations0001–0005 remain the authoritative portable model schema. No destructive source-database migration was introduced.

## Figma deliverables and limits

The connected Figma picker exposed no suitable MedNova file, so a dedicated file was created in the sole available plan. Code Connect discovery found no mappings. Available SDS assets were inspected; MedNova-owned tokens/components were built to retain the code's brand, sizing and state contract. The file contains:

-01 Foundations: semantic aliases, explicit variable scopes, CSS var syntax, Inter typography, state variants and component examples.
-02 Product screens:32 workflow studies in1440px desktop and390px mobile variants, including all five dashboards, auth, profile/wellness, directory/booking, clinical/history/reports, queue, pharmacy, data/settings/staff, payments/video/notifications/contact.
-03 Implemented directory: editable1280px and390px directory component variants with native text, vectors, Auto Layout/grid hierarchy and discrete logo imagery. These match the implemented public-page layout; they are not flattened page images.

Library inventory covers primary/secondary buttons, fields, badges, alerts, dropdowns, tabs, tooltip, dialog, sidebar/header/mobile navigation/breadcrumbs, dashboard card, chart, table/filter/pagination/empty state, calendar/doctor profile/timeline/notification and directory. Structural verification found no large flattened UI image fills. Temporary reference captures and failed composition nodes were removed by exact agent-owned IDs. Layout sizing/reflow defects were corrected after screenshots exposed them. Final IDs/variables/components/screen bounds are recorded in docs/design/figma-final-verification.json and figma-state.json; older construction IDs are historical.

Screenshots:

- [Implemented directory — desktop1280](design/screenshots/doctor-directory-desktop-app.png)
- [Implemented directory — mobile390](design/screenshots/doctor-directory-mobile-app.png)
- [Editable directory design — desktop](design/screenshots/directory-desktop-figma.png)
- [Editable directory design — mobile](design/screenshots/directory-mobile-figma.png)
- [Button states](design/screenshots/button-states.png), [booking study](design/screenshots/booking-mobile-figma.png), [dashboard study](design/screenshots/dashboard-desktop-figma.png)

Implementation screenshots were exported from Figma's capture of a public-only local render reference, using real template output/CSS/assets. No authenticated/private patient page was uploaded to Figma and application CSP/authentication were not disabled. These are layout render evidence, not proof that Figma examples are live application records. The reference server is temporary and has no backend/write functionality; the actual app remains the Django repository on8000/8002.

## Database and privacy evidence

Actual current primary: MySQL8.4.13, mednova_local,31 InnoDB tables, restricted mednova_local_app. Actual compatibility target: local PostgreSQL18.6, mednova_pg_rehearsal/private mednova,31 tables. Exact source→target types, columns, keys, relationships and snapshot counts: [POSTGRES_SCHEMA_INVENTORY.md](POSTGRES_SCHEMA_INVENTORY.md); [actual metadata JSON](verification/postgres-rehearsal-schema.json). The earlier MySQL inventory remains available in MYSQL_SCHEMA_INVENTORY.md.

The local rehearsal preserved all596 exported objects, including Django password hashes and relationships, without changing source MySQL. Exports/backups and credentials stay in ignored .runtime. The existing dataset is not asserted to contain only synthetic profiles; it was not sent to Supabase or external staging. Browser/HTTP mutations use synthetic accounts. Supabase staging must use fresh synthetic data until privacy, storage and deployment checks pass.

All31 private PostgreSQL tables have enabled+forced RLS. The mednova_pg_runtime policy permits only the server role; Django applies user-level permissions. Simulated anon/authenticated/service_role access to the private schema was denied. With temporary read grants in a rolled-back isolated restore transaction, anon/authenticated returned no rows under RLS; the simulated service_role had BYPASSRLS and bypassed RLS as expected. Its protection is revoked grants and secret custody, not RLS. The policy does not protect individual patients from someone holding the backend password; this is backend-only architecture, not an invented auth.uid() mapping. No Supabase browser client or public table grants are configured. Hosted API-role/JWT/storage-policy tests and advisors remain BLOCKED.

Evidence: [copy comparison](verification/postgres-migration-rehearsal.json), [RLS rehearsal](verification/postgres-rls-rehearsal.json), [backup/restore](verification/postgres-backup-restore.json), [binary provenance](verification/postgres-binary-provenance.json). The PostgreSQL backup restored to a new empty database with matching31-table counts. The initialized cluster was also stopped/restarted through the local helper; all31 table counts and the restricted-runtime health check survived (postgres-restart-persistence.json). A fresh current MySQL backup is preserved privately (transformation-source-backup.json). This does not prove managed Supabase PITR, S3 object recovery or cloud TLS. Loopback rehearsal connections intentionally have no verified production TLS identity.

## Current executed checks

| Command / method | Result | Evidence |
|---|---|---|
| manage.py test care --noinput --verbosity1; isolated SQLite | PASS116 | transformation-sqlite-tests.txt |
| Same regression suite + MySQLBookingAcceptance; dedicated MySQL test DB | PASS120 | transformation-mysql-tests.txt |
| Same regression suite + PostgreSQLBookingAcceptance; dedicated PostgreSQL test DB | PASS120 | transformation-postgres-tests.txt |
| Four SQL transaction races | PASS on MySQL and PostgreSQL | Same-slot booking, cancellation/reschedule, single dispensing deduction, unique daily queue tokens |
| Route/role matrices | PASS354 GET probes per backend | transformation-*-role-matrix.json; GET coverage alone is not write-workflow coverage |
| Actual PostgreSQL HTTP against non-owner runtime/RLS | PASS8 scenarios | transformation-postgres-http.txt |
| Real browser directory/schema interactions and207 responsive checks | PASS within scope | transformation-browser-summary.json |
| Public assets, private-path denial, checks/migrations/static/dependencies/JS syntax | Recorded in final local-check ledger | transformation-local-checks.json and related HTTP evidence |

These counts overlap:116 is the regression suite,120 adds four SQL race tests. They are not356 unique tests. Expected CSRF/access/storage-failure warning logs exercise denied/error paths. No provider success is inferred from a mocked test.

Keyboard/menu behavior, visible focus and labels were reviewed in the browser; reduced-motion rules are implemented. Five selected text/background palette pairs passed4.5:1 contrast (4.55–11.55);27 public/static/font/private-path HTTP checks passed. Numeric palette checks and public HTTP timing observations are bounded local checks, not a full accessibility/performance audit. Some new explanatory copy remains English; full professional Marathi/Hindi review is NOT TESTED. External SMTP/SMS, two-device TURN, gateway settlement, cloud scanner, private Supabase Storage and production monitoring remain BLOCKED/NOT TESTED as applicable.

## Run, provision, inspect, migrate and release

Primary existing local app:

```powershell
Set-Location 'C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Python-MySQL'
.\.venv\Scripts\python.exe tools/local_mysql.py serve
```

The existing server is left running; do not start a second copy on8000. The already prepared PostgreSQL rehearsal can run separately with `tools/local_postgres.py serve` on8002 while its loopback database is running. These helpers use private local configuration and never initialize/reset a database. See [Supabase migration/operations](SUPABASE_MIGRATION_AND_OPERATIONS.md) for architecture, verified migration scope, environment names, RLS, Dashboard/Table Editor/SQL Editor guidance, reviewed SELECT/UPDATE/INSERT/DELETE examples, backup/restore and rollback. MySQL setup/backup/admin instructions remain in MYSQL_OPERATIONS.md.

The intended administrator email/environment is still needed. Once supplied, use the supported hidden-password command or temporary secure runner environment; no password belongs in chat, source or process arguments. Existing valid administrators are not reset, conflicting accounts are not promoted, and new administrators must replace their bootstrap password before workspace access.

To continue hosted work: identify the intended Supabase organization/project/region and confirm actual project cost; provide/authorize the intended Vercel team/project and resolve project-creation access; configure separate staging DB/storage credentials privately. Apply/review migrations and private-schema RLS on that selected synthetic staging target, run security/performance advisors, verify CA/pooler/native Linux build, test real HTTPS/assets/login/CSRF/five roles/core writes and private file survival after redeploy, then verify required providers/monitoring/recovery. Only afterward consider a controlled production migration and staged promotion. No paid service, new production database or production release was created during this work.
