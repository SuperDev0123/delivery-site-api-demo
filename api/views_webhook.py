import logging
import json

from django.http import JsonResponse
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)

from api.models import Bookings, FP_status_history
from api.common import common_times as dme_time_lib, status_history
from api.fp_apis.operations.tracking import create_fp_status_history
from api.fp_apis.utils import (
    get_dme_status_from_fp_status,
    get_status_category_from_status,
)
from api.clients.biopak.index import update_biopak

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes((AllowAny,))
def st_tracking_webhook(request):
    LOG_ID = "[ST TRACK WEBHOOK]"
    logger.info(f"{LOG_ID} Payload: {request.data}")

    try:
        consignment_num = request.data["{www.startrack.com.au/events}Consignment"]
        status = request.data["{www.startrack.com.au/events}EventStatus"]
        event_at = request.data["{www.startrack.com.au/events}EventDateTime"]
        signature_name = request.data["{www.startrack.com.au/events}SignatureName"]
        signature_img = request.data["{www.startrack.com.au/events}SignatureImage"]

        bookings = Bookings.objects.filter(
            vx_freight_provider="Startrack", v_FPBookingNumber=consignment_num
        )

        # If Booking does exist
        if not bookings.exists():
            logger.info(f"{LOG_ID} Does not exist: {consignment_num}")
            return JsonResponse({}, status=200)

        booking = Bookings.first()
        fp_status_histories = FP_status_history.objects.filter(
            booking=booking
        ).order_by("id")

        # If event is duplicated
        if fp_status_histories.exists():
            last_fp_status = FP_status_history.last()
            if last_fp_status.status == status:
                logger.info(
                    f"{LOG_ID} Same with previous event. FP status: {consignment_num}"
                )
                return JsonResponse({}, status=200)

        fp = Fp_freight_providers.objects.get(fp_company_name="Startrack")
        fp_status_history_data = {
            "b_status_API": status,
            "status_desc": "",
            "event_time": event_at,
        }
        create_fp_status_history(booking, fp, fp_status_history_data)
        dme_status = get_dme_status_from_fp_status(fp.fp_company_name, status, booking)
        status_history.create(booking, dme_status, LOG_ID)

        # if booking.b_client_name == "BioPak":
        #     update_biopak(booking, fp, status, event_at)

        return JsonResponse({}, status=200)
    except Exception as e:
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"errorCode": "failure", "errorMessage": str(e)}, status=400
        )
