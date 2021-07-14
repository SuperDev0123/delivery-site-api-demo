import os
import json
import uuid
import logging
from datetime import datetime, date
from base64 import b64encode

from django.conf import settings
from django.db import transaction
from django.db.models import Q
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
    API_booking_quotes,
)
from api.serializers import SimpleQuoteSerializer
from api.serializers_client import *
from api.convertors import pdf
from api.common import (
    common_times as dme_time_lib,
    constants as dme_constants,
    status_history,
)
from api.common.pallet import get_number_of_pallets, get_palletized_by_ai
from api.common.booking_quote import set_booking_quote
from api.fp_apis.utils import (
    select_best_options,
    get_status_category_from_status,
    auto_select_pricing_4_bok,
    gen_consignment_num,
)
from api.fp_apis.operations.book import book as book_oper
from api.fp_apis.operations.pricing import pricing as pricing_oper
from api.operations import product_operations as product_oper
from api.operations.email_senders import send_email_to_admins
from api.operations.labels.index import build_label, get_barcode
from api.operations.pronto_xi.index import populate_bok as get_bok_from_pronto_xi
from api.operations.pronto_xi.index import send_info_back
from api.clients.operations.index import get_warehouse, get_suburb_state
from api.clients.jason_l.operations import (
    get_picked_items,
    update_when_no_quote_required,
    get_bok_by_talend,
)
from api.clients.jason_l.constants import NEED_PALLET_GROUP_CODES, SERVICE_GROUP_CODES
from api.helpers.cubic import get_cubic_meter


logger = logging.getLogger(__name__)


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
        "puPickUpAvailFrom_Date": next_biz_day,
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
        "pu_Address_Type": bok_1.get("b_027_b_pu_address_type") or "residential",
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
        "de_To_AddressType": bok_1.get("b_053_b_del_address_type") or "residential",
        "b_booking_tail_lift_pickup": bok_1.get("b_019_b_pu_tail_lift") or 0,
        "b_booking_tail_lift_deliver": bok_1.get("b_041_b_del_tail_lift") or 0,
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

    items = product_oper.get_product_items(bok_2s, client, True, False)

    for index, item in enumerate(items):
        booking_line = {
            "pk_lines_id": index,
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
    LOG_ID = "[PUSH Jason L]"  # PB - PUSH BOKS
    bok_1 = payload["booking"]
    bok_2s = []
    client_name = None
    old_quote = None
    best_quotes = None
    json_results = []

    # Assign vars
    is_biz = "_bizsys" in username
    is_web = "_websys" in username

    # Strip data
    if is_biz:
        bok_1["b_client_order_num"] = bok_1["b_client_order_num"].strip()
        bok_1["b_client_sales_inv_num"] = bok_1["b_client_sales_inv_num"].strip()
        bok_1["shipping_type"] = bok_1.get("shipping_type", "DMEM").strip()

    bok_1["b_053_b_del_address_type"] = (
        bok_1.get("b_053_b_del_delivery_type", "business").strip().lower()
    )

    if not bok_1["b_053_b_del_address_type"] in ["business", "residential"]:
        bok_1["b_053_b_del_address_type"] == "business"
        bok_1["shipping_type"] = "DMEM"

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
    else:
        if not bok_1.get("client_booking_id"):
            message = "'client_booking_id' is required."
            logger.info(f"{LOG_ID} {message}")
            raise ValidationError(message)

        if not payload.get("booking_lines"):
            message = "'booking_lines' is required."
            logger.info(f"{LOG_ID} {message}")
            raise ValidationError(message)

    # Check duplicated push with `b_client_order_num`
    selected_quote = None
    if method == "POST":
        if is_biz:
            bok_1_objs = BOK_1_headers.objects.filter(
                fk_client_id=client.dme_account_num,
                b_client_order_num=bok_1["b_client_order_num"],
            )

            if bok_1_objs.exists():
                message = f"BOKS API Error - Order(b_client_order_num={bok_1['b_client_order_num']}) does already exist."
                logger.info(f"@884 {LOG_ID} {message}")

                json_res = {
                    "status": False,
                    "message": f"Order(b_client_order_num={bok_1['b_client_order_num']}) does already exist.",
                }

                if (
                    int(bok_1_objs.first().success) == dme_constants.BOK_SUCCESS_3
                ):  # Update
                    # Delete existing data
                    pk_header_id = bok_1_objs.first().pk_header_id
                    old_bok_1 = bok_1_objs.first()
                    old_bok_2s = BOK_2_lines.objects.filter(fk_header_id=pk_header_id)
                    old_bok_3s = BOK_3_lines_data.objects.filter(
                        fk_header_id=pk_header_id
                    )
                    quotes = API_booking_quotes.objects.filter(
                        fk_booking_id=pk_header_id
                    )

                    # Check new Order info
                    # try:
                    #     bok_1, bok_2s = get_bok_from_pronto_xi(bok_1)
                    # except Exception as e:
                    #     logger.error(
                    #         f"@887 {LOG_ID} Failed to get Order by using Pronto API. OrderNo: {bok_1['b_client_order_num']}, Error: {str(e)}"
                    #     )
                    #     logger.info(
                    #         f"@888 Now trying to get Order by Talend App (for Archived Order)"
                    #     )
                    bok_1, bok_2s = get_bok_by_talend(bok_1["b_client_order_num"])

                    warehouse = get_warehouse(
                        client, code=f"JASON_L_{bok_1['warehouse_code']}"
                    )
                    del bok_1["warehouse_code"]
                    bok_1["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
                    bok_1["b_clientPU_Warehouse"] = warehouse.name
                    bok_1["b_client_warehouse_code"] = warehouse.client_warehouse_code
                    is_updated = update_when_no_quote_required(
                        old_bok_1, old_bok_2s, bok_1, bok_2s
                    )

                    if old_bok_1.quote:
                        old_quote = old_bok_1.quote

                    # if not is_updated:
                    if True:
                        logger.info(
                            f"@8850 {LOG_ID} Order {bok_1['b_client_order_num']} requires new quotes."
                        )
                        if old_bok_1.b_092_booking_type == "DMEM" and old_bok_1.quote:
                            selected_quote = old_bok_1.quote

                        quotes.delete()
                        old_bok_3s.delete()
                        old_bok_2s.delete()
                        old_bok_1.delete()
                    else:
                        # Return price page url
                        url = f"http://{settings.WEB_SITE_IP}/price/{bok_1_objs.first().client_booking_id}/"
                        json_res["pricePageUrl"] = url
                        logger.info(f"@885 {LOG_ID} Response: {json_res}")
                        return json_res
                else:
                    # Return status page url
                    url = f"http://{settings.WEB_SITE_IP}/status/{bok_1_objs.first().client_booking_id}/"
                    json_res["pricePageUrl"] = url
                    logger.info(f"@886 {LOG_ID} Response: {json_res}")
                    return json_res

    # Prepare population
    if is_biz and not bok_2s:
        # try:
        #     bok_1, bok_2s = get_bok_from_pronto_xi(bok_1)
        # except Exception as e:
        #     logger.error(
        #         f"@887 {LOG_ID} Failed to get Order by using Pronto API. OrderNo: {bok_1['b_client_order_num']}, Error: {str(e)}"
        #     )
        #     logger.info(
        #         f"@888 Now trying to get Order by Talend App (for Archived Order)"
        #     )
        bok_1, bok_2s = get_bok_by_talend(bok_1["b_client_order_num"])

        warehouse = get_warehouse(client, code=f"JASON_L_{bok_1['warehouse_code']}")
        del bok_1["warehouse_code"]
        bok_1["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
        bok_1["b_clientPU_Warehouse"] = warehouse.name
        bok_1["b_client_warehouse_code"] = warehouse.client_warehouse_code

    if is_web:
        for index, line in enumerate(payload.get("booking_lines")):
            bok_2s.append(
                {
                    "model_number": line["model_number"],
                    "qty": line["qty"],
                    "sequence": 1,
                    "UOMCode": "EACH",
                    "ProductGroupCode": "----",
                }
            )

        warehouse = get_warehouse(client)
        bok_1["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
        bok_1["b_clientPU_Warehouse"] = warehouse.name
        bok_1["b_client_warehouse_code"] = warehouse.client_warehouse_code

        next_biz_day = dme_time_lib.next_business_day(date.today(), 1)
        bok_1["b_021_b_pu_avail_from_date"] = str(next_biz_day)[:10]

    bok_1["pk_header_id"] = str(uuid.uuid4())

    # Generate `client_booking_id` for Pronto
    if is_biz:
        client_booking_id = f"{bok_1['b_client_order_num']}_{bok_1['pk_header_id']}_{datetime.strftime(datetime.utcnow(), '%s')}"
        bok_1["client_booking_id"] = client_booking_id

    bok_1["fk_client_id"] = client.dme_account_num
    bok_1["x_booking_Created_With"] = "DME PUSH API"
    bok_1["success"] = dme_constants.BOK_SUCCESS_2  # Default success code
    bok_1["b_092_booking_type"] = bok_1.get("shipping_type")

    # `DMEA` or `DMEM` - set `success` as 3
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

    bok_1["b_031_b_pu_address_state"] = bok_1["b_031_b_pu_address_state"].upper()

    bok_1_serializer = BOK_1_Serializer(data=bok_1)

    if not bok_1_serializer.is_valid():
        message = f"Serialiser Error - {bok_1_serializer.errors}"
        logger.info(f"@8821 {LOG_ID} {message}")
        raise Exception(message)

    # Save bok_2s (Product & Child items)
    # items = product_oper.get_product_items(bok_2s, client, is_web, False)
    items = bok_2s
    new_bok_2s = []
    bok_2_objs = []

    with transaction.atomic():
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
            line["zbl_102_text_2"] = (
                item["zbl_102_text_2"] if item["zbl_102_text_2"] else "_"
            )
            line["is_deleted"] = item["zbl_102_text_2"] in SERVICE_GROUP_CODES

            bok_2_serializer = BOK_2_Serializer(data=line)
            if bok_2_serializer.is_valid():
                bok_2_obj = bok_2_serializer.save()

                if not line["is_deleted"] and not "(Ignored)" in line["l_003_item"]:
                    bok_2_objs.append(bok_2_obj)
                    line["pk_lines_id"] = bok_2_obj.pk
                    new_bok_2s.append({"booking_line": line})
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
    need_palletize = False
    for bok_2_obj in bok_2_objs:
        carton_cnt += bok_2_obj.l_002_qty

        if bok_2_obj.zbl_102_text_2 in NEED_PALLET_GROUP_CODES:
            need_palletize = True
            logger.info(
                f"@8126 {LOG_ID} Need to be Palletized! - {bok_2_obj.zbl_102_text_2}"
            )
            break

    if carton_cnt > 2 or need_palletize:
        message = "Auto repacking..."
        logger.info(f"@8130 {LOG_ID} {message}")
        bok_2s = []

        # Select suitable pallet and get required pallets count
        pallets = Pallet.objects.all()
        palletized, non_palletized = get_palletized_by_ai(bok_2_objs, pallets)
        logger.info(f"@8831 {LOG_ID} {palletized}\n{non_palletized}")

        # Create one PAL bok_2
        for item in non_palletized:  # Non Palletized
            for new_bok_2 in new_bok_2s:
                if new_bok_2 == item["line_obj"]:
                    new_bok_2.l_002_qty = item["quantity"]
                    bok_2.append(new_bok_2)

        for palletized_item in palletized:  # Palletized
            pallet = pallets[palletized_item["pallet_index"]]

            total_weight = 0
            for _iter in palletized_item["lines"]:
                line_in_pallet = _iter["line_obj"]
                total_weight += (
                    line_in_pallet.l_009_weight_per_each
                    * _iter["quantity"]
                    / palletized_item["quantity"]
                )

            new_line = {}
            new_line["fk_header_id"] = bok_1["pk_header_id"]
            new_line["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
            new_line["pk_booking_lines_id"] = str(uuid.uuid1())
            new_line["success"] = bok_1["success"]
            new_line["l_001_type_of_packaging"] = "PAL"
            new_line["l_002_qty"] = palletized_item["quantity"]
            new_line["l_003_item"] = "Auto repacked item"
            new_line["l_004_dim_UOM"] = "mm"
            new_line["l_005_dim_length"] = pallet.length
            new_line["l_006_dim_width"] = pallet.width
            new_line["l_007_dim_height"] = pallet.height
            new_line["l_009_weight_per_each"] = round(total_weight, 2)
            new_line["l_008_weight_UOM"] = "KG"
            new_line["is_deleted"] = False

            bok_2_serializer = BOK_2_Serializer(data=new_line)
            if bok_2_serializer.is_valid():
                # Create Bok_3s
                for _iter in palletized_item["lines"]:
                    line = _iter["line_obj"]  # line_in_pallet
                    bok_3 = {}
                    bok_3["fk_header_id"] = bok_1["pk_header_id"]
                    bok_3["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
                    bok_3["fk_booking_lines_id"] = new_line["pk_booking_lines_id"]
                    bok_3["success"] = line.success
                    bok_3[
                        "ld_005_item_serial_number"
                    ] = line.zbl_121_integer_1  # Sequence
                    bok_3["ld_001_qty"] = line.l_002_qty
                    bok_3["ld_003_item_description"] = line.l_003_item
                    bok_3["ld_002_model_number"] = line.e_item_type
                    bok_3["zbld_121_integer_1"] = line.zbl_121_integer_1  # Sequence
                    bok_3["zbld_122_integer_2"] = _iter["quantity"]
                    bok_3["zbld_131_decimal_1"] = line.l_005_dim_length
                    bok_3["zbld_132_decimal_2"] = line.l_006_dim_width
                    bok_3["zbld_133_decimal_3"] = line.l_007_dim_height
                    bok_3["zbld_134_decimal_4"] = round(line.l_009_weight_per_each, 2)
                    bok_3["zbld_101_text_1"] = line.l_004_dim_UOM
                    bok_3["zbld_102_text_2"] = line.l_008_weight_UOM
                    bok_3["zbld_103_text_3"] = line.e_item_type
                    bok_3["zbld_104_text_4"] = line.l_001_type_of_packaging
                    bok_3["zbld_105_text_5"] = line.l_003_item

                    bok_3_serializer = BOK_3_Serializer(data=bok_3)
                    if bok_3_serializer.is_valid():
                        bok_3_serializer.save()

                        # Soft delete `line in pallet`
                        line.is_deleted = True
                        line.save()
                    else:
                        message = f"Serialiser Error - {bok_3_serializer.errors}"
                        logger.info(f"@8134 {LOG_ID} {message}")
                        raise Exception(message)

                bok_2_serializer.save()
                bok_2s.append({"booking_line": new_line})
            else:
                message = f"Serialiser Error - {bok_2_serializer.errors}"
                logger.info(f"@8135 {LOG_ID} {message}")
                raise Exception(message)

        # Set `auto_repack` flag
        bok_1_obj.b_081_b_pu_auto_pack = True
        bok_1_obj.save()

    # Get next business day
    next_biz_day = dme_time_lib.next_business_day(date.today(), 1)

    # Do not get pricing when there is issue
    if bok_1.get("zb_105_text_5") and "Error" in bok_1.get("zb_105_text_5"):
        logger.info(
            f"#515 {LOG_ID} Skip Pricing due to address issue: {bok_1.get('zb_105_text_5')}"
        )

        url = f"http://{settings.WEB_SITE_IP}/price/{bok_1['client_booking_id']}/"
        result = {"success": True, "pricePageUrl": url}
        logger.info(f"@8837 {LOG_ID} success: True, 201_created --- SKIP QUOTE!")
        return result

    # Get Pricings
    booking = {
        "pk_booking_id": bok_1["pk_header_id"],
        "puPickUpAvailFrom_Date": next_biz_day,
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
        "pu_Address_Type": bok_1["b_027_b_pu_address_type"],
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
        "de_To_AddressType": bok_1["b_053_b_del_address_type"],
        "b_booking_tail_lift_pickup": bok_1["b_019_b_pu_tail_lift"],
        "b_booking_tail_lift_deliver": bok_1["b_041_b_del_tail_lift"],
        "client_warehouse_code": bok_1["b_client_warehouse_code"],
        "kf_client_id": bok_1["fk_client_id"],
        "b_client_name": client.company_name,
    }

    booking_lines = []
    for bok_2 in bok_2s:
        _bok_2 = bok_2["booking_line"]

        if _bok_2["is_deleted"]:
            continue

        bok_2_line = {
            "fk_booking_id": _bok_2["fk_header_id"],
            "pk_lines_id": _bok_2["fk_header_id"],
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
    # fc_log.old_quote = old_quote
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
    if selected_quote:
        quote_set = quote_set.filter(
            freight_provider=selected_quote.freight_provider,
            service_name=selected_quote.service_name,
        )

    if quote_set.exists() and quote_set.count() > 0:
        auto_select_pricing_4_bok(bok_1_obj, quote_set)
        best_quotes = select_best_options(pricings=quote_set)
        logger.info(f"#520 {LOG_ID} Selected Best Pricings: {best_quotes}")

        context = {"client_customer_mark_up": client.client_customer_mark_up}
        json_results = SimpleQuoteSerializer(
            best_quotes, many=True, context=context
        ).data
        json_results = dme_time_lib.beautify_eta(json_results, best_quotes, client)

        # if bok_1["success"] == dme_constants.BOK_SUCCESS_4:
        best_quote = best_quotes[0]
        bok_1_obj.b_003_b_service_name = best_quote.service_name
        bok_1_obj.b_001_b_freight_provider = best_quote.freight_provider
        bok_1_obj.b_002_b_vehicle_type = (
            best_quote.vehicle.description if best_quote.vehicle else None
        )
        bok_1_obj.save()
        fc_log.new_quote = best_quotes[0]
        fc_log.save()

        # Send quote info back to Pronto
        # result = send_info_back(bok_1_obj, best_quote)
    else:
        b_client_order_num = bok_1.get("b_client_order_num")

        if b_client_order_num:
            message = f"#521 {LOG_ID} No Pricing results to select - BOK_1 pk_header_id: {bok_1['pk_header_id']}\nOrder Number: {bok_1['b_client_order_num']}"
            logger.error(message)

            if bok_1["b_client_order_num"]:
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

            # Commented (2021-06-18)
            # if bok_1["shipping_type"] == "DMEM":
            #     url = (
            #         f"http://{settings.WEB_SITE_IP}/price/{bok_1['client_booking_id']}/"
            #     )
            # elif bok_1["shipping_type"] == "DMEA":
            #     url = f"http://{settings.WEB_SITE_IP}/status/{bok_1['client_booking_id']}/"

            # Show price page either DMEA and DMEM
            url = f"http://{settings.WEB_SITE_IP}/price/{bok_1['client_booking_id']}/"

            result["pricePageUrl"] = url
            logger.info(f"@8837 {LOG_ID} success: True, 201_created")
            return result
        else:
            logger.info(f"@8838 {LOG_ID} success: True, 201_created")
            result = {"success": True, "results": json_results}
            return result
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
    bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id).exclude(
        l_003_item__icontains="(ignored)"
    )
    bok_3s = BOK_3_lines_data.objects.filter(fk_header_id=bok_1.pk_header_id)

    if repack_status:  # repack
        # Delete existing Bok_2s and Bok_3s
        bok_2s.filter(l_003_item="Auto repacked item").delete()
        bok_3s.delete()
        bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id).exclude(
            Q(zbl_102_text_2__in=SERVICE_GROUP_CODES)
            | Q(l_003_item__icontains="(ignored)")
        )

        # Get Pallet
        if pallet_id == -1:  # Use DME AI for Palletizing
            # Select suitable pallet and get required pallets count
            pallets = Pallet.objects.all()
            palletized, non_palletized = get_palletized_by_ai(bok_2s, pallets)
            logger.info(f"@8831 {LOG_ID} {palletized}\n{non_palletized}")

            # Create one PAL bok_2
            for item in non_palletized:  # Non-Palletized
                for bok_2 in bok_2s:
                    if bok_2 == item["line_obj"]:
                        bok_2.l_002_qty = item["quantity"]
                        new_bok_2s.append(bok_2)

            for palletized_item in palletized:  # Palletized
                pallet = pallets[palletized_item["pallet_index"]]

                total_weight = 0
                for _iter in palletized_item["lines"]:
                    line_in_pallet = _iter["line_obj"]
                    total_weight += (
                        line_in_pallet.l_009_weight_per_each * line_in_pallet.l_002_qty
                    )

                new_line = {}
                new_line["fk_header_id"] = bok_1.pk_header_id
                new_line["v_client_pk_consigment_num"] = bok_1.pk_header_id
                new_line["pk_booking_lines_id"] = str(uuid.uuid1())
                new_line["success"] = bok_1.success
                new_line["l_001_type_of_packaging"] = "PAL"
                new_line["l_002_qty"] = palletized_item["quantity"]
                new_line["l_003_item"] = "Auto repacked item"
                new_line["l_004_dim_UOM"] = "mm"
                new_line["l_005_dim_length"] = pallet.length
                new_line["l_006_dim_width"] = pallet.width
                new_line["l_007_dim_height"] = pallet.height
                new_line["l_009_weight_per_each"] = round(total_weight, 2)
                new_line["l_008_weight_UOM"] = "KG"
                new_line["is_deleted"] = False

                bok_2_serializer = BOK_2_Serializer(data=new_line)
                if bok_2_serializer.is_valid():
                    # Create Bok_3s
                    for _iter in palletized_item["lines"]:
                        line = _iter["line_obj"]  # line_in_pallet

                        if line.zbl_102_text_2 in SERVICE_GROUP_CODES:
                            continue

                        bok_3 = {}
                        bok_3["fk_header_id"] = bok_1.pk_header_id
                        bok_3["v_client_pk_consigment_num"] = bok_1.pk_header_id
                        bok_3["fk_booking_lines_id"] = new_line["pk_booking_lines_id"]
                        bok_3["success"] = line.success
                        bok_3[
                            "ld_005_item_serial_number"
                        ] = line.zbl_121_integer_1  # Sequence
                        bok_3["ld_001_qty"] = line.l_002_qty
                        bok_3["ld_003_item_description"] = line.l_003_item
                        bok_3["ld_002_model_number"] = line.e_item_type
                        bok_3["zbld_121_integer_1"] = line.zbl_121_integer_1  # Sequence
                        bok_3["zbld_122_integer_2"] = _iter["quantity"]
                        bok_3["zbld_131_decimal_1"] = line.l_005_dim_length
                        bok_3["zbld_132_decimal_2"] = line.l_006_dim_width
                        bok_3["zbld_133_decimal_3"] = line.l_007_dim_height
                        bok_3["zbld_134_decimal_4"] = round(
                            line.l_009_weight_per_each, 2
                        )
                        bok_3["zbld_101_text_1"] = line.l_004_dim_UOM
                        bok_3["zbld_102_text_2"] = line.l_008_weight_UOM
                        bok_3["zbld_103_text_3"] = line.e_item_type
                        bok_3["zbld_104_text_4"] = line.l_001_type_of_packaging
                        bok_3["zbld_105_text_5"] = line.l_003_item

                        bok_3_serializer = BOK_3_Serializer(data=bok_3)
                        if bok_3_serializer.is_valid():
                            bok_3_serializer.save()

                            # Soft delete `line in pallet`
                            line.is_deleted = True
                            line.save()
                        else:
                            message = f"Serialiser Error - {bok_3_serializer.errors}"
                            logger.info(f"@8134 {LOG_ID} {message}")
                            raise Exception(message)

                    new_bok_2 = bok_2_serializer.save()
                    new_bok_2s.append(new_bok_2)
                else:
                    message = f"Serialiser Error - {bok_2_serializer.errors}"
                    logger.info(f"@8135 {LOG_ID} {message}")
                    raise Exception(message)
        else:  # Select a Pallet
            pallet = Pallet.objects.get(pk=pallet_id)
            number_of_pallets, unpalletized_line_pks = get_number_of_pallets(
                bok_2s, pallet
            )

            if not number_of_pallets and not unpalletized_line_pks:
                message = "0 number of Pallets."
                logger.info(f"@801 {LOG_ID} {message}")
                return message

            total_weight = 0
            for bok_2 in bok_2s:
                total_weight += bok_2.l_009_weight_per_each * bok_2.l_002_qty

            # Create new *1* Pallet Bok_2
            for line_pk in unpalletized_line_pks:  # Non-Palletized
                for bok_2 in bok_2s:
                    if bok_2.pk == line_pk:
                        new_bok_2s.append(bok_2)

            if number_of_pallets:
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

                if (
                    bok_2.zbl_102_text_2 in SERVICE_GROUP_CODES
                    or bok_2.pk in unpalletized_line_pks
                ):
                    continue

                bok_3 = {}
                bok_3["fk_header_id"] = bok_1.pk_header_id
                bok_3["v_client_pk_consigment_num"] = bok_1.pk_header_id
                bok_3["fk_booking_lines_id"] = line["pk_booking_lines_id"]
                bok_3["success"] = bok_1.success
                bok_3["ld_005_item_serial_number"] = bok_2.zbl_121_integer_1  # Sequence
                bok_3["ld_001_qty"] = bok_2.l_002_qty
                bok_3["ld_003_item_description"] = bok_2.l_003_item
                bok_3["ld_002_model_number"] = bok_2.e_item_type
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
            if bok_2.is_deleted and not bok_2.zbl_102_text_2 in SERVICE_GROUP_CODES:
                bok_2.is_deleted = not bok_2.is_deleted
                bok_2.save()

                if not bok_2.is_deleted:
                    new_bok_2s.append(bok_2)

        for bok_3 in bok_3s:
            bok_3.is_deleted = not bok_3.is_deleted
            bok_3.save()

    bok_1.b_081_b_pu_auto_pack = repack_status
    bok_1.save()

    # Get next business day
    next_biz_day = dme_time_lib.next_business_day(date.today(), 1)

    # Get Pricings
    booking = {
        "pk_booking_id": bok_1.pk_header_id,
        "puPickUpAvailFrom_Date": next_biz_day,
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
        "pu_Address_Type": bok_1.b_027_b_pu_address_type,
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
        "de_To_AddressType": bok_1.b_053_b_del_address_type,
        "b_booking_tail_lift_pickup": bok_1.b_019_b_pu_tail_lift,
        "b_booking_tail_lift_deliver": bok_1.b_041_b_del_tail_lift,
        "client_warehouse_code": bok_1.b_client_warehouse_code,
        "kf_client_id": bok_1.fk_client_id,
        "b_client_name": client.company_name,
    }

    booking_lines = []
    for _bok_2 in new_bok_2s:
        if _bok_2.is_deleted:
            continue

        bok_2_line = {
            # "fk_booking_id": _bok_2.fk_header_id,
            "pk_lines_id": _bok_2.pk,
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
    json_results = []

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
            bok_1_obj.b_002_b_vehicle_type = (
                best_quote.vehicle.description if best_quote.vehicle else None
            )
            bok_1_obj.save()
            fc_log.new_quote = best_quotes[0]
            fc_log.save()
    else:
        message = f"#521 {LOG_ID} No Pricing results to select - BOK_1 pk_header_id: {bok_1.pk_header_id}\nOrder Number: {bok_1.b_client_order_num}"
        logger.error(message)

        if bok_1.b_client_order_num:
            send_email_to_admins("No FC result", message)

    # Set Express or Standard
    if len(json_results) == 1:
        json_results[0]["service_name"] = "Standard"
    elif len(json_results) > 1:
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

    # Fetch original data
    pk_booking_id = booking.pk_booking_id
    fp_name = booking.api_booking_quote.freight_provider.lower()
    lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
    line_datas = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)
    original_lines = lines.exclude(e_item="Auto repacked item").filter(
        sscc__isnull=True
    )

    logger.info(f"@360 {LOG_ID} Booking: {booking}")
    logger.info(f"@361 {LOG_ID} Lines: {lines}")
    logger.info(f"@362 {LOG_ID} Original Lines: {original_lines}")

    # prepare save
    sscc_list = []
    for item in picked_items:
        if item["sscc"] not in sscc_list:
            sscc_list.append(item["sscc"])

    with transaction.atomic():
        # Rollback `auto repack` | `already packed` operation
        for line in lines:
            if line.sscc:  # Delete prev sscc lines
                line.delete()
                # continue

            line.is_deleted = True
            line.save()

        # Delete all LineData
        for line_data in line_datas:
            line_data.delete()

        # Save
        sscc_lines = {}
        for sscc in sscc_list:
            first_item = None
            for picked_item in picked_items:
                if picked_item["sscc"] == sscc:
                    first_item = picked_item
                    break

            # Create new Line
            new_line = Booking_lines()
            new_line.fk_booking_id = pk_booking_id
            new_line.pk_booking_lines_id = str(uuid.uuid4())
            new_line.e_type_of_packaging = first_item.get("package_type")
            new_line.e_qty = 1
            new_line.zbl_121_integer_1 = 0
            new_line.e_item = "Picked Item"
            new_line.e_item_type = None
            new_line.e_dimUOM = first_item["dimensions"]["unit"]
            new_line.e_dimLength = first_item["dimensions"]["length"]
            new_line.e_dimWidth = first_item["dimensions"]["width"]
            new_line.e_dimHeight = first_item["dimensions"]["height"]
            new_line.e_weightUOM = first_item["weight"]["unit"]
            new_line.e_weightPerEach = first_item["weight"]["weight"]
            new_line.e_Total_KG_weight = round(
                new_line.e_weightPerEach * new_line.e_qty, 5
            )
            new_line.e_1_Total_dimCubicMeter = round(
                get_cubic_meter(
                    new_line.e_dimLength,
                    new_line.e_dimWidth,
                    new_line.e_dimHeight,
                    new_line.e_dimUOM,
                    new_line.e_qty,
                ),
                5,
            )
            new_line.is_deleted = False
            new_line.zbl_102_text_2 = None
            new_line.sscc = first_item["sscc"]
            new_line.picked_up_timestamp = first_item.get("timestamp") or datetime.now()
            new_line.save()

            sscc_lines[sscc] = [new_line]

            # Create new line_data(s)
            for picked_item in picked_items:
                if picked_item["sscc"] != sscc:
                    continue

                original_line = None
                for line in original_lines:
                    if line.zbl_121_integer_1 == picked_item["items"][0]["sequence"]:
                        original_line = line

                if original_line.zbl_102_text_2 in SERVICE_GROUP_CODES:
                    continue

                line_data = Booking_lines_data()
                line_data.fk_booking_id = pk_booking_id
                line_data.fk_booking_lines_id = new_line.pk_booking_lines_id
                line_data.quantity = picked_item["items"][0]["qty"]
                line_data.itemDescription = original_line.e_item
                line_data.modelNumber = original_line.e_item_type
                line_data.clientRefNumber = sscc
                line_data.itemSerialNumbers = original_line.zbl_121_integer_1
                line_data.save()

    # Should get pricing again
    next_biz_day = dme_time_lib.next_business_day(date.today(), 1)
    booking.puPickUpAvailFrom_Date = next_biz_day
    booking.save()

    new_fc_log = FC_Log.objects.create(
        client_booking_id=booking.b_client_booking_ref_num,
        old_quote=booking.api_booking_quote,
    )
    new_fc_log.save()
    logger.info(f"#371 {LOG_ID} {booking.b_bookingID_Visual} - getting Quotes again...")
    _, success, message, quotes = pricing_oper(body=None, booking_id=booking.pk)
    logger.info(
        f"#372 {LOG_ID} - Pricing result: success: {success}, message: {message}, results cnt: {quotes.count()}"
    )

    # Select best quotes(fastest, lowest)
    if quotes.exists() and quotes.count() > 0:
        if booking.booking_type == "DMEM":
            quotes = quotes.filter(
                freight_provider__iexact=booking.vx_freight_provider,
                service_name=booking.vx_serviceName,
            )

        best_quotes = select_best_options(pricings=quotes)
        logger.info(f"#373 {LOG_ID} - Selected Best Pricings: {best_quotes}")

        if best_quotes:
            set_booking_quote(booking, best_quotes[0])
            new_fc_log.new_quote = booking.api_booking_quote
            new_fc_log.save()
        else:
            set_booking_quote(booking, None)
    else:
        message = f"#521 {LOG_ID} SCAN with No Pricing! Order Number: {booking.b_client_order_num}"
        logger.error(message)

        if booking.b_client_order_num:
            send_email_to_admins("No FC result", message)

    # Build label with SSCC - one sscc should have one page label
    for index, sscc in enumerate(sscc_list):
        file_path = (
            f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au"
        )

        logger.info(f"@368 - building label with SSCC...")
        file_path, file_name = build_label(
            booking=booking,
            file_path=file_path,
            lines=sscc_lines[sscc],
            label_index=index,
            sscc=sscc,
            sscc_cnt=len(sscc_list),
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

    message = f"#379 {LOG_ID} - Successfully scanned. Booking Id: {booking.b_bookingID_Visual}"
    logger.info(message)

    booking.z_label_url = (
        f"http://{settings.WEB_SITE_IP}/label/{booking.b_client_booking_ref_num}/"
    )
    booking.z_downloaded_shipping_label_timestamp = datetime.utcnow()
    booking.save()

    res_json = {"labelUrl": booking.z_label_url}
    return res_json


def ready_boks(payload, client):
    """
    When it is ready(picked all items) on Warehouse
    """
    pass


#     LOG_ID = "[READY Jason L]"
#     b_client_order_num = payload.get("HostOrderNumber")

#     # Check required params are included
#     if not b_client_order_num:
#         message = "'HostOrderNumber' is required."
#         raise ValidationError(message)

#     # Check if Order exists
#     booking = (
#         Bookings.objects.select_related("api_booking_quote")
#         .filter(
#             b_client_name=client.company_name, b_client_order_num=b_client_order_num
#         )
#         .first()
#     )

#     if not booking:
#         message = "Order does not exist. HostOrderNumber' is invalid."
#         raise ValidationError(message)

#     # If Hunter Order
#     fp_name = booking.api_booking_quote.freight_provider.lower()

#     if fp_name == "hunter" and booking.b_status == "Booked":
#         message = "Order is already BOOKED."
#         logger.info(f"@340 {LOG_ID} {message}")
#         return message
#     elif fp_name == "hunter" and booking.b_status != "Booked":
#         # DME don't get the ready api for Hunter Order
#         message = "Please contact DME support center. <bookings@deliver-me.com.au>"
#         logger.info(f"@341 {LOG_ID} {message}")
#         raise Exception(message)

#     # Check if already ready
#     if booking.b_status not in ["Picking", "Ready for Booking"]:
#         message = "Order is already Ready."
#         logger.info(f"@342 {LOG_ID} {message}")
#         return message

#     # If NOT
#     pk_booking_id = booking.pk_booking_id
#     lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
#     line_datas = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)

#     # Update DB so that Booking can be BOOKED
#     if booking.api_booking_quote:
#         booking.b_status = "Ready for Booking"
#     else:
#         booking.b_status = "On Hold"
#         send_email_to_admins(
#             f"Quote issue on Booking(#{booking.b_bookingID_Visual})",
#             f"Original FP was {booking.vx_freight_provider}({booking.vx_serviceName})."
#             + f" After labels were made {booking.vx_freight_provider}({booking.vx_serviceName}) was not an option for shipment."
#             + f" Please do FC manually again on DME portal.",
#         )

#     booking.save()

#     message = "Order will be BOOKED soon."
#     logger.info(f"@349 {LOG_ID} {message}")
#     return message
