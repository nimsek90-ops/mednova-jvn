# MedNova controlled restructuring and workflow repair

## Architecture and recovery

The active request path is Vercel's `deployment/vercel` same-origin proxy → Render's Docker/Waitress Django application → Aiven MySQL `mednova`. Django `care.User` and sessions are the single authentication system. Cloudflare R2 is private object storage; Supabase is not in the live request path. No production database consolidation was needed. Local MySQL, PostgreSQL rehearsal databases and the private restore copy are explicitly non-production.

Recovery branch: `backup/pre-restructure-20261024`, preserving the previous deployed source. Existing untracked release evidence was retained. A private MySQL backup was restored into a new isolated local schema: 53 tables, zero row-count differences. The new migrations were rehearsed in the restored snapshot before production application. SQL backups, credentials and restored patient data remain under ignored `.runtime`, never committed or displayed.

## Feature classification and changes

| Role / feature | Assessment | Action |
|---|---|---|
| Patient booking, history, profile, payments, reviews and private records | Essential, existing workflows | Preserve canonical transactional services; rerun tests |
| Doctor appointment identity | Incorrect context | Lead appointment cards/details with patient name; display actual slot duration |
| Doctor cancellation | Essential but incomplete | Required reason, native confirmation dialog, immutable actor/time/doctor/patient/original-time snapshot, persistent notification, actual replacement availability |
| Doctor cancellation alternatives | Missing | Same-doctor future slots plus related doctors near original time, matching specialty prioritized; normal booking rechecks capacity and conflicts; cancelled visit never reopened |
| Reception, pharmacy and administrator operations | Essential, existing coverage | Preserve backend permissions and operational routes |
| Patient wellness/education links in staff menus | Unrelated role navigation | Limit the patient wellness section and assistant shortcut to patient navigation; keep working authorized routes |
| Video call lifecycle | Confirmed race and recovery weakness | Stop late media-permission results after End; guard stale polling results; abort outstanding requests on exit; request timeouts, bounded retry backoff, stop media after repeated failure; show remote participant identity |
| Session refresh | Repeated database writes | Refresh rolling expiry at most once per five minutes rather than on every API/video poll; retain 30-minute session expiry and browser-close expiry |
| Approved-doctor directory policy | Duplicated queryset | Reuse `approved_profiles()` in directory and profile/home policies |
| Generated files | Safe to remove from active source | Reversibly archive 81 bytecode cache files (1,023,228 bytes); keep databases, uploads, backup archives, tests and migrations |
| Optional PostgreSQL / direct-Django Vercel adapters | Tested compatibility paths, not competing live services | Retain and label rather than remove functional deployment/tests |

The doctor cancellation event uses `kind=cancelled_by_doctor`; `Appointment.status` remains `cancelled` for compatibility with existing billing/refund, queues, availability and video locks. Full reason and original appointment details remain in the event and original appointment. The unavailable doctor's withdrawn time is not advertised through waiting-list notifications. Repeated cancellation requests cannot create duplicate events or notifications. Positive paid amounts retain the existing refund-due behavior; a replacement booking has separate billing and does not transfer payment silently.

The notification column was widened from 200 to 1000 characters after a real MySQL browser submission exposed the length limit. This is a non-destructive widening, alongside the new cancellation table. No patient tables were dropped, existing appointments were not rewritten and no destructive data migration was introduced. Existing historical cancellations are not assigned invented actors or timestamps.

The reason dialog progressively enhances the existing POST form, which remains usable without JavaScript. New major cancellation action labels have English/Marathi/Hindi entries. Names, records and reasons retain their original language. A full professional translation review of every existing phrase is still not claimed.

## Verification and limitations

See `verification/restructure-20261024-*` for executed tests and release evidence. The new cancellation was submitted in an isolated browser session; the patient then signed in, saw the persisted notification and opened actual recovery options. The original cancellation remained in history. Mobile/tablet/desktop recovery layouts were measured without horizontal overflow. Existing authentication, role permissions, scheduling, manual payments, clinical, pharmacy and review tests are retained.

The first browser cancellation failed because the new notification exceeded the old database column length; the transaction rolled back. After widening, the same browser flow succeeded. A long-reason regression covers that boundary. An initial maximum-name test fixture exceeded User.name's existing 120-character limit; the fixture was corrected to use the model's actual maximum, without weakening the model.

Video lifecycle tests simulate only browser API timing and permission errors; they do not prove media transport. Two independent real devices/networks, camera/microphone permission grants and a configured secure TURN relay remain necessary. Production requires `TURN_URL` plus `TURN_SECRET` for the existing expiring HMAC credential contract; no new provider, secret or account access was fabricated. Render free-service cold starts remain a hosting limitation and are not repaired by client caching.

No sensitive appointment/medical responses were cached. Session expiry refresh is coalesced to five-minute intervals, so an idle session can expire up to five minutes earlier than a perfectly sliding 30-minute timer. Authentication/role checks still execute per request.

Full production video transport, real SMTP inbox delivery, fresh cloud object writes, real payment capture/refund and external PDF scanning must be separately authorized/configured/tested. Comprehensive load testing, penetration testing, assistive-technology certification and exhaustive visual review of every screen/device combination have not been performed. No standalone lint/type-check command is configured.

A broad runtime rewrite was deliberately avoided: static templates, form URLs, CSRF, database identifiers, authentication and existing service boundaries are preserved. The recursive inventory parses Python sources and hashes exact duplicates; its only duplicate source group is required empty package markers, which are retained. It is not a claim that a human reviewed every line of every file.

Deployment status and final test totals are appended after verified release. Automatic deletion review blocked recursive cache removal; the safe fallback archived generated bytecode instead. Archived caches may be regenerated during normal Python execution.

## Final pre-release checks

236 MySQL Django tests passed, including seven new cancellation/context/session regression tests. Two Node video lifecycle tests and two frontend routing tests passed: **240 automated tests, zero final failures**. The eight real HTTP acceptance groups and 250 six-role rendered link/asset checks passed separately. Frontend production build, JavaScript syntax, dependency consistency, migration drift/pending checks and Django checks passed. Deployment-setting checks used production security flags with isolated local settings; they do not prove external credential delivery.

The private restore rehearsal passed both `0015` and `0016`. Both migrations were then applied to authoritative Aiven MySQL; existing user, appointment and notification row counts were unchanged, and the new history table was empty. Schema writes were limited to these reviewed non-destructive migrations and Django migration metadata. No live synthetic appointment or cancellation was created.

The core feature repairs are ready for deployment. The video lifecycle guards are tested, but actual two-device media and secure relay behavior remain **not signed off**. SMTP delivery, fresh production object writes, payment-provider transactions and PDF scanner behavior remain unverified externally. A source commit and actual provider deployment status will be recorded in post-release evidence.
