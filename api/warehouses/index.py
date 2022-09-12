import json
import uuid
import logging
import requests
from datetime import datetime, date
from base64 import b64encode

from django.conf import settings
from django.db import models, transaction
from rest_framework.exceptions import ValidationError

from api.models import (
    Bookings,
    Booking_lines,
    Booking_lines_data,
    BOK_1_headers,
    BOK_2_lines,
    Log,
    FC_Log,
    FPRouting,
)
from api.fp_apis.utils import (
    select_best_options,
    auto_select_pricing_4_bok,
    gen_consignment_num,
)
from api.fp_apis.operations.pricing import pricing as pricing_oper
from api.operations.email_senders import send_email_to_admins
from api.operations.labels.index import build_label as build_label_oper
from api.operations.manifests.index import build_manifest as build_manifest_oper
from api.operations.labels.index import get_barcode
from api.common.booking_quote import set_booking_quote
from api.common.thread import background
from api.common import (
    common_times as dme_time_lib,
    constants as dme_constants,
    status_history,
    trace_error,
)
from api.convertors import pdf
from api.warehouses.libs import build_push_payload
from api.warehouses.constants import (
    SPOJIT_API_URL,
    SPOJIT_TOKEN,
    SPOJIT_WAREHOUSE_MAPPINGS,
    CARRIER_MAPPING,
)

logger = logging.getLogger(__name__)


def push(bok_1):
    LOG_ID = "[PUSH TO WHSE]"

    try:
        headers = {"content-type": "application/json", "Authorization": SPOJIT_TOKEN}
        url = f"{SPOJIT_API_URL}/webhook/{SPOJIT_WAREHOUSE_MAPPINGS[bok_1.b_client_warehouse_code]}"
        bok_2s = BOK_2_lines.objects.filter(
            fk_header_id=bok_1.pk_header_id, b_093_packed_status=BOK_2_lines.ORIGINAL
        )
        log = Log(fk_booking_id=bok_1.pk_header_id, request_type="WHSE_PUSH")
        log.save()

        try:
            logger.info(f"@9000 {LOG_ID} url - {url}")
            payload = build_push_payload(bok_1, bok_2s)
            logger.info(f"@9000 {LOG_ID} payload - {payload}")
        except Exception as e:
            error = f"@901 {LOG_ID} error on payload builder.\n\nError: {str(e)}\nBok_1: {str(bok_1.pk)}\nOrder Number: {bok_1.b_client_order_num}"
            logger.error(error)
            raise Exception(error)

        response = requests.post(url, headers=headers, json=payload)
        res_content = response.content.decode("utf8").replace("'", '"')
        json_data = json.loads(res_content)
        s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
        logger.info(f"### Response: {s0}")
    except Exception as e:
        if bok_1.b_client_order_num:
            to_emails = [settings.ADMIN_EMAIL_02]
            subject = "Error on Whse workflow"

            if settings.ENV == "prod":
                to_emails.append(settings.SUPPORT_CENTER_EMAIL)

            send_email(
                send_to=to_emails,
                send_cc=[],
                send_bcc=["goldj@deliver-me.com.au"],
                subject=subject,
                text=str(e),
            )
            logger.error(f"@905 {LOG_ID} Sent email notification!")

        return None


def push_webhook(data):
    LOG_ID = "[WHSE PUSH WEBHOOK]"
    logger.info(f"{LOG_ID} Webhook data: {data}")

    if data["code"] == "success":
        bok_1_pk = data.get("bookingId")
        order_num = data.get("orderNumber")

        if not bok_1_pk or not order_num:
            message = f"{LOG_ID} Webhook data is invalid. Data: {data}"
            logger.error(message)
            send_email_to_admins("Invalid webhook data", message)

        try:
            bok_1 = BOK_1_headers.objects.get(pk=bok_1_pk, b_client_order_num=order_num)
            bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)

            for bok_2 in bok_2s:
                bok_2.success = dme_constants.BOK_SUCCESS_4
                bok_2.save()

            bok_1.success = dme_constants.BOK_SUCCESS_4
            bok_1.save()
            logger.info(
                f"{LOG_ID} Bok_1 will be mapped. Detail: {bok_1_pk}(pk_auto_id), {order_num}(order number)"
            )
        except:
            message = f"{LOG_ID} BOK_1 does not exist. Data: {data}"
            logger.error(message)
            send_email_to_admins("No BOK_1", message)

    return None


@background
def get_quote(booking):
    LOG_ID = "[ASYNC RE-QUOTE]"
    new_fc_log = FC_Log.objects.create(
        client_booking_id=booking.b_client_booking_ref_num,
        old_quote=booking.api_booking_quote,
    )
    new_fc_log.save()
    logger.info(f"#371 {LOG_ID} {booking.b_bookingID_Visual} - Getting Quotes again...")
    _, success, message, quotes = pricing_oper(
        body=None,
        booking_id=booking.pk,
        is_pricing_only=False,
        packed_statuses=[Booking_lines.SCANNED_PACK],
    )
    logger.info(
        f"#372 {LOG_ID} - Pricing result: success: {success}, message: {message}, results cnt: {quotes.count()}"
    )

    # Select best quotes(fastest, lowest)
    if quotes.exists() and quotes.count() > 0:
        quotes = quotes.filter(packed_status=Booking_lines.SCANNED_PACK)

        if booking.booking_type == "DMEM":
            if booking.vx_freight_provider:
                quotes = quotes.filter(
                    freight_provider__iexact=booking.vx_freight_provider
                )
            if booking.vx_serviceName:
                quotes = quotes.filter(service_name=booking.vx_serviceName)

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

    # Build label with Line
    if not booking.api_booking_quote:
        logger.error(
            f"{LOG_ID} {booking.b_bookingID_Visual} Booking doens`t have quote."
        )
        raise Exception("Booking doens't have quote.")

    if not booking.vx_freight_provider and booking.api_booking_quote:
        _booking = set_booking_quote(booking, booking.api_booking_quote)


def scanned(payload):
    """
    called as get_label

    request when item(s) is picked(scanned) at warehouse
    should response LABEL if payload is correct
    """
    LOG_ID = "[SCANNED at WHSE]"
    client_name = payload.get("clientName")
    b_client_order_num = payload.get("orderNumber")
    picked_items = payload.get("items")

    # Check required params are included
    if not client_name:
        message = "'clientName' is required."
        raise ValidationError(message)

    if not b_client_order_num:
        message = "'orderNumber' is required."
        raise ValidationError(message)

    if not picked_items:
        message = "'items' is required."
        raise ValidationError(message)

    # Check if Order exists on Bookings table
    bookings = Bookings.objects.select_related("api_booking_quote").filter(
        b_client_name=client_name, b_client_order_num=b_client_order_num
    )

    if bookings.count() == 0:
        message = "Order does not exist. 'orderNumber' is invalid."
        raise ValidationError(message)

    # If Order exists
    booking = bookings.first()
    pk_booking_id = booking.pk_booking_id
    lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
    line_datas = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)
    original_items = lines.filter(
        sscc__isnull=True, packed_status=Booking_lines.ORIGINAL
    )
    scanned_items = lines.filter(sscc__isnull=False, e_item="Picked Item")
    sscc_list = scanned_items.values_list("sscc", flat=True)

    logger.info(f"@360 {LOG_ID} Booking: {booking}")
    logger.info(f"@361 {LOG_ID} Lines: {lines}")
    logger.info(f"@362 {LOG_ID} original_items: {original_items}")
    logger.info(f"@363 {LOG_ID} scanned_items: {scanned_items}")
    logger.info(f"@365 {LOG_ID} sscc(s): {sscc_list}")

    # Delete existing ssccs(for scanned ones)
    picked_ssccs = []
    for picked_item in picked_items:
        picked_ssccs.append(picked_item["sscc"])
    if picked_ssccs:
        Booking_lines.objects.filter(sscc__in=picked_ssccs).delete()

    # Save
    try:
        labels = []
        sscc_list = []
        sscc_lines = {}

        with transaction.atomic():
            for picked_item in picked_items:
                # Create new Lines
                new_line = Booking_lines()
                new_line.fk_booking_id = pk_booking_id
                new_line.pk_booking_lines_id = str(uuid.uuid4())
                new_line.e_type_of_packaging = picked_item.get("packageType") or "CTN"
                new_line.e_qty = 1
                new_line.e_item = "Picked Item"
                new_line.packed_status = Booking_lines.SCANNED_PACK
                new_line.e_dimUOM = picked_item["dimUOM"]
                new_line.e_dimLength = picked_item["length"]
                new_line.e_dimWidth = picked_item["width"]
                new_line.e_dimHeight = picked_item["height"]
                new_line.e_weightUOM = picked_item["weightUOM"]
                new_line.e_weightPerEach = picked_item["weight"]
                new_line.e_Total_KG_weight = picked_item["weight"]
                new_line.sscc = picked_item.get("sscc")
                new_line.picked_up_timestamp = (
                    picked_item.get("timestamp") or datetime.now()
                )
                new_line.save()

                if picked_item["sscc"] not in sscc_list:
                    sscc_list.append(picked_item["sscc"])
                    sscc_lines[picked_item["sscc"]] = [new_line]
                else:
                    sscc_lines[picked_item["sscc"]].append(new_line)

                # for item in picked_item["items"]:
                #     # Create new Line_Data
                #     line_data = Booking_lines_data()
                #     line_data.fk_booking_id = pk_booking_id
                #     line_data.fk_booking_lines_id = new_line.pk_booking_lines_id
                #     line_data.modelNumber = item["model_number"]
                #     line_data.itemDescription = "Picked at warehouse"
                #     line_data.quantity = item.get("qty")
                #     line_data.clientRefNumber = picked_item["sscc"]
                #     line_data.save()

        next_biz_day = dme_time_lib.next_business_day(date.today(), 1)
        booking.puPickUpAvailFrom_Date = next_biz_day
        booking.save()

        # Get quote in background
        get_quote(booking)

        # Build built-in label with SSCC - one sscc should have one page label
        label_urls = []

        for index, sscc in enumerate(sscc_list):
            file_path = f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au"

            logger.info(
                f"@368 - building label with SSCC...\n sscc_lines: {sscc_lines}"
            )
            file_path, file_name = build_label_oper(
                booking=booking,
                file_path=file_path,
                lines=sscc_lines[sscc],
                label_index=index,
                sscc=sscc,
                sscc_cnt=len(sscc_list),
                one_page_label=False,
            )

            # Convert label into ZPL format
            logger.info(
                f"@369 {LOG_ID} converting LABEL({file_path}/{file_name}) into ZPL format..."
            )
            label_url = f"{file_path}/{file_name}"
            label_urls.append(label_url)

            # # Plum ZPL printer requries portrait label
            # if booking.vx_freight_provider.lower() in ["hunter", "tnt"]:
            #     label_url = pdf.rotate_pdf(label_url)

            # result = pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

            # if not result:
            #     message = (
            #         "Please contact DME support center. <bookings@deliver-me.com.au>"
            #     )
            #     raise Exception(message)

            # with open(label_url[:-4] + ".zpl", "rb") as zpl:
            #     zpl_data = str(b64encode(zpl.read()))[2:-1]

            labels.append(
                {
                    "sscc": sscc,
                    "label": str(pdf.pdf_to_base64(label_url))[2:-1],
                    "barcode": get_barcode(
                        booking, [new_line], index + 1, len(sscc_list)
                    ),
                }
            )

        if label_urls:
            entire_label_url = f"{file_path}/DME{booking.b_bookingID_Visual}.pdf"
            pdf.pdf_merge(label_urls, entire_label_url)
            booking.z_label_url = f"{booking.vx_freight_provider.lower()}_au/DME{booking.b_bookingID_Visual}.pdf"
            # Set consignment number
            booking.v_FPBookingNumber = gen_consignment_num(
                booking.vx_freight_provider,
                booking.b_bookingID_Visual,
                booking.kf_client_id,
                booking,
            )
            booking.save()
            entire_label_b64 = str(pdf.pdf_to_base64(entire_label_url))[2:-1]

        logger.info(
            f"#379 {LOG_ID} - Successfully scanned. Booking Id: {booking.b_bookingID_Visual}"
        )

        if not booking.b_dateBookedDate and booking.b_status != "Picked":
            status_history.create(booking, "Picked", client_name)

        return {
            "success": True,
            "message": "Successfully updated picked info.",
            "consignmentNumber": gen_consignment_num(
                booking.vx_freight_provider,
                booking.b_bookingID_Visual,
                booking.kf_client_id,
            ),
            "labels": labels,
            "label": entire_label_b64,
            "freightProvider": CARRIER_MAPPING[booking.vx_freight_provider],
        }
    except Exception as e:
        trace_error.print()
        error_msg = f"@370 {LOG_ID} Exception: {str(e)}"
        logger.error(error_msg)
        send_email_to_admins(f"{LOG_ID}", f"{error_msg}")
        raise Exception(
            "Please contact DME support center. <bookings@deliver-me.com.au>"
        )


def reprint_label(params):
    """
    get label(already built)
    """
    LOG_ID = "[REPRINT from WHSE]"
    client_name = params.get("clientName")
    b_client_order_num = params.get("orderNumber")
    sscc = params.get("sscc")

    if not b_client_order_num:
        message = "'orderNumber' is required."
        raise ValidationError(message)

    booking = (
        Bookings.objects.select_related("api_booking_quote")
        .filter(b_client_order_num=b_client_order_num, b_client_name=client_name)
        .first()
    )

    if not booking:
        message = "Order does not exist. 'orderNumber' is invalid."
        raise ValidationError(message)

    fp_name = booking.api_booking_quote.freight_provider.lower()

    if sscc:
        is_exist = False
        sscc_line = None
        lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

        for line in lines:
            if line.sscc == sscc:
                is_exist = True
                sscc_line = line

        if not is_exist:
            message = "SSCC is not found."
            raise ValidationError(message)

    if not sscc and not booking.z_label_url:
        message = "Label is not ready."
        raise ValidationError(message)

    if sscc:  # Line label
        filename = f"{booking.pu_Address_State}_{str(booking.b_bookingID_Visual)}_{str(sscc_line.sscc)}.pdf"
        label_url = f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au/{filename}"
    else:  # Order Label
        if not "http" in booking.z_label_url:
            label_url = f"{settings.STATIC_PUBLIC}/pdfs/{booking.z_label_url}"
        else:
            label_url = f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au/DME{booking.b_bookingID_Visual}.pdf"

    # Plum ZPL printer requries portrait label
    if booking.vx_freight_provider.lower() == "allied":
        label_url = pdf.rotate_pdf(label_url)

    # Convert label into ZPL format
    logger.info(f"@369 - converting LABEL({label_url}) into ZPL format...")
    result = pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

    if not result:
        message = "Please contact DME support center. <bookings@deliver-me.com.au>"
        raise Exception(message)

    with open(label_url[:-4] + ".zpl", "rb") as zpl:
        zpl_data = str(b64encode(zpl.read()))[2:-1]

    return {
        "success": True,
        "message": "Successfully reprint label.",
        "label": zpl_data,
    }


def ready(payload):
    """
    When it is ready(picked all items) on Warehouse
    """
    LOG_ID = "[READY at WHSE]"
    client_name = payload.get("clientName")
    b_client_order_num = payload.get("orderNumber")

    # Check required params are included
    if not client_name:
        message = "'clientName' is required."
        raise ValidationError(message)

    if not b_client_order_num:
        message = "'orderNumber' is required."
        raise ValidationError(message)

    # Check if Order exists
    booking = (
        Bookings.objects.select_related("api_booking_quote")
        .filter(b_client_name=client_name, b_client_order_num=b_client_order_num)
        .first()
    )

    if not booking:
        message = "Order does not exist. orderNumber' is invalid."
        raise ValidationError(message)

    # Check if already ready
    if booking.b_status not in ["Picking", "Ready for Booking"]:
        message = "Order was already Ready."
        logger.info(f"@342 {LOG_ID} {message}")
        return {"success": True, "message": message}

    # Update DB so that Booking can be BOOKED
    if booking.api_booking_quote:
        status_history.create(booking, "Ready for Booking", "WHSE Module")
    else:
        status_history.create(booking, "Ready for Booking", "WHSE Module")
        send_email_to_admins(
            f"URGENT! Quote issue on Booking(#{booking.b_bookingID_Visual})",
            f"Original FP was {booking.vx_freight_provider}({booking.vx_serviceName})."
            + f" After labels were made {booking.vx_freight_provider}({booking.vx_serviceName}) was not an option for shipment."
            + f" Please do FC manually again on DME portal.",
        )

    return {"success": True, "message": "Order will be BOOKED soon."}


def manifest(payload):
    LOG_ID = "[MANIFEST WHSE]"
    client_name = payload.get("clientName")
    order_nums = payload.get("orderNumbers")

    # Required fields
    if not order_nums:
        message = "'orderNumbers' is required."
        raise ValidationError(message)

    bookings = Bookings.objects.filter(
        b_client_name=client_name, b_client_order_num__in=order_nums
    ).only("id", "b_client_order_num")

    booking_ids = []
    filtered_order_nums = []
    for booking in bookings:
        booking_ids.append(booking.id)
        filtered_order_nums.append(booking.b_client_order_num)

    missing_order_nums = list(set(order_nums) - set(filtered_order_nums))

    if missing_order_nums:
        _missing_order_nums = ", ".join(missing_order_nums)
        raise ValidationError(f"Missing Order numbers: {_missing_order_nums}")

    bookings, manifest_url = build_manifest_oper(booking_ids, "WHSE Module")
    manifest_full_url = f"{settings.STATIC_PUBLIC}/pdfs/startrack_au/{manifest_url}"

    with open(manifest_full_url, "rb") as manifest:
        manifest_data = str(b64encode(manifest.read()))

    Bookings.objects.filter(
        b_client_name=client_name, b_client_order_num__in=order_nums
    ).update(z_manifest_url=manifest_url)

    return {
        "success": True,
        "message": "Successfully manifested.",
        "manifest": manifest_data,
    }
