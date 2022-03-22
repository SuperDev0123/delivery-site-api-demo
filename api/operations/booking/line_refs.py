import logging
from api.models import Bookings, Booking_lines, Booking_lines_data
from api.common import trace_error, constants as dme_constants

logger = logging.getLogger(__name__)


def _get_pk_booking_ids(bookings):
    _pk_booking_ids = []

    try:
        for booking in bookings:
            pk_booking_id.append(booking.pk_booking_id)
    except:
        for booking in bookings:
            pk_booking_id.append(booking["pk_booking_id"])

    return _pk_booking_ids


def get_gapRas(bookings):
    pk_booking_ids = _get_pk_booking_ids(bookings)
    return Booking_lines_data.objects.filter(
        fk_booking_id__in=pk_booking_ids, gap_ra__isnull=False
    ).only("gap_ra", "client_item_reference")


def get_clientRefNumbers(bookings):
    pk_booking_ids = _get_pk_booking_ids(bookings)
    return Booking_lines_data.objects.filter(
        fk_booking_id__in=pk_booking_ids, client_item_reference__isnull=False
    ).only("fk_booking_id", "client_item_reference")


# TODO
# def get_(bookings):
#     pk_booking_ids = _get_pk_booking_ids(bookings)
#     return Booking_lines.objects.filter(fk_booking_id__in=pk_booking_ids).only(
#         "fk_booking_id", "e_Total_KG_weight", "e_1_Total_dimCubicMeter"
#     )
