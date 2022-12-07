from base64 import b64encode
from datetime import datetime

from django.conf import settings

from api.models import Bookings, Booking_lines
from api.clients.biopak.constants import FTP_INFO
from api.common import sftp, trace_error


def reprint_label(params, client):
    """
    get label(already built)
    """
    LOG_ID = "[REPRINT BioPak]"
    b_clientReference_RA_Numbers = params.get("clientReferences")
    item_description = params.get("itemDescription")
    labels = []

    if not b_clientReference_RA_Numbers:
        message = "'clientReferences' is required."
        raise ValidationError(message)
    else:
        b_clientReference_RA_Numbers = b_clientReference_RA_Numbers.split(",")

    bookings = Bookings.objects.filter(
        b_clientReference_RA_Numbers__in=b_clientReference_RA_Numbers,
        b_client_name=client.company_name,
    ).exclude(b_status="Closed")

    pk_booking_ids = [booking.pk_booking_id for booking in bookings]
    lines = Booking_lines.objects.filter(
        fk_booking_id__in=pk_booking_ids, packed_status=Booking_lines.SCANNED_PACK
    )

    if item_description:
        lines = lines.filter(e_item=item_description)

    for booking in bookings:
        booking_lines = []
        label = {"reference": booking.b_clientReference_RA_Numbers}

        # Get each line's label
        label_lines = []
        for line in lines:
            if booking.pk_booking_id == line.fk_booking_id:
                filename = (
                    booking.pu_Address_State
                    + "_"
                    + str(booking.b_bookingID_Visual)
                    + "_"
                    + str(line.sscc)
                    + ".pdf"
                )
                label_url = f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au/{filename}"
                with open(label_url, "rb") as file:
                    pdf_data = str(b64encode(file.read()))[2:-1]
                label_line = {"itemid": line.e_item, "label_base64": pdf_data}
                label_lines.append(label_line)

        if not item_description:
            # Get merged label
            label_url = f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au/DME{booking.b_bookingID_Visual}.pdf"
            with open(label_url, "rb") as file:
                pdf_data = str(b64encode(file.read()))[2:-1]
            label["merged"] = pdf_data

        label["lines"] = label_lines
        labels.append(label)

    return {"success": True, "labels": labels}


def _csv_write(fp_path, f):
    pass


def update_biopak(booking, fp, status, event_at):
    csv_name = str(datetime.now().strftime("%d-%m-%Y__%H_%M_%S")) + ".csv"
    f = open(CSV_DIR + csv_name, "w")
    csv_write(fpath, f)
    f.close()

    sftp.upload_sftp(
        FTP_INFO["host"],
        FTP_INFO["username"],
        FTP_INFO["password"],
        FTP_INFO["sftp_filepath"],
        FTP_INFO["local_filepath"],
        FTP_INFO["local_filepath_archive"],
        csv_name,
    )
