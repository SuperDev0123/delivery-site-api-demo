from api.models import Bookings
from api.operations.labels import ship_it, dhl, hunter


def build_label(booking, file_path, format="ship_it", lines=[]):
    result = None

    if format == "ship_it":
        result = ship_it.build_label(booking, file_path, lines)
    elif format == "dhl":
        result = dhl.build_label(booking, file_path, lines)
    elif format == "hunter":
        result = hunter.build_label(booking, file_path, lines)

    return result
