from .models import Hospital


def common(request):
    query = request.GET.copy()
    query.pop("page", None)
    return {
        "page_query": query.urlencode(),
        "hospital": Hospital.objects.first(),
        "language": getattr(request, "language", "en"),
    }
