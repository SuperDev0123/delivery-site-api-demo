import uuid
import logging
from datetime import datetime, date

from django.db import transaction

from api.models import Client_warehouses, FPRouting
from api.serializers import SimpleQuoteSerializer
from api.serializers_client import *
from api.common import common_times as dme_time_lib, constants as dme_constants
from api.operations import product_operations as product_oper
from api.clients.operations.index import get_suburb_state
from api.clients.tempo.operations import find_warehouse

logger = logging.getLogger(__name__)


def push_boks(payload, client, username, method):
    """
    PUSH api (bok_1, bok_2, bok_3)
    """
    LOG_ID = "[PUSH FROM TEMPO]"
    bok_1 = payload["booking"]
    bok_2s = payload["booking_lines"]

    if not bok_2s:
        raise Exception("No Lines")

    # Check `port_code`
    logger.info(f"{LOG_ID} Checking port_code...")
    pu_state = bok_1.get("b_031_b_pu_address_state")
    pu_suburb = bok_1.get("b_032_b_pu_address_suburb")
    pu_postcode = bok_1.get("b_033_b_pu_address_postalcode")

    # head_port and port_code
    fp_routings = FPRouting.objects.filter(
        freight_provider=13,
        suburb__iexact=pu_suburb,
        dest_postcode=pu_postcode,
        state__iexact=pu_state,
    )
    head_port = fp_routings[0].gateway if fp_routings and fp_routings[0].gateway else ""
    port_code = fp_routings[0].onfwd if fp_routings and fp_routings[0].onfwd else ""

    if not head_port or not port_code:
        message = f"No port_code.\n\n"
        message += f"Order Num: {bok_1['b_client_order_num']}\n"
        message += f"State: {pu_state}\nPostal Code: {pu_postcode}\nSuburb: {pu_suburb}"
        logger.error(f"{LOG_ID} {message}")
        raise Exception(message)

    bok_1["b_008_b_category"] = bok_1.get("b_008_b_category") or "salvage expense"
    b_008_b_category = bok_1.get("b_008_b_category")
    bok_1["pk_header_id"] = str(uuid.uuid4())
    if b_008_b_category and b_008_b_category.lower() == "salvage expense":
        # Find warehouse
        warehouse = find_warehouse(bok_1, bok_2s)
        bok_1["client_booking_id"] = bok_1["pk_header_id"]
        bok_1["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
        bok_1["b_clientPU_Warehouse"] = warehouse.name
        bok_1["b_client_warehouse_code"] = warehouse.client_warehouse_code
        bok_1["b_053_b_del_address_type"] = "Business"
        bok_1["b_054_b_del_company"] = warehouse.name
        bok_1["b_055_b_del_address_street_1"] = warehouse.address1
        bok_1["b_056_b_del_address_street_2"] = warehouse.address2
        bok_1["b_057_b_del_address_state"] = warehouse.state
        bok_1["b_059_b_del_address_postalcode"] = warehouse.postal_code
        bok_1["b_058_b_del_address_suburb"] = warehouse.suburb
        bok_1["b_060_b_del_address_country"] = "Australia"
        bok_1["b_061_b_del_contact_full_name"] = warehouse.contact_name
        bok_1["b_063_b_del_email"] = warehouse.contact_email
        bok_1["b_064_b_del_phone_main"] = warehouse.phone_main

    bok_1["b_028_b_pu_company"] = bok_1.get("b_028_b_pu_company") or bok_1.get(
        "b_035_b_pu_contact_full_name"
    )
    bok_1["x_booking_Created_With"] = "DME PUSH API"
    bok_1["success"] = dme_constants.BOK_SUCCESS_2  # Default success code
    bok_1["b_031_b_pu_address_state"] = bok_1.get("b_031_b_pu_address_state").upper()
    bok_1["fk_client_id"] = client.dme_account_num
    client_booking_id = (
        f"{bok_1['pk_header_id']}_{datetime.strftime(datetime.utcnow(), '%s')}"
    )
    bok_1["client_booking_id"] = client_booking_id
    bok_1["b_clientPU_Warehouse"] = (
        bok_1.get("b_clientPU_Warehouse") or "No - Warehouse"
    )
    bok_1["b_client_order_num"] = bok_1.get("b_client_order_num") or ""

    bok_1_serializer = BOK_1_Serializer(data=bok_1)
    if not bok_1_serializer.is_valid():
        message = f"Serialiser Error - {bok_1_serializer.errors}"
        logger.info(f"@8811 {LOG_ID} {message}")
        raise Exception(message)

    with transaction.atomic():
        # Save bok_2s
        for index, bok_2 in enumerate(bok_2s):
            _bok_2 = bok_2["booking_line"]
            _bok_2["fk_header_id"] = bok_1["pk_header_id"]
            _bok_2["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
            _bok_2["pk_booking_lines_id"] = str(uuid.uuid1())
            _bok_2["success"] = bok_1["success"]
            l_001 = "Carton" or _bok_2.get("l_001_type_of_packaging")
            _bok_2["l_001_type_of_packaging"] = l_001

            bok_2_serializer = BOK_2_Serializer(data=_bok_2)
            if bok_2_serializer.is_valid():
                bok_2_serializer.save()
            else:
                message = f"Serialiser Error - {bok_2_serializer.errors}"
                logger.info(f"@8821 {LOG_ID} {message}")
                raise Exception(message)

            # Save bok_3s
            if not "booking_lines_data" in bok_2:
                continue

            bok_3s = bok_2["booking_lines_data"]
            for bok_3 in bok_3s:
                bok_3["fk_header_id"] = bok_1["pk_header_id"]
                bok_3["fk_booking_lines_id"] = _bok_2["pk_booking_lines_id"]
                bok_3["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
                bok_3["success"] = bok_1["success"]

                bok_3_serializer = BOK_3_Serializer(data=bok_3)
                if bok_3_serializer.is_valid():
                    bok_3_serializer.save()
                else:
                    message = f"Serialiser Error - {bok_2_serializer.errors}"
                    logger.info(f"@8831 {LOG_ID} {message}")
                    raise Exception(message)

        bok_1_obj = bok_1_serializer.save()

    res_json = {"success": True, "message": "Push success!"}
    return res_json
