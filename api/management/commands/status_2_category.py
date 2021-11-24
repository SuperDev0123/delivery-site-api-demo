from datetime import datetime

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
                    "On Hold",
                    "Entered",
                    "Picking",
                    "Picked",
                ]
            )
            .exclude(z_lock_status=True)
            .only(
                "id",
                "b_bookingID_Visual",
                "b_status",
                "b_booking_Category",
                "z_ModifiedTimestamp",
            )
            .order_by("z_ModifiedTimestamp")
        )
        utl_categories = Utl_dme_status.objects.all()
        bookings_cnt = bookings.count()
        print(f"Bookings Cnt: {bookings_cnt}")

        for index, booking in enumerate(bookings):
            category = None

            for utl_category in utl_categories:
                if booking.b_status == utl_category.dme_delivery_status:
                    category = utl_category.dme_delivery_status_category
                    break

            if category and category != booking.b_booking_Category:
                print(
                    f"Processing {index + 1}/{bookings_cnt} {booking.b_bookingID_Visual}, {booking.b_status}({booking.b_booking_Category}) -> {category}, {booking.z_ModifiedTimestamp}"
                )
                booking.z_ModifiedTimestamp = datetime.now()
                booking.b_booking_Category = category
                booking.save()

        # print("\n----- Finished! -----")
