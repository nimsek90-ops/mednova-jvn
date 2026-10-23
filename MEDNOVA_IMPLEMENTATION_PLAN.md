# MedNova existing-project upgrade — 23 October 2026

## Audit and reuse

Django5.2 templates/Waitress/Python; custom email User with five server-authorized roles; MySQL8.4.13 mednova_local remains primary. PostgreSQL is an isolated compatibility rehearsal. Git was clean at inspection (002920c). All care models/forms/services/views, URLs, templates/static assets, migrations0001–0005, role tests, startup/configuration and existing reports were inventoried. No new application or auth system will replace them.

Existing: role links/admin provisioning fixed previously; real booking/payment records, locks for patient/doctor/stock, versioned clinical notes, permission-scoped reports/timeline, queue counters, inventory movements, privacy-safe admin metadata, outbox/reminder integration, WebRTC signaling, disabled-by-default payment/TURN/SMTP integrations. Baseline MySQL suite runs before changes.

Gaps: availability uses fixed12minute slots and no recurring/leave rules; no persistent MRN/registration card or bed requests; pharmacy has whole-prescription-only dispensing and no quarantine/supplier receipts; no patient assistant; video has signaling but no admission/consent/device picker and actual two-device media is unverified. Existing data must not be overwritten to fill these gaps.

## Sequence

1. Preserve baseline evidence; take private logical MySQL backup and schema/count snapshot.
2. Add portable, additive models/fields for recurring sessions, blocks, slot duration/buffer, registration details, beds/admissions, pharmacy safety/partial issues/purchase receipts, drafts/investigations/approved FAQs and video admission.
3. Integrate shared service validation/locks and existing booking/dispensing, reusable forms/pages/navigation and role task overview.
4. Add patient service assistant using deterministic approved information and real scoped queries; explicit confirmation remains required for writes. AI is optional/unconfigured; no model credentials required for core assistant.
5. Add video waiting-room/consent/device/retry controls around existing authenticated WebRTC. Real media tests require available browser devices/permissions; do not equate signaling tests with media success.
6. Validate migrations on test DBs, apply via private migration operator after backup, retain DML-only runtime, rerun full suites/concurrency/HTTP/browser responsive checks, source packaging and report.

## Risks and boundaries

Clinical/pharmacy rules are workflow validation, not independently validated drug-interaction data or regulatory certification. Reception/admin see operations, not clinical notes. Existing finalized notes remain immutable versions. No public SQL, plaintext password logging, fake payment, guessed wait time or invented alerts. New MRNs are identifiers for existing user records, never duplicate patient identities or automatic merges. Migrations add fields/tables and preserve original records. Existing12minute slots retain12minute/zero-buffer semantics.

TURN_URL/TURN_SECRET, HTTPS/two media-capable devices, SMTP, Razorpay credentials/webhooks, antivirus and private object storage are external setup dependencies. Lab/radiology/ward roles, insurance/TPA, controlled-drug validation, interactions/allergy knowledge base, hardware barcode/temperature feeds and validated hospital policy require additional implementation/credentials/policy review. Each requested subfeature will be marked implemented, blocked or incomplete with evidence; no blanket production-readiness claim.

## Current result

Core integrations implemented, migrations0006–0009 applied after backups; original31-table values preserved. Current46-table MySQL and separate PostgreSQL rehearsal pass the expanded suites and real HTTP workflows. Detailed PASS/PARTIAL/NOT IMPLEMENTED/NOT TESTED status, including real-media and advanced-HIS gaps, is in docs/HOSPITAL_UPGRADE_REPORT.md. This plan does not mark the full requested hospital specification complete.
