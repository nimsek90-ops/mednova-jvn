"""Start/manage the privately configured local MySQL preview. No default credentials."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

base=Path(__file__).resolve().parent.parent
private=base/'.runtime/local_mysql.json'
if not private.exists():
    raise SystemExit('Local MySQL has not been provisioned. Configure MYSQL_* securely or follow the database guide.')
config=json.loads(private.read_text())
env=os.environ.copy()
for key in ['MEDNOVA_TESTING','MEDNOVA_TEST_MYSQL','MEDNOVA_TEST_DB','MEDNOVA_TEST_POSTGRES','VERCEL']:
    env.pop(key,None)
env.update(DATABASE_VENDOR='mysql',APP_ENV='local',MEDNOVA_DEMO='1',DJANGO_SECRET_KEY=config['secret_key'],ALLOWED_HOSTS='localhost,127.0.0.1',MYSQL_HOST=config['host'],MYSQL_PORT=str(config['port']),MYSQL_DATABASE=config['database'],MYSQL_USER=config['user'],MYSQL_PASSWORD=config['password'])
args=sys.argv[1:]
if args and args[0]=='http_acceptance':
    env['MEDNOVA_HTTP_MYSQL']='1'
    raise SystemExit(subprocess.call([sys.executable,'tools/http_acceptance.py'],cwd=base,env=env))
if not args or args[0]=='serve':
    try:
        with socket.create_connection((config['host'],config['port']),timeout=2):pass
    except OSError:
        installation=base/'.runtime/mysql-8.4.13-winx64'
        data=base/'.runtime/mysql-data'
        if not (installation/'bin/mysqld.exe').exists() or not data.exists():
            raise SystemExit('Portable MySQL installation/data missing. No database was initialized or reset.')
        log=(base/'.runtime/mysql-console.log').open('ab')
        subprocess.Popen([str(installation/'bin/mysqld.exe'),'--no-defaults','--basedir='+str(installation),'--datadir='+str(data),'--bind-address=127.0.0.1','--port='+str(config['port']),'--mysqlx=OFF','--innodb-buffer-pool-size=128M'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        for _ in range(45):
            try:
                with socket.create_connection((config['host'],config['port']),timeout=1):break
            except OSError:time.sleep(1)
        else:raise SystemExit('MySQL did not start; inspect the private runtime log.')
    command=[sys.executable,'-m','waitress','--listen=127.0.0.1:8000','mednova.wsgi:application']
else:
    command=[sys.executable,'manage.py',*args]
raise SystemExit(subprocess.call(command,cwd=base,env=env))
