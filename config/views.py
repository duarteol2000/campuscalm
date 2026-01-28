from django.http import JsonResponse
from django.utils import timezone


def health_check(_request):
    return JsonResponse({"status": "ok", "timestamp": timezone.now().isoformat()})
