from datetime import datetime


def _set_error(booking, error_msg):
    booking.b_error_Capture = str(error_msg)[:999]
    booking.z_ModifiedTimestamp = datetime.now()
    booking.save()


def pre_check_book(booking):
    _fp_name = booking.vx_freight_provider.lower()
    _b_client_name = booking.b_client_name.lower()
    error_msg = None

    if booking.b_status.lower() == "booked":
        error_msg = "Booking is already booked."

    if booking.pu_Address_State is None or not booking.pu_Address_State:
        error_msg = "State for pickup postal address is required."
        _set_error(booking, error_msg)

    if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
        error_msg = "Suburb name for pickup postal address is required."
        _set_error(booking, error_msg)

    if _fp_name == "hunter" and not booking.puPickUpAvailFrom_Date:
        error_msg = "PU Available From Date is required."
        _set_error(booking, error_msg)

    if _b_client_name == "biopak" and not booking.b_clientReference_RA_Numbers:
        error_msg = "'FFL-' number is missing."
        _set_error(booking, error_msg)
    
    if _b_client_name == "allied":
        error_msg = pre_check_allied(booking)
    if _b_client_name == "tnt":
        error_msg = pre_check_tnt(booking)
    if _b_client_name == "hunter":
        error_msg = pre_check_hunter(booking)
    if _b_client_name == "startrack":
        error_msg = pre_check_startrack(booking)
    if _b_client_name == "sendle":
        error_msg = pre_check_sendle(booking)
        
    return error_msg

def pre_check_allied(booking):
    error_msg = None
    if len(booking.puCompany) > 40 :
        error_msg = "Pick Up Entity should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Contact_F_L_Name) > 20 :
        error_msg = "Pick Up Contact should be less than 20 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_1) > 30 :
        error_msg = "Pick Up Street 1 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_2) > 30 :
        error_msg = "Pick Up Street 2 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.deToCompanyName) > 40 :
        error_msg = "Delivery Entity should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.de_Contact) > 20 :
        error_msg = "Delivery Contact should be less than 20 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_1) > 30 :
        error_msg = "Delivery Street 1 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_2) > 30 :
        error_msg = "Delivery Street 2 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.de_to_Phone_Main) > 13 :
        error_msg = "Delivery Phone Number should be less than 13 chars."
        _set_error(booking, error_msg)
    return error_msg

def pre_check_tnt(booking):
    error_msg = None
    if len(booking.puCompany) > 30 :
        error_msg = "Pick Up Entity should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Contact_F_L_Name) > 20 :
        error_msg = "Pick Up Contact should be less than 20 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_1) > 30 :
        error_msg = "Pick Up Street 1 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_2) > 30 :
        error_msg = "Pick Up Street 2 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.deToCompanyName) > 30 :
        error_msg = "Delivery Entity should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.de_Contact) > 20 :
        error_msg = "Delivery Contact should be less than 20 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_1) > 30 :
        error_msg = "Delivery Street 1 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_2) > 30 :
        error_msg = "Delivery Street 2 should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.de_to_Phone_Main) > 13 :
        error_msg = "Delivery Phone Number should be less than 13 chars."
        _set_error(booking, error_msg)
    return error_msg

def pre_check_hunter(booking):
    error_msg = None
    if len(booking.puCompany) > 100 :
        error_msg = "Pick Up Entity should be less than 100 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_1) > 100 :
        error_msg = "Pick Up Street 1 should be less than 100 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_2) > 100 :
        error_msg = "Pick Up Street 2 should be less than 100 chars."
        _set_error(booking, error_msg)
    if len(booking.deToCompanyName) > 100 :
        error_msg = "Delivery Entity should be less than 100 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_1) > 100 :
        error_msg = "Delivery Street 1 should be less than 100 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_2) > 100 :
        error_msg = "Delivery Street 2 should be less than 100 chars."
        _set_error(booking, error_msg)
    if len(booking.de_to_Phone_Main) > 50 :
        error_msg = "Delivery Phone Number should be less than 50 chars."
        _set_error(booking, error_msg)
    return error_msg

def pre_check_startrack(booking):
    error_msg = None
    if len(booking.puCompany) > 30 :
        error_msg = "Pick Up Entity should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Contact_F_L_Name) > 30 :
        error_msg = "Pick Up Contact should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_1) > 40 :
        error_msg = "Pick Up Street 1 should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_2) > 40 :
        error_msg = "Pick Up Street 2 should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.deToCompanyName) > 30 :
        error_msg = "Delivery Entity should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.de_Contact) > 30 :
        error_msg = "Delivery Contact should be less than 30 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_1) > 40 :
        error_msg = "Delivery Street 1 should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_2) > 40 :
        error_msg = "Delivery Street 2 should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.de_to_Phone_Main) > 10 :
        error_msg = "Delivery Phone Number should be less than 13 chars."
        _set_error(booking, error_msg)
    return error_msg

def pre_check_sendle(booking):
    error_msg = None
    if len(booking.puCompany) > 255 :
        error_msg = "Pick Up Entity should be less than 255 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_1) > 40 :
        error_msg = "Pick Up Street 1 should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.pu_Address_Street_2) > 40 :
        error_msg = "Pick Up Street 2 should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.deToCompanyName) > 255 :
        error_msg = "Delivery Entity should be less than 255 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_1) > 40 :
        error_msg = "Delivery Street 1 should be less than 40 chars."
        _set_error(booking, error_msg)
    if len(booking.de_To_Address_Street_2) > 40 :
        error_msg = "Delivery Street 2 should be less than 40 chars."
        _set_error(booking, error_msg)
    return error_msg

def pre_check_rebook(booking):
    if booking.b_status.lower() == "ready for booking":
        error_msg = "Booking is not booked."
        return error_msg

    if booking.pu_Address_State is None or not booking.pu_Address_State:
        error_msg = "State for pickup postal address is required."
        _set_error(booking, error_msg)
        return error_msg

    if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
        error_msg = "Suburb name for pickup postal address is required."
        _set_error(booking, error_msg)
        return error_msg

    if (
        booking.vx_freight_provider.lower() == "hunter"
        and not booking.puPickUpAvailFrom_Date
    ):
        error_msg = "PU Available From Date is required."
        _set_error(booking, error_msg)
        return error_msg

def pre_check_label(booking):
    if booking.vx_freight_provider.lower() == "tnt":
        if not booking.pu_Phone_Main or (
            booking.pu_Phone_Main and len(booking.pu_Phone_Main) > 13
        ):
            error_msg = "Address.Phone must be between 0 and 13 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.de_to_Phone_Main or (
            booking.de_to_Phone_Main and len(booking.de_to_Phone_Main) > 13
        ):
            error_msg = "Address.Phone must be between 0 and 13 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.pu_Address_Street_1 or (
            booking.pu_Address_Street_1 and len(booking.pu_Address_Street_1) > 30
        ):
            error_msg = "Address.Street1 must be between 0 and 30 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.de_To_Address_Street_1 or (
            booking.de_To_Address_Street_1 and len(booking.de_To_Address_Street_1) > 30
        ):
            error_msg = "Address.Street1 must be between 0 and 30 characters."
            _set_error(booking, error_msg)
            return error_msg

        if booking.pu_Address_street_2 and len(booking.pu_Address_street_2) > 30:
            error_msg = "Address.Street2 must be between 0 and 30 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.puCompany or (booking.puCompany and len(booking.puCompany) > 30):
            error_msg = "Address.CompanyName must be between 0 and 30 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.deToCompanyName or (
            booking.deToCompanyName and len(booking.deToCompanyName) > 30
        ):
            error_msg = "Address.CompanyName must be between 0 and 30 characters."
            _set_error(booking, error_msg)
            return error_msg

        # Commented on 2021-02-15
        # Handled on AA
        # if not booking.pu_pickup_instructions_address or (
        #     booking.pu_pickup_instructions_address
        #     and len(booking.pu_pickup_instructions_address) > 80
        # ):
        #     error_msg = "Address.Instruction must be between 0 and 80 characters."
        #     _set_error(booking, error_msg)
        #     return error_msg

        if not booking.pu_Contact_F_L_Name or (
            booking.pu_Contact_F_L_Name and len(booking.pu_Contact_F_L_Name) > 20
        ):
            error_msg = "Address.ContactName must be between 0 and 20 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.de_to_Contact_F_LName or (
            booking.de_to_Contact_F_LName and len(booking.de_to_Contact_F_LName) > 20
        ):
            error_msg = "Address.ContactName must be between 0 and 20 characters."
            _set_error(booking, error_msg)
            return error_msg
