from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse

def validate_payment(val_id):
    import requests
    from django.conf import settings

    params = {
        "val_id": val_id,
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "v": "1",
        "format": "json"
    }

    response = requests.get(settings.SSLCOMMERZ_VALIDATION_URL, params=params)
    return response.json()

@csrf_exempt
def payment_ipn(request):
    if request.method == "POST":
        val_id = request.POST.get("val_id")
        tran_id = request.POST.get("tran_id")

        validation_data = validate_payment(val_id)

        if validation_data.get("status") == "VALID":
            # TODO:
            # 1. Check tran_id exists
            # 2. Check amount matches
            # 3. Mark order as paid

            print("Payment success:", tran_id)

        return HttpResponse("OK")

@csrf_exempt
def payment_success(request):
    val_id = request.POST.get("val_id")

    data = validate_payment(val_id)

    if data.get("status") == "VALID":
        return JsonResponse({"message": "Payment successful"})
    
    return JsonResponse({"message": "Validation failed"}, status=400)


@csrf_exempt
def payment_fail(request):
    return JsonResponse({"message": "Payment failed"})

@csrf_exempt
def payment_cancel(request):
    return JsonResponse({"message": "Payment cancelled"})
