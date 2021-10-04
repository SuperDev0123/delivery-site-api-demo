from django.core.management.base import BaseCommand

from api.models import Bookings, Utl_dme_status
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
            .exclude(z_lock_status=False)
            .only("id", "b_bookingID_Visual", "b_status", "b_booking_Category")
            .order_by("z_ModifiedTimestamp")
        )
        utl_categories = Utl_dme_status.objects.all()
        bookings_cnt = bookings.count()

        for index, booking in enumerate(bookings):
            category = None

            for utl_category in utl_categories:
                if booking.b_status == utl_category.dme_delivery_status:
                    category = utl_category.dme_delivery_status_category
                    break

            if category and category != booking.b_booking_Category:
                print(
                    f"Processing {index + 1}/{bookings_cnt} {booking.b_bookingID_Visual}, {booking.b_status} -> {category}"
                )
                booking.b_booking_Category = category
                booking.save()

        # print("\n----- Finished! -----")
