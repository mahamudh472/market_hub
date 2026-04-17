from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import requests


def initiate_sslcommerz_payment(request, order, address_snapshot):
    """Create an SSLCommerz session and return its gateway url."""
    if not settings.SSLCOMMERZ_STORE_ID or not settings.SSLCOMMERZ_STORE_PASSWORD or not settings.SSLCOMMERZ_API_URL:
        raise ValueError('SSLCommerz settings are not configured.')

    base_url = request.build_absolute_uri('/')[:-1] + '/api/v1'
    tran_id = str(order.id)

    payload = {
        'store_id': settings.SSLCOMMERZ_STORE_ID,
        'store_passwd': settings.SSLCOMMERZ_STORE_PASSWORD,
        'total_amount': str(order.total),
        'currency': 'BDT',
        'tran_id': tran_id,
        'success_url': f'{base_url}/orders/payment/success/',
        'fail_url': f'{base_url}/orders/payment/fail/',
        'cancel_url': f'{base_url}/orders/payment/cancel/',
        'ipn_url': f'{base_url}/orders/payment/ipn/',
        'cus_name': address_snapshot.get('full_name', 'Customer'),
        'cus_email': request.user.email,
        'cus_add1': address_snapshot.get('address', ''),
        'cus_phone': address_snapshot.get('phone_number', ''),
        'product_name': f'Order {order.order_number}',
        'product_category': 'General',
        'product_profile': 'general',
    }

    response = requests.post(settings.SSLCOMMERZ_API_URL, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get('status') != 'SUCCESS' or not data.get('GatewayPageURL'):
        raise ValueError(data.get('failedreason') or 'Could not generate SSLCommerz payment url.')

    return {
        'payment_url': data['GatewayPageURL'],
        'gateway_response': data,
        'transaction_id': tran_id,
    }

def validate_payment(val_id):
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
