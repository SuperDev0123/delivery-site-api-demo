import logging
from datetime import datetime

from api.models import (
    DME_clients,
    Client_Auto_Augment,
    Client_Process_Mgr,
    Booking_lines,
    API_booking_quotes,
)
from api.operations.booking.auto_augment import auto_augment as auto_augment_oper
from api.common.booking_quote import set_booking_quote
from api.helpers.list import *

logger = logging.getLogger(__name__)
IMPORTANT_FIELDS = [
    "e_qty",
    "e_dimLength",
    "e_dimWidth",
    "e_dimHeight",
    "e_weightPerEach",
    "e_dimUOM",
    "e_weightUOM",
]


def pre_save_handler(instance):
    LOG_ID = "[LINE PRE SAVE]"


def post_save_handler(instance, created, update_fields):
    LOG_ID = "[LINE POST SAVE]"

    if intersection(IMPORTANT_FIELDS, update_fields or []) or created:
        booking = instance.booking()

        if not booking:
            return

        # Ignore when plum scans
        if (
            booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000004"
            and instance.packed_status == Booking_lines.SCANNED_PACK
        ):
            return

        logger.info(f"{LOG_ID} Created new or updated important field.")
        packed_status = instance.packed_status
        if (
            booking.api_booking_quote
            and booking.api_booking_quote.packed_status == packed_status
        ):
            set_booking_quote(booking, None)

        quotes = API_booking_quotes.objects.filter(
            fk_booking_id=booking.pk_booking_id,
            packed_status=packed_status,
            is_used=False,
        )
        for quote in quotes:
            quote.is_used = True
            quote.save()


def post_delete_handler(instance):
    booking = instance.booking()
    cl_procs = Client_Process_Mgr.objects.filter(fk_booking_id=booking.pk)

    if cl_procs.exists():
        # Get client_auto_augment
        dme_client = DME_clients.objects.filter(
            dme_account_num=booking.kf_client_id
        ).first()

        client_auto_augment = Client_Auto_Augment.objects.filter(
            fk_id_dme_client_id=dme_client.pk,
            de_to_companyName__iexact=booking.deToCompanyName.strip().lower(),
        ).first()

        if not client_auto_augment:
            logger.error(
                f"#603 This Client is not set up for auto augment, bookingID: {booking.pk}"
            )

        auto_augment_oper(booking, client_auto_augment, cl_procs.first())
