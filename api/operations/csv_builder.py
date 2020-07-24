from api.utils import *

def _generate_csv(booking_ids, vx_freight_provider):
    # print('#900 - Running %s' % datetime.datetime.now())

    try:
        mysqlcon = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except:
        # print('Mysql DB connection error!')
        exit(1)

    bookings = get_available_bookings(booking_ids)

    if vx_freight_provider == "cope":
        csv_name = (
            "SEATEMP__"
            + str(len(booking_ids))
            + "__"
            + str(datetime.now().strftime("%d-%m-%Y__%H_%M_%S"))
            + ".csv"
        )
    elif vx_freight_provider == "dhl":
        csv_name = (
            "Seaway-Tempo-Aldi__"
            + str(len(booking_ids))
            + "__"
            + str(datetime.now().strftime("%d-%m-%Y__%H_%M_%S"))
            + ".csv"
        )
    elif vx_freight_provider.lower() == "state transport":
        csv_name = (
            "State-transport__"
            + str(len(booking_ids))
            + "__"
            + str(datetime.now().strftime("%d-%m-%Y__%H_%M_%S"))
            + ".csv"
        )

    if production:
        if vx_freight_provider == "cope":
            f = open(
                "/home/cope_au/dme_sftp/cope_au/pickup_ext/cope_au/" + csv_name, "w"
            )
        elif vx_freight_provider == "dhl":
            f = open(
                "/home/cope_au/dme_sftp/cope_au/pickup_ext/dhl_au/" + csv_name, "w"
            )
        elif vx_freight_provider == "state transport":
            f = open(
                "/home/cope_au/dme_sftp/cope_au/pickup_ext/state_transport_au/"
                + csv_name,
                "w",
            )
    else:
        if not os.path.exists("./static/csvs/statetransport_au/"):
            os.makedirs("./static/csvs/statetransport_au/")

        f = open("./static/csvs/statetransport_au/" + csv_name, "w")

    has_error = csv_write(f, bookings, vx_freight_provider, mysqlcon)
    f.close()

    if has_error:
        os.remove(f.name)

    # print('#901 - Finished %s' % datetime.datetime.now())
    mysqlcon.close()
    return has_error
    

def csv_write(fileHandler, bookings, vx_freight_provider, mysqlcon):
    has_error = False

    if vx_freight_provider == "cope":
        # Write Header
        fileHandler.write(
            "userId,connoteNo,connoteDate,customer,senderName,senderAddress1,senderAddress2,senderSuburb,senderPostcode,senderState,\
        senderContact,senderPhone,pickupDate,pickupTime,receiverName,receiverAddress1,receiverAddress2,receiverSuburb,receiverPostcode,receiverState, \
        receiverContact,receiverPhone,deliveryDate,deliveryTime,totalQuantity,totalPallets,totalWeight,totalVolume,senderReference,description, \
        specialInstructions,notes,jobType,serviceType,priorityType,vehicleType,itemCode,scanCode,freightCode,itemReference, \
        description,quantity,pallets,labels,totalWeight,totalVolume,length,width,height,weight, \
        docAmount,senderCode,receiverCode,warehouseOrderType,freightline_serialNumber,freightline_wbDocket,senderAddress3,receiverAddress3, senderEmail,receiverEmail, \
        noConnote"
        )

        # Write Each Line
        comma = ","
        newLine = "\n"
        if len(bookings) > 0:
            for booking in bookings:
                booking_lines = get_available_booking_lines(booking)
                eachLineText = "DVM0001"

                if booking["b_bookingID_Visual"] is None:
                    h0 = ""
                else:
                    h0 = wrap_in_quote("DME" + str(booking.get("b_bookingID_Visual")))

                if booking["puPickUpAvailFrom_Date"] is None:
                    h1 = ""
                else:
                    h1 = wrap_in_quote(str(booking.get("puPickUpAvailFrom_Date")))

                h2 = "009790"

                if booking["puCompany"] is None:
                    h00 = ""
                else:
                    h00 = wrap_in_quote(booking.get("puCompany"))

                if booking["pu_Address_Street_1"] is None:
                    h01 = ""
                else:
                    h01 = wrap_in_quote(booking.get("pu_Address_Street_1"))

                if booking["pu_Address_street_2"] is None:
                    h02 = ""
                else:
                    h02 = wrap_in_quote(booking.get("pu_Address_street_2"))

                if booking["pu_Address_Suburb"] is None:
                    h03 = ""
                else:
                    h03 = wrap_in_quote(booking.get("pu_Address_Suburb"))

                if booking["pu_Address_PostalCode"] is None:
                    h04 = ""
                else:
                    h04 = wrap_in_quote(booking.get("pu_Address_PostalCode"))

                if booking["pu_Address_State"] is None:
                    h05 = ""
                else:
                    h05 = wrap_in_quote(booking.get("pu_Address_State"))

                if booking["pu_Contact_F_L_Name"] is None:
                    h06 = ""
                else:
                    h06 = wrap_in_quote(booking.get("pu_Contact_F_L_Name"))

                if booking["pu_Phone_Main"] is None:
                    h07 = ""
                else:
                    h07 = str(booking.get("pu_Phone_Main"))

                if booking["pu_PickUp_Avail_From_Date_DME"] is None:
                    h08 = ""
                else:
                    h08 = wrap_in_quote(booking.get("pu_PickUp_Avail_From_Date_DME"))

                if booking["pu_PickUp_Avail_Time_Hours_DME"] is None:
                    h09 = ""
                else:
                    h09 = str(booking.get("pu_PickUp_Avail_Time_Hours_DME"))

                if booking["deToCompanyName"] is None:
                    h10 = ""
                else:
                    h10 = wrap_in_quote(booking.get("deToCompanyName"))

                if booking["de_To_Address_Street_1"] is None:
                    h11 = ""
                else:
                    h11 = wrap_in_quote(booking.get("de_To_Address_Street_1"))

                if booking["de_To_Address_Street_2"] is None:
                    h12 = ""
                else:
                    h12 = wrap_in_quote(booking.get("de_To_Address_Street_2"))

                if booking["de_To_Address_Suburb"] is None:
                    h13 = ""
                else:
                    h13 = wrap_in_quote(booking.get("de_To_Address_Suburb"))

                if booking["de_To_Address_PostalCode"] is None:
                    h14 = ""
                else:
                    h14 = wrap_in_quote(booking.get("de_To_Address_PostalCode"))

                if booking["de_To_Address_State"] is None:
                    h15 = ""
                else:
                    h15 = wrap_in_quote(booking.get("de_To_Address_State"))

                if booking["de_to_Contact_F_LName"] is None:
                    h16 = ""
                else:
                    h16 = wrap_in_quote(booking.get("de_to_Contact_F_LName"))

                if booking["de_to_Phone_Main"] is None:
                    h17 = ""
                else:
                    h17 = str(booking.get("de_to_Phone_Main"))

                if booking["de_Deliver_From_Date"] is None:
                    h18 = ""
                else:
                    h18 = wrap_in_quote(booking.get("de_Deliver_From_Date"))

                if booking["de_Deliver_From_Hours"] is None:
                    h19 = ""
                else:
                    h19 = str(booking.get("de_Deliver_From_Hours"))

                h20 = ""
                h21 = ""
                h22 = ""
                h23 = ""

                if booking["b_client_sales_inv_num"] is None:
                    h24 = ""
                else:
                    h24 = wrap_in_quote(booking.get("b_client_sales_inv_num"))

                if booking["b_client_order_num"] is None:
                    h25 = ""
                else:
                    h25 = wrap_in_quote(booking.get("b_client_order_num"))

                h26 = ""
                if booking["de_to_PickUp_Instructions_Address"]:
                    h26 = wrap_in_quote(
                        booking.get("de_to_PickUp_Instructions_Address")
                    )
                if booking["de_to_Pick_Up_Instructions_Contact"]:
                    h26 += " " + wrap_in_quote(
                        booking.get("de_to_Pick_Up_Instructions_Contact")
                    )

                h27 = ""

                if booking["vx_serviceName"] is None:
                    h28 = ""
                else:
                    h28 = wrap_in_quote(booking.get("vx_serviceName"))

                if booking["v_service_Type"] is None:
                    h29 = ""
                else:
                    h29 = wrap_in_quote(booking.get("v_service_Type"))

                h50 = h25
                h51 = ""

                if booking["pu_pickup_instructions_address"] is None:
                    h52 = ""
                else:
                    h52 = wrap_in_quote(booking.get("pu_pickup_instructions_address"))

                h53 = ""

                if booking["pu_Email"] is None:
                    h54 = ""
                else:
                    h54 = wrap_in_quote(booking.get("pu_Email"))
                if booking["de_Email"] is None:
                    h55 = ""
                else:
                    h55 = wrap_in_quote(booking.get("de_Email"))

                h56 = "N"

                h30 = ""
                h31 = ""
                if len(booking_lines) > 0:
                    for booking_line in booking_lines:
                        if booking["b_clientReference_RA_Numbers"] is None:
                            h32 = ""
                        else:
                            h32 = str(booking.get("b_clientReference_RA_Numbers"))

                        h33 = ""
                        if booking_line["e_type_of_packaging"] is None:
                            h34 = ""
                        else:
                            h34 = wrap_in_quote(booking_line.get("e_type_of_packaging"))
                        if booking_line["client_item_reference"] is None:
                            h35 = ""
                        else:
                            h35 = wrap_in_quote(
                                booking_line.get("client_item_reference")
                            )
                        if booking_line["e_item"] is None:
                            h36 = ""
                        else:
                            h36 = wrap_in_quote(booking_line.get("e_item"))
                        if booking_line["e_qty"] is None:
                            h37 = ""
                        else:
                            h37 = str(booking_line.get("e_qty"))

                        h38 = ""

                        if booking_line["e_qty"] is None:
                            h39 = ""
                        else:
                            h39 = str(booking_line.get("e_qty"))

                        # Calc totalWeight
                        h40 = "0"
                        if (
                            booking_line["e_weightUOM"] is not None
                            and booking_line["e_weightPerEach"] is not None
                            and booking_line["e_qty"] is not None
                        ):
                            if (
                                booking_line["e_weightUOM"].upper() == "GRAM"
                                or booking_line["e_weightUOM"].upper() == "GRAMS"
                            ):
                                h40 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_weightPerEach"]
                                    / 1000
                                )
                            elif (
                                booking_line["e_weightUOM"].upper() == "KILOGRAM"
                                or booking_line["e_weightUOM"].upper() == "KG"
                                or booking_line["e_weightUOM"].upper() == "KGS"
                                or booking_line["e_weightUOM"].upper() == "KILOGRAMS"
                            ):
                                h40 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_weightPerEach"]
                                )
                            elif (
                                booking_line["e_weightUOM"].upper() == "TON"
                                or booking_line["e_weightUOM"].upper() == "TONS"
                            ):
                                h40 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_weightPerEach"]
                                    * 1000
                                )
                            else:
                                h40 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_weightPerEach"]
                                )

                        # Calc totalVolume
                        h41 = "0"
                        if (
                            booking_line["e_dimUOM"] is not None
                            and booking_line["e_dimLength"] is not None
                            and booking_line["e_dimWidth"] is not None
                            and booking_line["e_dimHeight"] is not None
                            and booking_line["e_qty"] is not None
                        ):
                            if (
                                booking_line["e_dimUOM"].upper() == "CM"
                                or booking_line["e_dimUOM"].upper() == "CENTIMETER"
                            ):
                                h41 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_dimLength"]
                                    * booking_line["e_dimWidth"]
                                    * booking_line["e_dimHeight"]
                                    / 1000000
                                )
                            elif (
                                booking_line["e_dimUOM"].upper() == "METER"
                                or booking_line["e_dimUOM"].upper() == "M"
                            ):
                                h41 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_dimLength"]
                                    * booking_line["e_dimWidth"]
                                    * booking_line["e_dimHeight"]
                                )
                            elif (
                                booking_line["e_dimUOM"].upper() == "MILIMETER"
                                or booking_line["e_dimUOM"].upper() == "MM"
                            ):
                                h41 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_dimLength"]
                                    * booking_line["e_dimWidth"]
                                    * booking_line["e_dimHeight"]
                                    / 1000000000
                                )
                            else:
                                h41 = str(
                                    booking_line["e_qty"]
                                    * booking_line["e_dimLength"]
                                    * booking_line["e_dimWidth"]
                                    * booking_line["e_dimHeight"]
                                )

                        if booking_line["e_dimLength"] is None:
                            h42 = ""
                        else:
                            h42 = str(booking_line.get("e_dimLength"))
                        if booking_line["e_dimWidth"] is None:
                            h43 = ""
                        else:
                            h43 = str(booking_line.get("e_dimWidth"))
                        if booking_line["e_dimHeight"] is None:
                            h44 = ""
                        else:
                            h44 = str(booking_line.get("e_dimHeight"))
                        if booking_line["e_weightPerEach"] is None:
                            h45 = ""
                        else:
                            h45 = str(booking_line.get("e_weightPerEach"))
                        h46 = ""
                        h47 = ""
                        h48 = ""
                        h49 = ""

                        eachLineText += comma + h0 + comma + h1 + comma + h2
                        eachLineText += (
                            comma
                            + h00
                            + comma
                            + h01
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
                            + comma
                            + h19
                        )
                        eachLineText += (
                            comma
                            + h20
                            + comma
                            + h21
                            + comma
                            + h22
                            + comma
                            + h23
                            + comma
                            + h24
                            + comma
                            + h25
                            + comma
                            + h26
                            + comma
                            + h27
                            + comma
                            + h28
                            + comma
                            + h29
                        )
                        eachLineText += (
                            comma
                            + h30
                            + comma
                            + h31
                            + comma
                            + h32
                            + comma
                            + h33
                            + comma
                            + h34
                            + comma
                            + h35
                            + comma
                            + h36
                            + comma
                            + h37
                            + comma
                            + h38
                            + comma
                            + h39
                        )
                        eachLineText += (
                            comma
                            + h40
                            + comma
                            + h41
                            + comma
                            + h42
                            + comma
                            + h43
                            + comma
                            + h44
                            + comma
                            + h45
                            + comma
                            + h46
                            + comma
                            + h47
                            + comma
                            + h48
                            + comma
                            + h49
                        )
                        eachLineText += (
                            comma
                            + h50
                            + comma
                            + h51
                            + comma
                            + h52
                            + comma
                            + h53
                            + comma
                            + h54
                            + comma
                            + h55
                            + comma
                            + h56
                        )
                        fileHandler.write(newLine + eachLineText)
                        eachLineText = "DVM0001"
                else:
                    h32 = ""
                    h33 = ""
                    h34 = ""
                    h35 = ""
                    h36 = ""
                    h37 = ""
                    h38 = ""
                    h39 = ""
                    h40 = ""
                    h41 = ""
                    h42 = ""
                    h43 = ""
                    h44 = ""
                    h45 = ""
                    h46 = ""
                    h47 = ""
                    h48 = ""
                    h49 = ""

                    eachLineText += comma + h0 + comma + h1 + comma + h2
                    eachLineText += (
                        comma
                        + h00
                        + comma
                        + h01
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
                        + comma
                        + h19
                    )
                    eachLineText += (
                        comma
                        + h20
                        + comma
                        + h21
                        + comma
                        + h22
                        + comma
                        + h23
                        + comma
                        + h24
                        + comma
                        + h25
                        + comma
                        + h26
                        + comma
                        + h27
                        + comma
                        + h28
                        + comma
                        + h29
                    )
                    eachLineText += (
                        comma
                        + h30
                        + comma
                        + h31
                        + comma
                        + h32
                        + comma
                        + h33
                        + comma
                        + h34
                        + comma
                        + h35
                        + comma
                        + h36
                        + comma
                        + h37
                        + comma
                        + h38
                        + comma
                        + h39
                    )
                    eachLineText += (
                        comma
                        + h40
                        + comma
                        + h41
                        + comma
                        + h42
                        + comma
                        + h43
                        + comma
                        + h44
                        + comma
                        + h45
                        + comma
                        + h46
                        + comma
                        + h47
                        + comma
                        + h48
                        + comma
                        + h49
                    )
                    eachLineText += (
                        comma
                        + h50
                        + comma
                        + h51
                        + comma
                        + h52
                        + comma
                        + h53
                        + comma
                        + h54
                        + comma
                        + h55
                        + comma
                        + h56
                    )
                    fileHandler.write(newLine + eachLineText)
                    eachLineText = "DVM0001"
    elif vx_freight_provider == "dhl":
        # Write Header
        fileHandler.write(
            "unique_identifier, ref1, ref2(sinv), receiver_name, receiver_address1, receiver_address2, receiver_address3, receiver_address4, receiver_locality, receiver_state, \
            receiver_postcode, weight, length, width, height, receiver_contact, receiver_phone_no, receiver_email, pack_unit_code, pack_unit_description, \
            items, special_instructions, consignment_prefix, consignment_number, transporter_code, service_code, sender_code, sender_warehouse_code, freight_payer, freight_label_number, \
            barcode\n"
        )

        # Write Each Line
        comma = ","
        newLine = "\n"
        fp_info = Fp_freight_providers.objects.get(fp_company_name="DHL")
        fp_carriers = FP_carriers.objects.filter(fk_fp=fp_info.id)
        fp_carriers_old_vals = []

        for fp_carrier in fp_carriers:
            fp_carriers_old_vals.append(fp_carrier.current_value)

        if len(bookings) > 0:
            for booking in bookings:
                booking_lines = get_available_booking_lines(booking)

                if booking["b_client_order_num"] is None:
                    h00 = ""
                else:
                    h00 = str(booking.get("b_client_order_num"))

                if booking["b_clientReference_RA_Numbers"] is None:
                    h02 = ""
                else:
                    h02 = str(booking.get("b_clientReference_RA_Numbers"))

                if booking["b_client_sales_inv_num"] is None:
                    h03 = ""
                else:
                    h03 = str(booking.get("b_client_sales_inv_num"))

                if booking["deToCompanyName"] is None:
                    h04 = ""
                else:
                    h04 = str(booking.get("deToCompanyName"))

                if booking["de_To_Address_Street_1"] is None:
                    h05 = ""
                else:
                    h05 = str(booking.get("de_To_Address_Street_1"))

                if booking["de_To_Address_Street_2"] is None:
                    h06 = ""
                else:
                    h06 = str(booking.get("de_To_Address_Street_2"))

                h07 = ""
                h08 = ""

                if booking["de_To_Address_Suburb"] is None:
                    h09 = ""
                else:
                    h09 = str(booking.get("de_To_Address_Suburb"))

                if booking["de_To_Address_State"] is None:
                    h10 = ""
                else:
                    h10 = str(booking.get("de_To_Address_State"))

                if booking["de_To_Address_PostalCode"] is None:
                    h11 = ""
                else:
                    h11 = str(booking.get("de_To_Address_PostalCode"))

                if booking["de_to_Contact_F_LName"] is None:
                    h16 = ""
                else:
                    h16 = str(booking.get("de_to_Contact_F_LName"))

                if booking["de_to_Phone_Main"] is None:
                    h17 = ""
                else:
                    h17 = str(booking.get("de_to_Phone_Main"))

                if booking["de_Email"] is None:
                    h18 = ""
                else:
                    h18 = str(booking.get("de_Email"))

                if booking["de_to_PickUp_Instructions_Address"] is None:
                    h22 = ""
                else:
                    h22 = wrap_in_quote(
                        booking.get("de_to_PickUp_Instructions_Address").replace(
                            ";", " "
                        )
                    )

                if (
                    booking["de_To_Address_Suburb"] is not None
                    and booking["de_To_Address_State"] is not None
                    and booking["de_To_Address_PostalCode"] is not None
                ):
                    fp_zone = FP_zones.objects.filter(
                        fk_fp=fp_info.id,
                        state=booking["de_To_Address_State"],
                        suburb=booking["de_To_Address_Suburb"],
                        postal_code=booking["de_To_Address_PostalCode"],
                    ).first()

                if fp_zone is None:
                    has_error = True

                    # Update booking with FP bug
                    with mysqlcon.cursor() as cursor:
                        sql2 = "UPDATE dme_bookings \
                                SET b_error_Capture = %s \
                                WHERE id = %s"
                        adr2 = (
                            "DE address and FP_zones are not matching.",
                            booking["id"],
                        )
                        cursor.execute(sql2, adr2)
                        mysqlcon.commit()
                else:
                    h23 = "DMS" if fp_zone.carrier == "DHLSFS" else "DMB"

                    h25 = fp_zone.carrier
                    h26 = fp_zone.service
                    h27 = fp_zone.sender_code
                    h28 = "OWNSITE"  # HARDCODED - "sender_warehouse_code"
                    h29 = "S"

                    if len(booking_lines) > 0:
                        for booking_line in booking_lines:
                            eachLineText = ""
                            h12 = ""
                            if (
                                booking_line["e_weightUOM"] is not None
                                and booking_line["e_weightPerEach"] is not None
                            ):
                                if (
                                    booking_line["e_weightUOM"].upper() == "GRAM"
                                    or booking_line["e_weightUOM"].upper() == "GRAMS"
                                ):
                                    h12 = str(
                                        booking_line["e_qty"]
                                        * booking_line["e_weightPerEach"]
                                        / 1000
                                    )
                                elif (
                                    booking_line["e_weightUOM"].upper() == "TON"
                                    or booking_line["e_weightUOM"].upper() == "TONS"
                                ):
                                    h12 = str(
                                        booking_line["e_qty"]
                                        * booking_line["e_weightPerEach"]
                                        * 1000
                                    )
                                else:
                                    h12 = str(
                                        booking_line["e_qty"]
                                        * booking_line["e_weightPerEach"]
                                    )

                            if booking_line["e_dimLength"] is None:
                                h13 = ""
                            else:
                                h13 = str(booking_line.get("e_dimLength"))

                            if booking_line["e_dimWidth"] is None:
                                h14 = ""
                            else:
                                h14 = str(booking_line.get("e_dimWidth"))

                            if booking_line["e_dimHeight"] is None:
                                h15 = ""
                            else:
                                h15 = str(booking_line.get("e_dimHeight"))

                            # if booking_line["e_pallet_type"] is None:
                            #     h19 = ""
                            # else:
                            #     h19 = str(booking_line.get("e_pallet_type"))

                            # if booking_line["e_type_of_packaging"] is None:
                            #     h20 = ""
                            # else:
                            #     h20 = str(booking_line.get("e_type_of_packaging"))

                            h19 = "PAL"  # Hardcoded
                            h20 = "Pallet"  # Hardcoded

                            if booking_line["e_qty"] is None:
                                h21 = ""
                            else:
                                h21 = str(booking_line.get("e_qty"))

                            h24 = ""
                            h30 = ""
                            fp_carrier = None

                            try:
                                fp_carrier = fp_carriers.get(carrier=fp_zone.carrier)
                                h24 = h23 + str(
                                    fp_carrier.connote_start_value
                                    + fp_carrier.current_value
                                )
                                h30 = (
                                    h23
                                    + "L00"
                                    + str(
                                        fp_carrier.label_start_value
                                        + fp_carrier.current_value
                                    )
                                )

                                # Update booking while build CSV for DHL
                                with mysqlcon.cursor() as cursor:
                                    sql2 = "UPDATE dme_bookings \
                                            SET v_FPBookingNumber = %s, vx_freight_provider_carrier = %s, b_error_Capture = %s \
                                            WHERE id = %s"
                                    adr2 = (h24, fp_zone.carrier, None, booking["id"])
                                    cursor.execute(sql2, adr2)
                                    mysqlcon.commit()

                                if not has_error:
                                    fp_carrier.current_value += 1
                                    fp_carrier.save()
                            except FP_carriers.DoesNotExist:
                                has_error = True

                                # Update booking with FP bug
                                with mysqlcon.cursor() as cursor:
                                    sql2 = "UPDATE dme_bookings \
                                            SET b_error_Capture = %s \
                                            WHERE id = %s"
                                    adr2 = (
                                        "FP_carrier is not matching. Please check FP_zones.",
                                        booking["id"],
                                    )
                                    cursor.execute(sql2, adr2)
                                    mysqlcon.commit()

                            h31 = h24 + h30 + booking["de_To_Address_PostalCode"]

                            eachLineText += (
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
                                + comma
                                + h19
                            )
                            eachLineText += (
                                comma
                                + h20
                                + comma
                                + h21
                                + comma
                                + h22
                                + comma
                                + h23
                                + comma
                                + h24
                                + comma
                                + h25
                                + comma
                                + h26
                                + comma
                                + h27
                                + comma
                                + h28
                                + comma
                                + h29
                            )
                            eachLineText += comma + h30 + comma + h31

                            fileHandler.write(eachLineText + newLine)

    elif vx_freight_provider.lower() == "state transport":
        # Write Header
        fileHandler.write(
            "account, reference, ownno, sender_name, sender_address1, sender_address2, sender_suburb, sender_postcode, \
            receiver_name, receiver_addres1, receiver_addres2, receiver_suburb, receiver_postcode, \
            items, weight, service, labels, ready_time \n"
        )

        # Write Each Line
        comma = ","
        newLine = "\n"

        if len(bookings) > 0:
            for booking in bookings:
                booking_lines = get_available_booking_lines(booking)

                h00 = "FMS account"

                if booking["b_clientReference_RA_Numbers"] is None:
                    h02 = ""
                else:
                    h02 = str(booking.get("b_clientReference_RA_Numbers"))

                if booking["b_client_sales_inv_num"] is None:
                    h03 = ""
                else:
                    h03 = str(booking.get("b_client_sales_inv_num"))

                if booking["puCompany"] is None:
                    h04 = ""
                else:
                    h04 = str(booking.get("puCompany"))

                if booking["pu_Address_Street_1"] is None:
                    h05 = ""
                else:
                    h05 = str(booking.get("pu_Address_Street_1"))

                if booking["pu_Address_street_2"] is None:
                    h06 = ""
                else:
                    h06 = str(booking.get("pu_Address_street_2"))

                if booking["pu_Address_Suburb"] is None:
                    h07 = ""
                else:
                    h07 = str(booking.get("pu_Address_Suburb"))

                if booking["pu_Address_PostalCode"] is None:
                    h08 = ""
                else:
                    h08 = str(booking.get("pu_Address_PostalCode"))

                if booking["deToCompanyName"] is None:
                    h09 = ""
                else:
                    h09 = str(booking.get("deToCompanyName"))

                if booking["de_To_Address_Street_1"] is None:
                    h10 = ""
                else:
                    h10 = str(booking.get("de_To_Address_Street_1"))

                if booking["de_To_Address_Street_2"] is None:
                    h11 = ""
                else:
                    h11 = str(booking.get("de_To_Address_Street_2"))

                if booking["de_To_Address_Suburb"] is None:
                    h12 = ""
                else:
                    h12 = str(booking.get("de_To_Address_Suburb"))

                if booking["de_To_Address_PostalCode"] is None:
                    h13 = ""
                else:
                    h13 = str(booking.get("de_To_Address_PostalCode"))

                h14 = str(len(booking_lines))
                h15 = 0

                if len(booking_lines) > 0:
                    for booking_line in booking_lines:
                        if (
                            booking_line["e_weightUOM"] is not None
                            and booking_line["e_weightPerEach"] is not None
                        ):
                            if (
                                booking_line["e_weightUOM"].upper() == "GRAM"
                                or booking_line["e_weightUOM"].upper() == "GRAMS"
                            ):
                                h15 += (
                                    booking_line["e_qty"]
                                    * booking_line["e_weightPerEach"]
                                    / 1000
                                )

                            elif (
                                booking_line["e_weightUOM"].upper() == "TON"
                                or booking_line["e_weightUOM"].upper() == "TONS"
                            ):
                                h15 += (
                                    booking_line["e_qty"]
                                    * booking_line["e_weightPerEach"]
                                    * 1000
                                )
                            else:
                                h15 += (
                                    booking_line["e_qty"]
                                    * booking_line["e_weightPerEach"]
                                )

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
            # Clear booking updates
            with mysqlcon.cursor() as cursor:
                sql2 = "UPDATE dme_bookings \
                        SET v_FPBookingNumber = %s, vx_freight_provider_carrier = %s \
                        WHERE id = %s"
                adr2 = (None, None, booking["id"])
                cursor.execute(sql2, adr2)
                mysqlcon.commit()

        for index, fp_carrier in enumerate(fp_carriers):
            fp_carrier.current_value = fp_carriers_old_vals[index]
            fp_carrier.save()

    return has_error
