# Initial findings and final resolution - 21 October 2026

The findings below were recorded before implementation. Resolution: the preview now uses actual restricted MySQL mednova_local; targeted admin provisioning/forced replacement and task-first booking/dashboard/data-portal changes are implemented. Current evidence and remaining blockers: [FINAL_SYSTEM_REPORT.md](FINAL_SYSTEM_REPORT.md). The earlier SQLite/ensure_admin findings below are resolved locally; production connectivity and the requested human admin identity remain blocked.

## Initial inspection

Architecture: Django5.2, custom email-based user, MySQL production backend, server-rendered HTML, local CSS/vanillaJS, Argon2, session authentication/CSRF, five explicit roles. Care app contains booking, pharmacy, clinical, payment and operational workflows; product.py adds wellness/notes/queue/timeline. Routes and APIs are recorded in verification/product-route-inventory.json; previous product and redesign reports are historical evidence, not new acceptance results.

FAIL - Current running preview is configured with MEDNOVA_TESTING=1 and browser_acceptance.sqlite3. This is an explicit synthetic test database, not a verified production MySQL connection. Plan: preserve it, clone into a dedicated local MySQL schema, use a restricted runtime account and verify actual runtime metadata. No production database is reachable with supplied credentials.

PASS (inspection) - Core workflows are implemented with ORM validation, explicit permissions, CSRF and transactions. Private clinical records are scoped to patient/assigned doctor. Admin is a custom role plus staff/superuser flags; no Django admin SQL console is mounted.

GAPS - ensure_admin currently stops whenever any administrator exists, so it cannot safely target the intended email; it lacks an environment-based idempotent setup path and forced initial password change. Administrator identity/environment is awaiting user clarification; no email inferred from browser autofill.

UX GAPS - Introductory dashboard banner dominates real tasks; booking slots are not grouped into a clear date/visit flow; doctor profiles and directory repeat information; no central permitted-data management entry. Implement substantive task-first layouts and safe operational navigation, retaining underlying business services.

BLOCKED - Managed MySQL/TLS, private storage, SMTP/TURN/payment sandbox/scanner configuration and Vercel project authorization. Prior connected Vercel create request returned403. No deployment URL or production-readiness claim.

Next: secure targeted admin provisioning and change gate; schema inventory/integrity tooling and curated admin data portal; task-first dashboard/booking/profile changes; preserved local MySQL clone; execute current automated, real MySQL concurrency, HTTP and browser checks; document PASS/FAIL/BLOCKED/NOT TESTED results and safe DB operations.
