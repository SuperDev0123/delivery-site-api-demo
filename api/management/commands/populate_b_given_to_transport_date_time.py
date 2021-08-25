import json
import logging
import requests

from django.core.management.base import BaseCommand

from api.models import Bookings
from api.fp_apis.payload_builder import get_tracking_payload
from api.fp_apis.constants import S3_URL, DME_LEVEL_API_URL

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("----- Populating `b_given_to_transport_date_time` ... -----")
        bookings = (
            Bookings.objects.filter(b_given_to_transport_date_time__isnull=True)
            .exclude(
                b_status__in=[
                    "Entered",
                    "Ready for Despatch",
                    "Ready for Booking",
                    "Picking",
                    "Picked",
                    "Booked",
                ]
            )
            .only(
                "id",
                "b_bookingID_Visual",
                "vx_freight_provider",
                "b_status",
                "b_given_to_transport_date_time",
            )
        )
        bookings_cnt = bookings.count()
        print(f"    Bookings to process: {bookings_cnt}")

        for index, booking in enumerate(bookings[:20]):
            if index % 10 == 0:
                print(f"    {index}/{bookings_cnt} processing...")

            fp_name = booking.vx_freight_provider.lower()
            payload = get_tracking_payload(booking, fp_name)
            logger.info(f"### Payload ({fp_name} tracking): {payload}")
            url = DME_LEVEL_API_URL + "/tracking/trackconsignment"
            response = requests.post(url, params={}, json=payload)

            if fp_name.lower() in ["tnt"]:
                res_content = response.content.decode("utf8")
            else:
                res_content = response.content.decode("utf8").replace("'", '"')

            json_data = json.loads(res_content)
            s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
            logger.info(f"### Response ({fp_name} tracking): {s0}")

            consignmentTrackDetails = json_data["consignmentTrackDetails"][0]
            consignmentStatuses = consignmentTrackDetails["consignmentStatuses"]
            console.log("@1 - ", consignmentStatuses)

        print("\n----- Finished! -----")
