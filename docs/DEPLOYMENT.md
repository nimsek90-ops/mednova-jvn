# Production deployment — NOT DEPLOYED

No hosting account, approved domain or production MySQL connection was supplied. Local Waitress startup is verified; external deployment and TLS are UNVERIFIED.

## Architecture

Use a persistent Python WSGI service/VM behind an HTTPS reverse proxy, private persistent MySQL, and an encrypted persistent private-media volume. WhiteNoise serves collected public static files. No Node frontend host or Vercel deployment is configured. Schedule cleanup_transient every five minutes. No background worker is currently required.

Use a dedicated non-root OS account and fresh virtual environment. This run used Windows/Python 3.14; Linux packaging and the launcher's Python 3.12 require target verification. Linux may require MySQL client development libraries if binary wheels are unavailable.

## Environment

Transfer placeholder names from .env.example to the platform secret manager. Do not deploy local values unchanged:

- APP_ENV=production; DEBUG is hardcoded false.
- DJANGO_SECRET_KEY: unique random value of at least 50 characters, stable across instances.
- ALLOWED_HOSTS: exact approved hostnames; no wildcard.
- PUBLIC_ORIGIN: exact HTTPS origin without path, used in recovery links.
- CSRF_TRUSTED_ORIGINS: only necessary approved HTTPS origins; never null or wildcard.
- MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT: persistent private database and restricted runtime DML account.
- MYSQL_SSL_CA: trusted CA file for verified remote MySQL TLS.
- PRIVATE_MEDIA_ROOT: absolute encrypted persistent private volume path.
- EMAIL_HOST, EMAIL_PORT (default 587), EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL: verified SMTP sender with STARTTLS.
- TURN_URL, TURN_SECRET: authenticated coturn-compatible relay for production calls.
- RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET: optional online payments, all three required when enabled; sandbox first.
- CLAMAV_COMMAND: absolute clamscan executable for PDF uploads.
- TRUST_PROXY=1 only behind a controlled proxy that strips untrusted forwarded headers.

MEDNOVA_TESTING, MEDNOVA_TEST_DB and MEDNOVA_TEST_MYSQL must be unset. Never copy browser_acceptance.sqlite3, synthetic fixtures or laptop secrets into production. Never print environment values.

## Release commands and procedure

1. Provision MySQL runtime/migration accounts, TLS, media volume and encrypted backups. Follow DATABASE_SETUP.md and record a successful restore drill. Rehearse migration 0002 on a restored staging clone.
2. Deploy source excluding .env, .venv, test databases, backups, .git and private uploads. In a fresh virtual environment run:

```text
python -m pip install -r requirements.lock.txt
python -m pip check
python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
```

3. Run isolated regression and explicit MySQL concurrency suites on staging. Do not run tests using production credentials. During an agreed release window take a verified DB/media backup, inject migration-account credentials into the one-off migration process and run:

```text
python manage.py migrate --plan
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py showmigrations --plan
```

4. Restore restricted runtime DML credentials and run `python manage.py check_database`. Create the first administrator interactively using `python manage.py ensure_admin`; it invokes createsuperuser with password policy and no default password. Do not put passwords in command arguments or logs. Enter verified hospital details, departments and staff approvals through the application.
5. Start with the platform supervisor:

```text
waitress-serve --listen=127.0.0.1:8000 --threads=8 mednova.wsgi:application
```

For a platform requiring all-interface binding, bind only inside its private container/network and restrict ingress to the proxy. Configure graceful shutdown/restarts. Do not use launch.py or runserver in production. Size instances/threads against MySQL connection capacity.
6. Configure TLS, HTTP-to-HTTPS redirect, approved Host forwarding, upload limits (at most 6 MB), connection limits and edge login throttling. Enable TRUST_PROXY only after checking forwarded-header stripping. Never expose the project root, .env, .git, dumps or private uploads. Static access is limited to STATIC_ROOT; clinical files use authenticated Django downloads.
7. From outside the deployment request `https://APPROVED_HOST/health/` and require HTTP 200/status ok. Verify TLS, security headers, redirects, static assets, error pages and blocked private paths. Check migration status separately; health checks DB/schema access, not every migration. Run launch_check after setting hospital identity, SMTP and TURN; configuration checks do not verify real delivery or calls.
8. Execute browser workflows A–L in TEST_REPORT.md using synthetic staging users and desktop/mobile sizes. Verify data after restart and a rolling deployment. No production seeding is automatic.
9. Verify real SMTP reset delivery/token expiry, TURN on two devices/networks, optional Razorpay sandbox capture/signed webhooks/duplicates/refunds and ClamAV/private downloads. Promote only after recorded successful results. See INTEGRATIONS.md.

## Operations

Monitor HTTPS health, latency/errors, MySQL connections/deadlocks, storage capacity, backup age/restore results, SMTP failures and payment reconciliation. Logs must exclude credentials, request bodies, patient notes, report contents and reset links. Application audit records are not external tamper-proof audit storage. Keep dependencies/antivirus definitions updated. Establish hospital-approved retention, incident response and staff access review.

Schedule `python manage.py cleanup_transient` every five minutes. It removes expired signals, rate buckets and sessions, not medical records. Agree backup recovery point/time objectives and test restoration with private-media consistency.

## Rollback

Retain prior source/dependency artifacts and migration versions. Enter a controlled maintenance window if consistency is uncertain. For this additive migration prefer the previous application release with retained added schema after a compatibility rehearsal. Do not blindly reverse migrations: dropping Notification destroys records. Database/media restoration requires explicit approval, verified backup and a plan for writes since backup. Restore to a new isolated database/volume, verify privately and then switch configuration under supervision.

## Troubleshooting

- Startup configuration rejection: check secret length, exact hosts and APP_ENV without printing values.
- Health 503: check private connectivity, CA/TLS, account permissions and migration status; keep raw DB errors private.
- Redirect loop: verify TLS termination and controlled proxy headers before enabling TRUST_PROXY.
- Form 403: verify cookies and same-origin HTTPS requests. The connected in-app browser sent Origin: null during this audit; use a normal browser and retain CSRF protections.
- Missing static assets: collectstatic in the release artifact and verify STATIC_ROOT/proxy rules.
- Missing reports: check private-volume mount, permissions and backup consistency; never make reports public.
- Provider failure: follow INTEGRATIONS.md and keep unavailable services visibly disabled until verified.
