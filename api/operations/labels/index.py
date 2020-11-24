from api.models import Bookings
from api.operations.labels import ship_it


def build_label(booking_pk, file_path, format="ship_it"):
    if not booking_pk:
        raise Exception("Booking does not found.")

    booking = Bookings.objects.filter(id=booking_pk).first()

    if not booking:
        raise Exception("Booking does not found.")

    result = ship_it.build_label(booking, file_path)

    return result
