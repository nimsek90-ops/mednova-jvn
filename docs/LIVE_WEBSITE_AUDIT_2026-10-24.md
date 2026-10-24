# MedNova live website audit — 24 October 2026

**Score: 90/100. Status: Ready with Issues.** The public demonstration site works; email delivery and a real two-device video call still require verification before clinical use.

Site: https://mednova-jvn-vercel-snowy.vercel.app/

Backend: https://mednova-jvn-backend.onrender.com/health/

## Bugs found and fixed

| Priority | Finding | Fix and retest |
| --- | --- | --- |
| Critical | The copied database contained active synthetic accounts accepting the published fixture password, including an administrator. | Disabled all 24 matching reserved-domain fixture accounts and their doctor slots. Deleted no accounts, changed no real-user passwords, and confirmed one non-fixture administrator remains active. Live login with the published fixture admin credentials is now rejected. |
| High | Payment screenshot submission crashed with HTTP 500 because the storage endpoint contained the literal `YOUR_ACCOUNT_ID`; no R2 tokens existed. | Corrected the endpoint/bucket/region, created the explicitly approved one-bucket Object Read & Write credential, and installed it privately in Render. Added safe handling of storage-client configuration errors. Retested real private uploads, authorized retrieval and denial to another patient. |
| High | Database file references had not been accompanied by migration of the actual private files. | Copied all three historical referenced files into private R2 storage without overwriting different content. All three remote contents matched their local SHA-256 hashes; local originals remain intact. |
| Medium | HEAD requests to the homepage and health endpoint returned 405, misleading availability probes. | Both now support HEAD. Live responses return 200 and no body; regression test preserves 503 when the database fails and still rejects POST. |
| Low | Conventional favicon requests returned 404; the original icon referenced a roughly 982 KB logo. | Added named favicon aliases and a native 175-byte SVG icon. Both aliases return the icon successfully. |

The storage error-handling fix was independently exercised before credentials were repaired: a configuration failure returned a retryable 503 rather than a 500, with the payment remaining unpaid and no proof saved. Report-upload errors also remain readable and do not expose provider settings.

## Test evidence

| Check | Final result |
| --- | --- |
| Django suite on isolated MySQL | **228 passed, 0 failed**; baseline was 225 before three new regression tests |
| Vercel routing build tests | **2 passed, 0 failed** |
| Role-route assertions inside the automated suite | 540 checks across anonymous access and all five roles |
| Live authenticated route matrix | 132 HTTP requests across six synthetic accounts; zero server errors; non-admin user-management access denied |
| Live public crawl and security/probe checks | 59 requests; no broken rendered links/assets; private paths and Git/environment probes correctly return 404 |
| Production Django security checks | No issues at warning-or-higher failure level |
| Installed dependencies | `pip check` passed; OSV checked 26 packages and returned no listed advisories |
| Cloud database relationships | 73 foreign keys checked; zero orphan rows |
| Render release and public frontend | Fixes deployed; health and public navigation operational |

Totals above distinguish tests from HTTP checks: the 540 route assertions are part of the Django suite, not 540 additional independent tests. The 59 public requests include seven explicit probe/security requests. A complete security certification is outside this audit.

### Verified live workflows

- Registration creates the patient workspace; profile edits persist; duplicate email registration is rejected; missing-CSRF login submissions are rejected.
- Patient, doctor, receptionist, pharmacist and administrator synthetic accounts log in and receive their role access. Other patients cannot view the synthetic appointments or reviews.
- Video and in-person booking, assigned-doctor confirmation and patient cancellation persist in the cloud database.
- Offline payment remains pending until reception confirms it. Replaying the confirmation does not increment the verification version again.
- Both video and in-person online proofs upload to private R2 storage. Authorized retrieval succeeds with private caching; another patient's retrieval fails. Rejection, resubmission, confirmation and patient notifications persist.
- Uploading a screenshot does not unlock video. A paid eligible room opens only after staff verification. Patient self-admission fails; patient consent and assigned-doctor admission succeed; an unrelated patient cannot enter.
- A rating can be saved with no comment, edited without duplicates, and submitted through the real five-star browser controls. At a 390px viewport the review form has no horizontal overflow, exactly five star inputs, a persisted selected rating, and no required comment field.
- Pharmacist creates a synthetic inventory batch; assigned doctor issues a synthetic prescription; dispensing reduces only that batch's stock. Duplicate dispensing leaves stock unchanged, and patients cannot dispense. The test batch is now quarantined with zero stock.
- A synthetic medical image report uploads, downloads through authorization and is correctly re-encoded as a valid JPEG. Anonymous download attempts redirect to login.
- Assistant API doctor search, hospital-information request, conversation reset and invalid/empty JSON validation behave correctly.
- Public pages are styled, navigation works, the mobile menu opens, and sampled pages have no captured browser console errors. Private responses include no-store/private caching; HTTPS security headers are present.

### Evidence interpretation

Raw first-pass failures remain in `verification/live-audit-20261024-workflows.json` and `...-payment-final.json`. The storage failure was reproduced, fixed and retested. Initial booking/rating assertions and two immediate confirmation assertions did not all pass; independent HTTP rechecks, final database queries and browser review submission confirmed the intended persisted outcomes. These earlier failures were not silently removed or reported as initial passes.

The report-image raw-byte comparison is false by design: the upload validator converts PNG/JPEG input into sanitized JPEG output. The final persistence check verifies the resulting image format, dimensions and pixel content. Original and sanitized bytes are not expected to match.

## Blocked and not fully tested

**Blocked external check (1):** hospital payment-proof email delivery. The hospital recipient is empty; proof email status correctly reports unavailable. No address or SMTP credential was invented, and no real message was sent.

**Not fully tested live (6 groups):**

1. Real two-device WebRTC audio/video and TURN connectivity. Access control, payment lock, consent and admission were tested; a room rendering is not proof of a working media connection.
2. PDF antivirus-scanner integration. Image reports were exercised; PDF scanning was not configured or validated in this run.
3. Razorpay capture/refund against a real provider. Manual online-proof and offline verification were tested; no real payment was made.
4. Complete admission/bed lifecycle.
5. Complete procurement/GRN lifecycle.
6. Staff registration/approval and scheduling publication lifecycle.

The last three groups have automated local coverage and their live role routes were exercised, but their full mutations were not repeated on the public hospital database. They receive no claim of full live verification.

## Remaining actions

- Configure the actual hospital email recipient and approved mail delivery credentials, then test delivery to an explicitly authorized test mailbox.
- Verify a real two-device consultation, including TURN across different networks.
- Review any remaining pre-existing demonstration doctor profiles before a real hospital launch. They were not indiscriminately overwritten or deleted.
- Renew/rotate the restricted R2 credential before **24 October 2027**. It is limited to `mednova-private`; public bucket access remains disabled.

## Score method

| Category | Score | Basis |
| --- | --- | --- |
| Core functionality and workflows | 23/25 | Live registration, booking, reviews, dispensing and assistant; some full staff workflows remain local-only |
| Backend, APIs and database | 19/20 | Automated suite, live persistence and relationship checks; no sustained load test |
| Authentication and security | 19/20 | Legacy fixture vulnerability repaired; role, CSRF and private-file checks; not an exhaustive penetration test |
| UI/UX and responsiveness | 9/10 | Desktop/mobile browser checks; no exhaustive accessibility audit |
| Appointment, payment and video | 8/10 | Manual payment variants and video access gates verified; real media and email remain incomplete |
| Error handling and reliability | 4/5 | Storage crash fixed and regression-tested; initial live assertion mismatches retained in evidence |
| Build and deployment readiness | 8/10 | Live builds, private storage and headers; remaining provider verification prevents full credit |
| **Total** | **90/100** | Untested external functionality receives no full marks |

## Changes and cleanup

Code changed: `care/private_storage.py`, `care/views.py`, `care/test_audit_20261024.py`, `mednova/urls.py`, `templates/care/base.html`, `static/img/favicon.svg`. Render storage variables were updated without exposing values. No database schema changes or new runtime dependencies were required.

Seven new audit accounts were disabled and their slots made inactive. Synthetic pending/confirmed appointments were closed, test stock was quarantined and its adjustment recorded, and pending synthetic mail-outbox rows were made unavailable. Separately, 24 legacy accounts with the published fixture password were disabled. No real account or private record was deleted. Credentials, SQL backups, screenshots and raw operator files remain in ignored `.runtime/`, not Git.
