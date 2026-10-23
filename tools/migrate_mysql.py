"""Explicit local MySQL migration with a private backup; never initializes a database."""
import argparse
from datetime import datetime, timezone
from getpass import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

base = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true', help='Back up, show plan and apply pending migrations.')
parser.add_argument('--operator-config', help='Optional private JSON operator credentials; otherwise use hidden prompt.')
args = parser.parse_args()
os.chdir(base)
env = os.environ.copy()
for name in ('MEDNOVA_TESTING','MEDNOVA_TEST_MYSQL','MEDNOVA_TEST_POSTGRES','MEDNOVA_TEST_DB','VERCEL'):
    env.pop(name, None)
private = base / '.runtime'
if (private/'local_mysql.json').is_file():
    config = json.loads((private/'local_mysql.json').read_text())
    env.update(MYSQL_HOST=config['host'], MYSQL_PORT=str(config['port']), MYSQL_DATABASE=config['database'],
               DJANGO_SECRET_KEY=config['secret_key'])
elif (base/'.env').is_file():
    for line in (base/'.env').read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=',1)
            env.setdefault(key.strip(),value.strip())
else:
    raise SystemExit('No existing private MySQL configuration. Configure the intended database first.')
if env.get('MYSQL_HOST') not in ('localhost','127.0.0.1') or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',env.get('MYSQL_DATABASE','')):
    raise SystemExit('This helper only operates on an explicitly configured local MySQL schema.')
if args.operator_config:
    operator = json.loads(Path(args.operator_config).read_text())
    username, password = operator.get('user','root'), operator['password']
else:
    username = input('Authorized MySQL migration username: ').strip()
    password = getpass('MySQL migration password (hidden): ')
env.update(APP_ENV='local',DATABASE_VENDOR='mysql',MYSQL_USER=username,MYSQL_PASSWORD=password)
if args.apply:
    binary = base/'.runtime/mysql-8.4.13-winx64/bin/mysqldump.exe'
    dump = str(binary) if binary.is_file() else shutil.which('mysqldump')
    if not dump:
        raise SystemExit('Install the official MySQL client (mysqldump) before applying migrations. No schema changed.')
    backups = private/'backups'
    backups.mkdir(parents=True,exist_ok=True)
    destination = backups / ('before-upgrade-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sql')
    values = {'host':env['MYSQL_HOST'],'port':env.get('MYSQL_PORT','3306'),'user':username,'password':password}
    def quote(value):
        if '\n' in value or '\r' in value:
            raise SystemExit('Unsupported newline in client configuration; use the controlled DBA process.')
        return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',suffix='.cnf',prefix='migration-',dir=private,delete=False,encoding='utf-8') as handle:
            temporary = Path(handle.name)
            os.chmod(temporary,0o600)
            handle.write('[client]\n'+''.join(key+'='+quote(str(value))+'\n' for key,value in values.items()))
        subprocess.run([dump,'--defaults-extra-file='+str(temporary),'--single-transaction','--no-tablespaces',
            '--skip-add-drop-table','--set-gtid-purged=OFF','--hex-blob','--result-file='+str(destination),env['MYSQL_DATABASE']],check=True)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    if not destination.is_file() or destination.stat().st_size==0:
        raise SystemExit('Backup is empty. No migrations were applied.')
    print('Private backup saved. SHA256:',hashlib.sha256(destination.read_bytes()).hexdigest())
subprocess.run([sys.executable,'manage.py','migrate','--plan'],env=env,check=True)
if args.apply:
    subprocess.run([sys.executable,'manage.py','migrate','--noinput'],env=env,check=True)
    print('Migrations complete. Runtime application credentials were not changed. Restart the application.')
else:
    print('Preview only. Use --apply for a backup followed by migration.')
