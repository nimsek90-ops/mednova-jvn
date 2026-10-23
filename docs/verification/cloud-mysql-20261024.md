# Cloud MySQL migration verification — 24 October 2026

- Destination: existing Aiven free MySQL service `mysql-36cb1a3`, dedicated new database `mednova`.
- Verified provider certificate and hostname with MySQL `VERIFY_IDENTITY`.
- Checked destination had no application tables before import.
- Created a fresh private local SQL backup under ignored `.runtime/backups/`.
- Copied 53 tables. Compared exact row counts for every table: zero mismatches.
- Django `migrate --plan` against the cloud database: no planned operations.
- Read-only Django application requests using the cloud database: `/health/`, `/`, `/login/`, `/doctors/`, `/contact/` each returned HTTP 200.
- These application checks ran locally against Aiven; they do not establish public Render or Vercel deployment health.
- Local source database was not modified. Credentials and data exports are excluded from Git.
- Added the public provider CA certificate to the deployment image and configured Render database variables privately.

Detailed row counts and credentials are deliberately excluded from this public-source verification note. Private migration evidence remains in `.runtime/aiven-copy-verification.json`.

- Added a dedicated runtime database user restricted to SELECT/INSERT/UPDATE/DELETE on the MedNova schema; verified TLS connectivity and table visibility. Administrator credentials are retained only in ignored local operator configuration.
- Retested the Render startup entry point locally with the restricted cloud database user: health and homepage HTTP 200; eight sampled static assets HTTP 200.
