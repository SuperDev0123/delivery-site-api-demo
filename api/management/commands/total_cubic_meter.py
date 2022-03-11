from django.core.management.base import BaseCommand
from api.models import (
    Booking_lines
)
from bulk_update.helper import bulk_update

from api.helpers.cubic import get_cubic_meter

class Command(BaseCommand):
    def handle(self, *args, **options):
        booking_lines = Booking_lines.objects.filter(
            e_1_Total_dimCubicMeter__isnull=True,
            e_dimLength__isnull=False,
            e_dimWidth__isnull=False,
            e_dimHeight__isnull=False,
            e_dimUOM__isnull=False,
        ).order_by('-pk_lines_id')

        for booking_line in booking_lines:
            booking_line.e_1_Total_dimCubicMeter = get_cubic_meter(
                booking_line.e_dimLength,
                booking_line.e_dimWidth,
                booking_line.e_dimHeight,
                booking_line.e_dimUOM,
            )
        update_row_count = bulk_update(booking_lines)
        print("e_1_Total_dimCubicMeter updated on {update_row_count} of rows")
        
