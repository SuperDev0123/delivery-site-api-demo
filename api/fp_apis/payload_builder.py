from django.conf import settings
from api.models import *

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
    },
    "hunter": {"live": "DMEPAL"},
    "tnt": {"live": "30021385"},
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
        "live": {"accountKey": "RE1FUEFMOmRlbGl2ZXI=", "accountPassword": "deliver"}
    },
    "tnt": {"live": {"accountKey": "30021385", "accountPassword": "Deliver123"}},
}


def _get_account_details(booking, fp_name):
    if fp_name.lower() == "startrack":
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
    elif fp_name.lower() in ["hunter", "tnt"]:
        if settings.ENV in ["local", "dev"]:
            account_detail = {
                "accountCode": ACCOUTN_CODES[fp_name.lower()]["live"],
                **KEY_CHAINS[fp_name.lower()]["live"],
            }
        else:
            account_detail = {
                "accountCode": ACCOUTN_CODES[fp_name.lower()]["live"],
                **KEY_CHAINS[fp_name.lower()]["live"],
            }

    return account_detail


def _get_service_provider(fp_name):
    if fp_name.lower() == "startrack":
        return "ST"
    else:
        return fp_name.upper()


def _set_error(booking, error_msg):
    booking.b_error_Capture = str(error_msg)[:999]
    booking.save()


def get_tracking_payload(booking, fp_name):
    try:
        payload = {}
        consignmentDetails = []
        # for i in range(index * 10, (index + 1) * 10):  # Batch - 10
        consignmentDetails.append({"consignmentNumber": booking["v_FPBookingNumber"]})
        payload["consignmentDetails"] = consignmentDetails
        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = _get_service_provider(fp_name)

        return payload
    except Exception as e:
        # print(f"#400 - Error while build payload: {e}")
        return None


def get_book_payload(booking, fp_name):
    payload = {}
    payload["spAccountDetails"] = _get_account_details(booking, fp_name)
    payload["serviceProvider"] = _get_service_provider(fp_name)

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
        "instruction": ""
        if booking.pu_PickUp_Instructions_Contact is None
        else booking.pu_PickUp_Instructions_Contact,
        "phoneNumber": "0267651109"
        if booking.pu_Phone_Main is None
        else booking.pu_Phone_Main,
    }
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
        "instruction": ""
        if booking.de_to_Pick_Up_Instructions_Contact is None
        else booking.de_to_Pick_Up_Instructions_Contact,
        "phoneNumber": "0393920020"
        if booking.de_to_Phone_Main is None
        else booking.de_to_Phone_Main,
    }
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
        for i in range(line.e_qty):
            temp_item = {
                "dangerous": 0,
                "itemId": "EXP",
                "packagingType": "CTN" if fp_name.lower() == "startrack" else "PAL",
                "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                "length": 0 if line.e_dimLength is None else line.e_dimLength,
                "quantity": 0 if line.e_qty is None else line.e_qty,
                "volume": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                "weight": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                "width": 0 if line.e_dimWidth is None else line.e_dimWidth,
            }
            items.append(temp_item)

    payload["items"] = items

    # Detail for each FP
    if fp_name.lower() == "hunter":
        payload["serviceType"] = "RF"

    return payload


def get_cancel_book_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = _get_service_provider(fp_name)
        payload["consignmentNumbers"] = [booking.fk_fp_pickup_id]

        return payload
    except Exception as e:
        # print(f"#402 - Error while build payload: {e}")
        return None


def get_create_label_payload(booking, fp_name):
    try:
        payload = {}
        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = _get_service_provider(fp_name)
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
        payload["serviceProvider"] = _get_service_provider(fp_name)

        if fp_name.lower() == "startrack":
            payload["serviceProvider"] = _get_service_provider(fp_name)
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
        payload["serviceProvider"] = _get_service_provider(fp_name)
        payload["orderId"] = booking.vx_fp_order_id

        return payload
    except Exception as e:
        # print(f"#405 - Error while build payload: {e}")
        return None


def get_pod_payload(booking, fp_name):
    try:
        payload = {}
        consignmentDetails = []
        consignmentDetails.append({"consignmentNumber": booking["v_FPBookingNumber"]})
        payload["consignmentDetails"] = consignmentDetails
        payload["spAccountDetails"] = _get_account_details(booking, fp_name)
        payload["serviceProvider"] = _get_service_provider(fp_name)

        return payload
    except Exception as e:
        # print(f"#400 - Error while build payload: {e}")
        return None
