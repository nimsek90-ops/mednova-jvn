# Actual MySQL tables in VS Code

Primary on this prepared laptop: MySQL 8.4.13; host `127.0.0.1`, port `3307`, schema `mednova_local`, runtime user `mednova_local_app`. The separate PostgreSQL rehearsal is not the primary application. These values are inspected, not defaults for other machines.

1. Install **MySQL Shell for VS Code** by Oracle (`Oracle.mysql-shell-for-vs-code`) from the Extensions view. It is listed in this project's extension recommendations. Official setup: https://dev.mysql.com/doc/mysql-shell-gui/en/mysql-shell-for-vscode-setup.html . The extension itself has not been installed/configured by this handoff.
2. Open MySQL Shell in the Activity Bar, add a MySQL connection using the values above. Password: read your LOCAL ignored `.runtime/local_mysql.json` privately (password field), or use your authorized database operator's separate credentials. Enter it only in the extension's password prompt/OS credential store. Never put it in workspace settings, SQL, screenshots, Git or the ZIP. Do not select a cloud or PostgreSQL connection by mistake.
3. Expand `mednova_local` > Tables. Open a department table/result grid, browse paged results and use SQL WHERE/ORDER BY for precise filtering/sorting. Open table metadata for columns/indexes; use the information_schema queries below for relationships and constraints. Official connection/result documentation: https://dev.mysql.com/doc/mysql-shell-gui/en/mysql-shell-vscode-db-notebooks.html .
4. Begin with metadata and non-sensitive service rows. A database connection can access more than the MedNova Admin interface. Do not browse/export user hashes, sessions, tokens, private medical content or patient details into unrestricted files.

```sql
SELECT DATABASE(), CURRENT_USER(), VERSION();
SHOW TABLES;
SHOW COLUMNS FROM care_department;
SHOW INDEX FROM care_appointment;
SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL;
SELECT id, name, description FROM care_department ORDER BY name LIMIT 25;
SELECT id, name FROM care_department WHERE name LIKE '%cardio%' ORDER BY name LIMIT 25;
```

Prefer the app's audited validation forms for changes. If an installed extension offers an editable primary-key grid, use only explicitly authorized harmless records in an isolated training schema, review generated UPDATE/WHERE and transaction behavior before saving. Oracle result-grid browsing is documented; an editable grid was NOT TESTED here, and this guide does not claim it supports inline writeback. Use a reviewed transaction in its SQL notebook when grid editing is unavailable. Do not manually alter roles, passwords, inventory balances, appointment/payment states or clinical records.

```sql
START TRANSACTION;
SELECT id, description FROM care_department WHERE id = 123 FOR UPDATE;
-- Replace 123 only with an authorized synthetic training record.
UPDATE care_department SET description = 'Synthetic training description' WHERE id = 123;
SELECT ROW_COUNT() AS affected_rows; -- require exactly the intended count
SELECT id, description FROM care_department WHERE id = 123;
ROLLBACK; -- COMMIT only after explicit authorized review
```

For INSERT/DELETE, foreign-key handling, backup/restore commands and restricted operator identities, use [MYSQL_OPERATIONS.md](MYSQL_OPERATIONS.md). It contains rollback-first examples and backup steps; do not disable constraints. Full table/column/key/index documentation: [MYSQL_SCHEMA_INVENTORY.md](MYSQL_SCHEMA_INVENTORY.md); current metadata: [transformation-mysql-schema.json](verification/transformation-mysql-schema.json). Migration state: run `python tools/local_mysql.py showmigrations --plan` with the project interpreter. Export metadata using `python tools/local_mysql.py database_inventory --output docs/verification/local-schema.json`; it samples no private row values. Avoid unrestricted record exports.

## Web Admin tools

After authorized Admin login, open `/admin/data/` for whitelisted operations and `/admin/data/schema/` for all 31 tables' metadata. Search/select a table for native types, keys and indexes. Record lists have their existing search/pagination and business-specific forms: accounts/staff approval, departments, appointments, medicines and operational payments. Validated forms and audited actions remain the editing boundary. Clinical records/passwords/tokens are deliberately excluded; unrestricted CRUD for every SQL table is not provided. Changing a role link does not grant access. Ordinary patient/staff access to these Admin pages is denied server-side.
