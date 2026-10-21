# Production readiness — NOT READY

Local implementation and isolated tests have progressed; this is not a completed deployment or a claim of legal compliance.

Verified locally: 87 Django regression tests, eight real HTTP scenarios against Waitress, static collection, imports, migration consistency, dependency consistency and production security system checks with synthetic host/secret settings. See TEST_REPORT.md for exact limitations. New business workflows are described in FIXES_APPLIED.md.

## Blocking release gates

- UNVERIFIED: production MySQL credentials, connectivity, TLS, schema migration rehearsal, row-lock concurrency/deadlock behavior and connection capacity. No MySQL service/client/container runtime was found locally.
- BLOCKED: Vercel is the selected target. The connected account returned HTTP 403 when creating the project; no projects were visible. Deployment/build/public HTTPS health remain UNVERIFIED.
- VERIFIED locally: the main authenticated browser journeys, including prescription/dispensing and private file upload/download. The application header causing Origin: null was repaired. Full deployed staging browser coverage remains UNVERIFIED.
- UNVERIFIED: SMTP delivery and recovery in a real inbox; TURN calls on two devices/networks; Razorpay sandbox Checkout/capture/refund/webhook recovery; ClamAV operation and definitions. Missing service configuration is visible rather than simulated.
- UNVERIFIED: the implemented private S3 storage adapter against a real bucket, encrypted backups, restore drill, retention, monitoring and incident response. Vercel form uploads are capped at 3 MiB; local uploads retain 5 MiB.
- UNVERIFIED: hospital identity/contacts, actual clinician credentials and staff approval process, consent/legal notices, cancellation/refund policy and professional translations/accessibility review.

## Operational controls and remaining limitations

Consultations retain the established fixed duration of 12 minutes; slots support either/in-person/video. No automatic refund transfer, e-prescription signature, emergency dispatch or automated clinical advice is implemented. Refunds require independently verified external processing before receipt entry. Existing record retention remains a hospital-controlled process; no medical records are automatically deleted.

Notifications persist in the database; booking confirmations are not delivered by email/SMS. SMTP is used for password recovery only. No background email queue is included. Operational reports currently provide appointment/payment counts by status, not financial accounting or clinical analytics.

Application audit records remain in the same database and are not tamper-proof; export to controlled external audit storage if required. Infrastructure operators can access database/files. Role permissions govern application access, not host administrator access. Review least privilege, disk/backups encryption, staff onboarding/offboarding and monitoring before real patient use.

Email is normalized on ordinary saves and registration, with a unique email field. Existing mixed-case legacy rows must be audited for collisions before any bulk normalization; bulk SQL/queryset updates bypass save(). MySQL collation and existing-data behavior need staging verification. Do not auto-merge accounts.

Migration 0002 is additive but MySQL DDL behavior and live-table lock duration are unverified. Rehearse with a backup clone; do not infer MySQL migration safety from SQLite. Production must never set the MEDNOVA_TEST* flags. Deployment documentation lists required settings and exact release/rollback procedures.

Do not publish to real patients until every blocking gate has recorded evidence. No production database or external account was modified during this work.

Current detailed evidence and limitations: REPAIR_AND_VERCEL_REPORT.md. Vercel configuration, required environment names, upload/scanner limitations, deployment and rollback: VERCEL_DEPLOYMENT.md. Production uses private object storage rather than an ephemeral filesystem.
