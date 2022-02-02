import subprocess

from django.core.management.base import BaseCommand

from api.models import Bookings


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("----- Get JasonL orders status... -----")
        bookings = (
            Bookings.objects.select_related("api_booking_quote")
            .filter(b_dateBookedDate__isnull=True, b_client_name="Jason L")
            .only(
                "id",
                "b_bookingID_Visual",
                "vx_freight_provider",
                "b_status",
                "b_status_category",
                "api_booking_quote",
                "b_client_order_num",
            )
        )
        bookings_cnt = bookings.count()
        print(f"Bookings count: {bookings_cnt}")

        results = []
        for index, booking in enumerate(bookings[:10]):
            # - Split `order_num` and `suffix` -
            _order_num, suffix = booking.b_client_order_num, ""
            iters = _order_num.split("-")

            if len(iters) > 1:
                _order_num, suffix = iters[0], iters[1]

            print(f"OrderNum: {_order_num}, Suffix: {suffix}")
            # ---

            subprocess.run(
                [
                    "/home/ubuntu/jason_l/status/src/run.sh",
                    "--context_param",
                    f"param1={_order_num}",
                    "--context_param",
                    f"param2={suffix}",
                ]
            )
            file_path = "/home/ubuntu/jason_l/status/src/status.csv"
            csv_file = open(file_path)
            logger.info(f"@350 {LOG_ID} File({file_path}) opened!")

            if len(csv_file) > 1:
                results.append(csv_file[1])

        print(f"\nResult:\n {results}")
        print("\n----- Finished! -----")