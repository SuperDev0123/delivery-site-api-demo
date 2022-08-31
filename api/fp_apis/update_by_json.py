import json

import logging

from django.conf import settings

from api.models import Bookings
from api.common import sftp, trace_error

if settings.ENV == "local":
    production = False  # Local
else:
    production = True  # Dev

logger = logging.getLogger(__name__)
# sftp server infos
sftp_server_infos = {
    "biopak": {
        "type": "Client",
        "name": "BIOPAK",
        "host": "ftp.biopak.com.au",
        "username": "dme_biopak",
        "password": "3rp2NcHS",
        "sftp_filepath": "/DME/TRACK/",
    }
}


def build_json(booking):
    json_content = {
        "b_clientReference_RA_Numbers": booking.b_clientReference_RA_Numbers,
        "consignment_number": booking.v_FPBookingNumber,
        "dme_booking_number": booking.b_bookingID_Visual,
        "booked_timestamp": str(booking.z_CreatedTimestamp),
        "status": booking.b_status,
        "warehouse_code": booking.fk_client_warehouse.client_warehouse_code,
        "freight_provider": booking.vx_freight_provider,
        "shipment_id": booking.fk_fp_pickup_id,
    }

    return json.dumps(json_content)


def update_biopak_with_booked_booking(booking_id):
    LOG_ID = "[BIOPAK UPDATE VIA JSON]"

    if not settings.ENV == "prod":
        return

    try:
        booking = Bookings.objects.get(pk=booking_id)
        json_file_name = (
            booking.b_clientReference_RA_Numbers
            + "__"
            + booking.pk_booking_id
            + ".json"
        )

        if production:
            local_filepath = "/home/cope_au/dme_sftp/biopak_au/jsons/indata/"
            local_filepath_archive = "/home/cope_au/dme_sftp/biopak_au/jsons/archive/"
        # else:
        #     local_filepath = "./static/jsons/"
        #     local_filepath_archive = "./static/jsons/archive/"

        json_file = open(local_filepath + json_file_name, "w")
        json_content = build_json(booking)
        json_file.write(json_content)
        json_file.close()

        sftp.upload_sftp(
            sftp_server_infos["biopak"]["host"],
            sftp_server_infos["biopak"]["username"],
            sftp_server_infos["biopak"]["password"],
            sftp_server_infos["biopak"]["sftp_filepath"],
            local_filepath,
            local_filepath_archive,
            json_file_name,
        )
        logger.error(
            f"{LOG_ID} Booking: {booking.b_bookingID_Visual}, Status: SUCCESS!"
        )
    except Exception as e:
        logger.error(f"{LOG_ID} Booking: {booking.b_bookingID_Visual}, Error: {str(e)}")
        trace_error.print()
        pass
