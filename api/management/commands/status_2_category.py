from django.core.management.base import BaseCommand

from api.models import Bookings
from api.fp_apis.utils import get_status_category_from_status


class Command(BaseCommand):
    def handle(self, *args, **options):
        # print("----- Populating category from status... -----")
        bookings = Bookings.objects.filter(b_status__isnull=False).only(
            "id", "b_bookingID_Visual", "b_status", "b_booking_Category"
        )
        bookings_cnt = bookings.count()

        for index, booking in enumerate(bookings):
            category = get_status_category_from_status(booking.b_status)
            # print(
            #     f"Processing {index + 1}/{bookings_cnt} {booking.b_bookingID_Visual}, {booking.b_status} -> {category}"
            # )
            booking.b_booking_Category = category
            booking.save()

        # print("\n----- Finished! -----")
