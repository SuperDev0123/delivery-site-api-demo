import os
import logging
from datetime import datetime

from django.conf import settings

from api.models import Bookings, Booking_lines
from api.operations.csv.cope import build_csv as build_COPE_csv
from api.operations.csv.dhl import build_csv as build_DHL_csv
from api.operations.csv.state_transport import build_csv as build_STATE_TRANSPORT_csv
from api.operations.csv.century import build_csv as build_CENTURY_csv
from api.fp_apis.utils import gen_consignment_num
from api.utils import get_sydney_now_time

logger = logging.getLogger(__name__)


def get_booking_lines(bookings):
    pk_booking_ids = bookings.values_list("pk_booking_id", flat=True)

    return Booking_lines.objects.filter(
        fk_booking_id__in=pk_booking_ids, is_deleted=False
    )


def build_csv(booking_ids):
    LOG_ID = "[CSV BOOK]"
    logger.error(f"{LOG_ID} booking_ids: {booking_ids}")

    bookings = Bookings.objects.filter(pk__in=booking_ids)
    booking_lines = get_booking_lines(bookings)
    vx_freight_provider = bookings.first().vx_freight_provider.lower()
    now_str = str(get_sydney_now_time("datetime").strftime("%d-%m-%Y__%H_%M_%S"))

    # Generate CSV name
    if len(booking_ids) == 1:
        if not bookings[0].b_client_order_num:
            error_msg = f"{LOG_ID} Error: OrderNum is missing."
            logger.error(error_msg)
            return error_msg

        consignment_num = gen_consignment_num(
            bookings[0].vx_freight_provider, bookings[0].b_client_order_num
        )

        if vx_freight_provider == "cope":
            csv_name = f"SEATEMP__{consignment_num}__{now_str}.csv"
        elif vx_freight_provider == "dhl":
            csv_name = f"Seaway-Tempo-Aldi__{consignment_num}__{now_str}.csv"
        elif vx_freight_provider == "state transport":
            csv_name = f"State-Transport__{consignment_num}__{now_str}.csv"
        elif vx_freight_provider == "century":
            csv_name = f"Century__{consignment_num}__{now_str}.csv"
    else:
        if vx_freight_provider == "cope":
            csv_name = f"SEATEMP__{str(len(booking_ids))}__{now_str}.csv"
        elif vx_freight_provider == "dhl":
            csv_name = f"Seaway-Tempo-Aldi__{str(len(booking_ids))}__{now_str}.csv"
        elif vx_freight_provider == "state transport":
            csv_name = f"State-Transport__{str(len(booking_ids))}__{now_str}.csv"
        elif vx_freight_provider == "century":
            csv_name = f"Century__{str(len(booking_ids))}__{now_str}.csv"

    # Open CSV file
    if settings.ENV == "prod":
        if vx_freight_provider == "cope":
            f = open(f"/dme_sftp/cope_au/pickup_ext/cope_au/{csv_name}", "w")
        elif vx_freight_provider == "dhl":
            f = open(f"/dme_sftp/cope_au/pickup_ext/dhl_au/{csv_name}", "w")
        elif vx_freight_provider == "state transport":
            f = open(f"/dme_sftp/state_transport_au/book_csv/outdata/{csv_name}", "w")
        elif vx_freight_provider == "century":
            f = open(f"/dme_sftp/century_au/book_csv/outdata/{csv_name}", "w")
    else:
        local_path = f"{settings.STATIC_PUBLIC}/csvs/"
        if not os.path.exists(local_path):
            os.makedirs(local_path)
        f = open(f"{settings.STATIC_PUBLIC}/csvs/{csv_name}", "w")

    # Build CSV
    if vx_freight_provider == "cope":
        has_error = build_COPE_csv(f, bookings, booking_lines)
    elif vx_freight_provider == "dhl":
        has_error = build_DHL_csv(f, bookings, booking_lines)
    elif vx_freight_provider == "state transport":
        has_error = build_STATE_TRANSPORT_csv(f, bookings, booking_lines)
    elif vx_freight_provider == "century":
        has_error = build_CENTURY_csv(f, bookings, booking_lines)

    f.close()

    if has_error:
        os.remove(f.name)

    return has_error
