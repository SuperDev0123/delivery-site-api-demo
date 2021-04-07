from api.models import Bookings, Fp_freight_providers
from api.operations.labels import ship_it, dhl, hunter, tnt


def build_label(booking, file_path, lines=[], label_index=0, sscc=None):
    fp_name = booking.vx_freight_provider.lower()

    if fp_name == "dhl":
        file_path, file_name = dhl.build_label(
            booking,
            file_path,
            lines,
            label_index,
            sscc,
        )
    elif fp_name == "hunter":
        file_path, file_name = hunter.build_label(
            booking,
            file_path,
            lines,
            label_index,
            sscc,
        )
    elif fp_name == "tnt":
        file_path, file_name = tnt.build_label(
            booking,
            file_path,
            lines,
            label_index,
            sscc,
        )
    else:  # "auspost", "startrack", "TNT", "State Transport", "ship-it", "Allied"
        file_path, file_name = ship_it.build_label(
            booking,
            file_path,
            lines,
            label_index,
            sscc,
        )

    return file_path, file_name


def get_barcode(booking, booking_lines):
    """
    Build barcode for label
    """
    result = None
    fp_name = booking.vx_freight_provider.lower()

    if fp_name == "hunter":
        result = hunter.gen_barcode(booking, booking_lines)
    else:  # "auspost", "startrack", "TNT", "State Transport"
        result = ship_it.gen_barcode(booking, booking_lines)

    return result
