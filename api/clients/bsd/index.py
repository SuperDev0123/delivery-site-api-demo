import uuid
import logging
from datetime import datetime, date, timedelta

from django.db import transaction

from api.models import Client_warehouses, BOK_2_lines
from api.serializers import SimpleQuoteSerializer
from api.serializers_client import *
from api.common import common_times as dme_time_lib, constants as dme_constants
from api.operations import product_operations as product_oper
from api.operations.booking_line import index as line_oper
from api.clients.operations.index import get_suburb_state
from api.common.common_times import next_business_day

logger = logging.getLogger(__name__)


def push_boks(payload, client, username, method):
    """
    PUSH api (bok_1, bok_2, bok_3)
    """
    LOG_ID = "[PB Standard]"  # PB - PUSH BOKS
    bok_1 = payload["booking"]
    bok_1["pk_header_id"] = str(uuid.uuid4())
    bok_2s = payload["booking_lines"]

    with transaction.atomic():
        # Save bok_1
        bok_1["fk_client_id"] = client.dme_account_num
        bok_1["x_booking_Created_With"] = "DME PUSH API"
        bok_1["success"] = dme_constants.BOK_SUCCESS_5

        # PU avail from
        bok_1["b_021_b_pu_avail_from_date"] = None
        bok_1["b_022_b_pu_avail_from_time_hour"] = 0
        bok_1["b_023_b_pu_avail_from_time_minute"] = 0
        # if not bok_1.get("b_021_b_pu_avail_from_date"):
        #     now_time = datetime.now()
        #     start_date = (
        #         now_time - timedelta(days=1) if now_time.time().hour < 12 else now_time
        #     )
        #     bok_1["b_021_b_pu_avail_from_date"] = next_business_day(start_date, 3)

        # Warehouse
        bok_1["client_booking_id"] = bok_1["pk_header_id"]
        bok_1["fk_client_warehouse"] = 220
        bok_1["b_clientPU_Warehouse"] = "Bathroom Sales Direct"
        bok_1["b_client_warehouse_code"] = "BSD_MERRYLANDS"
        bok_1["booking_Created_For_Email"] = "info@bathroomsalesdirect.com.au"

        if not bok_1.get("b_054_b_del_company"):
            bok_1["b_054_b_del_company"] = bok_1["b_061_b_del_contact_full_name"]

        bok_1["b_057_b_del_address_state"] = bok_1["b_057_b_del_address_state"].upper()
        bok_1["b_031_b_pu_address_state"] = bok_1["b_031_b_pu_address_state"].upper()
        bok_1["b_027_b_pu_address_type"] = "business"
        bok_1["b_053_b_del_address_type"] = "residential"

        # Shipping Method (local_pickup, ...)
        b_010_b_notes = bok_1["shipping_method"]
        if bok_1["shipping_method"] == "local_pickup":
            bok_1["b_001_b_freight_provider"] = "Customer Collect"
        elif bok_1["shipping_method"] == "free_shipping":
            bok_1["b_093_b_promo_code"] = "Flash Sale Bulk"

        bok_1_serializer = BOK_1_Serializer(data=bok_1)
        if not bok_1_serializer.is_valid():
            message = f"Serialiser Error - {bok_1_serializer.errors}"
            logger.info(f"@8811 {LOG_ID} {message}")
            raise Exception(message)

        # Save bok_2s
        for index, bok_2 in enumerate(bok_2s):
            _bok_2 = bok_2["booking_line"]
            _bok_2["fk_header_id"] = bok_1["pk_header_id"]
            _bok_2["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
            _bok_2["pk_booking_lines_id"] = str(uuid.uuid1())
            _bok_2["success"] = bok_1["success"]
            _bok_2["is_deleted"] = 0
            _bok_2["b_093_packed_status"] = BOK_2_lines.ORIGINAL
            l_001 = "Carton" or _bok_2.get("l_001_type_of_packaging")
            _bok_2["l_001_type_of_packaging"] = l_001

            _bok_2 = line_oper.handle_zero(_bok_2)
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
                    message = f"Serialiser Error - {bok_3_serializer.errors}"
                    logger.info(f"@8831 {LOG_ID} {message}")
                    raise Exception(message)

        bok_1_obj = bok_1_serializer.save()

    res_json = {"success": True, "message": "Push success!"}
    return res_json
