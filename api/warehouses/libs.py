import logging

from api.models import BOK_1_headers, BOK_2_lines, Log, FPRouting, DME_clients
from api.operations.email_senders import send_email_to_admins

logger = logging.getLogger(__name__)


def check_port_code(bok_1):
    logger.info("Checking port_code...")
    de_suburb = bok_1.b_032_b_pu_address_suburb
    de_postcode = bok_1.b_033_b_pu_address_postalcode
    de_state = bok_1.b_031_b_pu_address_state

    # head_port and port_code
    fp_routings = FPRouting.objects.filter(
        freight_provider=13,
        dest_suburb__iexact=de_suburb,
        dest_postcode=de_postcode,
        dest_state__iexact=de_state,
    )
    head_port = fp_routings[0].gateway if fp_routings and fp_routings[0].gateway else ""
    port_code = fp_routings[0].onfwd if fp_routings and fp_routings[0].onfwd else ""

    if not head_port or not port_code:
        message = f"No port_code.\n\n"
        message += f"Order Num: {bok_1.b_client_order_num}\n"
        message += f"State: {de_state}\nPostal Code: {de_postcode}\nSuburb: {de_suburb}"
        logger.error(f"[PAPERLESS] {message}")
        send_email_to_admins("Failed to send order to ACR due to port_code", message)
        raise Exception(message)

    logger.info("[PAPERLESS] `port_code` is fine")


def get_address(bok_1):
    # Validations
    message = None

    if not bok_1.b_061_b_del_contact_full_name:
        message = "{bok_1.b_client_order_num} issue: 'b_061_b_del_contact_full_name' is missing"

    if not bok_1.b_055_b_del_address_street_1:
        message = "{bok_1.b_client_order_num} issue: 'b_055_b_del_address_street_1' is missing"

    if not bok_1.b_058_b_del_address_suburb:
        message = (
            "{bok_1.b_client_order_num} issue: 'b_058_b_del_address_suburb' is missing"
        )

    if not bok_1.b_057_b_del_address_state:
        message = (
            "{bok_1.b_client_order_num} issue: 'b_057_b_del_address_state' is missing"
        )

    if not bok_1.b_059_b_del_address_postalcode:
        message = "{bok_1.b_client_order_num} issue: 'b_059_b_del_address_postalcode' is missing"

    if message:
        raise Exception(message)

    return {
        "companyName": bok_1.b_054_b_del_company,
        "address1": bok_1.b_055_b_del_address_street_1,
        "address2": bok_1.b_056_b_del_address_street_2,
        "country": bok_1.b_060_b_del_address_country,
        "postalCode": bok_1.b_059_b_del_address_postalcode,
        "state": bok_1.b_057_b_del_address_state,
        "suburb": bok_1.b_058_b_del_address_suburb,
    }


def get_lines(bok_2s):
    _lines = []

    for bok_2 in bok_2s:
        _lines.append(
            {
                "lineID": bok_2.pk_lines_id,
                "width": bok_2.l_006_dim_width,
                "height": bok_2.l_007_dim_height,
                "length": bok_2.l_005_dim_length,
                "quantity": bok_2.l_002_qty,
                "volumn": bok_2.pk_lines_id,
                "weight": bok_2.l_009_weight_per_each,
                # "reference": bok_2.sscc,
                "dangerous": False,
                "productCode": bok_2.l_003_item,
            }
        )

    return _lines


def build_push_payload(bok_1, bok_2s):
    customerName = DME_clients.objects.get(
        dme_account_num=bok_1.fk_client_id
    ).company_name
    deliveryInstructions = f"{bok_1.b_043_b_del_instructions_contact or ''} {bok_1.b_044_b_del_instructions_address or ''}"

    return {
        "bookingID": bok_1.pk,
        "orderNumber": bok_1.b_client_order_num,
        "warehouseName": "",  # TODO
        "freightProvider": "",
        "customerName": customerName,
        "address": get_address(bok_1),
        "deliveryInstructions": deliveryInstructions,
        "specialInstructions": bok_1.b_016_b_pu_instructions_address or "",
        "phoneNumber": bok_1.b_064_b_del_phone_main,
        "emailAddress": bok_1.b_063_b_del_email,
        "bookingLines": get_lines(bok_2s),
        "customerCode": bok_1.b_500_b_client_cust_job_code or "",
    }
