import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render
from billing.services.metering import MeteringService

meter_service = MeteringService()

@csrf_exempt
@require_POST
def ingest_usage_event(request):
    """
    High-speed event ingestion endpoint. Checks Redis tokens in under 5ms.
    Returns HTTP 429 if the quota limit is reached.
    """
    try:
        data = json.loads(request.body)
        customer_id = data.get("customer_id")
        limit = int(data.get("limit", 100))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid JSON payload or parameters"}, status=400)

    if not customer_id:
        return JsonResponse({"error": "customer_id is required"}, status=400)

    allowed, remaining = meter_service.check_quota(customer_id, limit)
    if not allowed:
        return JsonResponse(
            {
                "message": "Quota limit reached! Out of credits.", 
                "remaining_tokens": remaining
            }, 
            status=429
        )

    return JsonResponse({"status": "accepted", "remaining_tokens": remaining})

def dashboard(request):
    """
    Renders the beautiful interactive LedgerBill dashboard.
    """
    return render(request, "billing/dashboard.html")
