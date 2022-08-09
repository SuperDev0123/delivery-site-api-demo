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
from api.operations.booking.quote import get_quote_again
from api.operations.genesis.index import create_shared_lines
from api.common.booking_quote import set_booking_quote
from api.helpers.list import *
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.utils import get_m3_to_kg_factor
from api.common.constants import PALLETS, SKIDS
from api.common.ratio import _get_dim_amount, _get_weight_amount

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

    booking = instance.booking()

    if not booking:
        return

    # Check if `Pallet` or `Skid`
    is_pallet = (
        instance.e_type_of_packaging.upper() in PALLETS
        or instance.e_type_of_packaging.upper() in SKIDS
    )
    need_update = True
    if not is_pallet:
        need_update = False
    # Check if height is less than 1.4m
    dim_ratio = _get_dim_amount(instance.e_dimUOM)
    height = instance.e_dimHeight * dim_ratio
    if height > 1.4:
        need_update = False

    height = instance.e_dimHeight * dim_ratio
    instance.e_util_height = 1.4 if need_update else height
    instance.e_util_height = instance.e_util_height / dim_ratio
    # Calc cubic mass factor
    weight_ratio = _get_weight_amount(instance.e_weightUOM)
    item_dead_weight = instance.e_weightPerEach * weight_ratio
    e_cubic_2_mass_factor = get_m3_to_kg_factor(
        booking.vx_freight_provider,
        {
            "is_pallet": is_pallet,
            "item_length": instance.e_dimLength * dim_ratio,
            "item_width": instance.e_dimWidth * dim_ratio,
            "item_height": instance.e_util_height * dim_ratio,
            "item_dead_weight": item_dead_weight,
        },
    )
    # Calc
    instance.e_util_cbm = get_cubic_meter(
        instance.e_dimLength,
        instance.e_dimWidth,
        instance.e_util_height,
        instance.e_dimUOM,
        1,
    )
    instance.e_util_cbm = round(instance.e_util_cbm * instance.e_qty, 3)
    instance.e_util_kg = instance.e_util_cbm * e_cubic_2_mass_factor
    instance.e_util_kg = round(instance.e_util_kg * instance.e_qty, 3)


def post_save_handler(instance, created, update_fields):
    LOG_ID = "[LINE POST SAVE]"

    if intersection(IMPORTANT_FIELDS, update_fields or []) or created:
        booking = instance.booking()

        if not booking:
            return

        # Ignore when plum scans
        if booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000004":
            return

        # Genesis
        if booking.b_dateBookedDate:
            create_shared_lines(booking)

        logger.info(f"{LOG_ID} Created new or updated important field.")
        # Reset selected Quote and connected Quotes
        if booking.booking_type != "DMEA":
            set_booking_quote(booking, None)
            quotes = API_booking_quotes.objects.filter(
                fk_booking_id=booking.pk_booking_id,
                is_used=False,
            )
            for quote in quotes:
                quote.is_used = True
                quote.save()
        # elif booking.booking_type == "DMEA":
        #     get_quote_again(booking)


def post_delete_handler(instance):
    booking = instance.booking()

    if not booking:
        return

    # Reset selected Quote and connected Quotes
    if booking.booking_type != "DMEA":
        set_booking_quote(booking, None)
        quotes = API_booking_quotes.objects.filter(
            fk_booking_id=booking.pk_booking_id,
            is_used=False,
        )
        for quote in quotes:
            quote.is_used = True
            quote.save()
    elif booking.booking_type == "DMEA":
        get_quote_again(booking)

    # Client_Process_Mgr
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
