"""Start the Windows/local application and open it after binding the HTTP socket."""

import os
import threading
import webbrowser

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mednova.settings")
from mednova.wsgi import application
from django.conf import settings
from waitress import create_server

if not settings.LOCAL:
    raise SystemExit(
        "START_WINDOWS is for local review. Set APP_ENV=local in your private .env."
    )
server = create_server(
    application,
    host="127.0.0.1",
    port=8000,
    threads=8,
    max_request_body_size=6 * 1024 * 1024,
)
threading.Timer(0.5, lambda: webbrowser.open_new_tab("http://127.0.0.1:8000")).start()
print("MedNova: http://127.0.0.1:8000. Press Ctrl+C to stop.")
try:
    server.run()
except KeyboardInterrupt:
    server.close()
