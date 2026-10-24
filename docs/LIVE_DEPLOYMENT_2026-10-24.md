# MedNova live deployment — 24 October 2026

Frontend: https://mednova-jvn-vercel-snowy.vercel.app/

Backend: https://mednova-jvn-backend.onrender.com/

Health: https://mednova-jvn-backend.onrender.com/health/

Source: https://github.com/nimsek90-ops/mednova-jvn — branch `cleanup/safe-2026-10-23`.

## Completed and verified

- Copied the local MySQL database into Aiven's existing free MySQL service over verified TLS. All 53 tables had matching row counts immediately after transfer. Source database unchanged; backups remain private.
- No pending migrations. Restricted database runtime account has SELECT/INSERT/UPDATE/DELETE on only the application database.
- Render Docker build and deployment completed. Provider reports live; public browser health endpoint returns `{"status":"ok"}`.
- Vercel Hobby deployment uses root `deployment/vercel`, Other framework and `MEDNOVA_BACKEND_ORIGIN`. Render's exact allowed hostnames, public origin and CSRF origins include the assigned frontend URL.
- Browser verified homepage, navigation, login form, synthetic patient login, correct patient dashboard, denial of patient access to `/admin/users/`, and logout through Vercel. New synthetic test identity disabled after verification.
- At a 390px mobile viewport the homepage displayed correctly and its Menu expanded. Eight sampled static assets passed HTTP 200 checks in the local production entry-point smoke test against the restricted cloud database account. Public screenshot confirms styled rendering; no captured frontend console errors.
- Fixed static collection ordering: initialize Django, collect assets, then initialize WSGI/WhiteNoise.

## Limits and remaining work

- Payment proof uploads to the configured cloud storage, delivery of email, TURN connectivity and full video calls have not been tested live. Do not treat previous local tests as live-provider verification.
- Historical private files have not been copied into cloud object storage. Existing database file references may require that separate transfer.
- All five roles and complete booking/payment/review workflows have not been retested live. The earlier 225 automated backend tests remain local-suite evidence.
- Imported data includes existing synthetic/demo doctors visible in the directory. Review demo content before a real hospital launch; no pre-existing user records were overwritten or deleted.
- Direct Python HTTP requests from this host to the Render domain timed out; the browser successfully accessed Render health and the Vercel site. Browser checks are the live-access evidence.
- The connected Vercel connector belongs to another account scope and returned 403; the user signed into the intended `jayesh-v-nimse` Hobby account, and deployment was completed through its browser dashboard.
- No domain purchased, no paid plan selected, no Supabase/database-engine conversion performed. `.jvn` is not a delegated public TLD; use the assigned Vercel domain.

Status: public demo is live; full hospital production readiness remains conditional on the outstanding provider/file/workflow checks.

Deployment readiness: **80/100**. Local backend regression/startup 20/20; deployment configuration and builds 20/20; source/account readiness 15/15; production database/storage/integrations 15/25; live end-to-end verification 10/20. Untested upload/email/video integrations and incomplete live role workflows receive no full credit. This is separate from the earlier local website audit score.

Environment names configured this session (values omitted): `APP_ENV`, `DATABASE_VENDOR`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_SSL_CA`, `PUBLIC_ORIGIN`, `CSRF_TRUSTED_ORIGINS`, `ALLOWED_HOSTS`, `MEDNOVA_BACKEND_ORIGIN`. Existing secret-key and storage settings were preserved.
