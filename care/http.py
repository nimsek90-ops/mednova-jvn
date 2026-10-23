"""Small HTTP helpers shared by views; no hospital models or permission policy."""
from functools import wraps
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.http import Http404
from django.shortcuts import render


def integer_id(value):
    try:
        number = int(value)
        if number <= 0:
            raise ValueError()
        return number
    except (ValueError, TypeError, OverflowError):
        raise Http404()


def paged(request, queryset, size=30):
    return Paginator(queryset, size).get_page(request.GET.get('page', 1))


def database_error_page(template, *, retry_after=None):
    """Catch DB failures outside a view's transaction, preserving its error page."""
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                return view(request, *args, **kwargs)
            except DatabaseError:
                response = render(request, template, status=503)
                if retry_after is not None:
                    response['Retry-After'] = str(retry_after)
                return response
        return wrapped
    return decorate
