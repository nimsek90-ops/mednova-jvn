# Patient reviews

Implemented 23 October 2026 within the existing Django, templates and MySQL architecture.

Patients open **Appointments → Completed → View appointment → Rate your appointment**. They choose one of five accessible, clickable stars and may submit with an empty comment. Once submitted, the same entry becomes **Edit your review**. Comments are optional, limited to 2,000 characters, and displayed publicly as “Verified patient”; the form explains that personal and medical information should be omitted.

Doctor profiles display the average, count and newest reviews, ten per page. Public output excludes patient identity, appointment identifiers and clinical details; comments are HTML escaped. No synthetic reviews were inserted into the working hospital database.

## Storage and permissions

Migration `0013_patient_reviews` adds `care_appointmentreview`, containing appointment, patient and doctor foreign keys, rating, optional comment, submission date and update date. The original submission date survives edits. Appointment uniqueness and a 1–5 rating check are enforced by the database. An appointment row lock serializes concurrent submissions; repeated submissions update the same review.

Only an authenticated, active, approved patient can access the form, and only for their own completed appointment. Both GET and POST enforce eligibility. Patient and doctor IDs are derived from the appointment, ignoring submitted identity fields. CSRF protection and existing audit events remain in use. No authentication, booking or completion rules were changed.

## Verification

- Full isolated MySQL suite: **198 tests passed**, including nine dedicated review tests and a concurrent review submission test.
- Role matrix: 84 routes × six roles = 504 requests, with no server errors and expected role restrictions.
- Browser: existing doctor completion action, completed patient appointment, five-star selection, submission without a comment, edit to four stars with a comment, and doctor-profile retrieval all passed in the isolated synthetic QA application on port 8003. The rendered narrow viewport was inspected. No additional desktop viewport emulation was available.
- Database readback confirmed exactly one edited review, correct patient/doctor/appointment relationships, rating, comment and timestamps.
- Main MySQL database backed up before applying migration 0013. Backup SHA256: `0ebdeadf29420e6eded50080c271dd3d170cbf452172defa493e0eccca9990a8`. Private backup is retained under `.runtime/backups/`.
- Main schema inventory: 52 tables; no row contents exported. Django checks and migration drift check passed. Static files collected and the local server restarted. Five read-only primary HTTP checks passed.

Evidence: [MySQL tests](verification/reviews-mysql-tests.txt), [role matrix](verification/reviews-mysql-role-matrix.json), [browser and database flow](verification/reviews-flow.json), [screenshot](verification/reviews-browser.png), [schema](verification/reviews-schema.json), [primary HTTP checks](verification/reviews-primary-http.json).

The main site runs at `http://127.0.0.1:8000/`. Other checkouts must run their normal database migration and static collection steps before starting. Hosted deployment was outside this feature request.
