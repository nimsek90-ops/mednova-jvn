# MedNova deployment handoff — 24 October 2026

Status: prepared locally; public deployment blocked. No public frontend/backend URL exists from this run, no branch was pushed, and no cloud resources or paid changes were created.

## Architecture

The existing application is Django with server-rendered templates and MySQL, not a separate JavaScript SPA. Vercel routes all browser requests to Render, preserving a single browser origin for pages, forms, cookies and APIs. Render serves Django and static assets. Private uploads require external S3-compatible storage. MySQL is preserved; Supabase migration is unnecessary and has not been attempted.

The Git branch is `cleanup/safe-2026-10-23`. This checkout has no remote. GitHub is connected as `nimsek90-ops` but exposes no repositories; the connector cannot create one, and the browser is signed out. Vercel is connected to team `jayeshnimse3-7880s-projects`; there is no matching project or owned domain. Render's plugin is installed, but no service-management tools, authenticated CLI or API key are available.

## Required setup in order

1. In GitHub, create an empty private repository named `mednova.jvn` and grant the GitHub integration access. Supply its repository URL. After reviewing the deployment diff, add that actual URL as the Git remote and push this branch. Do not upload `.runtime`, `.env`, private uploads, database backups or patient exports.
2. Connect the Render account through its integration or sign in to the Render Dashboard. Choose **New > Blueprint**, select the repository and this branch, and use root `render.yaml`. Review the free web service selection before creating it. Do not accept paid resources without approval. The Dockerfile is `Dockerfile.render`; it starts `python deployment/render/start.py`, binds `0.0.0.0:$PORT`, and checks `/health/`.
3. Supply a reachable production MySQL database with TLS and the existing schema/data preserved. The current database is local-only at loopback; Render cannot connect to it. Use a private, verified backup/restore into the selected MySQL host, compare schema and row counts, and inspect `python manage.py migrate --plan` before applying required migrations once. Do not expose the local MySQL port publicly. Startup deliberately does not run migrations.
4. Set Render environment values privately. Required names: `APP_ENV`, `DATABASE_VENDOR`, `DJANGO_SECRET_KEY` (at least 50 random characters), `ALLOWED_HOSTS`, `PUBLIC_ORIGIN`, `CSRF_TRUSTED_ORIGINS`, `TRUST_PROXY`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_SSL_CA`, `PRIVATE_STORAGE_BACKEND`, `S3_BUCKET_NAME`, `S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`. `MYSQL_SSL_CA` is a readable container path to the provider's public CA certificate; add the correct CA to `certs/` if necessary. Set `S3_ENDPOINT_URL` only for a provider requiring a custom endpoint; leave it blank for AWS. Initially use the actual Render HTTPS origin for `PUBLIC_ORIGIN` and its hostname in `ALLOWED_HOSTS`.
5. Configure existing email variables `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`, plus `TURN_URL` and `TURN_SECRET` for reliable video networking. Use the existing hospital recipient configuration from `.env.example`. Confirm that the chosen hosting plan permits the email provider's connection method. No email credentials, recipient address or TURN service were invented.
6. Deploy Render first. Confirm `/health/`, database access, logs and private upload storage before deploying Vercel. A successful health response alone does not prove all dependencies work.
7. In Vercel choose **Add New > Project**, import the repository, select this branch, set **Root Directory** to `deployment/vercel`, **Framework** to Other and **Build Command** to `npm run build`. The build generates the Build Output API directory `.vercel/output`; do not set a SPA output directory. Set `MEDNOVA_BACKEND_ORIGIN` to the actual healthy HTTPS `*.onrender.com` origin. The repository-root legacy `vercel.json` is not the configuration for this split deployment.
8. After Vercel assigns its real URL, update Render `PUBLIC_ORIGIN` and `CSRF_TRUSTED_ORIGINS` to that exact HTTPS origin; allow both real Render and Vercel hostnames in `ALLOWED_HOSTS`. Redeploy/restart as required. Do not use wildcard CORS or localhost production URLs.
9. Verify through the Vercel URL using synthetic accounts: login/logout and CSRF, each role's access, booking/cancellation, payment upload and staff verification, locked/unlocked video access, reviews including rating-only submission and edit, private downloads, email delivery and mobile navigation. Verify persistence after a redeploy. Never make real payments or contact patients during tests.

## Evidence and limits

| Check | Result |
| --- | --- |
| Existing backend automated suite on isolated MySQL | 225 passed |
| New Render startup entry point, port 10001, isolated database | HTTP 200, health status ok |
| Vercel build unit tests | 2 passed |
| Vercel routing production artifact generation | Passed with synthetic Render origin only |
| Render Blueprint against current official JSON schema | Valid; not platform-aware CLI validation |
| Linux Docker image build | Not tested: Docker is unavailable locally |
| Public Render/Vercel integration and browser workflows | Blocked: repository/account/database prerequisites |
| Cloud database, S3 persistence, SMTP and TURN | Not tested: production services/configuration unavailable |

Evidence files are under `docs/verification/deployment-20261024-*`. No synthetic routing target is a live deployment. Environment variable names exist in templates; their production values have not been configured remotely.

Deployment readiness score: **40/100**. Evidence-based checklist: local backend regression/startup 20/20; deployment configuration/build preparation 15/20 (container build unavailable); source/account readiness 5/15 (GitHub/Vercel connected, repository and Render access missing); production database/storage/integrations 0/25; live end-to-end verification 0/20. This is deployment readiness, separate from the earlier 81/100 local website audit.

## Domain

`mednova.jvn` can remain the product name, but `.jvn` is absent from the current IANA root zone, so it cannot presently be used as a public registered domain. Use the assigned Vercel URL first. Consider `.com` or `.in`; individual name availability has not been checked and no purchase was made. There are no owned Vercel domains to configure, so no DNS records can yet be supplied.

References: [IANA root-zone TLD list](https://data.iana.org/TLD/tlds-alpha-by-domain.txt), [Render Blueprint specification](https://render.com/docs/blueprint-spec), [Render Docker deployment](https://render.com/docs/docker).
