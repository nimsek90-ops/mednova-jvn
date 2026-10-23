> Current project state, verification and safe recovery: [README.md](README.md) and [cleanup report](docs/CLEANUP_REPORT.md). The working MySQL schema has 51 tables; earlier reports describe historical checkpoints.

# Open and run the complete MedNova source

## This prepared laptop: preserve the current MySQL data

Open this ORIGINAL folder (not the extracted source copy):

```powershell
Set-Location 'C:\Users\Niraj\Downloads\mednova-redesign\MedNova-Python-MySQL'
code .
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-MedNova.ps1
```

The existing app is http://127.0.0.1:8000. If it is already running, use that window instead of starting a second server. This path uses ignored `.runtime/local_mysql.json`, MySQL 8.4.13, `mednova_local`, 127.0.0.1:3307 and restricted `mednova_local_app`. No data reset or engine switch occurs. PostgreSQL on 8002 is a separate rehearsal.

## Clean ZIP on another machine

Extract completely, then open `MedNova.code-workspace` or use File > Open Folder. Source, migrations, assets, tests, pinned dependencies, Figma construction sources and documentation are included. Local databases, uploads, credentials, virtual environments and Git history are intentionally not in the ZIP. The original repository preserves them; a source ZIP cannot automatically reconnect to private data on another computer.

```powershell
code .
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-MedNova.ps1
```

Install Python 3.12 x64 and MySQL first. For a NEW empty local database only, use `Setup-MedNova.ps1 -ConfigureNewDatabase`; the interactive setup prompts for database credentials, applies migrations and creates a restricted runtime account. Choose a new database name. For an EXISTING database, securely configure `.env` from `.env.example` with the authorized runtime connection and a fresh random Django secret of at least 50 characters. Set APP_ENV=local, DATABASE_VENDOR=mysql, the exact MYSQL_* fields, and loopback ALLOWED_HOSTS. Do not run new-database configuration against existing records. Back up before applying pending migrations through a separate migration identity. See docs/MYSQL_OPERATIONS.md. Never use Go Live or npm for this Django project.

## Restore the intended administrator

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Admin-MedNova.ps1 -Email 'jayesh@gmail.com'
```

The command prompts twice for a NEW password with hidden input. It creates an absent admin with mandatory initial password replacement, preserves an existing valid admin, and refuses a conflicting non-admin account. No password is bundled or reset silently. Then open `/login/?role=admin`. The earlier absence finding is historical. Existing administrator accounts are preserved; do not rerun provisioning merely to start the website. For an existing admin needing recovery, use the configured Django `changepassword` command deliberately; never reuse an exposed bootstrap password.

## Work in VS Code

Terminal > Run Task offers start, dependency setup and administrator provisioning. The Python interpreter is `.venv/Scripts/python.exe`. Use the recommended extensions prompt; see docs/VSCODE_DATABASE.md for the real MySQL connection and safe table inspection. The source ZIP has no saved database password. See docs/LOGIN_AND_FOLDER_DELIVERY.md for current verification and remaining limits.
