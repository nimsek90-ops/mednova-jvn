# Current hosting note

Vercel is now the selected target. Use VERCEL_DEPLOYMENT.md for its environment names, verified-identity MySQL TLS and private S3 storage. PRIVATE_MEDIA_ROOT describes the persistent-host alternative; never rely on Vercel temporary files for reports. Real managed MySQL and object-storage connectivity remain UNVERIFIED. The local test database has all 17 migrations applied, and 87 isolated regression tests passed.

# Database setup and recovery

Production uses Django's MySQL backend. SQLite results in TEST_REPORT.md are isolated verification only. No production connection was verified.

Provision a supported MySQL server with InnoDB, utf8mb4, strict SQL mode, encrypted persistent storage, network access restricted to application/backup operators and verified TLS for remote access. Set MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT and MYSQL_SSL_CA using a private secret store or .env. Do not print them. Use separate runtime DML and migration/schema accounts; database/README.md describes local provisioning. Do not run configure.py against a remote host.

Run with the migration account injected into the process environment:

```powershell
python manage.py check_database
python manage.py showmigrations
python manage.py migrate --plan
python manage.py makemigrations --check --dry-run
# After verified backup and successful staging rehearsal:
python manage.py migrate --noinput
python manage.py showmigrations --plan
```

check_database requires existing care tables; on first provisioning run migrate before that command. Apply all auth/contenttypes/sessions/care migrations. 0002 adds slot consultation type (existing slots default to either), optional check-in time, cancellation notice (default zero), and an empty notifications table. It does not fabricate historical notifications. Switch back to runtime credentials after migration. CONN_MAX_AGE=60 recycles persistent connections; size application threads/instances below server connection limits and load test.

Verify /health/ returns HTTP 200 with status ok through HTTPS. It executes SELECT 1 and checks the Hospital table; it does not certify every table or migration. Check migration status separately. Database failures return HTTP 503 with no database details on this endpoint. Normal failed requests have a generic error response.

## Isolated verification

Default `python manage.py test care` creates an isolated in-memory SQLite test DB. For MySQL, explicitly provision a separate disposable database/account with permission to create/drop only its test database. Never use production credentials:

```powershell
$env:APP_ENV='local'
$env:MEDNOVA_TEST_MYSQL='1'
# Set MYSQL_* to your dedicated test service using a secret store.
python manage.py test care care.mysql_acceptance --noinput
```

Django creates test_<MYSQL_DATABASE> and destroys that isolated test database after testing. The two explicit concurrent tests use independent thread connections and fail if executed against SQLite. No concurrency test is silently skipped. MEDNOVA_TESTING, MEDNOVA_TEST_DB and MEDNOVA_TEST_MYSQL must be absent from production. MEDNOVA_TEST_DB is a test-only SQLite filename, used for local HTTP fixtures; it is never a production database choice.

## Backup and restoration

Agree recovery point/time objectives with the hospital. Schedule encrypted backups and access-controlled off-host retention. For InnoDB use the managed provider's consistent snapshot/PITR service or a logical dump during a controlled maintenance window. Keep private uploads consistent with the DB metadata and include deployment/migration version information. Store credentials in a protected MySQL option file, never command-line password flags:

```text
mysqldump --defaults-extra-file=/secure/backup.cnf --single-transaction --routines --triggers --events --result-file=/secure/backup/mednova.sql DATABASE_NAME
```

Do not place dumps under the project/static root. Encrypt and transfer with the approved backup system; verify checksums. Back up PRIVATE_MEDIA_ROOT with restricted filesystem permissions. Enable binary logs/PITR where required.

Rehearse restoration into a new, isolated database and private-media volume. Review the dump's database names and definer clauses before import. On a trusted shell supporting stdin redirection:

```text
mysql --defaults-extra-file=/secure/restore.cnf RESTORE_DATABASE < /secure/backup/mednova.sql
```

Verify migrations, record counts, relationships, private downloads and acceptance journeys against the restored copy. Record backup timestamp, recovery duration and result. A live restore or destructive rollback requires explicit approval and a verified backup; none was performed here.
