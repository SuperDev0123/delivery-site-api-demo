from django.core.management.base import BaseCommand

from api.models import Bookings
from api.fp_apis.utils import get_status_category_from_status


class Command(BaseCommand):
    def handle(self, *args, **options):
        # print("----- Populating category from status... -----")
        bookings = (
            Bookings.objects.filter(b_status__isnull=False)
            .exclude(
                b_status__in=[
                    "Delivered",
                    "Ready for Booking",
                    "Ready for Despatch",
                    "On Hold",
                    "Entered",
                ]
            )
            .exclude(z_lock_status=True)
            .only("id", "b_bookingID_Visual", "b_status", "b_booking_Category")
        )
        bookings_cnt = bookings.count()

        for index, booking in enumerate(bookings):
            category = get_status_category_from_status(booking.b_status)

            if category != booking.b_booking_Category:
                print(
                    f"Processing {index + 1}/{bookings_cnt} {booking.b_bookingID_Visual}, {booking.b_status} -> {category}"
                )
                booking.b_booking_Category = category
                booking.save()

        # print("\n----- Finished! -----")
