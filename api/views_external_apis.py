import logging

from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.authentication import TokenAuthentication
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework import views, serializers, status
from rest_framework.permissions import IsAuthenticated, AllowAny

from api.serializers_api import *
from api.models import *
from api.operations import paperless

logger = logging.getLogger("external_apis")


@api_view(["GET"])
@authentication_classes([JSONWebTokenAuthentication])
def get_booking_status_by_consignment(request):
    v_FPBookingNumber = request.GET.get("consignment", None)

    if not v_FPBookingNumber:
        return JsonResponse(
            {"status": "error", "error": "Consignment is null"}, status=400
        )
    else:
        try:
            booking = Bookings.objects.get(v_FPBookingNumber=v_FPBookingNumber)
            return JsonResponse(
                {
                    "status": "success",
                    "b_status": booking.b_status_API,
                    "z_lastStatusAPI_ProcessedTimeStamp": booking.z_lastStatusAPI_ProcessedTimeStamp,
                },
                status=200,
            )
        except Bookings.DoesNotExist:
            return JsonResponse(
                {"status": "error", "error": "No matching Booking"}, status=400
            )


# Paperless
@api_view(["POST"])
def send_order_to_paperless(request):
    logger.info(f"@680 Paperless request payload - {request.data}")
    b_client_sales_inv_num = request.data.get("b_client_sales_inv_num")

    if not b_client_sales_inv_num:
        message = "'b_client_sales_inv_num' is required"
        raise ValidationError({"code": "missing_param", "description": message})

    bok_1 = BOK_1_headers.objects.filter(
        b_client_sales_inv_num=b_client_sales_inv_num
    ).first()

    if not bok_1:
        message = "bok_1 does not exist with given b_client_sales_inv_num"
        raise ValidationError({"code": "not_found", "description": message})

    result = paperless.send_order_info(bok_1)

    if not result:
        return JsonResponse(
            {"success": True, "error": "Unknown erorr"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return JsonResponse(
        {"success": True, "error": None, "message": result}, status=status.HTTP_200_OK
    )
