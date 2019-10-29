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

    if (
        booking.vx_freight_provider.lower() == "hunter"
        and not booking.pu_PickUp_By_Date_DME
    ):
        error_msg = "PU By Date is required."
        _set_error(booking, error_msg)
        return error_msg

    return None
