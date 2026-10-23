"""Start the unchanged Django app behind Render's HTTPS edge."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mednova.settings')

if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.core.management import call_command
    from waitress import serve

    port = int(os.environ.get('PORT', '10000'))
    if not 1 <= port <= 65535:
        raise SystemExit('PORT must be between 1 and 65535.')
    django.setup()
    call_command('collectstatic', interactive=False, verbosity=0)
    # WhiteNoise indexes collected assets when the WSGI middleware is created.
    from mednova.wsgi import application
    # TLS terminates at Render. Ignore arbitrary forwarded headers; only use
    # this production entrypoint behind the platform's HTTPS edge.
    serve(application, host='0.0.0.0', port=port, threads=4,
          url_scheme='http' if settings.LOCAL else 'https',
          clear_untrusted_proxy_headers=True, max_request_body_size=6 * 1024 * 1024)
