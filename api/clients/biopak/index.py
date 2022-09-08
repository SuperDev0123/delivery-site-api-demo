from base64 import b64encode

from django.conf import settings

from api.models import Bookings, Booking_lines


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
    )

    pk_booking_ids = [booking.pk_booking_id for booking in bookings]
    lines = Booking_lines.objects.filter(
        fk_booking_id__in=pk_booking_ids, packed_status=Booking_lines.SCANNED_PACK
    )

    if item_description:
        lines = lines.filter(e_item=item_description)

    for booking in bookings:
        booking_lines = []
        label = {"reference": booking.b_clientReference_RA_Numbers}
        label[booking.b_clientReference_RA_Numbers] = {}

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
