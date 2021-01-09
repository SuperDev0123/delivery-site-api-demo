def filter_booking_lines(booking, booking_lines):
    _booking_lines = []

    for booking_line in booking_lines:
        if booking.pk_booking_id == booking_line.fk_booking_id:
            _booking_lines.append(booking_line)

    return _booking_lines


def wrap_in_quote(string):
    return '"' + str(string) + '"'


def build_csv(fileHandler, bookings, booking_lines):
    has_error = None

    # Write Header
    fileHandler.write(
        "account, reference, ownno, sender_name, sender_address1, sender_address2, sender_suburb, sender_postcode, \
receiver_name, receiver_addres1, receiver_addres2, receiver_suburb, receiver_postcode, \
items, weight, service, labels, ready_time \n"
    )

    # Write Each Line
    comma = ","
    newLine = "\n"

    for booking in bookings:
        _booking_lines = filter_booking_lines(booking, booking_lines)

        h00 = "FMS account"

        if not booking.b_clientReference_RA_Numbers:
            h02 = ""
        else:
            h02 = str(booking.b_clientReference_RA_Numbers)

        if not booking.b_client_sales_inv_num:
            h03 = ""
        else:
            h03 = str(booking.b_client_sales_inv_num)

        if not booking.puCompany:
            h04 = ""
        else:
            h04 = str(booking.puCompany)

        if not booking.pu_Address_Street_1:
            h05 = ""
        else:
            h05 = str(booking.pu_Address_Street_1)

        if not booking.pu_Address_street_2:
            h06 = ""
        else:
            h06 = str(booking.pu_Address_street_2)

        if not booking.pu_Address_Suburb:
            h07 = ""
        else:
            h07 = str(booking.pu_Address_Suburb)

        if not booking.pu_Address_PostalCode:
            h08 = ""
        else:
            h08 = str(booking.pu_Address_PostalCode)

        if not booking.deToCompanyName:
            h09 = ""
        else:
            h09 = str(booking.deToCompanyName)

        if not booking.de_To_Address_Street_1:
            h10 = ""
        else:
            h10 = str(booking.de_To_Address_Street_1)

        if not booking.de_To_Address_Street_2:
            h11 = ""
        else:
            h11 = str(booking.de_To_Address_Street_2)

        if not booking.de_To_Address_Suburb:
            h12 = ""
        else:
            h12 = str(booking.de_To_Address_Suburb)

        if not booking.de_To_Address_PostalCode:
            h13 = ""
        else:
            h13 = str(booking.de_To_Address_PostalCode)

        h14 = str(len(booking_lines))
        h15 = 0

        for booking_line in _booking_lines:
            if booking_line.e_weightUOM and booking_line.e_weightPerEach:
                if (
                    booking_line.e_weightUOM.upper() == "GRAM"
                    or booking_line.e_weightUOM.upper() == "GRAMS"
                ):
                    h15 += booking_line.e_qty * booking_line.e_weightPerEach / 1000

                elif (
                    booking_line.e_weightUOM.upper() == "TON"
                    or booking_line.e_weightUOM.upper() == "TONS"
                ):
                    h15 += booking_line.e_qty * booking_line.e_weightPerEach * 1000
                else:
                    h15 += booking_line.e_qty * booking_line.e_weightPerEach

        h15 = str(h15)
        h16 = "vip"
        h17 = ""
        h18 = str(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        eachLineText = (
            h00
            + comma
            + h02
            + comma
            + h03
            + comma
            + h04
            + comma
            + h05
            + comma
            + h06
            + comma
            + h07
            + comma
            + h08
            + comma
            + h09
        )
        eachLineText += (
            comma
            + h10
            + comma
            + h11
            + comma
            + h12
            + comma
            + h13
            + comma
            + h14
            + comma
            + h15
            + comma
            + h16
            + comma
            + h17
            + comma
            + h18
        )

        fileHandler.write(eachLineText + newLine)

    if has_error:
        for booking in bookings:
            booking.v_FPBookingNumber = None
            booking.vx_freight_provider_carrier = None
            booking.save()

    return has_error
