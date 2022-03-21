import logging
from api.models import Bookings, Booking_lines, Booking_lines_data
from api.common import trace_error, constants as dme_constants

logger = logging.getLogger(__name__)


def get_gapRas(booking):
    try:
        gap_ras = []

        try:
            pk_booking_id = booking.pk_booking_id
        except:
            pk_booking_id = booking["pk_booking_id"]

        booking_lines_data = Booking_lines_data.objects.filter(
            fk_booking_id=pk_booking_id
        )
        for booking_line_data in booking_lines_data:
            if booking_line_data.gap_ra:
                gap_ras.append(booking_line_data.gap_ra)
        return ", ".join(gap_ras)
    except Exception as e:
        trace_error.print()
        logger.error(f"#555 [gap_ras] - {str(e)}")
        return ""


def get_clientRefNumbers(booking):
    try:
        client_item_references = []

        try:
            pk_booking_id = booking.pk_booking_id
        except:
            pk_booking_id = booking["pk_booking_id"]

        booking_lines_data = Booking_lines_data.objects.filter(
            fk_booking_id=pk_booking_id
        )
        for booking_line in booking_lines:
            if booking_line.client_item_reference is not None:
                client_item_references.append(booking_line.client_item_reference)

        return ", ".join(client_item_references)
    except Exception as e:
        trace_error.print()
        logger.error(f"#553 [client_item_references] - {str(e)}")
        return ""
