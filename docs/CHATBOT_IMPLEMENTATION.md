# MedNova conversational hospital assistant

Historical first chatbot checkpoint. See [the current patient-assistant report](PATIENT_ASSISTANT_REPORT.md) for patient tools, persistent consented support cases and the current 48-table schema.

Implemented 23 October 2026 in the existing Django project. Open `/assistant/`.

## Audit finding

The previous assistant submitted a full-page form, required a topic dropdown, and searched entire questions as literal substrings. It had no conversational API, entity context, asynchronous exchange or retry controls. Existing doctor, scheduling, booking, records and FAQ modules were reusable.

## Implemented

- `/api/assistant/`: GET greeting/public service history; CSRF-protected JSON POST message or clear. Server input validation, 40 requests/minute, bounded doctor/FAQ results, friendly database failure responses.
- Local deterministic intent and entity matching: common specialist synonyms, selected spelling corrections, actual doctor names/departments/qualifications, today/tomorrow/weekdays/ISO dates, morning/afternoon/evening and consultation mode. Follow-ups preserve doctor/specialty context; date remains available for mode follow-ups. No provider, credential, network call or model-generated hospital facts.
- Approved active doctors only. Actual qualification, experience, fee, location, weekly sessions, duration/buffer and up to three matching live slots per doctor. Registered doctors without matching availability are explicitly labelled. At most eight doctors, with a full-directory link.
- Shared availability now excludes overlaps with existing appointments, including their buffers, as well as its existing leave/break, capacity and session restrictions.
- Slot-specific selection links open the existing booking form with the real date/time preselected. Selecting or asking does **not** book. The patient enters visit details, consent and confirms through the existing atomic booking service. Rescheduling and cancellation use existing authorized confirmation forms. No parallel booking database or fabricated success state.
- Own appointment summaries, links to permitted reports/billing/prescriptions/admissions/timeline. Role and ownership checks remain server-side. Inventory is restricted to approved pharmacy/admin accounts.
- Hospital configuration and approved FAQs only. Missing information is stated explicitly. Human support records account plus topic only, and links to actual contact details.
- Accessible chat log, separate message bubbles, timestamps, loading state, Enter/Shift+Enter, suggestions, retry, clear/new chat, close/reopen and responsive layout. Server content is rendered with `textContent`, never injected HTML.
- No schema migration, external provider, database replacement, cloud deployment or password changes.

## Privacy and limitations

Raw user questions are not persisted. Session context contains only public profile IDs, specialty/date filters and timestamps. Anonymous public service replies are retained for at most 30 minutes of inactivity, bounded to six replies. Authenticated patients' replies/private cards are not retained in history. The currently open page keeps its visible conversation until cleared/reloaded. Clear removes server context/history. Login/logout isolates session state.

This is a local hospital service recognizer, not an unrestricted language model or clinical triage system. Unknown terms need clarification or human support. Subspecialties can only be matched when present in published department/qualification records; the existing schema has no separate subspecialty field. Booking, cancellation, rescheduling and detailed clinical records finish on the existing secure pages, rather than inside the message bubble. Empty hospital policy/FAQ fields cannot supply answers. No general diagnosis, prescription generation, drug recommendation or external emergency dispatch is provided.

The emergency contact copy uses India's 112 emergency number, verified against the [Ministry of Home Affairs ERSS description](https://www.mha.gov.in/en/commoncontent/emergency-response-support-system-erss). The assistant explicitly states it has not contacted emergency services.

## Verification

- `care.test_chatbot`: natural language specialty variants, spelling correction, contextual dates, no fabricated specialists/today availability, leave and occupied overlaps, own-record isolation, unapproved FAQ exclusion, emergency/support, malformed/oversize inputs, CSRF, database errors, clear/privacy, rate limit, restricted inventory and real profile links.
- Booking flow test follows a returned slot link, verifies no booking on GET, confirms through the real form and verifies retries do not create another appointment.
- Final MySQL full suite: **161 tests passed**, including 12 chatbot tests and existing SQL concurrency acceptance cases. Results: `docs/verification/chatbot-mysql-tests.txt`; role matrix beside it.
- Browser evidence: `chatbot-browser.json`, `chatbot-desktop.jpg`. Confirmed send, suggestions, Enter, clear, close/reopen, anonymous authentication prompt, actual server outage and successful retry after recovery. Four widths (320, 390, 768, 1280) had no document overflow or duplicate IDs. Viewport restored after checks.
- Existing assistant POST workflow retained for compatibility and prior acceptance tests.

Run from the project folder: `.venv\Scripts\python.exe tools/local_mysql.py serve`.
