from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated, AllowAny

from .serializers_api import *
from .models import *
from django.conf import settings


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
                {"status": "success", "b_status": booking.b_status}, status=200
            )
        except Bookings.DoesNotExist:
            return JsonResponse(
                {"status": "error", "error": "No matching Booking"}, status=400
            )
