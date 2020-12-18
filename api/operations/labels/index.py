from api.models import Bookings
from api.operations.labels import ship_it, dhl, hunter


def build_label(booking, file_path, lines=[]):
    result = None
    fp_name = booking.vx_freight_provider.lower()

    if fp_name == "auspost":
        result = ship_it.build_label(booking, file_path, lines)
    elif fp_name == "dhl":
        result = dhl.build_label(booking, file_path, lines)
    elif fp_name == "hunter":
        result = hunter.build_label(booking, file_path, lines)

    return result


def get_barcode(booking, booking_lines):
    result = None
    fp_name = booking.vx_freight_provider.lower()

    if fp_name == "auspost":
        result = ship_it.gen_barcode(booking, booking_lines)
    # elif fp_name == "dhl":
    #     result = dhl.build_label(booking, file_path, lines)
    elif fp_name == "hunter":
        result = hunter.gen_barcode(booking, booking_lines)

    return result
