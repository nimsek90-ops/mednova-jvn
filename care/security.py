import hashlib
import hmac
from functools import wraps
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils import timezone
from .models import RateBucket, AuditEvent


def audit(user, action, target=""):
    AuditEvent.objects.create(
        actor=user if user and user.is_authenticated else None,
        action=action,
        target=str(target)[:120],
    )


def limited(key, limit, seconds):
    digest = hmac.new(
        settings.SECRET_KEY.encode(), key.encode(), hashlib.sha256
    ).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = RateBucket.objects.get_or_create(
            key=digest, defaults={"expires": now + timedelta(seconds=seconds)}
        )
        bucket = RateBucket.objects.select_for_update().get(pk=bucket.pk)
        if bucket.expires <= now:
            bucket.count = 0
            bucket.expires = now + timedelta(seconds=seconds)
        bucket.count += 1
        bucket.save(update_fields=["count", "expires"])
        return bucket.count > limit


def rate_limit(prefix, limit=30, seconds=60):
    def deco(fn):
        @wraps(fn)
        def wrapped(request, *a, **kw):
            who = (
                str(request.user.pk)
                if request.user.is_authenticated
                else request.META.get("REMOTE_ADDR", "unknown")
            )
            if limited(f"{prefix}:{who}", limit, seconds):
                response = HttpResponse(
                    "Too many requests. Please try again later.", status=429
                )
                response["Retry-After"] = str(seconds)
                return response
            return fn(request, *a, **kw)

        return wrapped

    return deco


def roles(*allowed, pending=False):
    def deco(fn):
        @wraps(fn)
        def wrapped(request, *a, **kw):
            u = request.user
            if not u.is_authenticated:
                return redirect("login")
            if not u.is_active or (not pending and u.approval != "approved"):
                return redirect("dashboard")
            if allowed and u.role not in allowed:
                return HttpResponseForbidden("You do not have access to this area.")
            return fn(request, *a, **kw)

        return wrapped

    return deco
