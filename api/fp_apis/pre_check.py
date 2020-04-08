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

        if not booking.pu_Address_street_2 or (
            booking.pu_Address_street_2 and len(booking.pu_Address_street_2) > 30
        ):
            error_msg = "Address.Street2 must be between 0 and 30 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.de_To_Address_Street_2 or (
            booking.de_To_Address_Street_2 and len(booking.de_To_Address_Street_2) > 30
        ):
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

        if not booking.pu_pickup_instructions_address or (
            booking.pu_pickup_instructions_address
            and len(booking.pu_pickup_instructions_address) > 80
        ):
            error_msg = "Address.Instruction must be between 0 and 80 characters."
            _set_error(booking, error_msg)
            return error_msg

        if not booking.de_to_PickUp_Instructions_Address or (
            booking.de_to_PickUp_Instructions_Address
            and len(booking.de_to_PickUp_Instructions_Address) > 80
        ):
            error_msg = "Address.Instrunction must be between 0 and 80 characters."
            _set_error(booking, error_msg)
            return error_msg

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
