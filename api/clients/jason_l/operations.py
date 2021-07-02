import os
import json
import logging
import subprocess
from datetime import datetime, date

from django.conf import settings

from api.models import (
    FC_Log,
    BOK_1_headers,
    BOK_2_lines,
    Pallet,
    API_booking_quotes,
    DME_clients,
)
from api.serializers import SimpleQuoteSerializer, SurchargeSerializer
from api.common import trace_error, common_times as dme_time_lib
from api.common.constants import AU_STATE_ABBRS
from api.fp_apis.operations.pricing import pricing as pricing_oper
from api.fp_apis.utils import (
    select_best_options,
    get_status_category_from_status,
    auto_select_pricing_4_bok,
    gen_consignment_num,
)
from api.clients.operations.index import get_suburb_state

logger = logging.getLogger(__name__)


def _extract_address(addrs):
    state, postal_code, suburb = "", "", ""

    _addrs = []
    errors = []
    for addr in addrs:
        _addr = addr.strip()
        _addrs.append(_addr)

        if len(_addr) in [3, 4] and _addr.isdigit():
            postal_code = _addr

    state, suburb = get_suburb_state(postal_code, ", ".join(_addrs))

    return errors, state, postal_code, suburb


def get_address(order_num):
    """
    Get address for JasonL

    Stop Error
    Pickup address
    Stop Error: Pickup postal code and suburb mismatch. (Hint perform a Google search for the correct match)

    Stop Error
    Pickup address
    Stop Error: Pickup postal code missing

    Stop Error
    Pickup address
    Stop Error: Pickup suburb missing or misspelled

    Stop Error
    Pickup address
    Stop Error: Pickup state missing or misspelled

    Stop Error
    Delivery address
    Stop Error: Delivery postal code and suburb mismatch. (Hint perform a Google search for the correct match)

    Stop Error
    Delivery address
    Stop Error: Delivery postal code missing

    Stop Error
    Delivery address
    Stop Error: Delivery suburb missing or misspelled

    Stop Error
    Delivery address
    Stop Error: Delivery state missing or misspelled

    Stop Error
    Delivery address
    Stop Error: Delivery address contact telephone no is a standard requirement for freight providers

    Warning
    Delivery address
    Warning: Missing email for delivery address, used to advise booking status*

    Warning
    Delivery address
    Warning: Missing mobile number for delivery address, used to text booking status**
    """
    LOG_ID = "[ADDRESS CSV READER]"

    # - Split `order_num` and `suffix` -
    _order_num, suffix = order_num, ""
    iters = _order_num.split("-")

    if len(iters) > 1:
        _order_num, suffix = iters[0], iters[1]

    message = f"@350 {LOG_ID} OrderNum: {_order_num}, Suffix: {suffix}"
    logger.info(message)
    # ---

    if settings.ENV != "local":  # Only on DEV or PROD
        logger.info(f"@351 {LOG_ID} Running .sh script...")
        subprocess.run(
            [
                "/home/ubuntu/jason_l/address/src/run.sh",
                "--context_param",
                f"param1={_order_num}",
                "--context_param",
                f"param2={suffix}",
            ]
        )
        logger.info(f"@352 {LOG_ID} Finish running .sh")

    if settings.ENV == "local":
        file_path = "/Users/juli/Desktop/del.csv"
    else:
        file_path = "/home/ubuntu/jason_l/address/src/del.csv"

    csv_file = open(file_path)
    logger.info(f"@350 {LOG_ID} File({file_path}) opened!")
    filtered_lines = []

    address = {
        "error": "",
        "phone": "",
        "email": "",
        "company_name": "",
        "street_1": "",
        "suburb": "",
        "state": "",
        "postal_code": "",
    }
    DA_phone = None
    DA_company_name = None
    DA_street_1 = None
    DA_suburb = None
    DA_state = None
    DA_postal_code = None
    errors = []
    for i, line in enumerate(csv_file):
        if i == 0:  # Ignore first header row
            continue

        line_items = line.split("|")
        type = line_items[0]
        na_type = line_items[4]
        address["phone"] = line_items[14] if line_items[14] else address["phone"]

        if type == "SO" and na_type == "DA":  # `Delivery Address` row
            logger.info(f"@351 {LOG_ID} DA: {line}")

            DA_company_name = line_items[5]
            DA_street_1 = line_items[6]
            DA_phone = line_items[14]

            try:
                errors, DA_state, DA_postal_code, DA_suburb = _extract_address(
                    line_items[7:]
                )
            except Exception as e:
                logger.info(f"@352 {LOG_ID} Error: {str(e)}")
                errors.append(
                    "Stop Error: Delivery postal code and suburb mismatch. (Hint perform a Google search for the correct match)"
                )

        if type == "CUS" and na_type == "E":
            address["email"] = line_items[5]

    address["company_name"] = DA_company_name
    address["street_1"] = DA_street_1
    address["suburb"] = DA_suburb
    address["state"] = DA_state
    address["postal_code"] = DA_postal_code
    address["phone"] = DA_phone if DA_phone else address["phone"]

    if not address["street_1"]:
        errors.append("Stop Error: Delivery street 1 missing or misspelled")

    if not address["state"]:
        errors.append("Stop Error: Delivery state missing or misspelled")

    if not address["postal_code"]:
        errors.append("Stop Error: Delivery postal code missing or misspelled")

    if not address["suburb"]:
        errors.append("Stop Error: Delivery suburb missing or misspelled")

    if not address["phone"]:
        errors.append(
            "Warning: Missing mobile number for delivery address, used to text booking status**"
        )

    if not address["email"]:
        errors.append(
            "Warning: Missing email for delivery address, used to advise booking status*"
        )

    address["error"] = "***".join(errors)
    logger.info(f"@359 {LOG_ID} {json.dumps(address, indent=2, sort_keys=True)}")
    return address


def get_picked_items(order_num, sscc):
    """
    used to build LABEL
    """
    LOG_ID = "[SSCC CSV READER]"

    # - Split `order_num` and `suffix` -
    _order_num, suffix = order_num, ""
    iters = _order_num.split("-")

    if len(iters) > 1:
        _order_num, suffix = iters[0], iters[1]

    message = f"@300 {LOG_ID} OrderNum: {_order_num}, Suffix: {suffix}"
    logger.info(message)
    # ---

    if settings.ENV != "local":  # Only on DEV or PROD
        logger.info(f"@301 {LOG_ID} Running .sh script...")
        subprocess.run(
            [
                "/home/ubuntu/jason_l/sscc/src/run.sh",
                "--context_param",
                f"param1={_order_num}",
                "--context_param",
                f"param2={suffix}",
            ]
        )
        logger.info(f"@302 {LOG_ID} Finish running .sh")

    if settings.ENV == "local":
        file_path = "/Users/juli/Desktop/sscc.csv"
    else:
        file_path = "/home/ubuntu/jason_l/sscc/src/sscc_so.csv"

    csv_file = open(file_path)
    logger.info(f"@320 {LOG_ID} File({file_path}) opened!")
    filtered_lines = []

    for i, line in enumerate(csv_file):
        line_items = line.split("|")
        order_num_csv = line_items[2].strip()
        suffix_csv = line_items[3].strip()

        if len(suffix_csv) > 0:
            order_num_csv = f"{order_num_csv}-{suffix_csv}"

        if str(order_num) == order_num_csv:
            if sscc and sscc != line_items[1].strip():
                continue

            filtered_lines.append(
                {
                    "sscc": line_items[1].strip(),
                    "timestamp": line_items[10][:19],
                    "is_repacked": True,
                    "package_type": line_items[9][:3],
                    "items": [
                        {
                            "sequence": int(float(line_items[0])),
                            "qty": int(float(line_items[4])),
                        }
                    ],
                    "dimensions": {
                        "width": float(line_items[6]),
                        "height": float(line_items[7]),
                        "length": float(line_items[5]),
                        "unit": "m",
                    },
                    "weight": {"weight": float(line_items[8]), "unit": "kg"},
                }
            )

    logger.info(f"@328 {LOG_ID} Finish reading CSV! Count: {len(filtered_lines)}")
    logger.info(f"@329 {LOG_ID} {json.dumps(filtered_lines, indent=2, sort_keys=True)}")
    return filtered_lines


def update_when_no_quote_required(old_bok_1, old_bok_2s, bok_1, bok_2s):
    """
    check if quote is required
    else update Order

    input:
        old_bok_1: Object
        old_bok_2s: Array of Object
        bok_1: Dict
        bok_2s: Array of Dict

    output:
        quote_required: Bool
    """

    if old_bok_1.b_client_warehouse_code != bok_1.get("b_client_warehouse_code"):
        return False

    if old_bok_1.b_055_b_del_address_street_1 != bok_1.get(
        "b_055_b_del_address_street_1"
    ):
        return False

    if old_bok_1.b_056_b_del_address_street_2 != bok_1.get(
        "b_056_b_del_address_street_2"
    ):
        return False

    if bok_1.get(
        "b_057_b_del_address_state"
    ) and old_bok_1.b_057_b_del_address_state != bok_1.get("b_057_b_del_address_state"):
        return False

    if bok_1.get(
        "b_058_b_del_address_suburb"
    ) and old_bok_1.b_058_b_del_address_suburb != bok_1.get(
        "b_058_b_del_address_suburb"
    ):
        return False

    if bok_1.get(
        "b_059_b_del_address_postalcode"
    ) and old_bok_1.b_059_b_del_address_postalcode != bok_1.get(
        "b_059_b_del_address_postalcode"
    ):
        return False

    if old_bok_1.b_067_assembly_required != bok_1.get("b_067_assembly_required"):
        return False

    if old_bok_1.b_068_b_del_location != bok_1.get("b_068_b_del_location"):
        return False

    if old_bok_1.b_069_b_del_floor_number != bok_1.get("b_069_b_del_floor_number"):
        return False

    if old_bok_1.b_070_b_del_floor_access_by != bok_1.get(
        "b_070_b_del_floor_access_by"
    ):
        return False

    if old_bok_1.b_071_b_del_sufficient_space != bok_1.get(
        "b_071_b_del_sufficient_space"
    ):
        return False

    for old_bok_2 in old_bok_2s:
        is_found = False

        for bok_2 in bok_2s:
            if old_bok_2.e_item_type == bok_2["model_number"]:
                is_found = True

                if old_bok_2.l_002_qty != bok_2["qty"]:
                    return False

        if not is_found:
            return False

    if old_bok_1.b_060_b_del_address_country != bok_1.get(
        "b_060_b_del_address_country"
    ):
        old_bok_1.b_060_b_del_address_country = bok_1.get("b_060_b_del_address_country")

    if old_bok_1.b_061_b_del_contact_full_name != bok_1.get(
        "b_061_b_del_contact_full_name"
    ):
        old_bok_1.b_061_b_del_contact_full_name = bok_1.get(
            "b_061_b_del_contact_full_name"
        )

    if old_bok_1.b_063_b_del_email != bok_1.get("b_063_b_del_email"):
        old_bok_1.b_063_b_del_email = bok_1.get("b_063_b_del_email")

    if old_bok_1.b_064_b_del_phone_main != bok_1.get("b_064_b_del_phone_main"):
        old_bok_1.b_064_b_del_phone_main = bok_1.get("b_064_b_del_phone_main")

    if old_bok_1.b_client_sales_inv_num != bok_1.get("b_client_sales_inv_num"):
        old_bok_1.b_client_sales_inv_num = bok_1.get("b_client_sales_inv_num")

    if old_bok_1.b_021_b_pu_avail_from_date != bok_1.get("b_021_b_pu_avail_from_date"):
        old_bok_1.b_021_b_pu_avail_from_date = bok_1.get("b_021_b_pu_avail_from_date")

    old_bok_1.save()
    return True


def do_quote(pk_header_id):
    LOG_ID = "[JASON_L QUOTE]"

    # Get Boks
    bok_1 = (
        BOK_1_headers.objects.select_related("quote")
        .filter(pk_header_id=pk_header_id)
        .first()
    )
    bok_2s = BOK_2_lines.objects.filter(
        fk_header_id=pk_header_id, is_deleted=False
    ).exclude(l_003_item__icontains="(ignored)")
    client = DME_clients.objects.get(pk=21)

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
    for _bok_2 in bok_2s:
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

        best_quote = best_quotes[0]
        bok_1_obj.b_003_b_service_name = best_quote.service_name
        bok_1_obj.b_001_b_freight_provider = best_quote.freight_provider
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
        logger.info(f"@8888 {LOG_ID} success: True, 201_created")
    else:
        message = "Pricing cannot be returned due to incorrect address information."
        logger.info(f"@8889 {LOG_ID} {message}")
