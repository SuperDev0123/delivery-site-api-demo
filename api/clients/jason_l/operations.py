import os
import json
import logging
import subprocess

from django.conf import settings

logger = logging.getLogger(__name__)


def get_picked_items(order_num, sscc):
    """
    used to build LABEL
    """
    LOG_ID = "[SSCC CSV READER]"
    logger.info(f"@300 {LOG_ID} Order: {order_num}")

    if settings.ENV != "local":  # Only on DEV or PROD
        logger.info(f"@301 {LOG_ID} Running .sh script...")
        cmd_dir = "/home/ubuntu/jason_l/JasonU01_part/src"
        cmd_file = os.path.join(cmd_dir, "run.sh")
        subprocess.call([cmd_file], cwd=cmd_dir)
        logger.info(f"@302 {LOG_ID} Finish running .sh")

    if settings.ENV == "local":
        file_path = "/Users/juli/Desktop/sscc.csv"
    else:
        file_path = "/home/ubuntu/jason_l/JasonU01_part/src/sscc_partial.csv"

    csv_file = open(file_path)
    logger.info(f"@320 {LOG_ID} File({file_path}) opened!")
    filtered_lines = []

    for i, line in enumerate(csv_file):
        order_num_csv = line.split("|")[2].strip()
        suffix_csv = line.split("|")[3].strip()

        if len(suffix_csv) > 0:
            order_num_csv = f"{order_num_csv}-{suffix_csv}"

        if str(order_num) == order_num_csv:
            if sscc and sscc != line.split("|")[1].strip():
                continue

            filtered_lines.append(
                {
                    "sscc": line.split("|")[1].strip(),
                    "timestamp": line.split("|")[10][:19],
                    "is_repacked": True,
                    "package_type": line.split("|")[9][:3],
                    "items": [
                        {
                            "sequence": int(float(line.split("|")[0])),
                            "qty": int(float(line.split("|")[4])),
                        }
                    ],
                    "dimensions": {
                        "width": float(line.split("|")[6]),
                        "height": float(line.split("|")[7]),
                        "length": float(line.split("|")[5]),
                        "unit": "m",
                    },
                    "weight": {"weight": float(line.split("|")[8]), "unit": "kg"},
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
