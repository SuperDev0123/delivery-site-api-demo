import logging

from rest_framework.decorators import (
    api_view,
    permission_classes,
    action,
)
from rest_framework.response import Response
from rest_framework import authentication, permissions, viewsets
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK, HTTP_201_CREATED

from api.models import Bookings, FP_status_history
from api.serializers import FPStatusHistorySerializer

logger = logging.getLogger(__name__)


class ScansViewSet(viewsets.ViewSet):
    serializer_class = FPStatusHistorySerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def get_scans_from_booking_id(self, request, pk=None):
        from api.fp_apis.utils import get_dme_status_from_fp_status

        booking_id = request.GET.get("bookingId")
        try:
            if not booking_id:
                booking = Bookings.objects.all().order_by("-z_CreatedTimestamp")[0]
                booking_id = booking.id

            booking = Bookings.objects.get(id=booking_id)
            fp_status_history = (
                FP_status_history.objects.values("status", "desc", "event_timestamp")
                .filter(booking_id=booking_id)
                .order_by("-event_timestamp")
            )
            fp_status_history = [item for item in fp_status_history]
            return Response({"scans": fp_status_history}, status=HTTP_200_OK)
        except Exception as e:
            logger.info(f"Get FP status history error: {str(e)}")
            return Response({"msg": str(e)}, status=HTTP_400_BAD_REQUEST)
