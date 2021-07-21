import logging

from api.models import Bookings, Fp_freight_providers
from api.operations.labels import (
    ship_it,
    dhl,
    hunter,
    hunter_normal,
    hunter_thermal,
    tnt,
    allied,
    default
)

logger = logging.getLogger(__name__)


def build_label(
    booking,
    file_path,
    lines=[],
    label_index=0,
    sscc=None,
    sscc_cnt=1,
    one_page_label=False,
):
    fp_name = booking.vx_freight_provider.lower()

    try:
        if fp_name == "dhl":
            file_path, file_name = dhl.build_label(
                booking, file_path, lines, label_index, sscc, sscc_cnt, one_page_label
            )
        elif fp_name == "hunter":
            file_path, file_name = hunter_normal.build_label(
                booking, file_path, lines, label_index, sscc, sscc_cnt, one_page_label
            )
        elif fp_name == "tnt":
            file_path, file_name = tnt.build_label(
                booking, file_path, lines, label_index, sscc, sscc_cnt, one_page_label
            )
        elif fp_name == "allied":
            file_path, file_name = allied.build_label(
                booking, file_path, lines, label_index, sscc, sscc_cnt, one_page_label
            )
        else:  # "Century", "ATC", "JasonL In house"
            file_path, file_name = default.build_label(
                booking, file_path, lines, label_index, sscc, sscc_cnt, one_page_label
            )

        return file_path, file_name
    except Exception as e:
        logger.error(f"[LABEL] error: {str(e)}")
        return None


def get_barcode(booking, booking_lines):
    """
    Get barcode for label
    """
    result = None
    fp_name = booking.vx_freight_provider.lower()

    if fp_name == "hunter":
        result = hunter.gen_barcode(booking, booking_lines)
    else:  # "auspost", "startrack", "TNT", "State Transport"
        result = ship_it.gen_barcode(booking, booking_lines)

    return result
