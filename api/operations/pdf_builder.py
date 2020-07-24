from api.utils import *

def build_pdf(booking_ids, vx_freight_provider):
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
        exit(1)
    mycursor = mysqlcon.cursor()
    i = 1
    if vx_freight_provider == "TASFR":
        try:
            bookings = get_available_bookings(booking_ids)

            # start check if pdfs folder exists
            if production:
                local_filepath = "/opt/s3_public/pdfs/tas_au/"
                local_filepath_dup = (
                    "/opt/s3_public/pdfs/tas_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )
            else:
                local_filepath = "./static/pdfs/tas_au/"
                local_filepath_dup = (
                    "./static/pdfs/tas_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )

            if not os.path.exists(local_filepath):
                os.makedirs(local_filepath)
            # end check if pdfs folder exists

            # start loop through data fetched from dme_bookings table
            i = 1
            for booking in bookings:
                booking_lines = get_available_booking_lines(booking)

                totalQty = 0
                for booking_line in booking_lines:
                    totalQty = totalQty + booking_line["e_qty"]

                # start pdf file name using naming convention
                filename = (
                    booking["pu_Address_State"]
                    + "_"
                    + str(booking["b_client_sales_inv_num"])
                    + "_"
                    + str(booking["v_FPBookingNumber"])
                    + "_"
                    + "DME"
                    + str(booking["b_bookingID_Visual"])
                    + ".pdf"
                )
                file = open(local_filepath + filename, "w")
                # end pdf file name using naming convention

                date = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
                doc = SimpleDocTemplate(
                    local_filepath + filename,
                    pagesize=(6 * inch, 4 * inch),
                    rightMargin=10,
                    leftMargin=10,
                    topMargin=10,
                    bottomMargin=10,
                )
                Story = []

                j = 1
                for booking_line in booking_lines:
                    for k in range(booking_line["e_qty"]):
                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=10><b>%s FREIGHT<br /></b></font>"
                                    % booking["vx_freight_provider"].upper(),
                                    style_left,
                                )
                            ],
                            [
                                Paragraph("<font size=8>C/N:</font>", style_left),
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % booking["v_FPBookingNumber"],
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph("<font size=8>Date:</font>", style_left),
                                Paragraph(
                                    "<font size=8><b>%s</b></font>"
                                    % booking["b_dateBookedDate"].strftime(
                                        "%d/%m/%Y %I:%M:%S %p"
                                    ),
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph("<font size=8>Reference:</font>", style_left),
                                Paragraph(
                                    "<font size=8><b>%s</b></font>"
                                    % booking_line["client_item_reference"],
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph("<font size=8>Service:</font>", style_left),
                                Paragraph(
                                    "<font size=8><b>%s</b></font>"
                                    % booking["vx_serviceName"],
                                    styles["BodyText"],
                                ),
                            ],
                        ]
                        t1 = Table(
                            tbl_data,
                            colWidths=(45, 220),
                            rowHeights=(12),
                            hAlign="LEFT",
                            style=[
                                ("SPAN", (0, 0), (1, 0)),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=34><b>%s</b></font>"
                                    % booking["de_To_Address_State"],
                                    styles["Normal"],
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=8><br /><br />%s, %s\n%s, %s, %s</font>"
                                    % (
                                        ACCOUNT_CODE,
                                        booking["pu_Address_Street_1"],
                                        booking["pu_Address_Suburb"],
                                        booking["pu_Address_PostalCode"],
                                        booking["pu_Address_State"],
                                    ),
                                    styles["Normal"],
                                )
                            ],
                        ]
                        t2 = Table(tbl_data, colWidths=(150), style=[])

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=34><b>%s</b></font>"
                                    % booking["de_To_Address_PostalCode"],
                                    style_right,
                                )
                            ],
                            [""],
                            [""],
                            [""],
                        ]
                        t3 = Table(tbl_data, colWidths=(150), style=[])

                        data = [[t1, t2, t3]]
                        # adjust the length of tables
                        t1_w = 2.35 * inch
                        t2_w = 1.2 * inch
                        t3_w = 2 * inch
                        shell_table = Table(
                            data,
                            colWidths=[t1_w, t2_w, t3_w],
                            style=[
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(shell_table)
                        Story.append(Spacer(1, 10))
                        Story.append(
                            HRFlowable(
                                width="100%",
                                thickness=1,
                                lineCap="round",
                                color="#000000",
                                spaceBefore=0,
                                spaceAfter=0,
                                hAlign="CENTER",
                                vAlign="MIDDLE",
                                dash=None,
                            )
                        )

                        # Story.append(Spacer(1, 3))

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % booking["de_to_Contact_F_LName"],
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % booking["de_To_Address_Street_1"],
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=10><b>%s, %s, %s</b></font> "
                                    % (
                                        booking["de_To_Address_Suburb"],
                                        booking["de_To_Address_PostalCode"],
                                        booking["de_To_Address_State"],
                                    ),
                                    style_left,
                                )
                            ],
                        ]
                        t1 = Table(
                            tbl_data,
                            colWidths=(180),
                            style=[
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=8>%s %s</font>"
                                    % (
                                        str(
                                            booking["de_to_PickUp_Instructions_Address"]
                                        ),
                                        str(
                                            booking[
                                                "de_to_Pick_Up_Instructions_Contact"
                                            ]
                                        ),
                                    ),
                                    styles["Normal"],
                                )
                            ],
                            [""],
                        ]
                        t2 = Table(tbl_data, colWidths=(160), style=[])

                        data = [[t1, t2]]
                        # adjust the length of tables
                        t1_w = 2.35 * inch
                        t2_w = 3.2 * inch
                        # t3_w = 2 * inch
                        shell_table = Table(
                            data,
                            colWidths=[t1_w, t2_w],
                            style=[
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(shell_table)

                        Story.append(Spacer(1, 35))

                        barcode = "S" + booking["v_FPBookingNumber"] + str(j).zfill(3)
                        barcode128 = code128.Code128(
                            barcode, barHeight=30 * mm, barWidth=1.2
                        )

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=8>Item: </font>", styles["Normal"]
                                ),
                                Paragraph(
                                    "<font size=12><b>%s of %s</b></font>"
                                    % (j, totalQty),
                                    style_left,
                                ),
                            ]
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(80, 140),
                            rowHeights=(20),
                            hAlign="LEFT",
                            style=[
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(tbl)

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=8><b>Desc</b>: %s</font>"
                                    % (
                                        str(booking_line["e_item"])
                                        if booking_line["e_item"]
                                        else ""
                                    ),
                                    style_left,
                                ),
                                barcode128,
                            ]
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(170, 170),
                            rowHeights=(12),
                            hAlign="LEFT",
                            style=[
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(tbl)
                        Story.append(
                            HRFlowable(
                                width="45%",
                                thickness=1,
                                lineCap="round",
                                color="#000000",
                                spaceBefore=1,
                                spaceAfter=2,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                dash=None,
                            )
                        )

                        tbl_data = [
                            [
                                Paragraph("<font size=8>L</font>", style_center),
                                Paragraph("<font size=8>W</font>", style_center),
                                Paragraph("<font size=8>H</font>", style_center),
                            ],
                            [
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % (str(booking_line["e_dimLength"])),
                                    style_center,
                                ),
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % str(booking_line["e_dimWidth"]),
                                    style_center,
                                ),
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % str(booking_line["e_dimHeight"]),
                                    style_center,
                                ),
                            ],
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(60, 60, 60),
                            rowHeights=10,
                            hAlign="LEFT",
                        )
                        tbl.setStyle(
                            [
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ]
                        )
                        Story.append(tbl)
                        Story.append(
                            HRFlowable(
                                width="45%",
                                thickness=1,
                                lineCap="round",
                                color="#000000",
                                spaceBefore=2,
                                spaceAfter=2,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                dash=None,
                            )
                        )

                        tbl_data = [
                            [
                                Paragraph("<font size=8>KG</font>", style_center),
                                Paragraph("<font size=8>VOL</font>", style_center),
                            ],
                            [
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % str(
                                        "{0:.2f}".format(
                                            booking_line["e_Total_KG_weight"]
                                            if booking_line["e_Total_KG_weight"]
                                            is not None
                                            else 0
                                        )
                                    ),
                                    style_center,
                                ),
                                Paragraph(
                                    "<font size=10><b>%s</b></font>"
                                    % str(
                                        "{0:.2f}".format(
                                            booking_line["e_1_Total_dimCubicMeter"]
                                            if booking_line["e_1_Total_dimCubicMeter"]
                                            is not None
                                            else 0
                                        )
                                    ),
                                    style_center,
                                ),
                                Paragraph(
                                    "<font size=8>%s</font>" % barcode, style_center
                                ),
                            ],
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(90, 90, 220),
                            rowHeights=10,
                            hAlign="LEFT",
                        )
                        tbl.setStyle(
                            [
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ]
                        )
                        Story.append(tbl)

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=8>Client Item Reference: </font>",
                                    styles["Normal"],
                                ),
                                Paragraph(
                                    "<font size=8><b>%s</b></font>"
                                    % booking_line["client_item_reference"],
                                    style_left,
                                ),
                            ]
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(80, 140),
                            rowHeights=(20),
                            hAlign="LEFT",
                            style=[
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(tbl)
                        Story.append(PageBreak())

                        j = j + 1

                i = i + 1
                doc.build(Story)
                # end writting data into pdf file
                
                sql2 = "UPDATE dme_bookings \
                    SET z_label_url = %s \
                    WHERE pk_booking_id = %s"
                adr2 = ("tas_au/" + filename, booking["pk_booking_id"])
                mycursor.execute(sql2, adr2)
                mysqlcon.commit()
                file.close()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info(f"#505 Error: - {e}")
    elif vx_freight_provider.upper() == "DHL":
        try:
            bookings = get_available_bookings(booking_ids)

            # start check if pdfs folder exists
            if production:
                local_filepath = "/opt/s3_public/pdfs/dhl_au/"
                local_filepath_dup = (
                    "/opt/s3_public/pdfs/dhl_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )
            else:
                local_filepath = "./static/pdfs/dhl_au/"
                local_filepath_dup = (
                    "./static/pdfs/dhl_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )

            if not os.path.exists(local_filepath):
                os.makedirs(local_filepath)
            # end check if pdfs folder exists

            # start loop through data fetched from dme_bookings table
            i = 1
            for booking in bookings:
                booking_lines = get_available_booking_lines(booking)

                totalQty = 0
                for booking_line in booking_lines:
                    totalQty = totalQty + booking_line["e_qty"]

                # start pdf file name using naming convention
                filename = (
                    booking["pu_Address_State"]
                    + "_"
                    + str(booking["b_client_sales_inv_num"])
                    + "_"
                    + str(booking["v_FPBookingNumber"])
                    + "_"
                    + "DME"
                    + str(booking["b_bookingID_Visual"])
                    + ".pdf"
                )
                file = open(local_filepath + filename, "w")
                # end pdf file name using naming convention

                date = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
                doc = SimpleDocTemplate(
                    local_filepath + filename,
                    pagesize=(6 * inch, 4 * inch),
                    rightMargin=10,
                    leftMargin=10,
                    topMargin=10,
                    bottomMargin=10,
                )
                Story = []

                fp_info = Fp_freight_providers.objects.get(fp_company_name="DHL")
                fp_zone = FP_zones.objects.filter(
                    fk_fp=fp_info.id,
                    state=booking["de_To_Address_State"],
                    suburb=booking["de_To_Address_Suburb"],
                    postal_code=booking["de_To_Address_PostalCode"],
                ).first()

                j = 1
                for booking_line in booking_lines:
                    for k in range(booking_line["e_qty"]):
                        tbl_data = [
                            [
                                Paragraph("<font size=6>From:</font>", style_left),
                                Paragraph(
                                    "<font size=6>%s</font>" % booking["puCompany"],
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph("<font size=6>Telephone:</font>", style_left),
                                Paragraph(
                                    "<font size=6>%s</font>" % booking["pu_Phone_Main"],
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph("<font size=6>Service:</font>", style_left),
                                Paragraph(
                                    "<font size=6>%s</font>" % fp_zone.service,
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph("<font size=6>Via:</font>", style_left),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["vx_freight_provider_carrier"],
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph("<font size=6>C/note:</font>", style_left),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["v_FPBookingNumber"],
                                    styles["BodyText"],
                                ),
                            ],
                            [
                                Paragraph(
                                    "<font size=6>Deliver To:</font>", style_left
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_to_Contact_F_LName"],
                                    styles["BodyText"],
                                ),
                            ],
                        ]
                        t1 = Table(
                            tbl_data,
                            colWidths=(40, 120),
                            rowHeights=(12),
                            hAlign="LEFT",
                            style=[
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=6>Item:&nbsp;&nbsp; %s - Of - %s</font>"
                                    % (j, totalQty),
                                    style_right,
                                ),
                                Paragraph(
                                    "<font size=6>Date:&nbsp;&nbsp; %s</font>"
                                    % booking["b_dateBookedDate"].strftime("%d/%m/%Y"),
                                    style_left,
                                ),
                            ],
                            [
                                Paragraph(
                                    "<font size=6>Reference No:</font>", style_right
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking_line["client_item_reference"],
                                    style_left,
                                ),
                            ],
                            [""],
                            [""],
                            [""],
                            [""],
                        ]
                        t2 = Table(
                            tbl_data,
                            colWidths=(55, 120),
                            rowHeights=(12),
                            hAlign="LEFT",
                            style=[],
                        )

                        barcode = (
                            booking["v_FPBookingNumber"]
                            + booking["v_FPBookingNumber"][0:3]
                            + "L"
                            + "00"
                            + str(
                                int(booking["v_FPBookingNumber"][3:])
                                - 100000
                                + 10000000
                            )
                            + booking["de_To_Address_PostalCode"]
                        )
                        barcode128 = code128.Code128(
                            barcode, barHeight=30 * mm, barWidth=1.3
                        )

                        tbl_data = [
                            [Paragraph("<font size=6> </font>", style_left)],
                            [get_barcode_rotated(barcode, 3 * inch)],
                        ]
                        t3 = Table(
                            tbl_data,
                            colWidths=(120),
                            rowHeights=(12, 65),
                            hAlign="LEFT",
                            style=[("VALIGN", (0, 0), (0, -1), "TOP")],
                        )

                        data = [[t1, t2, t3]]
                        # adjust the length of tables
                        t1_w = 1.6 * inch
                        t2_w = 1.9 * inch
                        t3_w = 1.1 * inch
                        shell_table = Table(
                            data,
                            colWidths=[t1_w, t2_w, t3_w],
                            style=[
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(shell_table)

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=7>%s</font>"
                                    % booking["de_to_Contact_F_LName"],
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=7>%s</font>"
                                    % booking["de_to_Phone_Main"],
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=7>%s</font>"
                                    % booking["de_To_Address_Street_1"],
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=7><b>%s</b></font> "
                                    % (booking["de_To_Address_Suburb"]),
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=7>%s %s</font> "
                                    % (
                                        booking["de_To_Address_State"],
                                        booking["de_To_Address_PostalCode"],
                                    ),
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=6>C/note: %s</font> "
                                    % (booking["v_FPBookingNumber"]),
                                    style_left,
                                )
                            ],
                            [
                                Paragraph(
                                    "<font size=6>Total Items %s</font> "
                                    % str(totalQty).zfill(4),
                                    style_left,
                                )
                            ],
                        ]
                        t1 = Table(
                            tbl_data,
                            colWidths=(165),
                            rowHeights=([13, 10, 10, 10, 10, 10, 10]),
                            hAlign="LEFT",
                            style=[
                                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                                ("TOPPADDING", (0, 0), (-1, -1), 5),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                            ],
                        )

                        tbl_data = [
                            [
                                Paragraph(
                                    '<font size=10 color="white">S01</font>', style_left
                                )
                            ]
                        ]
                        t2 = Table(
                            tbl_data,
                            colWidths=(30),
                            rowHeights=(30),
                            hAlign="CENTER",
                            vAlign="MIDDLE",
                            style=[
                                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                                ("VALIGN", (0, 0), (0, -1), "MIDDLE"),
                            ],
                        )

                        tbl_data = [[""]]
                        t3 = Table(
                            tbl_data,
                            colWidths=(250),
                            style=[("VALIGN", (0, 0), (0, -1), "TOP")],
                        )

                        data = [[t1, t2, t3]]
                        # adjust the length of tables
                        t1_w = 2.5 * inch
                        t2_w = 1 * inch
                        t3_w = 1.1 * inch
                        shell_table = Table(
                            data,
                            colWidths=[t1_w, t2_w, t3_w],
                            style=[
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(shell_table)

                        Story.append(Spacer(1, 5))

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=6>Special Inst:</font>", style_left
                                ),
                                Paragraph(
                                    "<font size=6>%s %s</font>"
                                    % (
                                        str(
                                            booking["de_to_PickUp_Instructions_Address"]
                                        )
                                        if booking["de_to_PickUp_Instructions_Address"]
                                        else "",
                                        str(
                                            booking[
                                                "de_to_Pick_Up_Instructions_Contact"
                                            ]
                                        )
                                        if booking["de_to_Pick_Up_Instructions_Contact"]
                                        else "",
                                    ),
                                    style_left,
                                ),
                            ],
                            [""],
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(45, 350),
                            rowHeights=(14),
                            hAlign="LEFT",
                            style=[
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ],
                        )
                        Story.append(tbl)
                        Story.append(PageBreak())

                        j += 1
                i += 1
                doc.build(Story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)

                sql2 = "UPDATE dme_bookings \
                    SET z_label_url = %s \
                    WHERE pk_booking_id = %s"
                adr2 = ("dhl_au/" + filename, booking["pk_booking_id"])
                mycursor.execute(sql2, adr2)
                mysqlcon.commit()

                file.close()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info(f"#506 Error: - {e}")
    mysqlcon.close()
    return i - 1
