import logging
from datetime import datetime, date

from rest_framework.exceptions import ValidationError

from django.conf import settings
from api.models import *
from api.common import common_times as dme_time_lib
from api.common.common_times import TIME_DIFFERENCE
from api.fp_apis.utils import _convert_UOM, gen_consignment_num
from api.fp_apis.constants import FP_CREDENTIALS, FP_CREDENTIALS, FP_UOM
from api.helpers.line import is_pallet

logger = logging.getLogger(__name__)  # Payload Builder


def get_account_detail(booking, fp_name):
    _fp_name = fp_name.lower()
    _b_client_name = booking.b_client_name.lower()
    account_code = None
    account_detail = None

    if _fp_name not in FP_CREDENTIALS:
        booking.b_errorCapture = f"Not supported FP"
        booking.save()
        raise ValidationError(booking.b_errorCapture)

    if booking.api_booking_quote:
        account_code = booking.api_booking_quote.account_code
    elif booking.vx_account_code:
        account_code = booking.vx_account_code

    if account_code:
        for client_name in FP_CREDENTIALS[_fp_name].keys():
            for key in FP_CREDENTIALS[_fp_name][client_name].keys():
                detail = FP_CREDENTIALS[_fp_name][client_name][key]

                if detail["accountCode"] == account_code:
                    account_detail = detail

    if _fp_name in ["startrack"] and _b_client_name == "biopak":
        _warehouse_code = booking.fk_client_warehouse.client_warehouse_code

        for client_name in FP_CREDENTIALS[_fp_name].keys():
            for key in FP_CREDENTIALS[_fp_name][client_name].keys():
                if key == _warehouse_code:
                    account_detail = FP_CREDENTIALS[_fp_name][client_name][key]

    if _fp_name in ["allied"]:
        if settings.ENV != "prod":
            account_detail = FP_CREDENTIALS["allied"]["test"]["test_bed_1"]
        else:
            account_detail = FP_CREDENTIALS["allied"]["dme"]["live_0"]

    if not account_detail:
        booking.b_errorCapture = f"Couldn't find Account Detail"
        booking.save()
        raise ValidationError(booking.b_errorCapture)
    else:
        return account_detail


def get_service_provider(fp_name, upper=True):
    try:
        fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)

        if fp_name.lower() == "startrack":
            return "ST" if upper else fp.fp_company_name
        elif fp_name.lower() == "hunter":
            return "HUNTER_V2"
        else:
            return fp_name.upper() if upper else fp.fp_company_name
    except Fp_freight_providers.DoesNotExist:
        logger.error("#810 - Not supported FP!")
        return None


def _set_error(booking, error_msg):
    booking.b_error_Capture = str(error_msg)[:999]
    booking.save()


def get_pu_from(booking):
    _pu_from = booking.puPickUpAvailFrom_Date.strftime("%Y-%m-%d")
    hour = booking.pu_PickUp_Avail_Time_Hours
    minute = booking.pu_PickUp_Avail_Time_Minutes
    _pu_from += f"T{str(hour).zfill(2)}" if hour else "T00"
    _pu_from += f":{str(minute).zfill(2)}" if minute else ":00"
    _pu_from += f"+{TIME_DIFFERENCE}:00"
    return _pu_from


def get_pu_to(booking):
    _pu_to = ""
    hour = booking.pu_PickUp_By_Time_Hours
    minute = booking.pu_PickUp_By_Time_Minutes

    if hour or minute:
        _pu_to += f"{str(pu_hour).zfill(2)}" if hour else "00"
        _pu_to += f":{str(minute).zfill(2)}" if minute else ":00"
        _pu_to += f"+{TIME_DIFFERENCE}:00"
        return _pu_to


def get_de_from(booking):
    if booking.de_Deliver_From_Date:
        _de_from = booking.de_Deliver_From_Date.strftime("%Y-%m-%d")
        hour = booking.de_Deliver_From_Hours
        minute = booking.de_Deliver_From_Minutes
        _de_from += f"T{str(hour).zfill(2)}" if hour else "T00"
        _de_from += f":{str(minute).zfill(2)}" if minute else ":00"
        _de_from += f"+{TIME_DIFFERENCE}:00"
        return _de_from


def get_de_to(booking):
    _de_to = ""
    hour = booking.de_Deliver_By_Hours
    minute = booking.de_Deliver_By_Minutes

    if hour or minute:
        _de_to += f"{str(hour).zfill(2)}" if hour else "00"
        _de_to += f":{str(minute).zfill(2)}" if minute else ":00"
        _de_to += f"+{TIME_DIFFERENCE}:00"
        return _de_to


def get_tracking_payload(booking, fp_name):
    try:
        payload = {}
        consignmentDetails = []
        consignmentDetails.append(
            {
                "consignmentNumber": booking.v_FPBookingNumber,
                "de_to_address_postcode": booking.de_To_Address_PostalCode,
            }
        )
        payload["consignmentDetails"] = consignmentDetails
        payload["spAccountDetails"] = get_account_detail(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        return payload
    except Exception as e:
        logger.error(f"#400 - Error while build payload: {e}")
        return None


def get_book_payload(booking, fp_name):
    payload = {}
    payload["spAccountDetails"] = get_account_detail(booking, fp_name)
    payload["serviceProvider"] = get_service_provider(fp_name)

    payload["readyDate"] = "" or str(booking.puPickUpAvailFrom_Date)
    payload["referenceNumber"] = "" or booking.b_clientReference_RA_Numbers

    client_process = None
    if hasattr(booking, "id"):
        client_process = (
            Client_Process_Mgr.objects.select_related()
            .filter(fk_booking_id=booking.id)
            .first()
        )

    if client_process:
        puCompany = client_process.origin_puCompany
        pu_Address_Street_1 = client_process.origin_pu_Address_Street_1
        pu_Address_street_2 = client_process.origin_pu_Address_Street_2
        pu_pickup_instructions_address = (
            client_process.origin_pu_pickup_instructions_address
        )
        deToCompanyName = client_process.origin_deToCompanyName
        de_Email = client_process.origin_de_Email
        # de_Email_Group_Emails = client_process.origin_de_Email_Group_Emails
        de_To_Address_Street_1 = client_process.origin_de_To_Address_Street_1
        de_To_Address_Street_2 = client_process.origin_de_To_Address_Street_2
    else:
        puCompany = booking.puCompany
        pu_Address_Street_1 = booking.pu_Address_Street_1
        pu_Address_street_2 = booking.pu_Address_street_2
        pu_pickup_instructions_address = booking.pu_pickup_instructions_address
        deToCompanyName = booking.deToCompanyName
        de_Email = booking.de_Email
        # de_Email_Group_Emails = booking.de_Email_Group_Emails
        de_To_Address_Street_1 = booking.de_To_Address_Street_1
        de_To_Address_Street_2 = booking.de_To_Address_Street_2

    payload["serviceType"] = booking.vx_serviceName or "R"
    payload["bookedBy"] = "DME"
    payload["pickupAddress"] = {
        "companyName": puCompany or "",
        "contact": (booking.pu_Contact_F_L_Name or " ")[:19],
        "emailAddress": booking.pu_Email or "",
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": booking.pu_Phone_Main or "0283111500",
    }

    payload["pickupAddress"]["instruction"] = " "
    if pu_pickup_instructions_address:
        payload["pickupAddress"]["instruction"] = f"{pu_pickup_instructions_address}"
    if booking.pu_PickUp_Instructions_Contact:
        payload["pickupAddress"][
            "instruction"
        ] += f" {booking.pu_PickUp_Instructions_Contact}"

    payload["pickupAddress"]["postalAddress"] = {
        "address1": pu_Address_Street_1 or "",
        "address2": pu_Address_street_2 or "_",
        "country": booking.pu_Address_Country or "",
        "postCode": booking.pu_Address_PostalCode or "",
        "state": booking.pu_Address_State or "",
        "suburb": booking.pu_Address_Suburb or "",
        "sortCode": booking.pu_Address_PostalCode or "",
    }
    payload["dropAddress"] = {
        "companyName": deToCompanyName or "",
        "contact": (booking.de_to_Contact_F_LName or " ")[:19],
        "emailAddress": de_Email or "",
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": booking.de_to_Phone_Main or "",
    }

    payload["dropAddress"]["instruction"] = " "
    if booking.de_to_PickUp_Instructions_Address:
        payload["dropAddress"][
            "instruction"
        ] = f"{booking.de_to_PickUp_Instructions_Address}"
    if booking.de_to_Pick_Up_Instructions_Contact:
        payload["dropAddress"][
            "instruction"
        ] += f" {booking.de_to_Pick_Up_Instructions_Contact}"

    de_street_1 = de_To_Address_Street_1 or de_To_Address_Street_2 or ""
    de_street_2 = de_To_Address_Street_2 or ""

    if not de_street_1 and not de_street_2:
        message = f"DE street info is required. BookingId: {booking.b_bookingID_Visual}"
        logger.error(message)
        raise Exception(message)

    payload["dropAddress"]["postalAddress"] = {
        "address1": de_street_1,
        "address2": de_street_2 if de_street_1 != de_street_2 else "_",
        "country": booking.de_To_Address_Country or "",
        "postCode": booking.de_To_Address_PostalCode or "",
        "state": booking.de_To_Address_State or "",
        "suburb": booking.de_To_Address_Suburb or "",
        "sortCode": booking.de_To_Address_PostalCode or "",
    }

    booking_lines = Booking_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_deleted=False
    )

    if booking.api_booking_quote:
        packed_status = booking.api_booking_quote.packed_status
        booking_lines = booking_lines.filter(packed_status=packed_status)
    else:
        scanned_lines = booking_lines.filter(packed_status=Booking_lines.SCANNED_PACK)
        booking_lines = scanned_lines or booking_lines

    items = []
    totalWeight = 0
    maxHeight = 0
    maxWidth = 0
    maxLength = 0
    for line in booking_lines:
        width = _convert_UOM(line.e_dimWidth, line.e_dimUOM, "dim", fp_name)
        height = _convert_UOM(line.e_dimHeight, line.e_dimUOM, "dim", fp_name)
        length = _convert_UOM(line.e_dimLength, line.e_dimUOM, "dim", fp_name)
        weight = _convert_UOM(line.e_weightPerEach, line.e_weightUOM, "weight", fp_name)

        for i in range(line.e_qty):
            item = {
                "dangerous": 0,
                "width": width or 0,
                "height": height or 0,
                "length": length or 0,
                "quantity": 1,
                "volume": round(width * height * length / 1000000, 5),
                "weight": weight or 0,
                "reference": line.sscc or "",
                "description": line.e_item,
            }

            if fp_name == "startrack":
                item["itemId"] = "EXP"
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )
            elif fp_name == "auspost":
                item["itemId"] = "7E55"  # PARCEL POST + SIGNATURE
            elif fp_name == "hunter":
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )
            elif fp_name == "tnt":
                item["packagingType"] = "D"
            elif fp_name == "dhl":
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )
                fp_carrier = FP_carriers.objects.get(carrier="DHLPFM")
                consignmentNoteNumber = gen_consignment_num(
                    "dhl", booking.b_bookingID_Visual
                )

                labelCode = str(fp_carrier.label_start_value + fp_carrier.current_value)
                fp_carrier.current_value = fp_carrier.current_value + 1
                fp_carrier.save()

                # Create api_bcls
                Api_booking_confirmation_lines(
                    fk_booking_id=booking.pk_booking_id,
                    fk_booking_line_id=line.pk_lines_id,
                    api_item_id=labelCode,
                    service_provider=booking.vx_freight_provider,
                    label_code=labelCode,
                    client_item_reference=line.client_item_reference,
                ).save()
                item["packageCode"] = labelCode

            items.append(item)

            if line.e_weightPerEach:
                totalWeight += weight
            if maxHeight < height:
                maxHeight = height
            if maxWidth < width:
                maxWidth = width
            if maxLength < length:
                maxLength = length

    payload["items"] = items

    # Detail for each FP
    if fp_name == "allied":
        payload["serviceType"] = "R"
        payload["docketNumber"] = gen_consignment_num(
            "allied", booking.b_bookingID_Visual
        )
    if fp_name == "hunter":
        if booking.vx_serviceName == "Road Freight":
            payload["serviceType"] = "RF"
        elif booking.vx_serviceName == "Air Freight":
            payload["serviceType"] = "AF"
        elif booking.vx_serviceName == "Re-Delivery":
            payload["serviceType"] = "RDL"
        elif booking.vx_serviceName == "Same Day Air Freight":
            payload["serviceType"] = "SDX"

        if booking.b_client_order_num:
            payload["reference1"] = booking.b_client_order_num
        elif booking.clientRefNumbers:
            payload["reference1"] = booking.clientRefNumbers
        elif booking.b_client_sales_inv_num:
            payload["reference1"] = booking.b_client_sales_inv_num
        else:
            payload["reference1"] = "reference1"

        # V2 fields
        payload["SenderReference"] = booking.clientRefNumbers
        payload["ReceiverReference"] = booking.gap_ras
        payload["ConsignmentSenderIsResidential"] = (
            "y" if booking.pu_Address_Type == "residential" else "n"
        )
        payload["ConsignmentReceiverIsResidential"] = (
            "y" if booking.de_To_AddressType == "residential" else "n"
        )
        payload["SpecialInstructions"] = booking.b_handling_Instructions or ""

        payload["consignmentNoteNumber"] = gen_consignment_num(
            "hunter", booking.b_bookingID_Visual, booking.kf_client_id
        )
        payload["ConsignmentPickupBookingTime"] = get_pu_from(booking)
        payload["ConsignmentPickupBookingTimeTo"] = get_pu_to(booking) or ""
        payload["ConsignmentBookingDateTime"] = get_de_from(booking) or ""
        payload["ConsignmentBookingDateTimeTo"] = get_de_to(booking) or ""

        # Plum
        if booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000004":
            payload["reference2"] = gen_consignment_num(
                "hunter", booking.b_bookingID_Visual, booking.kf_client_id
            )

        payload["connoteFormat"] = "Thermal"  # For `Thermal` type printers
    elif fp_name == "tnt":  # TNT
        payload["pickupAddressCopy"] = payload["pickupAddress"]
        payload["itemCount"] = len(items)
        payload["totalWeight"] = totalWeight
        payload["maxHeight"] = int(maxHeight)
        payload["maxWidth"] = int(maxWidth)
        payload["maxLength"] = int(maxLength)
        payload["packagingCode"] = "CT"
        payload["collectionDateTime"] = get_pu_from(booking)

        if booking.pu_PickUp_By_Time_Hours:
            payload["collectionCloseTime"] = str(
                booking.pu_PickUYp_By_Time_Hours
            ).zfill(2)

            if booking.pu_PickUp_By_Time_Minutes:
                payload["collectionCloseTime"] += str(
                    booking.pu_PickUp_By_Time_Minutes
                ).zfill(2)
            else:
                payload["collectionCloseTime"] += "00"
        else:
            payload["collectionCloseTime"] = "1500"

        if booking.api_booking_quote.service_name == "Overnight 09:00":
            payload["serviceCode"] = "712"
        elif booking.api_booking_quote.service_name == "Overnight 10:00":
            payload["serviceCode"] = "EX10"
        elif booking.api_booking_quote.service_name in [
            "Overnight 12:00",
            "12:00 Express",
        ]:
            payload["serviceCode"] = "EX12"
        elif booking.api_booking_quote.service_name == "Overnight Express":
            payload["serviceCode"] = "75"
        elif booking.api_booking_quote.service_name == "Road Express":
            payload["serviceCode"] = "76"
        elif (
            booking.api_booking_quote.service_name
            == "Technology Express - Sensitive Express"
        ):
            payload["serviceCode"] = "717B"
        elif booking.api_booking_quote.service_name == "Fashion Express – Carton":
            payload["serviceCode"] = "718"
        elif booking.api_booking_quote.service_name == "Sameday Domestic":
            payload["serviceCode"] = "701"
        else:
            error_msg = f"@118 Error: TNT({booking.api_booking_quote.service_name}) - there is no service code matched."
            logger.info(error_msg)

        payload["collectionInstructions"] = " "
        if payload["pickupAddress"]["instruction"]:
            payload[
                "collectionInstructions"
            ] = f"{payload['pickupAddress']['instruction']}"
        if payload["dropAddress"]["instruction"]:
            payload[
                "collectionInstructions"
            ] += f" {payload['dropAddress']['instruction']}"

        payload["consignmentNoteNumber"] = gen_consignment_num(
            "tnt", booking.b_bookingID_Visual
        )

        if booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002":  # Jason L
            payload["customerReference"] = booking.b_client_sales_inv_num or ""
        else:
            payload["customerReference"] = booking.clientRefNumbers

        payload["isDangerousGoods"] = False
        payload["payer"] = "Receiver"
        payload["receiver_Account"] = "30021385"
    elif fp_name == "capital":  # Capital
        payload["serviceType"] = "EC"
    elif fp_name == "dhl":  # DHL
        if booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000002":
            payload["clientType"] = "aldi"
            payload["consignmentNoteNumber"] = gen_consignment_num(
                "dhl", booking.b_bookingID_Visual
            )
            payload["orderNumber"] = booking.pk_booking_id
            booking.b_client_sales_inv_num = booking.pk_booking_id
            booking.save()
            utl_state = Utl_states.objects.get(state_code=booking.pu_Address_State)

            if not utl_state.sender_code:
                error_msg = "Not supported PU state"
                _set_error(error_msg)
                raise Exception(error_msg)
        else:
            payload["clientType"] = "***"
    elif fp_name == "sendle":  # Sendle
        if payload["pickupAddress"]["instruction"] == " ":
            payload["pickupAddress"]["instruction"] = "_"

        if payload["dropAddress"]["instruction"] == " ":
            payload["dropAddress"]["instruction"] = "_"

    return payload


def get_cancel_book_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = get_account_detail(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        payload["consignmentNumbers"] = [booking.fk_fp_pickup_id]

        return payload
    except Exception as e:
        logger.error(f"#402 - Error while build payload: {e}")
        return None


def get_getlabel_payload(booking, fp_name):
    payload = {}
    payload["spAccountDetails"] = get_account_detail(booking, fp_name)
    payload["serviceProvider"] = get_service_provider(fp_name)

    client_process = None
    if hasattr(booking, "id"):
        client_process = (
            Client_Process_Mgr.objects.select_related()
            .filter(fk_booking_id=booking.id)
            .first()
        )

    if client_process:
        puCompany = client_process.origin_puCompany
        pu_Address_Street_1 = client_process.origin_pu_Address_Street_1
        pu_Address_street_2 = client_process.origin_pu_Address_Street_2
        pu_pickup_instructions_address = (
            client_process.origin_pu_pickup_instructions_address
        )
        deToCompanyName = client_process.origin_deToCompanyName
        de_Email = client_process.origin_de_Email
        # de_Email_Group_Emails = client_process.origin_de_Email_Group_Emails
        de_To_Address_Street_1 = client_process.origin_de_To_Address_Street_1
        de_To_Address_Street_2 = client_process.origin_de_To_Address_Street_2
    else:
        puCompany = booking.puCompany
        pu_Address_Street_1 = booking.pu_Address_Street_1
        pu_Address_street_2 = booking.pu_Address_street_2
        pu_pickup_instructions_address = booking.pu_pickup_instructions_address
        deToCompanyName = booking.deToCompanyName
        de_Email = booking.de_Email
        # de_Email_Group_Emails = booking.de_Email_Group_Emails
        de_To_Address_Street_1 = booking.de_To_Address_Street_1
        de_To_Address_Street_2 = booking.de_To_Address_Street_2

    payload["pickupAddress"] = {
        "companyName": puCompany or "",
        "contact": (booking.pu_Contact_F_L_Name or " ")[:19],
        "emailAddress": booking.pu_Email or "",
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": booking.pu_Phone_Main or "0267651109",
    }

    payload["pickupAddress"]["instruction"] = " "
    if pu_pickup_instructions_address:
        payload["pickupAddress"]["instruction"] = f"{pu_pickup_instructions_address}"
    if booking.pu_PickUp_Instructions_Contact:
        payload["pickupAddress"][
            "instruction"
        ] += f" {booking.pu_PickUp_Instructions_Contact}"

    payload["pickupAddress"]["postalAddress"] = {
        "address1": (pu_Address_Street_1 or "")[:29],
        "address2": pu_Address_street_2 or "",
        "country": booking.pu_Address_Country or "",
        "postCode": booking.pu_Address_PostalCode or "",
        "state": booking.pu_Address_State or "",
        "suburb": booking.pu_Address_Suburb or "",
        "sortCode": booking.pu_Address_PostalCode or "",
    }
    payload["dropAddress"] = {
        "companyName": deToCompanyName or "",
        "contact": (booking.de_to_Contact_F_LName or " ")[:19],
        "emailAddress": de_Email or "",
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": booking.de_to_Phone_Main or "",
    }

    payload["dropAddress"]["instruction"] = " "
    if booking.de_to_PickUp_Instructions_Address:
        payload["dropAddress"][
            "instruction"
        ] = f"{booking.de_to_PickUp_Instructions_Address}"
    if booking.de_to_Pick_Up_Instructions_Contact:
        payload["dropAddress"][
            "instruction"
        ] += f" {booking.de_to_Pick_Up_Instructions_Contact}"

    de_street_1 = "" or de_To_Address_Street_1 or de_To_Address_Street_2
    de_street_2 = "" or de_To_Address_Street_2

    if not de_street_1 and not de_street_2:
        message = f"DE street info is required. BookingId: {booking.b_bookingID_Visual}"
        logger.error(message)
        raise Exception(message)

    if de_street_1 == de_street_2:
        de_street_2 = ""

    payload["dropAddress"]["postalAddress"] = {
        "address1": de_street_1[:29],
        "address2": de_street_2 if de_street_1 != de_street_2 else "_",
        "country": booking.de_To_Address_Country or "",
        "postCode": booking.de_To_Address_PostalCode or "",
        "state": booking.de_To_Address_State or "",
        "suburb": booking.de_To_Address_Suburb or "",
        "sortCode": booking.de_To_Address_PostalCode or "",
    }

    booking_lines = Booking_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_deleted=False
    )

    if booking.api_booking_quote:
        packed_status = booking.api_booking_quote.packed_status
        booking_lines = booking_lines.filter(packed_status=packed_status)
    else:
        scanned_lines = booking_lines.filter(packed_status=Booking_lines.SCANNED_PACK)
        booking_lines = scanned_lines if scanned_lines else booking_linesc

    items = []
    for line in booking_lines:
        booking_lines_data = Booking_lines_data.objects.filter(
            fk_booking_lines_id=line.pk_booking_lines_id
        )

        descriptions = []
        gaps = []
        for line_data in booking_lines_data:
            if line_data.itemDescription:
                descriptions.append(line_data.itemDescription[:19])

            if line_data.gap_ra:
                gaps.append(line_data.gap_ra)

        width = _convert_UOM(line.e_dimWidth, line.e_dimUOM, "dim", fp_name.lower())
        height = _convert_UOM(line.e_dimHeight, line.e_dimUOM, "dim", fp_name.lower())
        length = _convert_UOM(line.e_dimLength, line.e_dimUOM, "dim", fp_name.lower())
        weight = _convert_UOM(
            line.e_weightPerEach, line.e_weightUOM, "weight", fp_name.lower()
        )

        for i in range(line.e_qty):
            item = {
                "dangerous": 0,
                "itemId": "EXP",
                "width": 0 or width,
                "height": 0 or height,
                "length": 0 or length,
                "quantity": 1,
                "volume": round(width * height * length / 1000000, 5),
                "weight": 0 or weight,
                "description": ", ".join(descriptions)[:20] if descriptions else "_",
                "gapRa": ", ".join(gaps)[:15],
            }

            items.append(item)

            if fp_name == "startrack":
                item["itemId"] = "EXP"
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )
            elif fp_name == "auspost":
                item["itemId"] = "7E55"  # PARCEL POST + SIGNATURE
            elif fp_name == "hunter":
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )
            elif fp_name == "tnt":
                item["packagingType"] = "D"
            elif fp_name == "dhl":
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )

    payload["items"] = items

    # Detail for each FP
    if fp_name.lower() == "tnt":
        payload["consignmentNumber"] = gen_consignment_num(
            "tnt", booking.b_bookingID_Visual
        )
        payload["serviceType"] = "76"
        payload["labelType"] = "A"
        payload["consignmentDate"] = datetime.today().strftime("%d%m%Y")
        payload["collectionInstructions"] = ""

        if payload["pickupAddress"]["instruction"]:
            payload[
                "collectionInstructions"
            ] = f"{payload['pickupAddress']['instruction']}"
        if payload["dropAddress"]["instruction"]:
            payload[
                "collectionInstructions"
            ] += f" {payload['dropAddress']['instruction']}"

        payload["clientSalesInvNum"] = (
            ""
            if booking.b_client_sales_inv_num is None
            else booking.b_client_sales_inv_num
        )
    elif fp_name.lower() == "sendle":
        payload["consignmentNumber"] = booking.fk_fp_pickup_id

        if payload["pickupAddress"]["instruction"] == " ":
            payload["pickupAddress"]["instruction"] = "_"

        if payload["dropAddress"]["instruction"] == " ":
            payload["dropAddress"]["instruction"] = "_"

    return payload


def get_create_label_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = get_account_detail(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        payload["consignmentNumber"] = booking.fk_fp_pickup_id

        confirmation_items = Api_booking_confirmation_lines.objects.filter(
            fk_booking_id=booking.pk_booking_id
        )

        items = []
        for item in confirmation_items:
            temp_item = {"itemId": item.api_item_id, "packagingType": "CTN"}
            items.append(temp_item)
        payload["items"] = items

        if fp_name == "startrack":
            layout = "A4-1pp"
        elif fp_name == "auspost":
            layout = "A4-4pp"

        if fp_name in ["startrack", "auspost"]:
            payload["type"] = "PRINT"
            payload["labelType"] = "PRINT"
            payload["pageFormat"] = [
                {
                    "branded": "_CMK0E6mwiMAAAFoYvcg7Ha9",
                    "branded": False,
                    "layout": layout,
                    "leftOffset": 0,
                    "topOffset": 0,
                    "typeOfPost": "Express Post",
                }
            ]

        return payload
    except Exception as e:
        logger.error(f"#403 - Error while build payload: {e}")
        return None


def get_create_order_payload(bookings, fp_name):
    try:
        payload = {}
        booking = bookings.first()
        payload["spAccountDetails"] = get_account_detail(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)

        if fp_name.lower() in ["startrack", "auspost"]:
            payload["paymentMethods"] = "CHARGE_TO_ACCOUNT"
            payload["referenceNumber"] = "refer1"

            consignmentNumbers = []
            for booking in bookings:
                consignmentNumbers.append(booking.fk_fp_pickup_id)
            payload["consignmentNumbers"] = consignmentNumbers

        return payload
    except Exception as e:
        logger.error(f"#404 - Error while build payload(CREATE ORDER): {e}")
        return None


def get_get_order_summary_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = get_account_detail(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        payload["orderId"] = booking.vx_fp_order_id

        return payload
    except Exception as e:
        logger.error(f"#405 - Error while build payload: {e}")
        return None


def get_get_accounts_payload(fp_name):
    try:
        payload = {}

        for client_name in FP_CREDENTIALS[fp_name].keys():
            for key in FP_CREDENTIALS[fp_name][client_name].keys():
                detail = FP_CREDENTIALS[fp_name][client_name][key]
                payload["spAccountDetails"] = detail

        payload["serviceProvider"] = get_service_provider(fp_name)

        return payload
    except Exception as e:
        logger.error(f"#405 - Error while build payload: {e}")
        return None


def get_pod_payload(booking, fp_name):
    try:
        payload = {}

        payload["spAccountDetails"] = get_account_detail(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)

        if fp_name.lower() == "hunter":
            payload["consignmentDetails"] = {"consignmentNumber": booking.jobNumber}
            payload["jobDate"] = booking.jobDate
        else:
            payload["consignmentDetails"] = {
                "consignmentNumber": booking.v_FPBookingNumber
            }

        return payload
    except Exception as e:
        logger.error(f"#400 - Error while build payload: {e}")
        return None


def get_reprint_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = get_account_detail(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        payload["consignmentNumber"] = gen_consignment_num(
            "tnt", booking.b_bookingID_Visual
        )
        payload["labelType"] = "A"
        return payload
    except Exception as e:
        logger.error(f"#400 - Error while build payload: {e}")
        return None


def get_pricing_payload(
    booking,
    fp_name,
    account_detail,
    booking_lines,
    service_code=None,
):
    payload = {}

    if hasattr(booking, "client_warehouse_code"):
        client_warehouse_code = booking.client_warehouse_code
    else:
        client_warehouse_code = booking.fk_client_warehouse.client_warehouse_code

    payload["spAccountDetails"] = account_detail
    payload["serviceProvider"] = get_service_provider(fp_name)

    # Check puPickUpAvailFrom_Date
    pu_avail_from = booking.puPickUpAvailFrom_Date

    try:
        if not pu_avail_from or pu_avail_from < date.today():
            booking.b_error_Capture = "Please note that date and time you've entered is either a non working day or after hours. This will limit your options of providers available for your collection"
            booking.save()
    except TypeError as e:  # Pricing-only
        pass

    payload["readyDate"] = "" or str(pu_avail_from)[:10]
    payload["referenceNumber"] = "" or booking.b_clientReference_RA_Numbers

    client_process = None
    if hasattr(booking, "id"):
        client_process = (
            Client_Process_Mgr.objects.select_related()
            .filter(fk_booking_id=booking.id)
            .first()
        )

    if client_process:
        puCompany = client_process.origin_puCompany
        pu_Address_Street_1 = client_process.origin_pu_Address_Street_1
        pu_Address_street_2 = client_process.origin_pu_Address_Street_2
        # pu_pickup_instructions_address = (
        #    client_process.origin_pu_pickup_instructions_address
        # )
        deToCompanyName = client_process.origin_deToCompanyName
        de_Email = client_process.origin_de_Email
        # de_Email_Group_Emails = client_process.origin_de_Email_Group_Emails
        de_To_Address_Street_1 = client_process.origin_de_To_Address_Street_1
        de_To_Address_Street_2 = client_process.origin_de_To_Address_Street_2
    else:
        puCompany = booking.puCompany
        pu_Address_Street_1 = booking.pu_Address_Street_1
        pu_Address_street_2 = booking.pu_Address_street_2
        # pu_pickup_instructions_address = booking.pu_pickup_instructions_address
        deToCompanyName = booking.deToCompanyName
        de_Email = booking.de_Email
        # de_Email_Group_Emails = booking.de_Email_Group_Emails
        de_To_Address_Street_1 = booking.de_To_Address_Street_1
        de_To_Address_Street_2 = booking.de_To_Address_Street_2

    payload["pickupAddress"] = {
        "companyName": "" or puCompany,
        "contact": ((booking.pu_Contact_F_L_Name or " ")[:19])[:19],
        "emailAddress": "" or booking.pu_Email,
        "instruction": "",
        "phoneNumber": "0267651109" or booking.pu_Phone_Main,
    }

    payload["pickupAddress"]["postalAddress"] = {
        "address1": "" or pu_Address_Street_1,
        "address2": "" or pu_Address_street_2,
        "country": "" or booking.pu_Address_Country,
        "postCode": "" or booking.pu_Address_PostalCode,
        "state": "" or booking.pu_Address_State,
        "suburb": "" or booking.pu_Address_Suburb,
        "sortCode": "" or booking.pu_Address_PostalCode,
    }
    payload["dropAddress"] = {
        "companyName": "" or deToCompanyName,
        "contact": (booking.de_to_Contact_F_LName or " ")[:19],
        "emailAddress": "" or de_Email,
        "instruction": "",
        "phoneNumber": "" or booking.de_to_Phone_Main,
    }

    payload["dropAddress"]["postalAddress"] = {
        "address1": "" or de_To_Address_Street_1,
        "address2": "" or de_To_Address_Street_2,
        "country": "" or booking.de_To_Address_Country,
        "postCode": "" or booking.de_To_Address_PostalCode,
        "state": "" or booking.de_To_Address_State,
        "suburb": "" or booking.de_To_Address_Suburb,
        "sortCode": "" or booking.de_To_Address_PostalCode,
    }

    items = []
    for line in booking_lines:
        width = _convert_UOM(line.e_dimWidth, line.e_dimUOM, "dim", fp_name)
        height = _convert_UOM(line.e_dimHeight, line.e_dimUOM, "dim", fp_name)
        length = _convert_UOM(line.e_dimLength, line.e_dimUOM, "dim", fp_name)
        weight = _convert_UOM(line.e_weightPerEach, line.e_weightUOM, "weight", fp_name)

        # Sendle size limitation: 120cm
        if fp_name == "sendle" and (width > 120 or height > 120 or length > 120):
            return None

        for i in range(line.e_qty):
            item = {
                "dangerous": 0,
                "width": 0 or width,
                "height": 0 or height,
                "length": 0 or length,
                "quantity": 1,
                "volume": round(width * height * length / 1000000, 5),
                "weight": 0 or weight,
                "description": line.e_item,
            }

            if fp_name == "startrack":
                item["itemId"] = "EXP"
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )
            elif fp_name == "auspost":
                item["itemId"] = service_code  # PARCEL POST + SIGNATURE
            elif fp_name == "hunter":
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )
            elif fp_name == "tnt":
                item["packagingType"] = "D"
            elif fp_name == "dhl":
                item["packagingType"] = (
                    "PLT" if is_pallet(line.e_type_of_packaging) else "CTN"
                )

            items.append(item)

    payload["items"] = items

    # Detail for each FP
    if fp_name == "startrack":
        payload["serviceType"] = "R"
    elif fp_name == "hunter":
        payload["serviceType"] = "RF"
    elif fp_name == "capital":
        payload["serviceType"] = "EC"
    elif fp_name == "allied":
        payload["serviceType"] = "R"

    return payload


def get_etd_payload(booking, fp_name):
    payload = {}

    if hasattr(booking, "client_warehouse_code"):
        client_warehouse_code = booking.client_warehouse_code
    else:
        client_warehouse_code = booking.fk_client_warehouse.client_warehouse_code

    payload["spAccountDetails"] = {
        "accountCode": "00956684",  # Original
        "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
        "accountPassword": "xab801a41e663b5cb889",
    }
    payload["serviceProvider"] = get_service_provider(fp_name)
    payload["readyDate"] = "" or str(booking.puPickUpAvailFrom_Date)[:10]

    client_process = None
    if hasattr(booking, "id"):
        client_process = (
            Client_Process_Mgr.objects.select_related()
            .filter(fk_booking_id=booking.id)
            .first()
        )

    if client_process:
        puCompany = client_process.origin_puCompany
        pu_Address_Street_1 = client_process.origin_pu_Address_Street_1
        pu_Address_street_2 = client_process.origin_pu_Address_Street_2
        deToCompanyName = client_process.origin_deToCompanyName
        de_Email = client_process.origin_de_Email
        de_To_Address_Street_1 = client_process.origin_de_To_Address_Street_1
        de_To_Address_Street_2 = client_process.origin_de_To_Address_Street_2
    else:
        puCompany = booking.puCompany
        pu_Address_Street_1 = booking.pu_Address_Street_1
        pu_Address_street_2 = booking.pu_Address_street_2
        deToCompanyName = booking.deToCompanyName
        de_Email = booking.de_Email
        de_To_Address_Street_1 = booking.de_To_Address_Street_1
        de_To_Address_Street_2 = booking.de_To_Address_Street_2

    payload["pickupAddress"] = {
        "companyName": "" or puCompany,
        "contact": (booking.pu_Contact_F_L_Name or " ")[:19],
        "emailAddress": "" or booking.pu_Email,
        "instruction": "",
        "phoneNumber": "0267651109" or booking.pu_Phone_Main,
    }

    payload["pickupAddress"]["postalAddress"] = {
        "address1": "" or pu_Address_Street_1,
        "address2": "" or pu_Address_street_2,
        "country": "" or booking.pu_Address_Country,
        "postCode": "" or booking.pu_Address_PostalCode,
        "state": "" or booking.pu_Address_State,
        "suburb": "" or booking.pu_Address_Suburb,
        "sortCode": "" or booking.pu_Address_PostalCode,
    }
    payload["dropAddress"] = {
        "companyName": "" or deToCompanyName,
        "contact": (booking.de_to_Contact_F_LName or " ")[:19],
        "emailAddress": "" or de_Email,
        "instruction": "",
        "phoneNumber": "" or booking.de_to_Phone_Main,
    }

    payload["dropAddress"]["postalAddress"] = {
        "address1": "" or de_To_Address_Street_1,
        "address2": "" or de_To_Address_Street_2,
        "country": "" or booking.de_To_Address_Country,
        "postCode": "" or booking.de_To_Address_PostalCode,
        "state": "" or booking.de_To_Address_State,
        "suburb": "" or booking.de_To_Address_Suburb,
        "sortCode": "" or booking.de_To_Address_PostalCode,
    }

    # Detail for each FP
    if fp_name == "startrack":
        # etd = FP_Service_ETDs.objects.get(
        #     fp_delivery_time_description="PARCEL POST + SIGNATURE"
        # )
        # payload["product_ids"] = [etd.fp_delivery_service_code]
        payload["product_ids"] = "EXP"

    return payload
