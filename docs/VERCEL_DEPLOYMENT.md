# Vercel deployment — prepared, NOT DEPLOYED

Official documentation reviewed on 21 October 2026:

- [Django on Vercel](https://vercel.com/docs/frameworks/full-stack/django)
- [Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Function limits](https://vercel.com/docs/functions/limitations)
- [Private S3 backend configuration](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html)

The connected account returned HTTP 403 when creating mednova-smart-hospital. It has no visible existing project, and there is no authenticated local CLI fallback. There is no deployment URL or successful Vercel build to report.

## Architecture and repository configuration

Retain Django templates, sessions, permissions and ORM on Vercel's Python WSGI function. Use external persistent MySQL with verified TLS and a private S3-compatible bucket for reports. The existing HTTP polling signaling stays in MySQL; WebRTC media is peer/TURN traffic, not a long-lived Django process. No app rewrite, browser storage, fake database or standalone static login deployment is introduced.

The root directory must contain manage.py, requirements.txt, pyproject.toml and vercel.json. If importing the outer downloaded folder, choose MedNova-Python-MySQL as Root Directory; if importing this folder's new Git repository, use its root.

- .python-version selects supported Python 3.14, matching local verification.
- pyproject.toml sets tool.vercel.entrypoint to mednova.wsgi:application.
- vercel.json selects django and configures mednova/wsgi.py with a 60-second duration. There are no legacy builds or catch-all rewrites that could swallow static/public routes.
- Vercel's current Django integration discovers the WSGI app and collects STATIC_ROOT automatically; keep the default build command. Do not run migrations during import/build/request handling.
- Public static files use the staticfiles storage backend, independently of private report storage. WhiteNoise remains useful locally.
- .vercelignore excludes secrets, local databases, uploads, environments, test tools and private keys. Only an explicitly provided public certs/mysql-ca.pem may be bundled as a PEM file.

Vercel-specific settings reject local/test flags, missing remote MySQL settings, loopback database hosts, missing private S3 settings and insecure custom S3 endpoints. Database connections use CONN_MAX_AGE=0 on Vercel, health checks and a 10-second connection timeout. MySQL ssl_mode=VERIFY_IDENTITY verifies CA and host identity. Exact platform VERCEL_URL host/origin is added without accepting wildcard request hosts.

## Environment checklist — names only

Configure values directly in the deployment's environment settings or an approved secret manager. Do not paste secrets into chat or commit .env files. Set Preview and Production independently, using separate databases, buckets and provider test/live accounts.

| Name | Meaning |
|---|---|
| APP_ENV | production |
| DJANGO_SECRET_KEY | Unique random secret of at least 50 characters, stable across instances/releases |
| ALLOWED_HOSTS | Exact approved public hostname(s), including PUBLIC_ORIGIN host; no wildcard |
| PUBLIC_ORIGIN | HTTPS origin without path, used for recovery links |
| CSRF_TRUSTED_ORIGINS | Required approved HTTPS origins; never null or wildcard |
| TRUST_PROXY | 1 for the controlled Vercel HTTPS ingress; do not reuse on an untrusted direct server |
| MYSQL_HOST / MYSQL_PORT / MYSQL_DATABASE | Remote managed MySQL endpoint and persistent database |
| MYSQL_USER / MYSQL_PASSWORD | Restricted application DML credentials; migration account used separately |
| MYSQL_SSL_CA | Bundled/public provider CA certificate path, e.g. certs/mysql-ca.pem |
| PRIVATE_STORAGE_BACKEND | s3 |
| S3_BUCKET_NAME / S3_REGION_NAME | Private bucket and region |
| S3_ENDPOINT_URL | Optional HTTPS endpoint for an approved S3-compatible provider |
| AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY | Scoped private-object credentials; no public ACL permission |
| AWS_SESSION_TOKEN | Optional temporary credential token |
| CRON_SECRET | Random bearer secret used by the maintenance endpoint |
| EMAIL_HOST / EMAIL_PORT / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / DEFAULT_FROM_EMAIL | SMTP with STARTTLS and verified sender |
| TURN_URL / TURN_SECRET | Authenticated coturn-compatible relay for cross-network consultations |
| RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET | Optional gateway; leave all absent until sandbox verification |
| CLAMAV_COMMAND | Existing local scanner option; unavailable on Vercel unless a compatible scanner is explicitly packaged/verified |

Do not set MEDNOVA_TESTING, MEDNOVA_TEST_DB or MEDNOVA_TEST_MYSQL on Vercel. DEBUG stays false. PRIVATE_MEDIA_ROOT is for persistent-volume hosting, not Vercel report persistence. Never upload browser_acceptance.sqlite3 or seed production automatically.

## Private storage and upload limitations

Provision a private bucket with public access blocked, encryption at rest, restricted access to the reports/ prefix, object versioning/retention and verified backup/recovery. This adapter uses a scoped AWS-compatible credential pair; an OIDC-only identity needs a separately verified provider integration. URLs are signed only after application authorization, expire after 60 seconds and are returned with no-store. Do not log signed URLs. Anyone receiving a signed URL can use it until expiry; it is not a substitute for bucket access control.

Vercel's documented request/response payload limit is 4.5 MB. Server form uploads are explicitly capped at 3 MiB on Vercel, leaving multipart overhead; local hosting retains 5 MiB. Images are validated/re-encoded. Signed private downloads avoid proxying large bodies through the function. If the full 5 MiB upload contract is mandatory on Vercel, the additional architecture is direct upload into a private quarantine prefix, server scan/validation and authorized finalization. That direct-upload flow is NOT implemented or claimed verified.

Existing local report files must be migrated with a verified backup, preserved object keys, no overwrites of conflicting existing objects and checksum verification before switching storage. Changing configuration does not copy files. Do not point an existing medical database at an empty bucket.

PDFs continue to fail closed without antivirus scanning. A laptop clamscan path cannot run in the cloud. The smallest cloud adaptation is an independently maintained scanner service over an authenticated protected connection; its provider protocol and adapter must be supplied/verified before enabling PDF acceptance. Never expose an unauthenticated clamd TCP service or send reports to an unapproved scanning provider. No scanner service was provisioned.

## Exact release procedure

1. Have the account/team owner grant project-creation permission to the connected integration, or provide an existing project with deployment access. The observed create-project request was forbidden; repeating it with the same access will not fix it.
2. Create/import mednova-smart-hospital in the intended team, select Django and set the correct root directory above. If using CLI, install a reviewed Vercel CLI version at least 50.38.0, authenticate as the authorized owner, then run `vercel link --scope jayeshnimse3-7880s-projects` from this folder. No token belongs in source or command arguments.
3. Provision external MySQL and private object storage; configure all required Preview values. Supply the provider's public CA certificate. Keep the runtime account DML-only and the migration account scoped to the intended schema. No paid resources were provisioned during this repair.
4. On a trusted migration runner with reviewed source and injected Preview migration credentials, run:

```text
python -m pip install -r requirements.lock.txt
python -m pip check
python manage.py check --deploy --fail-level WARNING
python manage.py migrate --plan
python manage.py migrate --noinput
python manage.py showmigrations --plan
```

Current schema includes additive care0005 (initial password replacement), in addition to0003/0004. Local MySQL8.4.13 application migrations and the preserved-dataset copy passed;115 MySQL tests including four races passed. See FINAL_SYSTEM_REPORT.md for current evidence. Managed production database connectivity/TLS and migration rehearsal on a production clone remain UNVERIFIED. For an existing database, take and verify its backup before applying pending migrations and rehearse on a clone. Do not drop or reset it.
5. Return to restricted runtime credentials and run `python manage.py check_database`. Run `python manage.py ensure_admin --email VERIFIED_ADMIN_EMAIL` interactively on the trusted runner, or inject temporary MEDNOVA_ADMIN_EMAIL/MEDNOVA_ADMIN_PASSWORD and run `python manage.py ensure_admin --noinput`. Never put a password in command arguments. Existing valid administrators are not reset; new administrators must replace the initial password before workspace access. Remove bootstrap secrets after provisioning. See MYSQL_OPERATIONS.md. Enter only verified production hospital/staff details when available; staging uses labelled synthetic data.
6. Deploy Preview with `vercel deploy --scope jayeshnimse3-7880s-projects`. Vercel should install requirements, resolve the WSGI entrypoint and collect static assets. Inspect the actual build logs. mysqlclient includes a native extension; the Vercel Linux build and client-library availability have NOT been verified. If native build dependencies fail, provide a reviewed compatible Linux build artifact/library setup or retain Django/MySQL on a compatible backend host behind Vercel routing. Do not silently replace MySQL or spoof driver compatibility.
7. Verify the real HTTPS preview's /health/ returns 200/status ok, inspect logs without secrets, verify CSS/JS/logo/fonts and private-path rejection, then run the 14-step acceptance workflow in the final report against isolated staging data. Confirm MySQL writes and private object bytes survive a new deployment. Run `python manage.py test care care.mysql_acceptance --noinput` with MEDNOVA_TEST_MYSQL=1 against a dedicated disposable MySQL test database, never production credentials.
8. Verify SMTP delivery/reset tokens, two-device TURN calls and optional Razorpay sandbox capture/webhook/receipt/refund recovery. Offline/mocked tests do not prove real provider behavior. Leave unavailable integrations disabled.
9. Set Production values separately. Take verified database/object backups. Stage the production build without assigning the public domain using `vercel deploy --prod --skip-domain --scope jayeshnimse3-7880s-projects`. Verify that exact build, then promote its URL with `vercel promote DEPLOYMENT_URL --scope jayeshnimse3-7880s-projects`. Do not promote a Preview build and assume its tested configuration is unchanged. Confirm the public /health/, login/CSRF and saved-data workflows after promotion.

## Maintenance, backup and rollback

vercel.json uses a daily UTC cleanup schedule to avoid assuming a paid higher-frequency cron plan. /api/maintenance/cleanup/ requires Authorization: Bearer CRON_SECRET. Active signaling POSTs also remove expired signals for that appointment. HTTP retrieval never returns signals older than two minutes. On an approved plan, change cron to every five minutes and verify actual execution if the retention policy requires it; with the daily default, inactive expired rows can remain until the next daily run. Do not describe daily cleanup as five-minute deletion.

The same daily endpoint now also runs bounded notification outbox processing. Daily scheduling is insufficient for guaranteed timely reminders; use an approved higher-frequency scheduler and verify execution before promising reminders. Email is at-least-once; SMS is unavailable. See PRODUCT_IMPLEMENTATION_REPORT.md.

Monitor function failures/latency, MySQL capacity/deadlocks, storage, cron runs, provider failures and backups. Follow DATABASE_SETUP.md for consistent MySQL/private-object backups and an isolated restore rehearsal; include bucket versioning and object retention. Logs must exclude clinical content, request bodies, credentials and signed URLs.

Retain checkpoint/source releases. Vercel rollback changes application code, not database/object state. Prefer a compatible previous build with retained additive schema. Never blindly reverse migrations or restore over live patient data. A data restore requires explicit approval, a verified backup and reconciliation of writes since backup; validate in a new database/bucket first.

## Current release gates

BLOCKED: Vercel project-creation permission (actual HTTP 403); no managed MySQL or private bucket credentials; no real deployment/build/HTTPS endpoint. UNVERIFIED: Linux native-driver build, managed MySQL TLS/connectivity and production migration rehearsal, private storage operations and restore, SMTP/TURN/payment/scanner integrations, deployed browser acceptance. Local public and authenticated browser workflows now work; the earlier Origin: null browser blocker was fixed in application middleware.

At staging verification, confirm that REMOTE_ADDR is the actual client address used by the platform before relying on the application per-IP counters; otherwise use a verified trusted-ingress mapping and complementary edge client limits. Do not blindly trust client-supplied forwarded headers.
