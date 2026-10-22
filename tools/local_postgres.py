"""Use the already provisioned isolated local PostgreSQL rehearsal, never Supabase."""
import json
import os
from pathlib import Path
import subprocess
import sys
import socket

base = Path(__file__).resolve().parent.parent
private = base / '.runtime/postgres-local.json'
if not private.exists():
    raise SystemExit('Local PostgreSQL rehearsal is not provisioned. Configure a target explicitly; nothing was initialized.')
config = json.loads(private.read_text())
args = sys.argv[1:]
operator = '--operator' in args
args = [arg for arg in args if arg != '--operator']
env = os.environ.copy()
for name in ('MEDNOVA_TESTING','MEDNOVA_TEST_MYSQL','MEDNOVA_TEST_POSTGRES','MEDNOVA_TEST_DB','VERCEL'):
    env.pop(name, None)
env.update(APP_ENV='local', DATABASE_VENDOR='postgresql', PGHOST=config['host'],
           PGPORT=str(config['port']), PGDATABASE=config['database'], PGSCHEMA='mednova',
           PGUSER=config['user'] if operator else 'mednova_pg_runtime',
           PGPASSWORD=config['password'] if operator else config['runtime_password'],
           PGSSLMODE='disable', ALLOWED_HOSTS='127.0.0.1,localhost', MEDNOVA_DEMO='1',
           DJANGO_SECRET_KEY=json.loads((base/'.runtime/local_mysql.json').read_text())['secret_key'])
if args == ['http_acceptance']:
    env.update(MEDNOVA_HTTP_POSTGRES='1', MEDNOVA_HTTP_ORIGIN='http://127.0.0.1:8002')
    command = [sys.executable, 'tools/http_acceptance.py']
elif not args or args == ['serve']:
    if operator:
        raise SystemExit('The web server must use restricted runtime credentials.')
    if config['host'] != '127.0.0.1':
        raise SystemExit('This helper is restricted to the isolated loopback rehearsal.')
    try:
        with socket.create_connection((config['host'], config['port']), timeout=2):
            pass
    except OSError:
        installation = base / '.runtime/postgres-official/pgsql'
        data = base / '.runtime/pg-data'
        if not (installation/'bin/pg_ctl.exe').exists() or not data.exists():
            raise SystemExit('Initialized rehearsal cluster is missing; nothing was reset.')
        with (base/'.runtime/pg-start.log').open('ab') as log:
            result = subprocess.run([str(installation/'bin/pg_ctl.exe'), '-D', str(data),
                '-l', str(base/'.runtime/pg-server.log'), '-o',
                f'-h 127.0.0.1 -p {config["port"]}', '-w', 'start'],
                stdout=log, stderr=log, timeout=45,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if result.returncode:
            raise SystemExit('PostgreSQL startup failed; inspect the private runtime log.')
    command = [sys.executable, '-m', 'waitress', '--listen=127.0.0.1:8002', 'mednova.wsgi:application']
else:
    command = [sys.executable, 'manage.py', *args]
raise SystemExit(subprocess.call(command, cwd=base, env=env))
