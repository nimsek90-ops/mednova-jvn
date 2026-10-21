# MySQL database

Django migrations in `care/migrations/` are the authoritative, versioned schema. The application defaults to `django.db.backends.mysql`; SQLite is used only by isolated automated tests. Runtime application data is not stored in the browser.

`configure.py` creates the selected database and its tables using administrator credentials supplied interactively. It generates a separate local application account with only SELECT, INSERT, UPDATE and DELETE access to that database. Administrator credentials are not saved. Run schema upgrades separately with a migration account; do not grant the runtime account global or schema-management privileges.

Tables cover users/roles, hospital details, departments, doctor profiles, slots, appointments, prescriptions/items, medicine batches, private report metadata, payments, audit events, rate limits and temporary call signals. Django also creates its session, permission and migration tables.

Use MySQL 8.0.11 or newer, preferably a currently supported MySQL LTS release. The SQL mode is strict and the connection uses utf8mb4. Keep the server private, require TLS for remote connections, encrypt storage and backups, and test restoration before real patient use. The archive contains no patient database dump and no database credentials.

Appointment writes use transactions and row locks. MySQL concurrency testing is still required on the target server; passing the SQLite tests does not establish MySQL row-lock behavior.
