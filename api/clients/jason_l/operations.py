import os
import re
import json
import logging
import subprocess
from datetime import datetime, date

from django.conf import settings
from django.db import transaction

from api.models import (
    FC_Log,
    BOK_1_headers,
    BOK_2_lines,
    Pallet,
    API_booking_quotes,
    DME_clients,
    Client_Products,
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
from api.clients.operations.index import (
    get_suburb_state,
    get_similar_suburb,
    is_postalcode_in_state,
)
from api.clients.jason_l.constants import (
    ITEM_CODES_TO_BE_IGNORED as JASONL_ITEM_CODES_TO_BE_IGNORED,
)

logger = logging.getLogger(__name__)

# IS_TESTING = True  # Used for Testing
IS_TESTING = False


def _extract_address(addrs):
    errors = []
    state, postal_code, suburb = "", "", ""

    _addrs = []
    _state = None
    for addr in addrs:
        _addr = addr.strip()
        _addrs.append(_addr)

        if len(_addr) in [3, 4] and _addr.isdigit():
            postal_code = _addr

        if _addr.upper() in AU_STATE_ABBRS:
            _state = _addr.upper()

    state, suburb = get_suburb_state(postal_code, ", ".join(_addrs))

    if not _state:
        errors.append("Stop Error: Delivery state missing or misspelled")
    elif _state != state:
        errors.append(
            "Stop Error: Delivery state and suburb mistmatch (Hint perform a Google search for the correct match)"
        )

    return errors, _state, postal_code, suburb


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
        file_path = "/Users/juli/Documents/talend_sample_data/del.csv"
    else:
        file_path = "/home/ubuntu/jason_l/address/src/del.csv"

    csv_file = open(file_path)
    logger.info(f"@350 {LOG_ID} File({file_path}) opened!")
    filtered_lines = []

    address = {
        "error": "",
        "company_name": "",
        "street_1": "",
        "street_2": "",
        "suburb": "",
        "state": "",
        "postal_code": "",
        "phone": "",
        "email": "",
    }

    DA_company_name, CUS_company_name = None, None
    DA_street_1, CUS_street_1 = None, None
    DA_suburb, CUS_suburb = None, None
    DA_state, CUS_state = None, None
    DA_postal_code, CUS_postal_code = None, None
    DA_phone = None
    DA_email = None
    errors = []
    has_DA = False
    clue_DA = ""
    clue_CUS = ""
    for i, line in enumerate(csv_file):
        if i == 0:  # Ignore first header row
            continue

        line_items = line.split("|")
        type = line_items[0]
        na_type = line_items[4]
        address["phone"] = line_items[14] if line_items[14] else address["phone"]

        if type == "SO" and na_type == "DA":  # `Delivery Address` row
            has_DA = True
            logger.info(f"@351 {LOG_ID} DA: {line}")

            DA_company_name = line_items[5]
            DA_street_1 = line_items[6]
            DA_phone = line_items[14]

            for item in line_items:
                _item = item.strip()
                email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

                if re.match(email_regex, _item):
                    DA_email = _item
            try:
                clue_DA = line_items[7:]
                errors, DA_state, DA_postal_code, DA_suburb = _extract_address(clue_DA)
            except Exception as e:
                logger.info(f"@352 {LOG_ID} Error: {str(e)}")
                pass
        if type == "CUS" and na_type == "C":  # `Customer Contract` row
            logger.info(f"@353 {LOG_ID} CUS: {line}")

            CUS_company_name = line_items[5]
            CUS_street_1 = line_items[6]

            try:
                clue_CUS = line_items[7:]
                errors, CUS_state, CUS_postal_code, CUS_suburb = _extract_address(
                    clue_CUS
                )
            except Exception as e:
                logger.info(f"@354 {LOG_ID} Error: {str(e)}")
                pass

        if type == "CUS" and na_type == "E":
            address["email"] = line_items[5]

    if not has_DA:
        address["company_name"] = CUS_company_name or ""
        address["street_1"] = CUS_street_1 or ""
        address["suburb"] = CUS_suburb or ""
        address["state"] = CUS_state or ""
        address["postal_code"] = CUS_postal_code or ""
    else:
        clue_CUS = []
        address["company_name"] = DA_company_name or ""
        address["street_1"] = DA_street_1 or ""
        address["suburb"] = DA_suburb or ""
        address["state"] = DA_state or ""
        address["postal_code"] = DA_postal_code or ""

    address["phone"] = DA_phone or address["phone"]
    address["email"] = DA_email or address["email"]

    if not address["postal_code"]:
        errors.append("Stop Error: Delivery postal code missing or misspelled")

    if address["state"] and address["postal_code"]:
        if not is_postalcode_in_state(address["state"], address["postal_code"]):
            errors.append(
                "Stop Error: Delivery state and postal code mismatch (Hint perform a Google search for the correct match)"
            )

    if not address["suburb"] and address["postal_code"]:
        suburb = get_similar_suburb(address["postal_code"], clue_DA or clue_CUS)

        if suburb:
            address["suburb"] = suburb
            errors.append("Stop Error: Delivery suburb misspelled")
        else:
            errors.append("Stop Error: Delivery suburb missing")

    if not address["phone"]:
        errors.append(
            "Warning: Missing phone number, if SMS status is desired please submit mobile number"
        )
    else:
        _phone = address["phone"]
        _phone = _phone.replace(" ", "")
        _phone = _phone.replace("+61", "")
        _phone = _phone.replace("+", "")

        if not re.match("\d{6,10}", _phone):
            errors.append("Warning: Wrong phone number")
        elif "+61" in address["phone"] and len(_phone) != 9:
            errors.append("Warning: Wrong phone number")
        elif "+61" in address["phone"] and len(_phone) == 9 and _phone[0] != "4":
            errors.append(
                "Warning: Missing mobile number for delivery address, used to text booking status"
            )
        elif not "+61" in address["phone"] and len(_phone) not in [6, 10]:
            errors.append("Warning: Wrong phone number")
        elif (
            not "+61" in address["phone"]
            and len(_phone) == 10
            and (_phone[0] != "0" or _phone[1] != "4")
        ):
            errors.append(
                "Warning: Missing mobile number for delivery address, used to text booking status"
            )
        elif not "+61" in address["phone"] and len(_phone) == 6:
            errors.append(
                "Warning: Missing mobile number for delivery address, used to text booking status"
            )

    # Email
    if not address["email"]:
        if clue_DA or clue_CUS:
            for clue in clue_DA or clue_CUS:
                if "@" in clue:
                    address["email"] = clue.strip()
                    errors.append("Warning: Email is formatted incorrectly")
                    break

        if not address["email"]:
            errors.append(
                "Warning: Missing email for delivery address, used to advise booking status"
            )

    # Street 1
    if not address["street_1"] and (clue_DA or clue_CUS):
        for clue in clue_DA or clue_CUS:
            if (
                clue
                and clue.strip().upper() != address["company_name"].upper()
                and clue.strip().upper() != address["state"].upper()
                and clue.strip().upper() != address["suburb"].upper()
                and clue.strip().upper() != address["postal_code"].upper()
                and clue.strip().upper() != address["phone"].upper()
                and clue.strip().upper() != address["email"].upper()
            ):
                address["street_1"] = clue

    # Street 2
    if clue_DA or clue_CUS:
        street_2 = []
        for clue in clue_DA or clue_CUS:
            if (
                clue
                and clue.strip().upper() != address["company_name"].upper()
                and clue.strip().upper() != address["street_1"].upper()
                and clue.strip().upper() != address["state"].upper()
                and clue.strip().upper() != address["suburb"].upper()
                and clue.strip().upper() != address["postal_code"].upper()
                and clue.strip().upper() != address["phone"].upper()
                and clue.strip().upper() != address["email"].upper()
            ):
                street_2.append(clue.strip())

        if street_2:
            address["street_2"] = ", ".join(street_2)

    if not address["street_1"]:
        errors.append("Stop Error: Delivery street 1 missing or misspelled")

    address["error"] = "***".join(errors)
    logger.info(f"@359 {LOG_ID} {json.dumps(address, indent=2, sort_keys=True)}")
    return address


def get_bok_by_talend(order_num):
    from api.operations.pronto_xi.apis import get_product_group_code, get_token

    LOG_ID = "[FETCH BOK BY TALEND]"

    # - Split `order_num` and `suffix` -
    _order_num, suffix = order_num, ""
    iters = _order_num.split("-")

    if len(iters) > 1:
        _order_num, suffix = iters[0], iters[1]

    message = f"@380 {LOG_ID} OrderNum: {_order_num}, Suffix: {suffix}"
    logger.info(message)
    # ---

    if settings.ENV != "local":  # Only on DEV or PROD
        logger.info(f"@381 {LOG_ID} Running .sh script...")
        subprocess.run(
            [
                "/home/ubuntu/jason_l/solines/src/run.sh",
                "--context_param",
                f"param1={_order_num}",
                "--context_param",
                f"param2={suffix}",
            ]
        )
        logger.info(f"@382 {LOG_ID} Finish running .sh")

    if settings.ENV == "local":
        file_path = "/Users/juli/Documents/talend_sample_data/solines.csv"
    else:
        file_path = "/home/ubuntu/jason_l/solines/src/solines.csv"

    csv_file = open(file_path)
    logger.info(f"@383 {LOG_ID} File({file_path}) opened!")

    # Test Usage #
    if IS_TESTING:
        address = {
            "error": "Postal Code and Suburb mismatch",
            "phone": "0490001222",
            "email": "aaa@email.com",
            "street_1": "690 Ann Street",
            "street_2": "",
            "suburb": "DEE WHY",
            "state": "NSW",
            "postal_code": "2099",
        }
    else:
        # get address by using `Talend` .sh script
        address = get_address(order_num)
    ##############

    line_cnt = 0
    first_line = 0
    for line in csv_file:
        first_line = line
        line_cnt += 1

    if line_cnt < 2:
        logger.info(f"@384 {LOG_ID} No enough information!")
        return None, None

    b_021 = datetime.strptime(first_line.split("|")[3], "%d-%b-%Y").strftime("%Y-%m-%d")
    b_055 = address["street_1"]
    b_056 = address["street_2"]
    b_057 = address["state"]
    b_058 = address["suburb"]
    b_059 = address["postal_code"] or " "
    b_060 = "Australia"
    b_061 = address["company_name"]
    b_063 = address["email"]
    b_064 = address["phone"]
    b_066 = "Phone"  # Not provided
    b_067 = 0  # Not provided
    b_068 = "Drop at Door / Warehouse Dock"  # Not provided
    b_069 = 1  # Not provided
    b_070 = "Escalator"  # Not provided
    b_071 = 1  # Not provided
    warehouse_code = first_line.split("|")[8]

    order = {
        "b_client_order_num": order_num,
        "b_021_b_pu_avail_from_date": b_021,
        "b_055_b_del_address_street_1": b_055,
        "b_056_b_del_address_street_2": b_056,
        "b_057_b_del_address_state": b_057,
        "b_058_b_del_address_suburb": b_058,
        "b_059_b_del_address_postalcode": b_059,
        "b_060_b_del_address_country": b_060,
        "b_061_b_del_contact_full_name": b_061,
        "b_063_b_del_email": b_063,
        "b_064_b_del_phone_main": b_064,
        "b_066_b_del_communicate_via": b_066,
        "b_067_assembly_required": b_067,
        "b_068_b_del_location": b_068,
        "b_069_b_del_floor_number": b_069,
        "b_070_b_del_floor_access_by": b_070,
        "b_071_b_del_sufficient_space": b_071,
        "warehouse_code": warehouse_code,
        "zb_105_text_5": address["error"],
    }

    lines = []
    ignored_items = []
    token = get_token()
    csv_file = open(file_path)
    for i, line in enumerate(csv_file):
        if i == 0:  # Ignore first header row
            continue

        iters = line.split("|")
        ItemCode = iters[13]
        OrderedQty = iters[17]
        SequenceNo = iters[2]
        UOMCode = iters[15]

        if ItemCode and ItemCode.upper() in JASONL_ITEM_CODES_TO_BE_IGNORED:
            ignored_items.append(ItemCode)
            message = f"@6410 {LOG_ID} IGNORED (LISTED ITEM) --- itemCode: {ItemCode}"
            logger.info(message)
            continue

        ProductGroupCode = get_product_group_code(ItemCode, token)
        if not ProductGroupCode:
            ignored_items.append(ItemCode)
            message = f"@6410 {LOG_ID} IGNORED (MISSING ITEM) --- itemCode: {ItemCode}"
            logger.info(message)
            # continue

        line = {
            "e_item_type": ItemCode,
            "description": "",
            "qty": int(float(OrderedQty)),
            "zbl_121_integer_1": int(float(SequenceNo)),
            "e_dimUOM": "M",
            "e_weightUOM": "KG",
            "e_type_of_packaging": "UOMCode",
        }
        lines.append(line)

    if ignored_items:
        order["b_010_b_notes"] = ", ".join(ignored_items)

    lines = sucso_handler(order_num, lines)

    return order, lines


def sucso_handler(order_num, lines):
    """
    sucso talend app handler
    It will retrieve all the `lines` info of an `Order`

    Sample Data:
        so_order_no|so_bo_suffix|sol_line_seq|stock_code|stk_unit_desc|sopk_length|sopk_width|sopk_height|sopk_weight
        1034241|  |1.0|08663                         |EACH|0.37|0.69|0.61|14.000
        1034241|  |2.0|ASSEM                         |EACH|0.00|0.00|0.00|0.000
        1034241|  |2.0|ASSEM                         |EACH|0.00|0.00|0.00|0.000
        1034241|  |3.0|S068                          |EACH|0.00|0.00|0.00|0.000
        1034241|  |3.0|S068                          |EACH|0.00|0.00|0.00|0.000
    """

    LOG_ID = "[TALEND SUCSO]"

    # - Split `order_num` and `suffix` -
    _order_num, suffix = order_num, ""
    iters = _order_num.split("-")

    if len(iters) > 1:
        _order_num, suffix = iters[0], iters[1]

    message = f"@310 {LOG_ID} OrderNum: {_order_num}, Suffix: {suffix}"
    logger.info(message)
    # ---

    if settings.ENV != "local":  # Only on DEV or PROD
        logger.info(f"@311 {LOG_ID} Running .sh script...")
        subprocess.run(
            [
                "/home/ubuntu/jason_l/sucso/src/run.sh",
                "--context_param",
                f"param1={_order_num}",
                "--context_param",
                f"param2={suffix}",
            ]
        )
        logger.info(f"@312 {LOG_ID} Finish running .sh")

    if settings.ENV == "local":
        file_path = "/Users/juli/Documents/talend_sample_data/sucso.csv"
    else:
        file_path = "/home/ubuntu/jason_l/sucso/src/sucso.csv"

    csv_file = open(file_path)
    logger.info(f"@313 {LOG_ID} File({file_path}) opened!")

    new_lines = []
    for i, line in enumerate(csv_file):
        if i == 0:  # Ignore first header row
            continue

        iters = line.split("|")
        SequenceNo = int(iters[2])
        ItemCode = iters[3].strip()
        UnitCode = iters[4]
        length = float(iters[5])
        width = float(iters[6])
        height = float(iters[7])
        weight = float(iters[8])

        for line in lines:
            if line["model_number"] == ItemCode:
                line["e_dimLength"] = length
                line["e_dimWidth"] = width
                line["e_dimHeight"] = height
                line["e_weightPerEach"] = weight
                new_lines.append(line)

    logger.info(f"@319 {LOG_ID} result: {new_lines}")
    return new_lines


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
        file_path = "/Users/juli/Documents/talend_sample_data/sscc.csv"
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


def create_or_update_product(new_product):
    LOG_ID = "[JASON_L PRODUCT]"

    products = Client_Products.objects.filter(
        fk_id_dme_client_id=21, parent_model_number=new_product["e_item_type"]
    )

    with transaction.atomic():
        if products:
            logger.info("@190 - New Product!")
            product = products.first()
        else:
            logger.info("@190 - Existing Product!")
            product = Client_Products()

        product.fk_id_dme_client_id = 21
        product.parent_model_number = new_product["e_item_type"]
        product.child_model_number = new_product["e_item_type"]
        product.description = new_product["e_item"]
        product.qty = 1
        product.e_dimUOM = new_product["e_dimUOM"]
        product.e_dimLength = new_product["e_dimLength"]
        product.e_dimWidth = new_product["e_dimWidth"]
        product.e_dimHeight = new_product["e_dimHeight"]
        product.e_weightUOM = new_product["e_weightUOM"]
        product.e_weightPerEach = new_product["e_weightPerEach"]
        product.is_ignored = new_product["is_ignored"]
        product.save()

    return product
