from api.models import Bookings
from api.operations.labels import ship_it, dhl


def build_label(booking_pk, file_path, format="ship_it"):
    if not booking_pk:
        raise Exception("Booking does not found.")

    booking = Bookings.objects.filter(id=booking_pk).first()

    if not booking:
        raise Exception("Booking does not found.")

    result = None

    if format == "ship_it":
        result = ship_it.build_label(booking, file_path)
    elif format == "dhl":
        result = dhl.build_label(booking, file_path)

    return result


def build_label_with_lines(booking, lines, file_path, format="ship_it"):
    result = None

    if format == "ship_it":
        result = ship_it.build_label_with_lines(booking, lines, file_path)
    elif format == "dhl":
        result = dhl.build_label_with_lines(booking, lines, file_path)

    return result
