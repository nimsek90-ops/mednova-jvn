from .models import Hospital
from django.conf import settings


def common(request):
    query = request.GET.copy()
    query.pop("page", None)
    return {
        "demo_mode": settings.LOCAL and (settings.TESTING or settings.LOCAL_DEMO),
        "page_query": query.urlencode(),
        "hospital": Hospital.objects.first(),
        "language": getattr(request, "language", "en"),
    }
