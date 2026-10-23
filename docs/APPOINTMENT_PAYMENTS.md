# Appointment payment and verification

Implemented and verified locally across 23–24 October 2026, using the existing Django authentication, appointment, payment, private storage, notification and email architecture.

## Patient and staff flow

Open a confirmed appointment and select **Payment instructions & status**. Online instructions display the supplied payment number **9373084858** and the appointment's actual amount due.

| Appointment | Payment choice | Confirmation |
| --- | --- | --- |
| Video | Online, with PNG/JPEG screenshot | Receptionist or assigned doctor independently verifies funds |
| Hospital visit | Online, with PNG/JPEG screenshot | Receptionist or assigned doctor independently verifies funds |
| Hospital visit | Offline Payment at Reception, no screenshot | Receptionist records receipt of payment |

An upload sets **Payment Pending Verification**, never Payment Confirmed. Offline selection leaves **Payment Pending**. Staff can confirm an eligible receipt or reject it with a reason, producing **Payment Confirmed** or **Payment Rejected**. The patient receives an existing in-app notification and can view the reason and resubmit after rejection. Existing refund states and authorized administrator billing access are retained.

Doctor and receptionist dashboards preview pending verifications and link to the paginated queue. Review screens show patient, full appointment ID, doctor, type, amount, method, screenshot link, status, verifier and timestamps. Doctors see only their assigned patients and cannot confirm cash received at reception. Screenshot access is restricted to the owning patient, assigned doctor, receptionist and administrator.

Payment confirmation retains the appointment's existing **Confirmed** state; it does not complete, reschedule or reopen a cancelled visit. A video room and every signalling request additionally require confirmed payment, a staff verifier for nonzero fees, correct participants, confirmed appointment, valid time window and existing consent/admission rules. Existing captured gateway payments retain financial status but require staff clearance before a paid video visit. Captured funds needing reversal use the existing refund process. Free appointments remain supported.

## Database and file handling

Migration `0014_payment_proof_verification` extends `Payment` with current proof reference, verification version, verification date and rejection reason. It adds `PaymentProof` with UUID, private screenshot reference, amount snapshot, submission date and tracked email delivery state/attempts/lease/date. Existing payment rows and amounts are preserved. Historical rejected screenshots remain attached to their payment for review.

Uploads have the existing configured size limit (5 MB locally, 3 MB for Vercel), must decode as PNG/JPEG and remain within the pixel limit. They are re-encoded as PNG to strip metadata/embedded payloads, assigned random storage names and served through an authenticated, no-store endpoint. Direct storage URLs are not exposed. CSRF, approved account checks and bounded submission throttling apply. Reading status does not consume upload quota.

Appointment and payment locks serialize decisions. A version token rejects stale forms, repeated confirmations and competing staff decisions without duplicate patient notifications. Rescheduling is blocked while proof verification is pending, and cash-paid visits cannot be converted into video visits. Legacy cash recording cannot bypass the new online/video verification flow.

## Hospital email configuration and retries

The recipient comes exclusively from **Admin → Hospital settings → Email** (`/admin/settings/`). SMTP and sender use the existing `EMAIL_HOST`, port/TLS, username/password and `DEFAULT_FROM_EMAIL` configuration; no recipient or credentials were invented or hardcoded.

After a committed upload, the hospital email includes the sanitized screenshot attachment, submission ID/date, appointment ID/time, patient and doctor names, appointment type, method and amount. Clinical reason and records are excluded. Delivery state never changes payment verification state.

**Current local limitation:** both the hospital recipient and SMTP configuration are blank. Proofs therefore show **Hospital email: Unavailable** and remain accessible in the verification queue. Actual SMTP delivery has not been established. Set the real hospital recipient and private SMTP configuration, restart, and retry with:

```powershell
.venv\Scripts\python.exe tools/local_mysql.py send_payment_proofs
```

The existing `process_notifications` maintenance command also retries a bounded number of proof emails. SMTP retry is at least once: a crash after server acceptance can result in a duplicate email, but never duplicate payment confirmation.

## Verification and local rollout

- **218 tests passed on isolated MySQL**, including 19 dedicated payment tests and simultaneous staff confirmation with exactly one winner. The full six-role matrix covers 88 routes / 528 requests.
- Tests cover both appointment types, both valid hospital payment methods, required and invalid screenshots, limits, sanitization, server-derived identity/amount, private retrieval, staff ownership, CSRF, rejection/resubmission, duplicates, cancelled appointments, rescheduling and video room/signalling locks before and after confirmation.
- Hospital email attachment, recipient, non-clinical contents, failure/retry and deduplication tested using Django's in-memory mail backend. No real email delivery or money transfer was performed during QA.
- Live HTTP tests passed in the isolated synthetic application for video/online, hospital/online and hospital/reception workflows, including doctor rejection, patient resubmission, reception and doctor confirmation, patient notifications, protected screenshots and video unlock.
- Browser verified dashboard preview, full review screen, both decision buttons and a real synthetic Confirm Payment submission. Desktop and 375-pixel mobile payment detail and patient form were inspected without horizontal overflow. Temporary viewport reset and QA server stopped afterward.
- Database readback confirmed identities, amount, proof history, verifier, timestamps and unchanged confirmed appointment status. No synthetic payment or proof was created in the working hospital database.
- Midnight-sensitive calendar, daily-cap and check-in test fixtures were stabilized; those production features were not changed.
- A private MySQL backup preceded migration 0014. SHA256: `7ec3b9cf1ba352b2225958361e4f06e03aa23e63e4480c1b7d46e48f7e2eb084`. Local schema has **53 tables**; checks and migration drift check pass. Main site restarted and five read-only HTTP checks pass.

Evidence: [MySQL suite](verification/payments-mysql-tests.txt), [role matrix](verification/payments-mysql-role-matrix.json), [live flow](verification/payments-http-flow.json), [database readback](verification/payments-database-flow.json), [schema](verification/payments-schema.json), [primary HTTP checks](verification/payments-primary-http.json), [staff controls](verification/payments-browser-verification.png), [confirmed result](verification/payments-browser-confirmed.png), [mobile form](verification/payments-browser-patient-mobile.png).

The main site is `http://127.0.0.1:8000/`. Other checkouts need their usual migration step before starting. No hosted deployment or production email delivery is claimed.
