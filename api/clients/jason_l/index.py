import json
import uuid
import logging
from datetime import datetime, date
from base64 import b64encode

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from api.models import (
    Bookings,
    Booking_lines,
    Booking_lines_data,
    FC_Log,
    BOK_1_headers,
    BOK_2_lines,
    BOK_3_lines_data,
    Pallet,
)
from api.serializers import SimpleQuoteSerializer
from api.serializers_client import *
from api.convertors import pdf
from api.common import (
    common_times as dme_time_lib,
    constants as dme_constants,
    status_history,
)
from api.fp_apis.utils import (
    select_best_options,
    get_status_category_from_status,
    auto_select_pricing_4_bok,
    gen_consignment_num,
)
from api.fp_apis.operations.book import book as book_oper
from api.fp_apis.operations.pricing import pricing as pricing_oper
from api.operations import push_operations, product_operations as product_oper
from api.operations.manifests.index import build_manifest
from api.operations.email_senders import send_email_to_admins
from api.operations.labels.index import build_label, get_barcode
from api.operations.pronto_xi.index import populate_bok as get_bok_from_pronto_xi
from api.clients.operations.index import get_warehouse, get_suburb_state
from api.clients.jason_l.operations import get_picked_items
from api.common.pallet import get_number_of_pallets

logger = logging.getLogger("JASON")


def partial_pricing(payload, client, warehouse):
    LOG_ID = "[PP Jason L]"
    bok_1 = payload["booking"]
    bok_1["pk_header_id"] = str(uuid.uuid4())
    bok_2s = payload["booking_lines"]
    json_results = []

    de_postal_code = bok_1.get("b_059_b_del_address_postalcode")
    de_state, de_suburb = get_suburb_state(de_postal_code)

    # Check if has lines
    if len(bok_2s) == 0:
        message = "Line items are required."
        logger.info(f"@815 {LOG_ID} {message}")
        raise Exception(message)

    # Get next business day
    next_biz_day = dme_time_lib.next_business_day(date.today(), 1)
    bok_1["b_021_b_pu_avail_from_date"] = str(next_biz_day)[:10]

    booking = {
        "pk_booking_id": bok_1["pk_header_id"],
        "puPickUpAvailFrom_Date": bok_1["b_021_b_pu_avail_from_date"],
        "b_clientReference_RA_Numbers": "initial_RA_num",
        "puCompany": warehouse.name,
        "pu_Contact_F_L_Name": "initial_PU_contact",
        "pu_Email": "pu@email.com",
        "pu_Phone_Main": "419294339",
        "pu_Address_Street_1": warehouse.address1,
        "pu_Address_street_2": warehouse.address2,
        "pu_Address_Country": "Australia",
        "pu_Address_PostalCode": warehouse.postal_code,
        "pu_Address_State": warehouse.state,
        "pu_Address_Suburb": warehouse.suburb,
        "deToCompanyName": "initial_DE_company",
        "de_to_Contact_F_LName": "initial_DE_contact",
        "de_Email": "de@email.com",
        "de_to_Phone_Main": "419294339",
        "de_To_Address_Street_1": "initial_DE_street_1",
        "de_To_Address_Street_2": "",
        "de_To_Address_Country": "Australia",
        "de_To_Address_PostalCode": de_postal_code,
        "de_To_Address_State": de_state.upper(),
        "de_To_Address_Suburb": de_suburb,
        "client_warehouse_code": warehouse.client_warehouse_code,
        "vx_serviceName": "exp",
        "kf_client_id": warehouse.fk_id_dme_client.dme_account_num,
        "b_client_name": client.company_name,
    }

    booking_lines = []

    # Product & Child items
    missing_model_numbers = product_oper.find_missing_model_numbers(bok_2s, client)

    if missing_model_numbers:
        missing_model_numbers_str = {", ".join(missing_model_numbers)}
        message = f"System is missing model numbers - {missing_model_numbers_str}"
        logger.info(f"@816 {LOG_ID} {message}")
        raise Exception(message)

    items = product_oper.get_product_items(bok_2s, client, True)

    for item in items:
        booking_line = {
            "e_type_of_packaging": "Carton" or item["e_type_of_packaging"],
            "fk_booking_id": bok_1["pk_header_id"],
            "e_qty": item["qty"],
            "e_item": item["description"],
            "e_dimUOM": item["e_dimUOM"],
            "e_dimLength": item["e_dimLength"],
            "e_dimWidth": item["e_dimWidth"],
            "e_dimHeight": item["e_dimHeight"],
            "e_weightUOM": item["e_weightUOM"],
            "e_weightPerEach": item["e_weightPerEach"],
        }
        booking_lines.append(booking_line)

    _, success, message, quote_set = pricing_oper(
        body={"booking": booking, "booking_lines": booking_lines},
        booking_id=None,
        is_pricing_only=True,
    )
    logger.info(
        f"#519 {LOG_ID} Pricing result: success: {success}, message: {message}, results cnt: {quote_set}"
    )

    # Select best quotes(fastest, lowest)
    if quote_set.count() > 0:
        best_quotes = select_best_options(pricings=quote_set)
        logger.info(f"#520 {LOG_ID} Selected Best Pricings: {best_quotes}")

        context = {"client_customer_mark_up": client.client_customer_mark_up}
        json_results = SimpleQuoteSerializer(
            best_quotes, many=True, context=context
        ).data
        json_results = dme_time_lib.beautify_eta(json_results, best_quotes, client)

        # delete quotes
        quote_set.delete()

    # Set Express or Standard
    if len(json_results) == 1:
        json_results[0]["service_name"] = "Standard"
    else:
        if float(json_results[0]["cost"]) > float(json_results[1]["cost"]):
            json_results[0]["service_name"] = "Express"
            json_results[1]["service_name"] = "Standard"

            if json_results[0]["eta"] == json_results[1]["eta"]:
                eta = f"{int(json_results[1]['eta'].split(' ')[0]) + 1} days"
                json_results[1]["eta"] = eta

            json_results = [json_results[1], json_results[0]]
        else:
            json_results[1]["service_name"] = "Express"
            json_results[0]["service_name"] = "Standard"

            if json_results[0]["eta"] == json_results[1]["eta"]:
                eta = f"{int(json_results[0]['eta'].split(' ')[0]) + 1} days"
                json_results[0]["eta"] = eta

    if json_results:
        logger.info(f"@818 {LOG_ID} Success!")
        return json_results
    else:
        logger.info(f"@819 {LOG_ID} Failure!")
        return json_results


def push_boks(payload, client, username, method):
    """
    PUSH api (bok_1, bok_2, bok_3)

    Sample payload:
        {
            "booking": {
                "b_client_order_num": "    20176",
                "shipping_type": "DMEM",
                "b_client_sales_inv_num": "    TEST ORDER 20176"
            }
        }
    """
    LOG_ID = "[PB Jason L]"  # PB - PUSH BOKS
    bok_1 = payload["booking"]
    bok_1["pk_header_id"] = str(uuid.uuid4())
    client_name = None
    old_quote = None
    best_quotes = None
    json_results = []

    warehouse = get_warehouse(client)

    # Assign vars
    is_biz = "_bizsys" in username
    is_web = "_websys" in username

    # Strip data
    bok_1["b_client_order_num"] = bok_1["b_client_order_num"].strip()
    bok_1["b_client_sales_inv_num"] = bok_1["b_client_sales_inv_num"].strip()
    bok_1["shipping_type"] = bok_1["shipping_type"].strip()
    bok_1["b_053_b_del_address_type"] = (
        bok_1["b_053_b_del_delivery_type"].strip().lower()
    )
    del bok_1["b_053_b_del_delivery_type"]

    # Check required fields
    if is_biz:
        if not bok_1.get("shipping_type"):
            message = "'shipping_type' is required."
            logger.info(f"{LOG_ID} {message}")
            raise ValidationError(message)
        elif len(bok_1.get("shipping_type")) != 4:
            message = "'shipping_type' is not valid."
            logger.info(f"{LOG_ID} {message}")
            raise ValidationError(message)

        if not bok_1.get("b_client_order_num"):
            message = "'b_client_order_num' is required."
            logger.info(f"{LOG_ID} {message}")
            raise ValidationError(message)

        if not bok_1["b_053_b_del_address_type"] in ["business", "residential"]:
            message = (
                "'b_053_b_del_address_type' should be `business` or `residential`."
            )
            logger.info(f"{LOG_ID} {message}")
            raise ValidationError(message)

    bok_1["pk_header_id"] = str(uuid.uuid4())

    # Check duplicated push with `b_client_order_num`
    if method == "POST":
        if is_biz:
            bok_1s = BOK_1_headers.objects.filter(
                fk_client_id=client.dme_account_num,
                b_client_order_num=bok_1["b_client_order_num"],
            )
            if bok_1s.exists():
                # If "sales quote" request, then clear all existing information
                if bok_1["b_client_order_num"][:2] == "Q_":
                    pk_header_id = bok_1s.first().pk_header_id
                    old_bok_1 = bok_1s.first()
                    old_bok_2s = BOK_2_lines.objects.filter(fk_header_id=pk_header_id)
                    old_bok_3s = BOK_3_lines_data.objects.filter(
                        fk_header_id=pk_header_id
                    )
                    old_bok_1.delete()
                    old_bok_2s.delete()
                    old_bok_3s.delete()
                    old_quote = old_bok_1.quote
                else:
                    message = f"BOKS API Error - Order(b_client_order_num={bok_1['b_client_order_num']}) does already exist."
                    logger.info(f"@884 {LOG_ID} {message}")

                    json_res = {
                        "status": False,
                        "message": f"Order(b_client_order_num={bok_1['b_client_order_num']}) does already exist.",
                    }

                    if bok_1s.first().success == dme_constants.BOK_SUCCESS_3:
                        url = f"http://{settings.WEB_SITE_IP}/price/{bok_1s.first().client_booking_id}/"
                    else:
                        url = f"http://{settings.WEB_SITE_IP}/status/{bok_1s.first().client_booking_id}/"

                    json_res["pricePageUrl"] = url
                    logger.info(f"@885 {LOG_ID} Response: {json_res}")

                    return json_res

    # Generate `client_booking_id` for SAPB1
    if is_biz:
        client_booking_id = f"{bok_1['b_client_order_num']}_{bok_1['pk_header_id']}_{datetime.strftime(datetime.utcnow(), '%s')}"
        bok_1["client_booking_id"] = client_booking_id

    with transaction.atomic():
        # Save bok_1
        bok_1["fk_client_id"] = client.dme_account_num
        bok_1["x_booking_Created_With"] = "DME PUSH API"
        bok_1["success"] = dme_constants.BOK_SUCCESS_2  # Default success code
        bok_1["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
        bok_1["b_clientPU_Warehouse"] = warehouse.name
        bok_1["b_client_warehouse_code"] = warehouse.client_warehouse_code

        if bok_1.get("shipping_type") == "DMEA":
            bok_1["success"] = dme_constants.BOK_SUCCESS_4
        else:
            bok_1["success"] = dme_constants.BOK_SUCCESS_3

        if not bok_1.get("b_028_b_pu_company"):
            bok_1["b_028_b_pu_company"] = warehouse.name

        if not bok_1.get("b_035_b_pu_contact_full_name"):
            bok_1["b_035_b_pu_contact_full_name"] = warehouse.contact_name

        if not bok_1.get("b_037_b_pu_email"):
            bok_1["b_037_b_pu_email"] = warehouse.contact_email

        if not bok_1.get("b_038_b_pu_phone_main"):
            bok_1["b_038_b_pu_phone_main"] = warehouse.phone_main

        if not bok_1.get("b_029_b_pu_address_street_1"):
            bok_1["b_029_b_pu_address_street_1"] = warehouse.address1

        if not bok_1.get("b_030_b_pu_address_street_2"):
            bok_1["b_030_b_pu_address_street_2"] = warehouse.address2

        if not bok_1.get("b_034_b_pu_address_country"):
            bok_1["b_034_b_pu_address_country"] = "AU"

        if not bok_1.get("b_033_b_pu_address_postalcode"):
            bok_1["b_033_b_pu_address_postalcode"] = warehouse.postal_code

        if not bok_1.get("b_031_b_pu_address_state"):
            bok_1["b_031_b_pu_address_state"] = warehouse.state.upper()

        if not bok_1.get("b_032_b_pu_address_suburb"):
            bok_1["b_032_b_pu_address_suburb"] = warehouse.suburb

        if not bok_1.get("b_021_b_pu_avail_from_date"):
            next_biz_day = dme_time_lib.next_business_day(date.today(), 1)
            bok_1["b_021_b_pu_avail_from_date"] = str(next_biz_day)[:10]

        bok_1, bok_2s = get_bok_from_pronto_xi(bok_1)

        if not bok_1.get("b_027_b_pu_address_type"):
            bok_1["b_027_b_pu_address_type"] = "business"
        if not bok_1.get("b_053_b_del_address_type"):
            bok_1["b_053_b_del_address_type"] = "business"

        if not bok_1.get("b_019_b_pu_tail_lift"):
            bok_1["b_019_b_pu_tail_lift"] = False
        if not bok_1.get("b_041_b_del_tail_lift"):
            bok_1["b_041_b_del_tail_lift"] = 0

        if not bok_1.get("b_072_b_pu_no_of_assists"):
            bok_1["b_072_b_pu_no_of_assists"] = 0
        if not bok_1.get("b_073_b_del_no_of_assists"):
            bok_1["b_073_b_del_no_of_assists"] = 0

        if not bok_1.get("b_078_b_pu_location"):
            bok_1["b_078_b_pu_location"] = BOK_1_headers.PDWD
        if not bok_1.get("b_068_b_del_location"):
            bok_1["b_068_b_del_location"] = BOK_1_headers.DDWD

        if not bok_1.get("b_074_b_pu_access"):
            bok_1["b_074_b_pu_access"] = "Level Driveway"
        if not bok_1.get("b_075_b_del_access"):
            bok_1["b_075_b_del_access"] = "Level Driveway"

        if not bok_1.get("b_079_b_pu_floor_number"):
            bok_1["b_079_b_pu_floor_number"] = 0  # Ground
        if not bok_1.get("b_069_b_del_floor_number"):
            bok_1["b_069_b_del_floor_number"] = 0  # Ground

        if not bok_1.get("b_080_b_pu_floor_access_by"):
            bok_1["b_080_b_pu_floor_access_by"] = BOK_1_headers.NONE
        if not bok_1.get("b_070_b_del_floor_access_by"):
            bok_1["b_070_b_del_floor_access_by"] = BOK_1_headers.NONE

        if not bok_1.get("b_076_b_pu_service"):
            bok_1["b_076_b_pu_service"] = BOK_1_headers.NONE
        if not bok_1.get("b_077_b_pu_service"):
            bok_1["b_077_b_pu_service"] = BOK_1_headers.NONE

        if not bok_1.get("b_054_b_del_company"):
            bok_1["b_054_b_del_company"] = bok_1["b_061_b_del_contact_full_name"]

        de_postal_code = bok_1.get("b_059_b_del_address_postalcode")
        de_state, de_suburb = get_suburb_state(de_postal_code)
        bok_1["b_057_b_del_address_state"] = de_state.upper()
        bok_1["b_058_b_del_address_suburb"] = de_suburb
        bok_1["b_031_b_pu_address_state"] = bok_1["b_031_b_pu_address_state"].upper()

        bok_1_serializer = BOK_1_Serializer(data=bok_1)

        if not bok_1_serializer.is_valid():
            message = f"Serialiser Error - {bok_1_serializer.errors}"
            logger.info(f"@8821 {LOG_ID} {message}")
            raise Exception(message)

        # Save bok_2s (Product & Child items)
        items = product_oper.get_product_items(bok_2s, client, is_web)
        new_bok_2s = []
        bok_2_objs = []

        for index, item in enumerate(items):
            line = {}
            line["fk_header_id"] = bok_1["pk_header_id"]
            line["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
            line["pk_booking_lines_id"] = str(uuid.uuid1())
            line["success"] = bok_1["success"]
            line["l_001_type_of_packaging"] = item["e_type_of_packaging"]
            line["l_002_qty"] = item["qty"]
            line["l_003_item"] = item["description"]
            line["l_004_dim_UOM"] = item["e_dimUOM"].upper()
            line["l_005_dim_length"] = item["e_dimLength"]
            line["l_006_dim_width"] = item["e_dimWidth"]
            line["l_007_dim_height"] = item["e_dimHeight"]
            line["l_009_weight_per_each"] = item["e_weightPerEach"]
            line["l_008_weight_UOM"] = item["e_weightUOM"].upper()
            line["e_item_type"] = item["e_item_type"]
            line["zbl_121_integer_1"] = item["zbl_121_integer_1"]
            new_bok_2s.append({"booking_line": line})

            bok_2_serializer = BOK_2_Serializer(data=line)
            if bok_2_serializer.is_valid():
                bok_2_obj = bok_2_serializer.save()
                bok_2_objs.append(bok_2_obj)
            else:
                message = f"Serialiser Error - {bok_2_serializer.errors}"
                logger.info(f"@8831 {LOG_ID} {message}")
                raise Exception(message)

        bok_2s = new_bok_2s
        bok_1_obj = bok_1_serializer.save()

    # create status history
    status_history.create_4_bok(bok_1["pk_header_id"], "Pushed", username)

    # `auto_repack` logic
    carton_cnt = 0
    total_weight = 0

    pallet = Pallet.objects.all().first()
    number_of_pallets, unpalletized_lines = get_number_of_pallets(bok_2_objs, pallet)

    if not number_of_pallets and not unpalletized_lines:
        message = "0 number of Pallets and 0 `unpalletized_lines`."
        logger.info(f"@801 {LOG_ID} {message}")
        return message

    # Get number of lines (`EACH`, `CTN`, `PAL`)
    for bok_2_obj in bok_2_objs:
        total_weight += bok_2_obj.l_009_weight_per_each * bok_2_obj.l_002_qty
        carton_cnt += bok_2_obj.l_002_qty

    if number_of_pallets and carton_cnt > 2:
        message = "Auto repacking..."
        logger.info(f"@8130 {LOG_ID} {message}")
        new_bok_2s = []

        # Create one PAL bok_2
        line = {}
        line["fk_header_id"] = bok_1["pk_header_id"]
        line["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
        line["pk_booking_lines_id"] = str(uuid.uuid1())
        line["success"] = bok_1["success"]
        line["l_001_type_of_packaging"] = "PAL"
        line["l_002_qty"] = number_of_pallets
        line["l_003_item"] = "Auto repacked item"
        line["l_004_dim_UOM"] = "mm"
        line["l_005_dim_length"] = pallet.length
        line["l_006_dim_width"] = pallet.width
        line["l_007_dim_height"] = pallet.height
        line["l_009_weight_per_each"] = total_weight / number_of_pallets
        line["l_008_weight_UOM"] = "KG"
        new_bok_2s.append({"booking_line": line})

        bok_2_serializer = BOK_2_Serializer(data=line)
        if bok_2_serializer.is_valid():
            bok_2_serializer.save()
        else:
            message = f"Serialiser Error - {bok_2_serializer.errors}"
            logger.info(f"@8131 {LOG_ID} {message}")
            raise Exception(message)

        # Create Bok_3s
        for bok_2_obj in bok_2_objs:
            if bok_2_obj in unpalletized_lines:
                continue

            bok_3 = {}
            bok_3["fk_header_id"] = bok_1_obj.pk_header_id
            bok_3["fk_booking_lines_id"] = line["pk_booking_lines_id"]
            bok_3["success"] = bok_1_obj.success
            bok_3["zbld_121_integer_1"] = bok_2_obj.zbl_121_integer_1  # Sequence
            bok_3["zbld_122_integer_2"] = bok_2_obj.l_002_qty
            bok_3["zbld_131_decimal_1"] = bok_2_obj.l_005_dim_length
            bok_3["zbld_132_decimal_2"] = bok_2_obj.l_006_dim_width
            bok_3["zbld_133_decimal_3"] = bok_2_obj.l_007_dim_height
            bok_3["zbld_134_decimal_4"] = bok_2_obj.l_009_weight_per_each
            bok_3["zbld_101_text_1"] = bok_2_obj.l_004_dim_UOM
            bok_3["zbld_102_text_2"] = bok_2_obj.l_008_weight_UOM
            bok_3["zbld_103_text_3"] = bok_2_obj.e_item_type
            bok_3["zbld_104_text_4"] = bok_2_obj.l_001_type_of_packaging
            bok_3["zbld_105_text_5"] = bok_2_obj.l_003_item

            bok_3_serializer = BOK_3_Serializer(data=bok_3)
            if bok_3_serializer.is_valid():
                bok_3_serializer.save()
            else:
                message = f"Serialiser Error - {bok_3_serializer.errors}"
                logger.info(f"@8132 {LOG_ID} {message}")
                raise Exception(message)

            bok_2_obj.is_deleted = True
            bok_2_obj.save()

        # Set `auto_repack` flag
        bok_1_obj.b_081_b_pu_auto_pack = True
        bok_1_obj.save()

    # Get Pricings
    booking = {
        "pk_booking_id": bok_1["pk_header_id"],
        "puPickUpAvailFrom_Date": bok_1["b_021_b_pu_avail_from_date"],
        "b_clientReference_RA_Numbers": "",
        "puCompany": bok_1["b_028_b_pu_company"],
        "pu_Contact_F_L_Name": bok_1["b_035_b_pu_contact_full_name"],
        "pu_Email": bok_1["b_037_b_pu_email"],
        "pu_Phone_Main": bok_1["b_038_b_pu_phone_main"],
        "pu_Address_Street_1": bok_1["b_029_b_pu_address_street_1"],
        "pu_Address_street_2": bok_1["b_030_b_pu_address_street_2"],
        "pu_Address_Country": bok_1["b_034_b_pu_address_country"],
        "pu_Address_PostalCode": bok_1["b_033_b_pu_address_postalcode"],
        "pu_Address_State": bok_1["b_031_b_pu_address_state"],
        "pu_Address_Suburb": bok_1["b_032_b_pu_address_suburb"],
        "deToCompanyName": bok_1["b_054_b_del_company"],
        "de_to_Contact_F_LName": bok_1["b_061_b_del_contact_full_name"],
        "de_Email": bok_1["b_063_b_del_email"],
        "de_to_Phone_Main": bok_1["b_064_b_del_phone_main"],
        "de_To_Address_Street_1": bok_1["b_055_b_del_address_street_1"],
        "de_To_Address_Street_2": bok_1["b_056_b_del_address_street_2"],
        "de_To_Address_Country": bok_1["b_060_b_del_address_country"],
        "de_To_Address_PostalCode": bok_1["b_059_b_del_address_postalcode"],
        "de_To_Address_State": bok_1["b_057_b_del_address_state"],
        "de_To_Address_Suburb": bok_1["b_058_b_del_address_suburb"],
        "client_warehouse_code": bok_1["b_client_warehouse_code"],
        "kf_client_id": bok_1["fk_client_id"],
        "b_client_name": client.company_name,
    }

    booking_lines = []
    for bok_2 in bok_2s:
        _bok_2 = bok_2["booking_line"]
        bok_2_line = {
            "fk_booking_id": _bok_2["fk_header_id"],
            "e_type_of_packaging": _bok_2["l_001_type_of_packaging"],
            "e_qty": _bok_2["l_002_qty"],
            "e_item": _bok_2["l_003_item"],
            "e_dimUOM": _bok_2["l_004_dim_UOM"],
            "e_dimLength": _bok_2["l_005_dim_length"],
            "e_dimWidth": _bok_2["l_006_dim_width"],
            "e_dimHeight": _bok_2["l_007_dim_height"],
            "e_weightUOM": _bok_2["l_008_weight_UOM"],
            "e_weightPerEach": _bok_2["l_009_weight_per_each"],
        }
        booking_lines.append(bok_2_line)

    fc_log, _ = FC_Log.objects.get_or_create(
        client_booking_id=bok_1["client_booking_id"],
        old_quote__isnull=True,
        new_quote__isnull=True,
    )
    fc_log.old_quote = old_quote
    body = {"booking": booking, "booking_lines": booking_lines}
    _, success, message, quote_set = pricing_oper(
        body=body,
        booking_id=None,
        is_pricing_only=True,
    )
    logger.info(
        f"#519 {LOG_ID} Pricing result: success: {success}, message: {message}, results cnt: {quote_set.count()}"
    )

    # Select best quotes(fastest, lowest)
    if quote_set.exists() and quote_set.count() > 0:
        auto_select_pricing_4_bok(bok_1_obj, quote_set)
        best_quotes = select_best_options(pricings=quote_set)
        logger.info(f"#520 {LOG_ID} Selected Best Pricings: {best_quotes}")

        context = {"client_customer_mark_up": client.client_customer_mark_up}
        json_results = SimpleQuoteSerializer(
            best_quotes, many=True, context=context
        ).data
        json_results = dme_time_lib.beautify_eta(json_results, best_quotes, client)

        if bok_1["success"] == dme_constants.BOK_SUCCESS_4:
            best_quote = best_quotes[0]
            bok_1_obj.b_003_b_service_name = best_quote.service_name
            bok_1_obj.b_001_b_freight_provider = best_quote.freight_provider
            bok_1_obj.save()
            fc_log.new_quote = best_quotes[0]
            fc_log.save()
    else:
        message = f"#521 {LOG_ID} No Pricing results to select - BOK_1 pk_header_id: {bok_1['pk_header_id']}"
        logger.error(message)
        send_email_to_admins("No FC result", message)

    # Set Express or Standard
    if len(json_results) == 1:
        json_results[0]["service_name"] = "Standard"
    else:
        if float(json_results[0]["cost"]) > float(json_results[1]["cost"]):
            json_results[0]["service_name"] = "Express"
            json_results[1]["service_name"] = "Standard"

            if json_results[0]["eta"] == json_results[1]["eta"]:
                eta = f"{int(json_results[1]['eta'].split(' ')[0]) + 1} days"
                json_results[1]["eta"] = eta

            json_results = [json_results[1], json_results[0]]
        else:
            json_results[1]["service_name"] = "Express"
            json_results[0]["service_name"] = "Standard"

            if json_results[0]["eta"] == json_results[1]["eta"]:
                eta = f"{int(json_results[0]['eta'].split(' ')[0]) + 1} days"
                json_results[0]["eta"] = eta

    # Response
    if json_results:
        if is_biz:
            result = {"success": True, "results": json_results}
            url = None

            if bok_1["success"] == dme_constants.BOK_SUCCESS_3:
                url = (
                    f"http://{settings.WEB_SITE_IP}/price/{bok_1['client_booking_id']}/"
                )
            elif bok_1["success"] == dme_constants.BOK_SUCCESS_4:
                url = f"http://{settings.WEB_SITE_IP}/status/{bok_1['client_booking_id']}/"

            result["pricePageUrl"] = url
            logger.info(f"@8837 {LOG_ID} success: True, 201_created")
            return result
        else:
            logger.info(f"@8838 {LOG_ID} success: True, 201_created")
            return json_results
    else:
        message = "Pricing cannot be returned due to incorrect address information."
        logger.info(f"@8839 {LOG_ID} {message}")
        return message


def auto_repack(payload, client):
    LOG_ID = "[AR Jason L]"  # Auto Repack
    client_booking_id = payload.get("identifier")
    repack_status = payload.get("status")
    pallet_id = payload.get("palletId")
    new_bok_2s = []

    # Get Boks
    bok_1 = (
        BOK_1_headers.objects.select_related("quote")
        .filter(client_booking_id=client_booking_id)
        .first()
    )
    bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)
    bok_3s = BOK_3_lines_data.objects.filter(fk_header_id=bok_1.pk_header_id)

    if repack_status:  # repack
        # Get Pallet
        pallet = Pallet.objects.get(pk=pallet_id)
        number_of_pallets, unpalletized_lines = get_number_of_pallets(bok_2s, pallet)

        if not number_of_pallets:
            message = "0 number of Pallets."
            logger.info(f"@801 {LOG_ID} {message}")
            return message

        total_weight = 0
        for bok_2 in bok_2s:
            total_weight += bok_2.l_009_weight_per_each * bok_2.l_002_qty

        # Delete existing Pallet Bok_2
        for bok_2 in bok_2s:
            if bok_2.l_001_type_of_packaging == "PAL":
                bok_2.delete()

        # Delete existing Bok_3s
        for bok_3 in bok_3s:
            bok_3.delete()

        # Create new *1* Pallet Bok_2
        line = {}
        line["fk_header_id"] = bok_1.pk_header_id
        line["v_client_pk_consigment_num"] = bok_1.pk_header_id
        line["pk_booking_lines_id"] = str(uuid.uuid1())
        line["success"] = bok_1.success
        line["l_001_type_of_packaging"] = "PAL"
        line["l_002_qty"] = number_of_pallets
        line["l_003_item"] = "Auto repacked item"
        line["l_004_dim_UOM"] = "mm"
        line["l_005_dim_length"] = pallet.length
        line["l_006_dim_width"] = pallet.width
        line["l_007_dim_height"] = pallet.height
        line["l_009_weight_per_each"] = total_weight / number_of_pallets
        line["l_008_weight_UOM"] = "KG"

        bok_2_serializer = BOK_2_Serializer(data=line)
        if bok_2_serializer.is_valid():
            new_bok_2 = bok_2_serializer.save()
            new_bok_2s.append(new_bok_2)
        else:
            message = f"Serialiser Error - {bok_2_serializer.errors}"
            logger.info(f"@8131 {LOG_ID} {message}")
            raise Exception(message)

        # Create Bok_3 and soft delete existing CTN Bok_2
        for bok_2 in bok_2s:
            if bok_2.l_001_type_of_packaging == "PAL":
                continue
            elif bok_2 in unpalletized_lines:
                new_bok_2s.append(bok_2)
            else:
                bok_3 = {}
                bok_3["fk_header_id"] = bok_1.pk_header_id
                bok_3["fk_booking_lines_id"] = line["pk_booking_lines_id"]
                bok_3["success"] = bok_1.success
                bok_3["zbld_121_integer_1"] = bok_2.zbl_121_integer_1  # Sequence
                bok_3["zbld_122_integer_2"] = bok_2.l_002_qty
                bok_3["zbld_131_decimal_1"] = bok_2.l_005_dim_length
                bok_3["zbld_132_decimal_2"] = bok_2.l_006_dim_width
                bok_3["zbld_133_decimal_3"] = bok_2.l_007_dim_height
                bok_3["zbld_134_decimal_4"] = bok_2.l_009_weight_per_each
                bok_3["zbld_101_text_1"] = bok_2.l_004_dim_UOM
                bok_3["zbld_102_text_2"] = bok_2.l_008_weight_UOM
                bok_3["zbld_103_text_3"] = bok_2.e_item_type
                bok_3["zbld_104_text_4"] = bok_2.l_001_type_of_packaging
                bok_3["zbld_105_text_5"] = bok_2.l_003_item

                bok_3_serializer = BOK_3_Serializer(data=bok_3)
                if bok_3_serializer.is_valid():
                    bok_3_serializer.save()
                else:
                    message = f"Serialiser Error - {bok_3_serializer.errors}"
                    logger.info(f"@8132 {LOG_ID} {message}, {bok_3}")
                    raise Exception(message)

                bok_2.is_deleted = not bok_2.is_deleted
                bok_2.save()
    else:  # rollback repack
        for bok_2 in bok_2s:
            # Delete existing Pallet
            if (
                bok_2.l_001_type_of_packaging == "PAL"
                and bok_2.l_003_item == "Auto repacked item"
            ):
                bok_2.delete()

            # Rollback deleted original Bok_2
            if bok_2.is_deleted:
                bok_2.is_deleted = not bok_2.is_deleted
                bok_2.save()

            if not bok_2.is_deleted:
                new_bok_2s.append(bok_2)

        for bok_3 in bok_3s:
            bok_3.is_deleted = not bok_3.is_deleted
            bok_3.save()

    bok_1.b_081_b_pu_auto_pack = repack_status
    bok_1.save()

    # Get Pricings
    booking = {
        "pk_booking_id": bok_1.pk_header_id,
        "puPickUpAvailFrom_Date": bok_1.b_021_b_pu_avail_from_date,
        "b_clientReference_RA_Numbers": "",
        "puCompany": bok_1.b_028_b_pu_company,
        "pu_Contact_F_L_Name": bok_1.b_035_b_pu_contact_full_name,
        "pu_Email": bok_1.b_037_b_pu_email,
        "pu_Phone_Main": bok_1.b_038_b_pu_phone_main,
        "pu_Address_Street_1": bok_1.b_029_b_pu_address_street_1,
        "pu_Address_street_2": bok_1.b_030_b_pu_address_street_2,
        "pu_Address_Country": bok_1.b_034_b_pu_address_country,
        "pu_Address_PostalCode": bok_1.b_033_b_pu_address_postalcode,
        "pu_Address_State": bok_1.b_031_b_pu_address_state,
        "pu_Address_Suburb": bok_1.b_032_b_pu_address_suburb,
        "deToCompanyName": bok_1.b_054_b_del_company,
        "de_to_Contact_F_LName": bok_1.b_061_b_del_contact_full_name,
        "de_Email": bok_1.b_063_b_del_email,
        "de_to_Phone_Main": bok_1.b_064_b_del_phone_main,
        "de_To_Address_Street_1": bok_1.b_055_b_del_address_street_1,
        "de_To_Address_Street_2": bok_1.b_056_b_del_address_street_2,
        "de_To_Address_Country": bok_1.b_060_b_del_address_country,
        "de_To_Address_PostalCode": bok_1.b_059_b_del_address_postalcode,
        "de_To_Address_State": bok_1.b_057_b_del_address_state,
        "de_To_Address_Suburb": bok_1.b_058_b_del_address_suburb,
        "client_warehouse_code": bok_1.b_client_warehouse_code,
        "kf_client_id": bok_1.fk_client_id,
        "b_client_name": client.company_name,
    }

    booking_lines = []
    for _bok_2 in new_bok_2s:
        bok_2_line = {
            # "fk_booking_id": _bok_2.fk_header_id,
            "e_type_of_packaging": _bok_2.l_001_type_of_packaging,
            "e_qty": int(_bok_2.l_002_qty),
            "e_item": _bok_2.l_003_item,
            "e_dimUOM": _bok_2.l_004_dim_UOM,
            "e_dimLength": _bok_2.l_005_dim_length,
            "e_dimWidth": _bok_2.l_006_dim_width,
            "e_dimHeight": _bok_2.l_007_dim_height,
            "e_weightUOM": _bok_2.l_008_weight_UOM,
            "e_weightPerEach": _bok_2.l_009_weight_per_each,
        }
        booking_lines.append(bok_2_line)

    fc_log, _ = FC_Log.objects.get_or_create(
        client_booking_id=bok_1.client_booking_id,
        old_quote__isnull=True,
        new_quote__isnull=True,
    )
    fc_log.old_quote = bok_1.quote
    body = {"booking": booking, "booking_lines": booking_lines}
    _, success, message, quote_set = pricing_oper(
        body=body,
        booking_id=None,
        is_pricing_only=True,
    )
    logger.info(
        f"#519 {LOG_ID} Pricing result: success: {success}, message: {message}, results cnt: {quote_set.count()}"
    )

    # Select best quotes(fastest, lowest)
    if quote_set.exists() and quote_set.count() > 0:
        bok_1_obj = bok_1
        auto_select_pricing_4_bok(bok_1_obj, quote_set)
        best_quotes = select_best_options(pricings=quote_set)
        logger.info(f"#520 {LOG_ID} Selected Best Pricings: {best_quotes}")

        context = {"client_customer_mark_up": client.client_customer_mark_up}
        json_results = SimpleQuoteSerializer(
            best_quotes, many=True, context=context
        ).data
        json_results = dme_time_lib.beautify_eta(json_results, best_quotes, client)

        if bok_1.success == dme_constants.BOK_SUCCESS_4:
            best_quote = best_quotes[0]
            bok_1_obj.b_003_b_service_name = best_quote.service_name
            bok_1_obj.b_001_b_freight_provider = best_quote.freight_provider
            bok_1_obj.save()
            fc_log.new_quote = best_quotes[0]
            fc_log.save()
    else:
        message = f"#521 {LOG_ID} No Pricing results to select - BOK_1 pk_header_id: {bok_1.pk_header_id}"
        logger.error(message)
        send_email_to_admins("No FC result", message)

    # Set Express or Standard
    if len(json_results) == 1:
        json_results[0]["service_name"] = "Standard"
    else:
        if float(json_results[0]["cost"]) > float(json_results[1]["cost"]):
            json_results[0]["service_name"] = "Express"
            json_results[1]["service_name"] = "Standard"

            if json_results[0]["eta"] == json_results[1]["eta"]:
                eta = f"{int(json_results[1]['eta'].split(' ')[0]) + 1} days"
                json_results[1]["eta"] = eta

            json_results = [json_results[1], json_results[0]]
        else:
            json_results[1]["service_name"] = "Express"
            json_results[0]["service_name"] = "Standard"

            if json_results[0]["eta"] == json_results[1]["eta"]:
                eta = f"{int(json_results[0]['eta'].split(' ')[0]) + 1} days"
                json_results[0]["eta"] = eta

    # Response
    if json_results:
        logger.info(f"@8838 {LOG_ID} success: True, 201_created")
        return json_results
    else:
        message = "Pricing cannot be returned due to incorrect address information."
        logger.info(f"@8839 {LOG_ID} {message}")
        return message


def scanned(payload, client):
    """
    called as get_label

    request when item(s) is picked(scanned) at warehouse
    should response LABEL if payload is correct
    """
    LOG_ID = "[SCANNED Jason L]"
    b_client_order_num = payload.get("HostOrderNumber")
    sscc = payload.get("sscc")  # Optional for single SSCC get-label

    # Check required params are included
    if not b_client_order_num:
        message = "'HostOrderNumber' is required."
        raise ValidationError(message)

    # Trim data
    b_client_order_num = b_client_order_num.strip()
    sscc = None if not sscc else sscc.strip()

    # Check if Order exists on Bookings table
    booking = (
        Bookings.objects.select_related("api_booking_quote")
        .filter(
            b_client_name=client.company_name, b_client_order_num=b_client_order_num
        )
        .first()
    )

    if not booking:
        message = "Order does not exist. 'HostOrderNumber' is invalid."
        logger.info(f"@350 {LOG_ID} Booking: {booking}")
        raise ValidationError(message)

    if not booking.api_booking_quote:
        logger.info(f"@351 {LOG_ID} No quote! Booking: {booking}")
        raise Exception("Booking doens't have quote.")

    # Fetch SSCC data by using `Talend` app
    picked_items = get_picked_items(b_client_order_num, sscc)

    if sscc and not picked_items:
        message = f"Wrong SSCC - {sscc}"
        logger.info(f"@351 {LOG_ID} {message}")
        raise ValidationError(message)
    elif not sscc and not picked_items:
        message = f"No SSCC found for the Order - {b_client_order_num}"
        logger.info(f"@352 {LOG_ID} {message}")
        raise ValidationError(message)

    # If Order exists
    pk_booking_id = booking.pk_booking_id
    fp_name = booking.api_booking_quote.freight_provider.lower()
    lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
    line_datas = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)
    original_items = lines.exclude(e_item="Auto repacked item").filter(
        sscc__isnull=True
    )

    logger.info(f"@360 {LOG_ID} Booking: {booking}")
    logger.info(f"@361 {LOG_ID} Lines: {lines}")
    logger.info(f"@362 {LOG_ID} Original Lines: {original_items}")

    with transaction.atomic():
        # Rollback `auto repack` | `already packed` operation
        for line in lines:
            if (
                line.e_item == "Auto repacked item"
                and line.e_type_of_packaging == "PAL"
            ):
                line.is_deleted = True
                line.save()

            if line.sscc:
                line.delete()

        # Delete all LineData
        for line_data in line_datas:
            line_data.delete()

        # Save
        sscc_lines = {}
        for picked_item in picked_items:
            # Find source line
            old_line = None
            first_item = picked_item["items"][0]

            for original_item in original_items:
                if original_item.zbl_121_integer_1 == first_item["sequence"]:
                    old_line = original_item

            # Create new Lines
            new_line = Booking_lines()
            new_line.fk_booking_id = pk_booking_id
            new_line.pk_booking_lines_id = str(uuid.uuid4())
            new_line.e_type_of_packaging = picked_item.get("package_type")
            new_line.e_qty = first_item["qty"]
            new_line.zbl_121_integer_1 = first_item["sequence"]
            new_line.e_item = old_line.e_item
            new_line.e_item_type = old_line.e_item_type
            new_line.e_dimUOM = picked_item["dimensions"]["unit"]
            new_line.e_dimLength = picked_item["dimensions"]["length"]
            new_line.e_dimWidth = picked_item["dimensions"]["width"]
            new_line.e_dimHeight = picked_item["dimensions"]["height"]
            new_line.e_weightUOM = picked_item["weight"]["unit"]
            new_line.e_weightPerEach = picked_item["weight"]["weight"]
            new_line.sscc = picked_item["sscc"]
            new_line.picked_up_timestamp = (
                picked_item.get("timestamp") or datetime.now()
            )
            new_line.save()

            # Soft delete source line
            old_line.is_deleted = True
            old_line.save()

            # Create new line_data
            for item in picked_item["items"]:
                line_data = Booking_lines_data()
                line_data.fk_booking_id = pk_booking_id
                line_data.fk_booking_lines_id = new_line.pk_booking_lines_id
                line_data.itemDescription = "Picked at warehouse"
                line_data.quantity = item.get("qty")
                line_data.clientRefNumber = picked_item["sscc"]
                line_data.save()

            if picked_item["sscc"] not in sscc_lines:
                sscc_lines[picked_item["sscc"]] = [new_line]
            else:
                sscc_lines[picked_item["sscc"]].append(new_line)

    # Build label with SSCC - one sscc should have one page label
    labeled_ssccs = []
    for sscc in sscc_lines:
        if sscc in labeled_ssccs:
            continue

        if not booking.vx_freight_provider and booking.api_booking_quote:
            _booking = migrate_quote_info_to_booking(booking, booking.api_booking_quote)

        file_path = (
            f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au"
        )

        logger.info(f"@368 - building label with SSCC...")
        file_path, file_name = build_label(
            booking=booking,
            file_path=file_path,
            lines=sscc_lines[sscc],
            label_index=0,
            sscc=sscc,
            one_page_label=True,
        )

        # Convert label into ZPL format
        logger.info(
            f"@369 {LOG_ID} converting LABEL({file_path}/{file_name}) into ZPL format..."
        )
        label_url = f"{file_path}/{file_name}"
        result = pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

        if not result:
            message = "Please contact DME support center. <bookings@deliver-me.com.au>"
            raise Exception(message)

        with open(label_url[:-4] + ".zpl", "rb") as zpl:
            zpl_data = str(b64encode(zpl.read()))[2:-1]

        labeled_ssccs.append(labeled_ssccs)

    """
        Move to Ready api
    """
    # # Should get pricing again when if fully picked
    # if is_picked_all:
    #     next_biz_day = dme_time_lib.next_business_day(date.today(), 1)
    #     booking.puPickUpAvailFrom_Date = str(next_biz_day)[:10]
    #     booking.save()

    #     new_fc_log = FC_Log.objects.create(
    #         client_booking_id=booking.b_client_booking_ref_num,
    #         old_quote=booking.api_booking_quote,
    #     )
    #     new_fc_log.save()
    #     logger.info(
    #         f"#371 {LOG_ID} - Picked all items: {booking.b_bookingID_Visual}, now getting Quotes again..."
    #     )
    #     _, success, message, quotes = pricing_oper(body=None, booking_id=booking.pk)
    #     logger.info(
    #         f"#372 {LOG_ID} - Pricing result: success: {success}, message: {message}, results cnt: {quotes.count()}"
    #     )

    #     # Select best quotes(fastest, lowest)
    #     if quotes.exists() and quotes.count() > 0:
    #         quotes = quotes.filter(
    #             freight_provider__iexact=booking.vx_freight_provider,
    #             service_name=booking.vx_serviceName,
    #         )
    #         best_quotes = select_best_options(pricings=quotes)
    #         logger.info(f"#373 {LOG_ID} - Selected Best Pricings: {best_quotes}")

    #         if best_quotes:
    #             booking.api_booking_quote = best_quotes[0]
    #             booking.save()
    #             new_fc_log.new_quote = booking.api_booking_quote
    #             new_fc_log.save()
    #         else:
    #             booking.api_booking_quote = None
    #             booking.save()

    logger.info(
        f"#379 {LOG_ID} - Successfully scanned. Booking Id: {booking.b_bookingID_Visual}"
    )

    return {
        "labelUrl": f"http://{settings.WEB_SITE_IP}/label/{booking.b_client_booking_ref_num}/"
    }


def ready_boks(payload, client):
    """
    When it is ready(picked all items) on Warehouse
    """
    LOG_ID = "[READY Jason L]"
    b_client_order_num = payload.get("HostOrderNumber")

    # Check required params are included
    if not b_client_order_num:
        message = "'HostOrderNumber' is required."
        raise ValidationError(message)

    # Check if Order exists
    booking = (
        Bookings.objects.select_related("api_booking_quote")
        .filter(
            b_client_name=client.company_name, b_client_order_num=b_client_order_num
        )
        .first()
    )

    if not booking:
        message = "Order does not exist. HostOrderNumber' is invalid."
        raise ValidationError(message)

    # If Hunter Order
    fp_name = booking.api_booking_quote.freight_provider.lower()

    if fp_name == "hunter" and booking.b_status == "Booked":
        message = "Order is already BOOKED."
        logger.info(f"@340 {LOG_ID} {message}")
        return message
    elif fp_name == "hunter" and booking.b_status != "Booked":
        # DME don't get the ready api for Hunter Order
        message = "Please contact DME support center. <bookings@deliver-me.com.au>"
        logger.info(f"@341 {LOG_ID} {message}")
        raise Exception(message)

    # Check if already ready
    if booking.b_status not in ["Picking", "Ready for Booking"]:
        message = "Order is already Ready."
        logger.info(f"@342 {LOG_ID} {message}")
        return message

    # If NOT
    pk_booking_id = booking.pk_booking_id
    lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
    line_datas = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)

    # Update DB so that Booking can be BOOKED
    if booking.api_booking_quote:
        booking.b_status = "Ready for Booking"
    else:
        booking.b_status = "On Hold"
        send_email_to_admins(
            f"Quote issue on Booking(#{booking.b_bookingID_Visual})",
            f"Original FP was {booking.vx_freight_provider}({booking.vx_serviceName})."
            + f" After labels were made {booking.vx_freight_provider}({booking.vx_serviceName}) was not an option for shipment."
            + f" Please do FC manually again on DME portal.",
        )

    booking.save()

    message = "Order will be BOOKED soon."
    logger.info(f"@349 {LOG_ID} {message}")
    return message
