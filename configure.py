"""Interactive first-run setup. Administrator DB credentials stay in process memory."""

import getpass, os, re, secrets, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.chdir(BASE)
try:
    import MySQLdb
except ImportError:
    print("Install requirements.txt first.")
    sys.exit(1)


def ask(prompt, default):
    return input(f"{prompt} [{default}]: ").strip() or default


def main():
    if (BASE / ".env").exists():
        print("Existing .env preserved. Checking the existing database connection.")
        return subprocess.call([sys.executable, "manage.py", "check_database"])
    print(
        "MedNova local setup. Start MySQL before continuing. No data will be deleted."
    )
    host = ask("MySQL host", "127.0.0.1")
    port = int(ask("MySQL port", "3306"))
    database = ask("Database name", "mednova")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,40}", database):
        raise ValueError(
            "Database name must contain only letters, digits and underscores."
        )
    root_user = ask("MySQL administrator username", "root")
    root_password = getpass.getpass("MySQL administrator password (hidden): ")
    conn = MySQLdb.connect(
        host=host, port=port, user=root_user, passwd=root_password, charset="utf8mb4"
    )
    app_user = "mednova_" + secrets.token_hex(4)
    app_password = secrets.token_urlsafe(36)
    # Local setup intentionally creates only a localhost application account.
    if host not in ("localhost", "127.0.0.1"):
        raise ValueError(
            "This setup is for local MySQL only. Use .env.example and the deployment guide for a remote database."
        )
    with conn.cursor() as c:
        c.execute(
            f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        c.execute(
            "CREATE USER %s@'localhost' IDENTIFIED BY %s", (app_user, app_password)
        )
        c.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{database}`.* TO %s@'localhost'",
            (app_user,),
        )
    conn.close()
    secret = secrets.token_urlsafe(64)
    lines = (BASE / ".env.example").read_text(encoding="utf-8")
    values = {
        "DJANGO_SECRET_KEY": secret,
        "MYSQL_HOST": host,
        "MYSQL_PORT": str(port),
        "MYSQL_DATABASE": database,
        "MYSQL_USER": app_user,
        "MYSQL_PASSWORD": app_password,
    }
    for key, value in values.items():
        lines = re.sub(r"^" + key + r"=.*$", key + "=" + value, lines, flags=re.M)
    # Administrator credentials are passed only through the subprocess environment for schema migration.
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "local",
            "DJANGO_SECRET_KEY": secret,
            "MYSQL_HOST": host,
            "MYSQL_PORT": str(port),
            "MYSQL_DATABASE": database,
            "MYSQL_USER": root_user,
            "MYSQL_PASSWORD": root_password,
        }
    )
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"], env=env, check=True
    )
    app = MySQLdb.connect(
        host=host,
        port=port,
        user=app_user,
        passwd=app_password,
        db=database,
        charset="utf8mb4",
    )
    with app.cursor() as c:
        c.execute("SELECT COUNT(*) FROM care_user")
        c.fetchone()
    app.close()
    path = BASE / ".env"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(lines)
    print(
        "MySQL connected. Tables created. A restricted database account is configured."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(1)
    except Exception as exc:
        if isinstance(exc, ValueError):
            print(str(exc))
        else:
            print(
                "Setup could not complete. Check MySQL is running, the administrator credentials are correct, and the account can create databases and users. No database password is printed."
            )
        sys.exit(1)
