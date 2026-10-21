# MedNova security and verification review

Final verification: 12 October 2026. Scope: the supplied `mednova-redesign.zip` and the replacement application in this archive. This is a source review, automated regression suite, dependency scan and configuration check. It is not a completed live penetration test or a certification for handling patient data.

## Findings in the supplied project

The original archive was a React frontend prototype. Most records lived in browser localStorage; role selection was not server authorization; demo OTP `123456`, demo session entry, sample patient records and illustrative metrics existed. There was no Python backend or MySQL schema. The rewrite removes those flows and runtime samples entirely.

The supplied archive had no `.git` directory/history and no live `.env` file. Therefore Git-history leaks and actual deployed environment values could not be audited. A source scan found no matches for the scanned high-confidence private-key, AWS, Google API, Stripe secret or GitHub-token patterns. This limited pattern scan does not prove the absence of every possible secret.

## Controls implemented

| Area | Implementation |
|---|---|
| Authentication | Email/password, Argon2 hashes, Django sessions, secure password validation and no demo bypass |
| Authorization | Server-side roles, approved staff status, patient ownership and assigned-doctor scoping |
| Admin protection | Admin role required for staff approval, departments, settings and audit pages; no public admin signup |
| Session protection | HttpOnly session cookies, SameSite=Lax, 30-minute activity timeout, session rotation on login, POST logout |
| CSRF | Django CSRF protection on state changes; only signed payment-provider webhook is exempt |
| XSS | Autoescaped templates, plain text clinical inputs, no untrusted innerHTML, self-only CSP on ordinary pages |
| Payment-page CSP | Razorpay Checkout script/frame domains enabled only on the explicit payment page; inline styles allowed there for Checkout |
| Forms/files | Server validation, bounded fields, 5 MB uploads, image type validation/re-encoding, PDF scan fail-closed |
| Private reports | Random filenames outside static roots; authorization and attachment download required |
| Rate limits | Database-backed counters for login IP/account, signup, password reset, booking, uploads/downloads, payment API and signaling |
| CORS | No cross-origin permission headers; frontend/backend share the same origin |
| Headers | CSP, frame denial, nosniff, no-referrer, camera/microphone permissions and no-store for application responses |
| Production settings | Debug false; HTTPS redirect, secure cookies and HSTS; exact allowed hosts; minimum secret length |
| Secrets | Environment configuration; no private provider secret in frontend source; unique first-run secret |
| Database | ORM queries, strict MySQL mode, utf8mb4, transactions/row locks and restricted runtime DB account |
| Payments | Stored server-side amount, HMAC verification, captured amount/currency verification, signed idempotent webhook |
| Video | Appointment participants only, time-window checks, short-lived relay credentials, no recording |
| Audit | Login, profile, approval, appointment, upload/download, prescription, inventory and payment events; no password/clinical body logging |

## Completed checks

- **55 automated tests passed**, using an isolated SQLite test database. These cover login and role tampering, staff approval, ownership isolation, private downloads, CSRF, XSS escaping, duplicate/overlapping booking rejection, rescheduling, cancellation/refund state, malicious file types, stock/expiry checks, double dispensing, video/signaling authorization, forged payment rejection, webhook amount checks/idempotency, password-session invalidation, template compilation and relevant server-rendered pages.
- Django application system checks passed.
- Production security settings passed `check --deploy` with only the database backend substituted for the check because MySQL was unavailable. This does not verify the production database or host.
- JavaScript syntax checks and Python compilation passed.
- **17 pinned application packages scanned; zero known vulnerability matches** in the vulnerability database consulted. This includes the pinned mysqlclient package, which could not be installed on this Linux environment because native build prerequisites were unavailable.
- Windows CPython 3.12 binary wheels were successfully resolved/downloaded for all 17 pinned packages. The Windows installer itself was not executed here.
- Bandit reported **zero high, zero medium and five low findings** after removal of the test-only fixed key. The remaining findings flag subprocess imports/calls in antivirus scanning and local setup. Review: commands are fixed application paths or an administrator-configured scanner path; arguments are passed as arrays without a shell. Uploaded names never become command strings. These findings remain visible in the included report and were not suppressed.
- Packaging excludes live environments, private uploads, databases, virtual environments, caches and the old React bundle.

## Outstanding verification and limits

- **Actual MySQL connection and concurrent row-lock behavior:** no MySQL server was available here. The database must be connected and the workflows tested on the user's Windows machine and the eventual host.
- **Desktop/mobile visual and end-to-end browser QA:** unavailable in this environment. Templates render in server tests; that is not a visual browser check.
- **Two-device video/audio and TURN:** not connected or tested. Local WebRTC signaling tests are not evidence of successful real media calls.
- **Live SMTP, payment Checkout/capture/webhook and ClamAV:** credentials/services were not provided. Tests validate server behavior and mocked/local cases, not actual provider delivery.
- **Hospital identity, contact numbers, clinician credentials, cancellation/refund policy, retention and legal review:** must be completed by the hospital. No verified hospital contact information was supplied.
- **Clinical completeness:** immutable prescriptions have no amendment/signature workflow, hospital verification is manual, and uploads are appointment-linked. Confirm these workflows meet the hospital's requirements before any real patient use.
- **Translation:** primary interface labels and many messages are provided in English/Marathi/Hindi. Some detailed errors, legal text and provider/browser messages remain English; professional language review is outstanding.
- **Infrastructure:** no deployed firewall, TLS certificate, backup/restore drill, monitoring, data-at-rest encryption or independent penetration test was performed. Audit events are not externally tamper-proof. Review `DEPLOYMENT.md` before launch.

The absence of known dependency vulnerabilities and passing tests are evidence for this build, not a promise that it cannot be compromised. Public launch remains deferred until owner approval and custom-domain configuration.

## Reference documentation consulted

- Django security release 5.2.18: https://www.djangoproject.com/weblog/2026/oct/06/security-releases/
- Django deployment checklist: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- Razorpay payment verification/security: https://razorpay.com/security/checklist
- WebRTC peer connections: https://webrtc.org/getting-started/peer-connections
- WebRTC network protocols/TURN: https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols
