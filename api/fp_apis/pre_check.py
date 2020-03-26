def _set_error(booking, error_msg):
    booking.b_error_Capture = str(error_msg)[:999]
    booking.save()


def pre_check_book(booking):
    if booking.b_status.lower() == "booked":
        error_msg = "Booking is already booked."
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
        if not booking.pu_Contact_F_L_Name or not booking.de_to_Contact_F_LName:
            error_msg = "Address.ContactName must be between 0 and 20 characters."
            _set_error(booking, error_msg)
            return error_msg

        if booking.pu_Contact_F_L_Name and len(booking.pu_Contact_F_L_Name) > 20:
            error_msg = "Address.ContactName must be between 0 and 20 characters."
            _set_error(booking, error_msg)
            return error_msg

        if booking.de_to_Contact_F_LName and len(booking.de_to_Contact_F_LName) > 20:
            error_msg = "Address.ContactName must be between 0 and 20 characters."
            _set_error(booking, error_msg)
            return error_msg
