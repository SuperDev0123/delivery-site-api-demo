from django.core.management.base import BaseCommand
from api.models import Booking_lines

from api.helpers.cubic import get_cubic_meter


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("----- Fetching lines... -----")
        booking_lines = Booking_lines.objects.filter(
            e_dimLength__isnull=False,
            e_dimWidth__isnull=False,
            e_dimHeight__isnull=False,
            e_dimUOM__isnull=False,
        ).only(
            "e_dimLength",
            "e_dimWidth",
            "e_dimHeight",
            "e_dimUOM",
            "e_1_Total_dimCubicMeter",
        )
        print(f"Fetched {booking_lines.count()} lines")
        print("----- Calculating cubic meter... -----")
        update_row_count = 0
        for index, booking_line in enumerate(booking_lines):
            if index + 1 % 100 == 0:
                print(f"Processed {index} lines")

            old_e_1_Total_dimCubicMeter = booking_line.e_1_Total_dimCubicMeter
            booking_line.e_1_Total_dimCubicMeter = get_cubic_meter(
                booking_line.e_dimLength,
                booking_line.e_dimWidth,
                booking_line.e_dimHeight,
                booking_line.e_dimUOM,
            )

            if old_e_1_Total_dimCubicMeter != booking_line.e_1_Total_dimCubicMeter:
                update_row_count += 1
                booking_line.save()
        print(f"\n'e_1_Total_dimCubicMeter' updated on {update_row_count} of rows")
        print("\n----- Finished! -----")
