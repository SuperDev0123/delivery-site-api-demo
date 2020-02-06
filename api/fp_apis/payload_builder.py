from datetime import datetime

from django.conf import settings
from api.models import *
from api.common import ratio, common_times
from api.common import common_times

ACCOUTN_CODES = {
    "startrack": {
        "test_bed_0": "00956684",  # Original
        "test_bed_1": "00251522",  # ST Premium and ST Express
        "BIO - BON": "10145902",
        "BIO - ROC": "10145593",
        "BIO - CAV": "10145596",
        "BIO - TRU": "10149944",
        "BIO - HAZ": "10145597",
        "BIO - EAS": "10149943",
        "BIO - HTW": "10160226",
    },
    "hunter": {
        "live_0": "DELIME",
        "live_1": "DEMELP",
        "live_2": "DMEMEL",
        "live_3": "DMEBNE",
        "live_4": "DMEPAL",
        # "live_5": "DEMELK",
        # "live_6": "DMEADL",
        "live_bunnings_0": "DELIMB",
        "live_bunnings_1": "DELIMS",
    },
    "tnt": {"live_0": "30021385"},
    "capital": {"live_0": "DMENSW"},
    "sendle": {"live_0": "XXX"},
    "fastway": {"live_0": "XXX"},
    "allied": {"test_bed_1": "DELVME", "live_0": "DELVME"},
}

KEY_CHAINS = {
    "startrack": {
        "test_bed_0": {
            "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
            "accountPassword": "xab801a41e663b5cb889",
        },
        "test_bed_1": {
            "accountKey": "71eb98b2-fa8d-4a38-b1b7-6fb2a5c5c486",
            "accountPassword": "x9083d2fed4d50aa2ad5",
        },
        "live": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
    },
    "hunter": {
        "live_0": {"accountKey": "REVMSU1FOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_1": {"accountKey": "REVNRUxQOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_2": {"accountKey": "RE1FTUVMOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_3": {"accountKey": "RE1FQk5FOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_4": {"accountKey": "RE1FUEFMOmRlbGl2ZXI=", "accountPassword": "deliver"},
        # "live_5": {"accountKey": "REVNRUxLOmRlbGl2ZXI=", "accountPassword": "deliver"},
        # "live_6": {"accountKey": "RE1FQURMOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_bunnings_0": {
            "accountKey": "REVMSU1COmRlbGl2ZXIyMA==",
            "accountPassword": "deliver20",
        },
        "live_bunnings_1": {
            "accountKey": "REVMSU1TOmRlbGl2ZXIyMA==",
            "accountPassword": "deliver20",
        },
    },
    "tnt": {
        "live_0": {
            "accountKey": "30021385",
            "accountState": "DELME",
            "accountPassword": "Deliver123",
            "accountUsername": "CIT00000000000098839",
        }
    },
    "capital": {
        "live_0": {
            "accountKey": "eYte9AeLruGYmM78",
            "accountState": "NSW",
            "accountUsername": "deliverme",
        }
    },
    "sendle": {
        "live_0": {"accountKey": "FAKE_KEY_01", "accountState": "FAKE_STATE_01"}
    },
    "fastway": {
        "live_0": {
            "accountKey": "ebdb18c3ce966bc3a4e3f115d311b453",
            "accountState": "FAKE_STATE_01",
        }
    },
    "allied": {
        "test_bed_1": {
            "accountKey": "11e328f646051c3decc4b2bb4584530b",
            "accountState": "NSW",
        },
        "live_0": {
            "accountKey": "ce0d58fd22ae8619974958e65302a715",
            "accountState": "NSW",
        },
    },
}

FP_UOM = {
    "startrack": {"dim": "cm", "weight": "kg"},
    "hunter": {"dim": "cm", "weight": "kg"},
    "tnt": {"dim": "cm", "weight": "kg"},
    "capital": {"dim": "cm", "weight": "kg"},
    "sendle": {"dim": "cm", "weight": "kg"},
    "fastway": {"dim": "cm", "weight": "kg"},
    "allied": {"dim": "cm", "weight": "kg"},
}


def _get_account_details(booking, fp_name, account_code_key=None):
    account_detail = None
    default_account_code_key = "live_0" if not account_code_key else account_code_key

    if fp_name.lower() in ["startrack", "allied"]:
        if settings.ENV in ["local", "dev"]:
            account_detail = {
                "accountCode": ACCOUTN_CODES[fp_name.lower()]["test_bed_1"],
                **KEY_CHAINS[fp_name.lower()]["test_bed_1"],
            }
        else:
            account_detail = {
                "accountCode": ACCOUTN_CODES[fp_name.lower()][
                    booking.fk_client_warehouse.client_warehouse_code
                ],
                **KEY_CHAINS[fp_name.lower()]["live"],
            }
    elif fp_name.lower() in ["hunter", "tnt", "capital", "sendle", "fastway"]:
        if settings.ENV in ["local", "dev"]:
            account_detail = {
                "accountCode": ACCOUTN_CODES[fp_name.lower()][default_account_code_key],
                **KEY_CHAINS[fp_name.lower()][default_account_code_key],
            }
        else:
            account_detail = {
                "accountCode": ACCOUTN_CODES[fp_name.lower()][default_account_code_key],
                **KEY_CHAINS[fp_name.lower()][default_account_code_key],
            }

    return account_detail


def get_service_provider(fp_name):
    if fp_name.lower() == "startrack":
        return "ST"
    else:
        return fp_name.upper()


def _set_error(booking, error_msg):
    booking.b_error_Capture = str(error_msg)[:999]
    booking.save()


def _convert(value, uom, type, fp_name):
    converted_value = value * ratio.get_ratio(uom, FP_UOM[fp_name][type], type)
    return round(converted_value, 2)


def get_tracking_payload(booking, fp_name, account_code_key=None):
    try:
        payload = {}
        consignmentDetails = []
        consignmentDetails.append({"consignmentNumber": booking.v_FPBookingNumber})
        payload["consignmentDetails"] = consignmentDetails
        payload["spAccountDetails"] = _get_account_details(
            booking, fp_name, account_code_key
        )
        payload["serviceProvider"] = get_service_provider(fp_name)

        return payload
    except Exception as e:
        # print(f"#400 - Error while build payload: {e}")
        return None


def get_book_payload(booking, fp_name, account_code_key=None):
    payload = {}
    payload["spAccountDetails"] = _get_account_details(
        booking, fp_name, account_code_key
    )
    payload["serviceProvider"] = get_service_provider(fp_name)

    payload["readyDate"] = (
        ""
        if booking.puPickUpAvailFrom_Date is None
        else str(booking.puPickUpAvailFrom_Date)
    )
    payload["referenceNumber"] = (
        ""
        if booking.b_clientReference_RA_Numbers is None
        else booking.b_clientReference_RA_Numbers
    )
    payload["serviceType"] = "R" if booking.vx_serviceName is None else "R"
    payload["bookedBy"] = "Mr.CharlieBrown"
    payload["pickupAddress"] = {
        "companyName": "" if booking.puCompany is None else booking.puCompany,
        "contact": "Rosie Stokeld"
        if booking.pu_Contact_F_L_Name is None
        else booking.pu_Contact_F_L_Name,
        "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": "0267651109"
        if booking.pu_Phone_Main is None
        else booking.pu_Phone_Main,
    }

    if booking.pu_pickup_instructions_address:
        payload["pickupAddress"][
            "instruction"
        ] += f"Address: {booking.pu_pickup_instructions_address}"
    if booking.pu_PickUp_Instructions_Contact:
        payload["pickupAddress"][
            "instruction"
        ] += f" Contact: {booking.pu_PickUp_Instructions_Contact}"

    payload["pickupAddress"]["postalAddress"] = {
        "address1": ""
        if booking.pu_Address_Street_1 is None
        else booking.pu_Address_Street_1,
        "address2": ""
        if booking.pu_Address_street_2 is None
        else booking.pu_Address_street_2,
        "country": ""
        if booking.pu_Address_Country is None
        else booking.pu_Address_Country,
        "postCode": ""
        if booking.pu_Address_PostalCode is None
        else booking.pu_Address_PostalCode,
        "state": "" if booking.pu_Address_State is None else booking.pu_Address_State,
        "suburb": ""
        if booking.pu_Address_Suburb is None
        else booking.pu_Address_Suburb,
        "sortCode": ""
        if booking.pu_Address_PostalCode is None
        else booking.pu_Address_PostalCode,
    }
    payload["dropAddress"] = {
        "companyName": ""
        if booking.deToCompanyName is None
        else booking.deToCompanyName,
        "contact": "James Sam"
        if booking.de_to_Contact_F_LName is None
        else booking.de_to_Contact_F_LName,
        "emailAddress": "" if booking.de_Email is None else booking.de_Email,
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": "0393920020"
        if booking.de_to_Phone_Main is None
        else booking.de_to_Phone_Main,
    }

    if booking.de_to_PickUp_Instructions_Address:
        payload["dropAddress"][
            "instruction"
        ] += f"Address: {booking.de_to_PickUp_Instructions_Address}"
    if booking.de_to_Pick_Up_Instructions_Contact:
        payload["dropAddress"][
            "instruction"
        ] += f" Contact: {booking.de_to_Pick_Up_Instructions_Contact}"

    payload["dropAddress"]["postalAddress"] = {
        "address1": ""
        if booking.de_To_Address_Street_1 is None
        else booking.de_To_Address_Street_1,
        "address2": ""
        if booking.de_To_Address_Street_2 is None
        else booking.de_To_Address_Street_2,
        "country": ""
        if booking.de_To_Address_Country is None
        else booking.de_To_Address_Country,
        "postCode": ""
        if booking.de_To_Address_PostalCode is None
        else booking.de_To_Address_PostalCode,
        "state": ""
        if booking.de_To_Address_State is None
        else booking.de_To_Address_State,
        "suburb": ""
        if booking.de_To_Address_Suburb is None
        else booking.de_To_Address_Suburb,
        "sortCode": ""
        if booking.de_To_Address_PostalCode is None
        else booking.de_To_Address_PostalCode,
    }

    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    items = []
    totalWeight = 0
    maxHeight = 0
    maxWidth = 0
    maxLength = 0
    for line in booking_lines:
        width = _convert(line.e_dimWidth, line.e_dimUOM, "dim", fp_name.lower())
        height = _convert(line.e_dimHeight, line.e_dimUOM, "dim", fp_name.lower())
        length = _convert(line.e_dimLength, line.e_dimUOM, "dim", fp_name.lower())
        weight = _convert(
            line.e_weightPerEach, line.e_weightUOM, "weight", fp_name.lower()
        )

        for i in range(line.e_qty):
            item = {
                "dangerous": 0,
                "itemId": "EXP",
                "width": 0 if not line.e_dimWidth else width,
                "height": 0 if not line.e_dimHeight else height,
                "length": 0 if not line.e_dimLength else length,
                "quantity": 1,
                "volume": 0
                if not line.total_2_cubic_mass_factor_calc
                else line.total_2_cubic_mass_factor_calc,
                "weight": 0 if not line.e_weightPerEach else weight,
            }

            if fp_name.lower() == "startrack":
                item["packagingType"] = "CTN"
            elif fp_name.lower() == "hunter":
                item["packagingType"] = "PAL"
            elif fp_name.lower() == "tnt":
                item["packagingType"] = "D"

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
    if fp_name.lower() == "hunter":
        payload["serviceType"] = "RF"
    elif fp_name.lower() == "tnt":
        payload["pickupAddressCopy"] = payload["pickupAddress"]
        payload["itemCount"] = len(items)
        payload["totalWeight"] = totalWeight
        payload["maxHeight"] = int(maxHeight)
        payload["maxWidth"] = int(maxWidth)
        payload["maxLength"] = int(maxLength)
        payload["packagingCode"] = "CT"
        payload["collectionDateTime"] = booking.puPickUpAvailFrom_Date.strftime(
            "%Y-%m-%d"
        )

        if booking.pu_PickUp_Avail_Time_Hours:
            if booking.pu_PickUp_Avail_Time_Hours < 10:
                payload[
                    "collectionDateTime"
                ] += f"T0{booking.pu_PickUp_Avail_Time_Hours}"
            else:
                payload[
                    "collectionDateTime"
                ] += f"T{booking.pu_PickUp_Avail_Time_Hours}"
        else:
            payload["collectionDateTime"] += "T00"

        if booking.pu_PickUp_Avail_Time_Minutes:
            if booking.pu_PickUp_Avail_Time_Minutes < 10:
                payload[
                    "collectionDateTime"
                ] += f"0{booking.pu_PickUp_Avail_Time_Minutes}"
            else:
                payload[
                    "collectionDateTime"
                ] += f"{booking.pu_PickUp_Avail_Time_Minutes}"
        else:
            payload["collectionDateTime"] += ":00:00"

        payload["collectionCloseTime"] = "1700"
        payload["serviceCode"] = "76"
        payload["collectionInstructions"] = ""

        if payload["pickupAddress"]["instruction"]:
            payload[
                "collectionInstructions"
            ] = f"PU instruction: {payload['pickupAddress']['instruction']}"
        if payload["dropAddress"]["instruction"]:
            payload[
                "collectionInstructions"
            ] += f" DE instruction: {payload['dropAddress']['instruction']}"

        payload[
            "consignmentNoteNumber"
        ] = f"DME{str(booking.b_bookingID_Visual).zfill(9)}"
        payload["customerReference"] = "CS00301476"
        payload["isDangerousGoods"] = "false"
        payload["payer"] = "Receiver"
        payload["receiver_Account"] = "30021385"
    elif fp_name.lower() == "capital":
        payload["serviceType"] = "EC"

    return payload


def get_cancel_book_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        payload["consignmentNumbers"] = [booking.fk_fp_pickup_id]

        return payload
    except Exception as e:
        # print(f"#402 - Error while build payload: {e}")
        return None


def get_getlabel_payload(booking, fp_name):
    payload = {}
    payload["spAccountDetails"] = _get_account_details(booking, fp_name)
    payload["serviceProvider"] = get_service_provider(fp_name)
    payload["pickupAddress"] = {
        "companyName": "" if booking.puCompany is None else booking.puCompany,
        "contact": "Rosie Stokeld"
        if booking.pu_Contact_F_L_Name is None
        else booking.pu_Contact_F_L_Name,
        "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": "0267651109"
        if booking.pu_Phone_Main is None
        else booking.pu_Phone_Main,
    }

    if booking.pu_pickup_instructions_address:
        payload["pickupAddress"][
            "instruction"
        ] += f"Address: {booking.pu_pickup_instructions_address}"
    if booking.pu_PickUp_Instructions_Contact:
        payload["pickupAddress"][
            "instruction"
        ] += f" Contact: {booking.pu_PickUp_Instructions_Contact}"

    payload["pickupAddress"]["postalAddress"] = {
        "address1": ""
        if booking.pu_Address_Street_1 is None
        else booking.pu_Address_Street_1,
        "address2": ""
        if booking.pu_Address_street_2 is None
        else booking.pu_Address_street_2,
        "country": ""
        if booking.pu_Address_Country is None
        else booking.pu_Address_Country,
        "postCode": ""
        if booking.pu_Address_PostalCode is None
        else booking.pu_Address_PostalCode,
        "state": "" if booking.pu_Address_State is None else booking.pu_Address_State,
        "suburb": ""
        if booking.pu_Address_Suburb is None
        else booking.pu_Address_Suburb,
        "sortCode": ""
        if booking.pu_Address_PostalCode is None
        else booking.pu_Address_PostalCode,
    }
    payload["dropAddress"] = {
        "companyName": ""
        if booking.deToCompanyName is None
        else booking.deToCompanyName,
        "contact": "James Sam"
        if booking.de_to_Contact_F_LName is None
        else booking.de_to_Contact_F_LName,
        "emailAddress": "" if booking.de_Email is None else booking.de_Email,
        "instruction": "",
        "contactPhoneAreaCode": "0",
        "phoneNumber": "0393920020"
        if booking.de_to_Phone_Main is None
        else booking.de_to_Phone_Main,
    }

    if booking.de_to_PickUp_Instructions_Address:
        payload["dropAddress"][
            "instruction"
        ] += f"Address: {booking.de_to_PickUp_Instructions_Address}"
    if booking.de_to_Pick_Up_Instructions_Contact:
        payload["dropAddress"][
            "instruction"
        ] += f" Contact: {booking.de_to_Pick_Up_Instructions_Contact}"

    payload["dropAddress"]["postalAddress"] = {
        "address1": ""
        if booking.de_To_Address_Street_1 is None
        else booking.de_To_Address_Street_1,
        "address2": ""
        if booking.de_To_Address_Street_2 is None
        else booking.de_To_Address_Street_2,
        "country": ""
        if booking.de_To_Address_Country is None
        else booking.de_To_Address_Country,
        "postCode": ""
        if booking.de_To_Address_PostalCode is None
        else booking.de_To_Address_PostalCode,
        "state": ""
        if booking.de_To_Address_State is None
        else booking.de_To_Address_State,
        "suburb": ""
        if booking.de_To_Address_Suburb is None
        else booking.de_To_Address_Suburb,
        "sortCode": ""
        if booking.de_To_Address_PostalCode is None
        else booking.de_To_Address_PostalCode,
    }

    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    items = []
    for line in booking_lines:
        width = _convert(line.e_dimWidth, line.e_dimUOM, "dim", fp_name.lower())
        height = _convert(line.e_dimHeight, line.e_dimUOM, "dim", fp_name.lower())
        length = _convert(line.e_dimLength, line.e_dimUOM, "dim", fp_name.lower())
        weight = _convert(
            line.e_weightPerEach, line.e_weightUOM, "weight", fp_name.lower()
        )

        for i in range(line.e_qty):
            item = {
                "dangerous": 0,
                "itemId": "EXP",
                "width": 0 if not line.e_dimWidth else width,
                "height": 0 if not line.e_dimHeight else height,
                "length": 0 if not line.e_dimLength else length,
                "quantity": 1,
                "volume": 0
                if not line.total_2_cubic_mass_factor_calc
                else line.total_2_cubic_mass_factor_calc,
                "weight": 0 if not line.e_weightPerEach else weight,
            }
            items.append(item)

            if fp_name.lower() == "startrack":
                item["packagingType"] = "CTN"
            elif fp_name.lower() == "hunter":
                item["packagingType"] = "PAL"
            elif fp_name.lower() == "tnt":
                item["packagingType"] = "D"

    payload["items"] = items

    # Detail for each FP
    if fp_name.lower() == "tnt":
        payload["consignmentNumber"] = f"DME{str(booking.b_bookingID_Visual).zfill(9)}"
        payload["serviceType"] = "76"
        payload["labelType"] = "A"
        payload["consignmentDate"] = datetime.today().strftime("%d%m%Y")
    elif fp_name.lower() == "sendle":
        payload["consignmentNumber"] = f"{str(booking.v_FPBookingNumber)}"

    return payload


def get_create_label_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
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

        if fp_name.lower() == "startrack":
            payload["type"] = "PRINT"
            payload["labelType"] = "PRINT"
            payload["pageFormat"] = [
                {
                    "branded": "_CMK0E6mwiMAAAFoYvcg7Ha9",
                    "branded": False,
                    "layout": "A4-1pp",
                    "leftOffset": 0,
                    "topOffset": 0,
                    "typeOfPost": "Express Post",
                }
            ]

        return payload
    except Exception as e:
        # print(f"#403 - Error while build payload: {e}")
        return None


def get_create_order_payload(bookings, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = _get_account_details(bookings.first(), fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)

        if fp_name.lower() == "startrack":
            payload["serviceProvider"] = get_service_provider(fp_name)
            payload["paymentMethods"] = "CHARGE_TO_ACCOUNT"
            payload["referenceNumber"] = "refer1"

            consignmentNumbers = []
            for booking in bookings:
                consignmentNumbers.append(booking.fk_fp_pickup_id)
            payload["consignmentNumbers"] = consignmentNumbers

        return payload
    except Exception as e:
        # print(f"#404 - Error while build payload: {e}")
        return None


def get_get_order_summary_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        payload["orderId"] = booking.vx_fp_order_id

        return payload
    except Exception as e:
        # print(f"#405 - Error while build payload: {e}")
        return None


def get_pod_payload(booking, fp_name):
    try:
        payload = {}

        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)

        if fp_name.lower() == "hunter":
            # payload["consignmentDetails"] = {"consignmentNumber": 'DME000106541'}
            payload["consignmentDetails"] = {"consignmentNumber": booking.jobNumber}
            payload["jobDate"] = booking.jobDate
        else:
            payload["consignmentDetails"] = {
                "consignmentNumber": booking.v_FPBookingNumber
            }

        return payload
    except Exception as e:
        # print(f"#400 - Error while build payload: {e}")
        return None


def get_reprint_payload(booking, fp_name):
    try:
        payload = {}

        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = get_service_provider(fp_name)
        payload["consignmentNumber"] = f"DME000{booking.b_bookingID_Visual}"
        payload["labelType"] = "A"
        # payload["consignmentNumber"] = 'DME000106541'
        return payload
    except Exception as e:
        # print(f"#400 - Error while build payload: {e}")
        return None


def get_pricing_payload(booking, fp_name, account_code_key):
    payload = {}
    payload["spAccountDetails"] = _get_account_details(
        booking, fp_name, account_code_key
    )
    payload["serviceProvider"] = get_service_provider(fp_name)

    payload["readyDate"] = (
        ""
        if booking.puPickUpAvailFrom_Date is None
        else str(booking.puPickUpAvailFrom_Date)
    )
    payload["referenceNumber"] = (
        ""
        if booking.b_clientReference_RA_Numbers is None
        else booking.b_clientReference_RA_Numbers
    )
    payload["bookedBy"] = "Mr.CharlieBrown"
    payload["pickupAddress"] = {
        "companyName": "" if booking.puCompany is None else booking.puCompany,
        "contact": "Rosie Stokeld"
        if booking.pu_Contact_F_L_Name is None
        else booking.pu_Contact_F_L_Name,
        "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
        "instruction": "",
        "phoneNumber": "0267651109"
        if booking.pu_Phone_Main is None
        else booking.pu_Phone_Main,
    }

    if booking.pu_pickup_instructions_address:
        payload["pickupAddress"][
            "instruction"
        ] += f"Address: {booking.pu_pickup_instructions_address}"
    if booking.pu_PickUp_Instructions_Contact:
        payload["pickupAddress"][
            "instruction"
        ] += f" Contact: {booking.pu_PickUp_Instructions_Contact}"

    payload["pickupAddress"]["postalAddress"] = {
        "address1": ""
        if booking.pu_Address_Street_1 is None
        else booking.pu_Address_Street_1,
        "address2": ""
        if booking.pu_Address_street_2 is None
        else booking.pu_Address_street_2,
        "country": ""
        if booking.pu_Address_Country is None
        else booking.pu_Address_Country,
        "postCode": ""
        if booking.pu_Address_PostalCode is None
        else booking.pu_Address_PostalCode,
        "state": "" if booking.pu_Address_State is None else booking.pu_Address_State,
        "suburb": ""
        if booking.pu_Address_Suburb is None
        else booking.pu_Address_Suburb,
        "sortCode": ""
        if booking.pu_Address_PostalCode is None
        else booking.pu_Address_PostalCode,
    }
    payload["dropAddress"] = {
        "companyName": ""
        if booking.deToCompanyName is None
        else booking.deToCompanyName,
        "contact": "James Sam"
        if booking.de_to_Contact_F_LName is None
        else booking.de_to_Contact_F_LName,
        "emailAddress": "" if booking.de_Email is None else booking.de_Email,
        "instruction": "",
        "phoneNumber": "0393920020"
        if booking.de_to_Phone_Main is None
        else booking.de_to_Phone_Main,
    }

    if booking.de_to_PickUp_Instructions_Address:
        payload["dropAddress"][
            "instruction"
        ] += f"Address: {booking.de_to_PickUp_Instructions_Address}"
    if booking.de_to_Pick_Up_Instructions_Contact:
        payload["dropAddress"][
            "instruction"
        ] += f" Contact: {booking.de_to_Pick_Up_Instructions_Contact}"

    payload["dropAddress"]["postalAddress"] = {
        "address1": ""
        if booking.de_To_Address_Street_1 is None
        else booking.de_To_Address_Street_1,
        "address2": ""
        if booking.de_To_Address_Street_2 is None
        else booking.de_To_Address_Street_2,
        "country": ""
        if booking.de_To_Address_Country is None
        else booking.de_To_Address_Country,
        "postCode": ""
        if booking.de_To_Address_PostalCode is None
        else booking.de_To_Address_PostalCode,
        "state": ""
        if booking.de_To_Address_State is None
        else booking.de_To_Address_State,
        "suburb": ""
        if booking.de_To_Address_Suburb is None
        else booking.de_To_Address_Suburb,
        "sortCode": ""
        if booking.de_To_Address_PostalCode is None
        else booking.de_To_Address_PostalCode,
    }

    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
    items = []
    for line in booking_lines:
        width = _convert(line.e_dimWidth, line.e_dimUOM, "dim", fp_name.lower())
        height = _convert(line.e_dimHeight, line.e_dimUOM, "dim", fp_name.lower())
        length = _convert(line.e_dimLength, line.e_dimUOM, "dim", fp_name.lower())
        weight = _convert(
            line.e_weightPerEach, line.e_weightUOM, "weight", fp_name.lower()
        )

        for i in range(line.e_qty):
            item = {
                "dangerous": 0,
                "itemId": "EXP",
                "width": 0 if not line.e_dimWidth else width,
                "height": 0 if not line.e_dimHeight else height,
                "length": 0 if not line.e_dimLength else length,
                "quantity": 1,
                "volume": 0
                if not line.total_2_cubic_mass_factor_calc
                else line.total_2_cubic_mass_factor_calc,
                "weight": 0 if not line.e_weightPerEach else weight,
            }

            if fp_name.lower() == "startrack":
                item["packagingType"] = "CTN"
            elif fp_name.lower() == "hunter":
                item["packagingType"] = "PAL"
            elif fp_name.lower() == "tnt":
                item["packagingType"] = "D"

            items.append(item)

    payload["items"] = items

    # Detail for each FP
    if fp_name.lower() == "startrack":
        payload["serviceType"] = "R" if not booking.vx_serviceName else "R"
    elif fp_name.lower() == "hunter":
        payload["serviceType"] = "RF"
    elif fp_name.lower() == "capital":
        payload["serviceType"] = "EC"
    elif fp_name.lower() == "allied":
        payload["serviceType"] = "R"

    return payload
