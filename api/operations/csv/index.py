import os
from datetime import datetime

from django.conf import settings

from api.models import Bookings, Booking_lines
from api.operations.csv.cope import build_csv as build_COPE_csv
from api.operations.csv.dhl import build_csv as build_DHL_csv
from api.operations.csv.state_transport import build_csv as build_STATE_TRANSPORT_csv


def get_booking_lines(bookings):
    pk_booking_ids = bookings.values_list("pk_booking_id", flat=True)

    return Booking_lines.objects.filter(
        fk_booking_id__in=pk_booking_ids, is_deleted=False
    )


def build_csv(booking_ids):
    bookings = Bookings.objects.filter(pk__in=booking_ids)
    booking_lines = get_booking_lines(bookings)
    vx_freight_provider = bookings.first().vx_freight_provider.lower()
    now_str = str(datetime.now().strftime("%d-%m-%Y__%H_%M_%S"))

    # Generate CSV name
    if vx_freight_provider == "cope":
        csv_name = f"SEATEMP__{str(len(booking_ids))}__{now_str}.csv"
    elif vx_freight_provider == "dhl":
        csv_name = f"Seaway-Tempo-Aldi__{str(len(booking_ids))}__{now_str}.csv"
    elif vx_freight_provider == "state transport":
        csv_name = f"State-Transport__{str(len(booking_ids))}__{now_str}.csv"

    # Open CSV file
    if settings.ENV == "prod":
        if vx_freight_provider == "cope":
            f = open(f"/dme_sftp/cope_au/pickup_ext/cope_au/{csv_name}", "w")
        elif vx_freight_provider == "dhl":
            f = open(f"/dme_sftp/cope_au/pickup_ext/dhl_au/{csv_name}", "w")
        elif vx_freight_provider == "state transport":
            f = open(f"/dme_sftp/state_transport_au/csv/{csv_name}", "w")
    else:
        f = open(f"{settings.STATIC_PUBLIC}/csvs/{csv_name}", "w")

    # Build CSV
    if vx_freight_provider == "cope":
        has_error = build_COPE_csv(f, bookings, booking_lines)
    elif vx_freight_provider == "dhl":
        has_error = build_DHL_csv(f, bookings, booking_lines)
    elif vx_freight_provider == "state transport":
        has_error = build_STATE_TRANSPORT_csv(f, bookings, booking_lines)

    f.close()

    if has_error:
        os.remove(f.name)

    return has_error