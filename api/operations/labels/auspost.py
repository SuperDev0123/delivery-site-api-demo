import os
import math
from datetime import datetime
import pandas as pd
import logging
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
    Table,
    NextPageTemplate,
    Frame,
    PageTemplate,
    TableStyle,
)
from reportlab.platypus.flowables import Image, Spacer, HRFlowable, PageBreak, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code39, code128, code93, qrencoder
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.graphics.barcode import createBarcodeDrawing

from api.models import Booking_lines, FPRouting, FP_zones, Fp_freight_providers
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.constants import FP_CREDENTIALS
from api.operations.api_booking_confirmation_lines import index as api_bcl

logger = logging.getLogger(__name__)

styles = getSampleStyleSheet()
style_right = ParagraphStyle(
    name="right",
    parent=styles["Normal"],
    alignment=TA_RIGHT,
    leading=18,
    fontSize=18,
)
style_left = ParagraphStyle(
    name="left",
    parent=styles["Normal"],
    alignment=TA_LEFT,
    leading=10,
    fontSize=8,
)
style_left_large = ParagraphStyle(
    name="left",
    parent=styles["Normal"],
    alignment=TA_LEFT,
    leading=15,
    fontSize=10,
)
style_extra_large = ParagraphStyle(
    name="left",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    leading=18,
    fontSize=18,
)
style_left_small = ParagraphStyle(
    name="left",
    parent=styles["Normal"],
    alignment=TA_LEFT,
    leading=8,
    fontSize=8,
)
style_center = ParagraphStyle(
    name="center",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    leading=12,
    fontSize=8,
)
style_center_bg = ParagraphStyle(
    name="right",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    leading=16,
    backColor="#64a1fc",
)
style_uppercase = ParagraphStyle(
    name="uppercase",
    parent=styles["Normal"],
    alignment=TA_LEFT,
    leading=9,
    spaceBefore=0,
    spaceAfter=0,
    textTransform="uppercase",
)
style_back_black = ParagraphStyle(
    name="back_black",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    leading=14,
    backColor="black",
)
style_PRD = ParagraphStyle(
    name="PRD",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    fontSize=25,
    leading=25,
    backColor="#D51827",
    color="white",
)

tableStyle = [
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
]

styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY))


def myFirstPage(canvas, doc):
    canvas.saveState()
    canvas.rotate(180)
    canvas.restoreState()


def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.rotate(90)
    canvas.restoreState()

def gen_QRcodeString(
    booking,
    booking_line,
    v_FPBookingNumber,
    totalCubic,
    atl_number,
    item_no=0,
):
    item_index = str(item_no).zfill(5)
    receiver_suburb = str(booking.de_To_Address_Suburb).ljust(30)
    postal_code = str(booking.de_To_Address_PostalCode).ljust(4)
    consignment_num = str(v_FPBookingNumber).ljust(12)
    product_code = str(booking.vx_serviceName)
    freight_item_id = consignment_num + product_code + item_index
    payer_account = str("").ljust(8)
    sender_account = (
        FP_CREDENTIALS["startrack"][booking.b_client_name.lower()][
            booking.b_client_warehouse_code
        ]["accountCode"]
    ).ljust(8)
    consignment_quantity = str(booking_line.e_qty).ljust(4)
    consignment_weight = str(math.ceil(booking_line.e_Total_KG_weight)).ljust(5)
    consignment_cube = str(number_format(round(totalCubic, 3))).ljust(5)
    if booking.b_dateBookedDate:
        despatch_date = booking.b_dateBookedDate.strftime("%Y%m%d")
    else:
        despatch_date = booking.puPickUpAvailFrom_Date.strftime("%Y%m%d")
    receiver_name1 = str(booking.de_to_Contact_F_LName or "").ljust(40)
    receiver_name2 = str(
        ""
        if booking.deToCompanyName == booking.de_to_Contact_F_LName
        else (booking.deToCompanyName or "")
    ).ljust(40)
    unit_type = str(
        "CTN"
        if len(booking_line.e_type_of_packaging or "") != 3
        else booking_line.e_type_of_packaging
    )
    destination_depot = str("R2").ljust(4)
    receiver_address1 = str(booking.de_To_Address_Street_1).ljust(40)
    receiver_address2 = str("").ljust(40)
    receiver_phone = str(booking.de_to_Phone_Main).ljust(14)
    dangerous_goods_indicator = "Y" if booking_line.e_dangerousGoods == True else "N"
    movement_type_indicator = "N"
    not_before_date = str("").ljust(12)
    not_after_date = str("").ljust(12)
    atl_number = str(atl_number).ljust(10)
    rl_number = str("").ljust(10)

    label_code = f"019931265099999891T77000126101000600209420300092476093648008140123142938"
    logger.info(label_code)
    return label_code


def number_format(num):
    return str(round(num * 1000))


def gen_Barcode(booking, item_no=0):
    item_index = str(item_no).zfill(5)

    label_code = f"0199312650999998911JDQ019457101000930308 "

    return label_code


def get_serviceName(temp):
    return "Express" if temp == "EXP" else "Parcel"


def get_ATL_number(booking):
    freight_provider = Fp_freight_providers.objects.filter(
        fp_company_name=booking.vx_freight_provider
    )
    last_atl_number = freight_provider.first().last_atl_number
    freight_provider.update(last_atl_number=last_atl_number + 1)
    return f"C{str(freight_provider.first().last_atl_number).zfill(9)}"


def build_label(
    booking, filepath, lines, label_index, sscc, sscc_cnt=1, one_page_label=True
):
    logger.info(
        f"#110 [{booking.vx_freight_provider} LABEL] Started building label... (Booking ID: {booking.b_bookingID_Visual}, Lines: {lines})"
    )
    v_FPBookingNumber = booking.v_FPBookingNumber

    # start check if pdfs folder exists
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    # end check if pdfs folder exists

    fp_id = Fp_freight_providers.objects.get(
        fp_company_name=booking.vx_freight_provider
    ).id
    try:
        carrier = FP_zones.objects.get(
            state=booking.de_To_Address_State,
            suburb=booking.de_To_Address_Suburb,
            postal_code=booking.de_To_Address_PostalCode,
            fk_fp=fp_id,
        ).carrier
    except FP_zones.DoesNotExist:
        carrier = ""
    except Exception as e:
        logger.info(f"#110 [{booking.vx_freight_provider} LABEL] Error: {str(e)}")

    # start pdf file name using naming convention
    if lines:
        if sscc:
            filename = (
                booking.pu_Address_State
                + "_"
                + str(booking.b_bookingID_Visual)
                + "_"
                + str(sscc)
                + ".pdf"
            )
        else:
            filename = (
                booking.pu_Address_State
                + "_"
                + str(booking.b_bookingID_Visual)
                + "_"
                + str(lines[0].pk)
                + ".pdf"
            )
    else:
        filename = (
            booking.pu_Address_State
            + "_"
            + v_FPBookingNumber
            + "_"
            + str(booking.b_bookingID_Visual)
            + ".pdf"
        )

    file = open(f"{filepath}/{filename}", "w")
    logger.info(
        f"#111 [{booking.vx_freight_provider} LABEL] File full path: {filepath}/{filename}"
    )
    # end pdf file name using naming convention

    if not lines:
        lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    # label_settings = get_label_settings( 146, 104 )[0]
    label_settings = {
        "font_family": "Arial",
        "font_size_extra_small": "4",
        "font_size_small": "6",
        "font_size_medium": "8",
        "font_size_large": "10",
        "font_size_extra_large": "12",
        "label_dimension_length": "150",
        "label_dimension_width": "100",
        "label_image_size_length": "143",
        "label_image_size_width": "93",
        "header_length": "16",
        "fp_logo_width": "10",
        "fp_logo_length": "10",
        "barcode_dimension_length": "85",
        "barcode_dimension_width": "30",
        "barcode_font_size": "18",
        "qrcode_length": "22",
        "line_height_extra_small": "3",
        "line_height_small": "5",
        "line_height_medium": "6",
        "line_height_large": "8",
        "line_height_extra_large": "12",
        "margin_v": "3.5",
        "margin_h": "3.5",
    }

    width = float(label_settings["label_dimension_width"]) * mm
    height = float(label_settings["label_dimension_length"]) * mm
    doc = SimpleDocTemplate(
        f"{filepath}/{filename}",
        pagesize=(width, height),
        rightMargin=float(label_settings["margin_h"]) * mm,
        leftMargin=float(label_settings["margin_h"]) * mm,
        topMargin=float(label_settings["margin_v"]) * mm,
        bottomMargin=float(label_settings["margin_v"]) * mm,
    )

    dme_logo = "./static/assets/logos/dme.png"
    dme_img = Image(dme_logo, 28 * mm, 7.7 * mm)

    fp_logo = "./static/assets/logos/auspost.png"
    fp_img = Image(
        fp_logo,
        float(label_settings['fp_logo_width']) * mm,
        float(label_settings['fp_logo_length']) * mm,
    )

    fp_color_code = (
        Fp_freight_providers.objects.get(
            fp_company_name=booking.vx_freight_provider
        ).hex_color_code
        or "808080"
    )

    style_center_bg = ParagraphStyle(
        name="right",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        leading=16,
        backColor=f"#{fp_color_code}",
    )

    Story = []
    j = 1

    totalQty = sscc_cnt
    totalQty = 0
    for booking_line in lines:
        totalQty = totalQty + booking_line.e_qty

    totalWeight = 0
    totalCubic = 0
    for booking_line in lines:
        totalWeight = totalWeight + booking_line.e_qty * booking_line.e_weightPerEach
        totalCubic = totalCubic + get_cubic_meter(
            booking_line.e_dimLength,
            booking_line.e_dimWidth,
            booking_line.e_dimHeight,
            booking_line.e_dimUOM,
            booking_line.e_qty,
        )

    if sscc:
        j = 1 + label_index

    for booking_line in lines:
        for k in range(booking_line.e_qty):
            atl_number = get_ATL_number(booking)
            if one_page_label and k > 0:
                continue
            t1_w = float(label_settings["label_image_size_width"]) / 10 * mm
            locations = pd.read_excel(
                "./static/assets/xlsx/startrack_rt1_rt2_LOCATION-20210606.xls"
            )

            prd_data = Table(
                [
                    [
                        fp_img,
                        Spacer(2,2),
                        Paragraph(
                            "<font color='%s'><b>%s Post</b></font>" %(colors.white, get_serviceName(booking)),
                            style_PRD,
                        )
                    ]
                ],
                colWidths=[float(label_settings['fp_logo_width']) * mm, 2 * mm, (float(label_settings["label_image_size_width"]) - float(label_settings['fp_logo_width']) - 2) * mm],
                rowHeights=[float(label_settings['fp_logo_length']) * mm],
                style=[
                    *tableStyle,
                    ("BACKGROUND", (2, 0), (2, 0), "#D51827"),
                ],
            )
            Story.append(prd_data)


            table = Table(
                [
                    [
                        Spacer(2,2)
                    ],
                    [
                        Paragraph("<b>TO: </b>", style_left_large)
                    ]
                ],
                colWidths=[t1_w * 10],
                style=tableStyle,
            )
            Story.append(table)

            infoTable = Table([
                [
                    Table(
                        [
                            [
                                Paragraph(
                                    "%s %s %s %s %s %s %s" % (
                                        ((booking.de_to_Contact_F_LName + "<br></br>") if booking.de_to_Contact_F_LName else ""),
                                        ((booking.deToCompanyName + "<br></br>") if booking.de_to_Contact_F_LName != booking.deToCompanyName else ""),
                                        ((booking.de_To_Address_Street_1 + "<br></br>") if booking.de_To_Address_Street_1 else ""),
                                        ((booking.de_To_Address_Street_2 + "<br></br>") if booking.de_To_Address_Street_2 else ""),
                                        booking.de_To_Address_State or "",
                                        booking.de_To_Address_Suburb or "",
                                        booking.de_To_Address_PostalCode or "",
                                    ),
                                    style_left),
                            ],
                            [
                                "",
                            ],
                            [
                                Paragraph("PH : %s" % (booking.de_to_Phone_Main), style_left),
                            ],
                            [
                                Table([
                                        [
                                                Paragraph("Dead Weight", style_left),
                                                Paragraph("Delivery features", style_left),
                                        ],
                                        [
                                                Paragraph("%skg" % (booking_line.e_Total_KG_weight), style_extra_large),
                                                "",
                                        ],
                                    ],
                                    colWidths=[t1_w * 2.5, t1_w * 5],
                                    rowHeights=[10,24],
                                    style=[
                                        *tableStyle,
                                        ("LINEBEFORE", (1, 0), (1, -1), 2, "#E5DBCB"),
                                        ("LINEAFTER", (0, 0), (0, -1), 2, "#E5DBCB"),
                                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                                    ]
                                )
                            ]                            
                        ],
                        colWidths=[t1_w * 7.5],
                        rowHeights=[25 * mm, 13 * mm, 5 * mm, 13 * mm],
                        style=[
                            *tableStyle,
                            ("INNERGRID", (0, 0), (-1, -1), 2, "#E5DBCB"),
                            ("BOX", (0, 0), (-1, -1), 2, "#E5DBCB"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ],
                    )
                ],
                [
                    Table([
                            [
                                " ",
                                Paragraph("Cons No: %s" % (str(v_FPBookingNumber or " ")), style_left)
                            ],
                            [
                                Paragraph("<b>FROM:</b>", style_left),
                                Paragraph("Parcel: %s of %s" % (j, totalQty), style_left)
                            ]
                        ],
                        rowHeights=[10, 12],
                        style=[
                            *tableStyle,
                        ],
                    )
                ],
                [
                    Table(
                        [
                            [
                                Paragraph(
                                    "%s %s %s %s %s %s" % (
                                        ((booking.puCompany + "<br></br>") if booking.puCompany else ""),
                                        booking.pu_Address_Street_1,
                                        (booking.pu_Address_street_2 if booking.pu_Address_Street_1 != booking.pu_Address_street_2 else "") + "<br></br>",
                                        booking.de_To_Address_State or "",
                                        booking.de_To_Address_Suburb or "",
                                        booking.de_To_Address_PostalCode or "",
                                    ),
                                    style_left),
                            ],
                            [
                                Paragraph("<font color='#D51827'>Aviation Security and Dangerous Goods Declaration</font>", style_left),
                            ],
                            [
                                Paragraph(" ", style_left),
                            ],
                            [
                                Paragraph("%s %s" % (
                                        booking.b_clientReference_RA_Numbers,
                                        booking.b_dateBookedDate.strftime(
                                            "%d-%b-%Y"
                                        )
                                        if booking.b_dateBookedDate
                                        else booking.puPickUpAvailFrom_Date.strftime(
                                            "%d-%b-%Y"
                                        ),
                                    ), style_left)
                            ],
                            [
                                Paragraph(" ", style_left)
                            ]                            
                        ],
                        colWidths=[t1_w * 7.5],
                        rowHeights=[25 * mm, 4 * mm, 14 * mm, 8 * mm, 8 * mm],
                        style=[
                            *tableStyle,
                            ("INNERGRID", (0, 0), (-1, -1), 2, "#E5DBCB"),
                            ("BOX", (0, 0), (-1, -1), 2, "#E5DBCB"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("SPAN", (0, 1), (0, 2)),
                        ],
                    )
                ]
            ],
            style=tableStyle
            )
             

            barcode = gen_Barcode(booking)

            barcodeD = Drawing(100 * mm, 20 * mm)
            barcodeD.add(Rect(0, 0, 0, 0, strokeWidth=1, fillColor=colors.red))
            barcode_graphic = createBarcodeDrawing(
                "Code128",
                value=barcode,
                format='png',
                width=100 * mm,
                height=20 * mm,
                humanReadable=False,
            )            
            barcode_graphic.transform = [1.25,0,0,2,-70,10]
            barcodeD.add(
                barcode_graphic
            )
            barcodeD.add(String(-10, 1, barcode, fontSize=7, fillColor=colors.black))
            barcodeD.add(String(150, 1, datetime.now().strftime("%m%d"), fontSize=7, fillColor=colors.black))
            barcodeD.rotate(-90)
            
            qrCodeString = gen_QRcodeString(
                booking,
                booking_line,
                v_FPBookingNumber,
                totalCubic,
                atl_number,
                j,
            )
            qrD = Drawing(float(label_settings["qrcode_length"]) * mm, float(label_settings["qrcode_length"]) * mm)
            qrD.add(Rect(0, 0, 0, 0, strokeWidth=1, fillColor=None))
            qrD.add(QrCodeWidget(value=qrCodeString, barWidth=float(label_settings["qrcode_length"]) * mm, barHeight=float(label_settings["qrcode_length"]) * mm))
            markD = Drawing(20 * mm, 10 * mm)
            markD.add(Rect(0, 0, 0, 0, strokeWidth=1, fillColor=None))
            markD.add(String(10,2, "Powered by", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.black))
            markD.add(String(10,-10, "eParcel", fontName="Helvetica", fontSize=12, fillColor=colors.black))
            markD.add(String(53,-5, "TM", fontName="Helvetica-Bold", fontSize=5, fillColor=colors.black))
            tbl_data = [
                [
                    Table(
                        [
                            [
                                Paragraph("<b>Postage Paid</b>", style_left_small)
                            ],
                            [
                                qrD,
                            ],
                            [
                                barcodeD
                            ],
                            [
                                markD
                            ]
                        ],
                        rowHeights=[10, 25 * mm, 76 * mm, 5 * mm],
                        style=[
                            *tableStyle,
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("LEFTPADDING", (0, 0), (0, 0), 10),
                            ("LEFTPADDING", (0, 1), (0, 1), 5),
                        ],
                    ),
                ],
            ]

            rightBar = Table(
                tbl_data,
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ],
            )

            mainTable = Table(
                [
                    [
                        infoTable,
                        rightBar,
                    ]
                ],
                colWidths=[t1_w * 7.5, t1_w * 2.5],
                style=tableStyle,
            )
            Story.append(mainTable)
            

            Story.append(PageBreak())

            j += 1

    doc.build(Story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)
    file.close()
    logger.info(
        f"#119 [{booking.vx_freight_provider} LABEL] Finished building label... (Booking ID: {booking.b_bookingID_Visual})"
    )
    return filepath, filename
