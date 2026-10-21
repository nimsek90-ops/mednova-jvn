# MySQL and administrator operations — Windows

Local verification: PASS. The running application uses MySQL 8.4.13, schema `mednova_local`, at `127.0.0.1:3307`. It does not use SQLite. The runtime identity `mednova_local_app` has SELECT/INSERT/UPDATE/DELETE on that schema only. Migration/backup privileges belong to a separate operator. Private connection configuration is in the ignored `.runtime/local_mysql.json`; never share it. This loopback development connection has no verified TLS identity and is not a production connection.

## Start the existing local installation

```powershell
Set-Location 'C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Python-MySQL'
.\.venv\Scripts\python.exe tools/local_mysql.py check_database
.\.venv\Scripts\python.exe tools/local_mysql.py showmigrations --plan
.\.venv\Scripts\python.exe tools/local_mysql.py serve
```

Open http://127.0.0.1:8000/. Keep the server terminal open. `serve` starts the already initialized portable MySQL installation if necessary; it never initializes/resets data. Stop only the web server with Ctrl+C. If port 8000 is already occupied, use the existing server or stop its terminal before starting another. This helper is specific to this prepared laptop; new installations use SETUP_WINDOWS.cmd with their own MySQL instance and credentials.

```powershell
.\.venv\Scripts\python.exe tools/local_mysql.py database_inventory --output docs/verification/final-mysql-schema.json
.\.venv\Scripts\python.exe tools/local_mysql.py check
.\.venv\Scripts\python.exe tools/local_mysql.py makemigrations --check --dry-run
```

Run actual migrations through `manage.py migrate --plan`, then `manage.py migrate --noinput`, on a trusted runner configured with the correct schema and a schema-scoped migration identity. The local runtime account intentionally cannot alter tables. Do not change its grants just to run migrations. Back up and rehearse pending migrations on a clone first. Never use `flush`, drop, reset, or a seed command on existing patient data.

## Connect and inspect

In MySQL Workbench create a Standard TCP/IP connection, hostname 127.0.0.1, port 3307, user mednova_local_app, default schema mednova_local. Enter the private password locally through the password prompt/vault. Do not paste it into chat or screenshots. A separate operator account is needed for backup, restoration and migrations.

```powershell
$mysql = Join-Path (Get-Location) '.runtime\mysql-8.4.13-winx64\bin\mysql.exe'
& $mysql --host=127.0.0.1 --port=3307 --user=mednova_local_app --password mednova_local
```

`--password` without a value prompts securely. Never put a password after `=` or in shell history. For managed production MySQL, use the provider hostname and add `--ssl-mode=VERIFY_IDENTITY --ssl-ca=C:\approved\provider-ca.pem`. Verify the provider certificate/hostname; do not copy local loopback assumptions into production.

```sql
SELECT DATABASE(), VERSION(), @@session.transaction_isolation, @@foreign_key_checks;
SHOW SESSION STATUS LIKE 'Ssl_cipher';
SHOW DATABASES; -- only schemas permitted to this identity
USE mednova_local;
SHOW TABLES;
SHOW CREATE TABLE care_appointment;
SHOW COLUMNS FROM care_department;
SHOW INDEX FROM care_appointment;
SELECT id, name, description FROM care_department ORDER BY name LIMIT 25;
SELECT id, name FROM care_department WHERE name LIKE '%cardio%' ORDER BY name LIMIT 25;
SELECT status, COUNT(*) AS appointment_count FROM care_appointment GROUP BY status;
```

Use parameterized ORM queries in application code. Workbench access must be restricted to authorized operators. Do not use `SELECT *` against users, sessions, clinical notes, reports, signals or audit payloads. A database account's access is broader than application role permissions; do not give it to ordinary portal administrators. See MYSQL_SCHEMA_INVENTORY.md for every table/column/index/relationship and the JSON for exact DDL.

## Safe manual changes

Prefer the audited application forms. These SQL rehearsals default to ROLLBACK. Check the database identity first, select the exact record, lock it, use a precise WHERE, and inspect affected rows immediately. Do not edit roles, password hashes, clinical records, payment state, stock balances or appointment state manually: their business rules involve other records and audit events.

```sql
USE mednova_local;
START TRANSACTION;
SELECT id, opening_hours FROM care_hospital WHERE id = 1 FOR UPDATE;
UPDATE care_hospital SET opening_hours = 'Training rehearsal only' WHERE id = 1;
SELECT ROW_COUNT() AS affected_rows; -- must be exactly the intended row count
SELECT id, opening_hours FROM care_hospital WHERE id = 1;
ROLLBACK; -- use COMMIT only after authorized review of the intended real change
```

Insert/delete rehearsal, only in an isolated training schema. It leaves no committed rows. Protected referenced entities must not be deleted; foreign keys stay enabled.

```sql
USE mednova_restore_qa; -- isolated restored training schema, never production
START TRANSACTION;
SET @training_name = CONCAT('SYNTHETIC SQL REHEARSAL ', UUID());
INSERT INTO care_department (name, description, active) VALUES (@training_name, 'Uncommitted operator exercise', 1);
SET @training_id = LAST_INSERT_ID();
SELECT id, name FROM care_department WHERE id = @training_id;
SELECT COUNT(*) AS references_count FROM care_doctorprofile WHERE department_id = @training_id;
DELETE FROM care_department WHERE id = @training_id AND name = @training_name;
SELECT ROW_COUNT() AS deleted_rows; -- one unreferenced training row only
ROLLBACK;
```

An SQL exception or unexpected affected-row count means ROLLBACK and investigate, not retry against a wider WHERE. Manual SQL bypasses application audit; record an approved change ticket and operator evidence. Never disable foreign-key checks to force deletion.

## Backup and isolated restore

PASS: a consistent dump of mednova_local was restored into a separate empty mednova_restore_qa schema; all 31 table counts matched. Evidence: verification/final-backup-restore.json. That snapshot predates later synthetic browser/HTTP writes. This proves a local SQL restore, not production point-in-time recovery or object-storage recovery. Backups contain private data and password hashes: restrict access, encrypt, retain privately and never commit/upload them.

```powershell
$mysqlBin = Join-Path (Get-Location) '.runtime\mysql-8.4.13-winx64\bin'
New-Item -ItemType Directory -Force -Path '.runtime\backups' | Out-Null
$backup = Join-Path (Get-Location) ('.runtime\backups\mednova-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.sql')
$operator = Read-Host 'Authorized local backup operator'
& "$mysqlBin\mysqldump.exe" --host=127.0.0.1 --port=3307 --user=$operator --password --single-transaction --no-tablespaces --skip-add-drop-table --set-gtid-purged=OFF --hex-blob --result-file=$backup mednova_local
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; do not use this file.' }
Get-FileHash -Algorithm SHA256 -LiteralPath $backup
```

`--result-file` avoids PowerShell redirection encoding changes. All current tables are InnoDB; `--single-transaction` is consistent for them, but avoid concurrent DDL during the dump. For production append verified TLS options, use its approved backup identity and provider snapshot/PITR policy. Back up private uploaded files/object versions separately with a DB/object consistency plan.

Restore only to a new empty schema. Do not overwrite a live schema. Choose a new unique schema name and record the verified hash; this example name is not the already-used mednova_restore_qa.

```powershell
& "$mysqlBin\mysql.exe" --host=127.0.0.1 --port=3307 --user=$operator --password
```

Inside the MySQL client (replace the SOURCE path with the exact verified backup path, using forward slashes):

```sql
CREATE DATABASE mednova_restore_review_20261021 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE mednova_restore_review_20261021;
SOURCE C:/approved/private/path/verified-backup.sql;
SHOW TABLES;
SELECT COUNT(*) FROM care_department;
```

CREATE DATABASE must fail if the destination already exists; do not add IF NOT EXISTS and import over it. Check import errors, every table count, migrations, orphan counts and application access against this isolated clone before considering recovery. Reconcile writes since the backup and obtain explicit approval before any live replacement. Restoring code or promoting an older deployment does not undo database writes.

## Initial administrator

BLOCKED for the requested human account: the intended email and target environment have not been supplied unambiguously in the available conversation. No existing patient's email was inferred as an administrator. PASS for the implementation and synthetic login/idempotence/permission/password-change tests.

```powershell
$env:MEDNOVA_ADMIN_EMAIL = Read-Host 'Verified administrator email'
.\.venv\Scripts\python.exe tools/local_mysql.py ensure_admin
Remove-Item Env:MEDNOVA_ADMIN_EMAIL
```

The command prompts twice for a new hidden password, validates it, and creates an active approved custom admin with Django staff/superuser flags. Initial sign-in requires replacement at `/password/` before workspace access. Use a new strong password, not one shared in chat. Repeating the command for an existing valid administrator does not reset its password/flags; an existing patient/staff identity is rejected without promotion. It does not run automatically during build/startup.

For a trusted noninteractive deployment runner, inject MEDNOVA_ADMIN_EMAIL and MEDNOVA_ADMIN_PASSWORD as temporary secrets, then run `python manage.py ensure_admin --noinput`. A local PowerShell equivalent is:

```powershell
$env:MEDNOVA_ADMIN_EMAIL = Read-Host 'Verified administrator email'
$initialSecret = Read-Host 'New initial administrator password' -AsSecureString
try {
    $env:MEDNOVA_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new('', $initialSecret).Password
    .\.venv\Scripts\python.exe tools/local_mysql.py ensure_admin --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Provisioning failed; inspect the non-secret error.' }
} finally {
    Remove-Item Env:MEDNOVA_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:MEDNOVA_ADMIN_EMAIL -ErrorAction SilentlyContinue
    $initialSecret.Dispose()
}
```

For deployment use manage.py directly with the intended production/staging runtime configuration, never the local helper. Complete/verify migrations through the privileged migration runner, switch back to the restricted app identity, run check_database and ensure_admin, then remove bootstrap secrets from the runner/provider environment and redeploy if they were ever attached to a deployment. Keep the stable Django secret and DB credentials in the provider secret store. Verify actual login, initial password replacement, admin features and denied clinical access over the deployed HTTPS origin. See VERCEL_DEPLOYMENT.md for environment names, preview steps and remaining release gates.

Official references: [mysqldump](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html), [loading SQL dumps](https://dev.mysql.com/doc/refman/8.4/en/reloading-sql-format-dumps.html).
