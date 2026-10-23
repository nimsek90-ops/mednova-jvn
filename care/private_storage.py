"""Safe responses for private-file outages, without exposing provider details."""
from botocore.exceptions import BotoCoreError, ClientError
from django.http import HttpResponse

STORAGE_ERRORS = (OSError, BotoCoreError, ClientError)


def unavailable():
    response = HttpResponse('Private file storage is temporarily unavailable. Please retry or contact the hospital.', status=503)
    response['Retry-After'] = '60'
    response['Cache-Control'] = 'private, no-store'
    return response
