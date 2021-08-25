import json
import logging
import requests

from django.core.management.base import BaseCommand

from api.models import Bookings
from api.fp_apis.payload_builder import get_tracking_payload
from api.fp_apis.constants import S3_URL, DME_LEVEL_API_URL
from api.fp_apis.operations.tracking import _extract as extract_status

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("----- Populating `b_given_to_transport_date_time` ... -----")
        bookings = (
            Bookings.objects.filter(b_given_to_transport_date_time__isnull=True)
            .filter(vx_freight_provider__in=["TNT", "HUNTER", "SENDLE", "ALLIED"])
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

            try:
                consignmentStatuses = get_tracking_info_from_FP(booking)
                consignmentStatuses = sort_consignment_statuses(
                    booking, consignmentStatuses
                )
                dme_statuses = get_dme_status(booking, consignmentStatuses)
                transit_statuses = get_transit_infos(booking, dme_statuses)

                if transit_statuses:
                    print(
                        f"    {booking.b_bookingID_Visual} - {str(transit_statuses[0]['event_time'])}"
                    )
            except Exception as e:
                print(
                    f"    Issue from Booking({booking.b_bookingID_Visual} - {booking.vx_freight_provider}), Error: {str(e)}"
                )
                pass

        print("\n----- Finished! -----")


def get_transit_infos(booking, dme_statuses):
    _transit_infos = []

    for status in dme_statuses:
        if status["b_status_category"] == "Transit":
            _transit_infos.append(status)

    return _transit_infos


def get_dme_status(booking, consignmentStatuses):
    from api.fp_apis.utils import get_dme_status_from_fp_status
    from api.fp_apis.utils import get_status_category_from_status

    dme_statuses = []
    fp_name = booking.vx_freight_provider.lower()

    for consignmentStatuse in consignmentStatuses:
        b_status_API, status_desc, event_time = extract_status(
            fp_name.lower(), consignmentStatuse
        )
        b_status = get_dme_status_from_fp_status(fp_name, b_status_API, booking)
        dme_category = get_status_category_from_status(b_status)
        dme_statuses.append(
            {
                "b_status": b_status,
                "b_status_category": dme_category,
                "b_status_API": b_status_API,
                "status_desc": status_desc,
                "event_time": event_time,
            }
        )

    return dme_statuses


def sort_consignment_statuses(booking, consignmentStatuses):
    fp_name = booking.vx_freight_provider.lower()
    _consignmentStatuses = consignmentStatuses

    if fp_name.lower() == "allied":
        # Sort by timestamp
        _consignmentStatuses = sorted(
            consignmentStatuses, key=lambda x: x["statusUpdate"]
        )

        # Check Partially Delivered
        has_delivered_status = False
        delivered_status_cnt = 0
        last_consignmentStatus = _consignmentStatuses[len(_consignmentStatuses) - 1]

        for _consignmentStatus in _consignmentStatuses:
            if _consignmentStatus["status"] == "DEL":
                has_delivered_status = True
                delivered_status_cnt += 1

        if has_delivered_status:
            lines = booking.lines().filter(is_deleted=False)

            if delivered_status_cnt < lines.count():
                logger.info(
                    f"#382 [TRACKING] Allied Partially Delivered BookingId: {booking.b_bookingID_Visual}, statuses: {_consignmentStatuses}"
                )
                _consignmentStatuses.append(
                    {
                        "status": "PARTDEL",
                        "statusDescription": "Partially Delivered",
                        "statusUpdate": last_consignmentStatus["statusUpdate"],
                    }
                )

    return _consignmentStatuses


def get_tracking_info_from_FP(booking):
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

    return consignmentStatuses
