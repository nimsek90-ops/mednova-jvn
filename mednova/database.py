"""Explicit database selection. No network calls or credential logging."""
import re
from django.core.exceptions import ImproperlyConfigured


def postgres_database(env, local=False):
    required = ('PGHOST', 'PGDATABASE', 'PGUSER', 'PGPASSWORD')
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise ImproperlyConfigured('Missing PostgreSQL settings: ' + ', '.join(missing))
    schema = env.get('PGSCHEMA', 'mednova')
    if not re.fullmatch(r'[a-z_][a-z0-9_]*', schema):
        raise ImproperlyConfigured('PGSCHEMA must be a simple lowercase schema identifier.')
    sslmode = env.get('PGSSLMODE', 'verify-full')
    if not local and (sslmode != 'verify-full' or not env.get('PGSSLROOTCERT')):
        raise ImproperlyConfigured('Production PostgreSQL requires verify-full and PGSSLROOTCERT.')
    if not local and schema == 'public':
        raise ImproperlyConfigured('Use a private application schema for Django PostgreSQL.')
    if sslmode not in ('disable', 'require', 'verify-ca', 'verify-full'):
        raise ImproperlyConfigured('Invalid PGSSLMODE.')
    options = {'connect_timeout': 10, 'sslmode': sslmode,
               'options': f'-c search_path={schema} -c statement_timeout=15000',
               'prepare_threshold': None}
    if env.get('PGSSLROOTCERT'):
        options['sslrootcert'] = env['PGSSLROOTCERT']
    return {'ENGINE': 'django.db.backends.postgresql', 'NAME': env['PGDATABASE'],
            'USER': env['PGUSER'], 'PASSWORD': env['PGPASSWORD'], 'HOST': env['PGHOST'],
            'PORT': env.get('PGPORT', '5432'), 'CONN_MAX_AGE': 0,
            'CONN_HEALTH_CHECKS': True, 'DISABLE_SERVER_SIDE_CURSORS': True,
            'OPTIONS': options}
