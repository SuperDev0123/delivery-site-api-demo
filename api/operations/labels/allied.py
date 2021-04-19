import os
import datetime
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
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.graphics.barcode import createBarcodeDrawing

from api.models import Booking_lines, FPRouting
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.utils import gen_consignment_num

logger = logging.getLogger("dme_api")

styles = getSampleStyleSheet()
style_right = ParagraphStyle(name="right", parent=styles["Normal"], alignment=TA_RIGHT)
style_left = ParagraphStyle(
    name="left",
    parent=styles["Normal"],
    alignment=TA_LEFT,
    leading=10,
    spaceBefore=0,
)
style_center = ParagraphStyle(
    name="center",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    leading=10,
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
    alignment=TA_LEFT,
    leading=12,
    backColor="black",
    spaceAfter=10,
)

styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY))


def myFirstPage(canvas, doc):
    canvas.saveState()
    canvas.rotate(180)
    canvas.restoreState()


def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.rotate(90)
    canvas.restoreState()


def gen_barcode(booking, booking_lines, line_index=0, label_index=0):
    TT = 11
    CCCCCC = "132214"  # DME
    item_index = str(label_index + line_index + 1).zfill(3)
    postal_code = str(booking.de_To_Address_PostalCode)

    return f"6104{TT}{CCCCCC}{str(booking.b_bookingID_Visual).zfill(9)}{item_index}{postal_code.zfill(5)}0"


def build_label(booking, filepath, lines=[], label_index=0):
    logger.info(
        f"#110 [ALLIED LABEL] Started building label... (Booking ID: {booking.b_bookingID_Visual}, Lines: {lines})"
    )
    v_FPBookingNumber = gen_consignment_num(
        booking.vx_freight_provider, booking.b_bookingID_Visual
    )

    # start check if pdfs folder exists
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    # end check if pdfs folder exists

    # start pdf file name using naming convention
    if lines:
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
    logger.info(f"#111 [ALLIED LABEL] File full path: {filepath}/{filename}")
    # end pdf file name using naming convention

    if not lines:
        lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    totalQty = 0
    for booking_line in lines:
        totalQty = totalQty + booking_line.e_qty

    # label_settings = get_label_settings( 146, 104 )[0]
    label_settings = {
        "font_family": "Verdana",
        "font_size_extra_small": "4",
        "font_size_small": "6",
        "font_size_normal": "7",
        "font_size_medium": "8",
        "font_size_large": "10",
        "font_size_extra_large": "13",
        "label_dimension_length": "100",
        "label_dimension_width": "160",
        "label_image_size_length": "85",
        "label_image_size_width": "130",
        "barcode_dimension_height": "33",
        "barcode_dimension_width": "0.75",
        "barcode_font_size": "18",
        "line_height_extra_small": "3",
        "line_height_small": "5",
        "line_height_medium": "6",
        "line_height_large": "8",
        "line_height_extra_large": "12",
        "margin_v": "2",
        "margin_h": "0",
    }

    width = float(label_settings["label_dimension_length"]) * mm
    height = float(label_settings["label_dimension_width"]) * mm
    doc = SimpleDocTemplate(
        f"{filepath}/{filename}",
        pagesize=(width, height),
        rightMargin=float(label_settings["margin_h"]) * mm,
        leftMargin=float(label_settings["margin_h"]) * mm,
        topMargin=float(label_settings["margin_v"]) * mm,
        bottomMargin=float(label_settings["margin_v"]) * mm,
    )

    tnt_logo = "./static/assets/tnt_fedex_logo.png"
    tnt_img = Image(tnt_logo, 30 * mm, 6.6 * mm)

    dme_logo = "./static/assets/dme_logo.png"
    dme_img = Image(dme_logo, 30 * mm, 7.7 * mm)

    Story = []
    j = 1

    totalQty = 0
    totalWeight = 0
    totalCubic = 0
    for booking_line in lines:
        totalQty = totalQty + booking_line.e_qty
        totalWeight = totalWeight + booking_line.e_Total_KG_weight
        totalCubic = totalCubic + booking_line.e_1_Total_dimCubicMeter

    for booking_line in lines:
        for k in range(booking_line.e_qty):
            tbl_data = [
                [
                    Paragraph(
                        "<font size=%s>From: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.puCompany or "",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s>P/U Phone: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.pu_Phone_Main or "",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s>Date: %s</font>"
                        % (label_settings["font_size_medium"], "date"),
                        style_left,
                    ),
                ]
            ]

            shell_table = Table(
                tbl_data,
                colWidths=(
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                ),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (0, -1), "TOP"),
                ],
            )

            Story.append(shell_table)

            tbl_data = [
                [
                    Paragraph(
                        "<font size=%s>Contact: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.de_to_Contact_F_LName or "",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s>Phone: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.de_to_Phone_Main or "",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s>Package: %s of %s</font>"
                        % (label_settings["font_size_medium"], j, totalQty),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s>Parcel ID: <b>%s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.v_FPBookingNumber or "",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s>Order Ref: %s</font>"
                        % (label_settings["font_size_medium"], ""),
                        style_left,
                    ),
                ],
            ]

            shell_table = Table(
                tbl_data,
                colWidths=(
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                ),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (0, -1), "TOP"),
                ],
            )
            Story.append(shell_table)

            Story.append(Spacer(1, 2))

            # barcode = gen_barcode(booking, lines, j - 1, label_index)
            barcode = (
                booking.v_FPBookingNumber
                + "DESC"
                + str(j + 1).zfill(10)
                + booking.de_To_Address_PostalCode
            )

            tbl_data = [
                [
                    code128.Code128(
                        barcode,
                        barHeight=15 * mm,
                        barWidth=0.7,
                        humanReadable=False,
                    )
                ],
            ]

            barcode_table = Table(
                tbl_data,
                colWidths=((float(label_settings["label_image_size_length"])) * mm),
                style=[
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (0, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (0, -1), 0),
                    ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ],
            )

            Story.append(barcode_table)

            tbl_parcelId = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.v_FPBookingNumber or "",
                        ),
                        style_left,
                    ),
                ],
            ]

            tbl_data2 = [
                [
                    Paragraph(
                        "<font size=%s>Service: </font>"
                        % (label_settings["font_size_medium"]),
                        style_left,
                    ),
                    Paragraph(
                        '<font size=%s color="white"><b>&nbsp;&nbsp;%s</b> </font>'
                        % (
                            label_settings["font_size_extra_large"],
                            booking.vx_serviceName or "ROAD",
                        ),
                        style_back_black,
                    ),
                ],
            ]

            tbl_service = Table(
                tbl_data2,
                colWidths=(
                    45,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm
                    - 45,
                ),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ],
            )

            tbl_package = [
                [
                    Paragraph(
                        "<font size=%s>Package: %s of %s</font>"
                        % (label_settings["font_size_medium"], j, totalQty),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s>Weight: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking_line.e_Total_KG_weight or "",
                        ),
                        style_left,
                    ),
                ],
            ]

            data = [[tbl_parcelId, tbl_service, tbl_package]]
            shell_table = Table(
                data,
                colWidths=(
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                ),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ],
            )

            Story.append(shell_table)

            Story.append(Spacer(1, 5))

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s>To: <br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.de_To_Address_Street_1 or "",
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.de_To_Address_Street_2 or "",
                        ),
                        style_left,
                    )
                ],
            ]

            shell_table = Table(
                tbl_data1,
                colWidths=(float(label_settings["label_image_size_length"]) * mm),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ],
            )

            Story.append(shell_table)

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["line_height_extra_large"],
                            booking.de_To_Address_State or "",
                        ),
                        style_left,
                    ),
                ]
            ]

            tbl_data2 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["line_height_extra_large"],
                            booking.de_To_Address_Suburb or "",
                        ),
                        style_left,
                    ),
                ]
            ]

            tbl_data3 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["line_height_extra_large"],
                            booking.de_To_Address_PostalCode or "",
                        ),
                        style_left,
                    ),
                ]
            ]

            data = [[tbl_data1, tbl_data2, tbl_data3]]

            t1_w = float(label_settings["label_image_size_length"]) * (1 / 6) * mm
            t2_w = float(label_settings["label_image_size_length"]) * (1 / 4) * mm
            t3_w = float(label_settings["label_image_size_length"]) * (1 / 12) * mm

            shell_table = Table(
                data,
                colWidths=[t1_w, t2_w, t3_w],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ],
            )

            tbl_data2 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["line_height_extra_large"],
                            "PORT MELBORUNE",
                        ),
                        style_left,
                    ),
                ],
                [Spacer(1, 10)],
                [shell_table],
            ]

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s>&nbsp;&nbsp;&nbsp;&nbsp; %s x %s x %s = %s </font>"
                        % (
                            label_settings["font_size_medium"],
                            booking_line.e_dimWidth or "",
                            booking_line.e_dimHeight or "",
                            booking_line.e_dimLength or "",
                            booking_line.e_1_Total_dimCubicMeter or "",
                        ),
                        style_left,
                    )
                ]
            ]

            data = [[tbl_data1, tbl_data2]]

            t1_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm
            t2_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm

            shell_table = Table(
                data,
                colWidths=(t1_w, t2_w),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (0, -1), "TOP"),
                ],
            )

            Story.append(shell_table)

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s><b>Dangerous Goods Enclosed: %s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            "YES" if booking_line.e_dangerousGoods == True else "NO",
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>Instruction: %s</font>"
                        % (label_settings["font_size_medium"], ""),
                        style_left,
                    )
                ],
            ]

            shell_table = Table(
                tbl_data1,
                colWidths=(float(label_settings["label_image_size_length"]) * mm),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ],
            )

            Story.append(shell_table)

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s>Reference: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.b_clientReference_RA_Numbers or "",
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s>Other Reference: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.b_clientReference_RA_Numbers or "",
                        ),
                        style_left,
                    ),
                ],
            ]

            t1 = Table(
                tbl_data1,
                colWidths=(float(label_settings["label_image_size_length"]) * mm),
                rowHeights=(float(label_settings["line_height_extra_small"]) * mm),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (0, -1), "BOTTOM"),
                ],
            )

            data = [[t1]]

            t_w = float(label_settings["label_image_size_length"]) * mm

            shell_table = Table(
                data,
                colWidths=[t_w],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMBORDER", (0, 0), (-1, -1), 0),
                ],
            )

            Story.append(shell_table)

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s>Account: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.vx_account_code or "TEST",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s>Date: %s</font>"
                        % (label_settings["font_size_medium"], "date"),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s><b>Date %s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            "&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;",
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>Name %s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            "&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s><b>Signature %s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            "&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;",
                        ),
                        style_left,
                    ),
                    Paragraph(
                        "<font size=%s><b>Time %s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            "&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;&#95;",
                        ),
                        style_left,
                    ),
                ],
            ]

            signature_table = Table(
                tbl_data1,
                colWidths=(
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                    float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                ),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (0, -1), "BOTTOM"),
                ],
            )

            Story.append(signature_table)
            Story.append(Spacer(1, 2))

            hr = HRFlowable(
                width=(float(label_settings["label_image_size_length"]) * mm),
                thickness=1,
                lineCap="square",
                color=colors.black,
                spaceBefore=1,
                spaceAfter=1,
                vAlign="BOTTOM",
                dash=None,
            )
            Story.append(hr)

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s>%s</font>"
                        % (
                            label_settings["font_size_small"],
                            "RECEIVED IN GOOD CONDITION. SUBJECT TO CARRIER TERMS AND CONDITIONS.",
                        ),
                        style_center,
                    )
                ],
            ]

            footer_table = Table(
                tbl_data1,
                colWidths=(float(label_settings["label_image_size_length"]) * mm),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ],
            )

            Story.append(footer_table)
            Story.append(PageBreak())

            j += 1

    doc.build(Story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)
    file.close()
    logger.info(
        f"#119 [ALLIED LABEL] Finished building label... (Booking ID: {booking.b_bookingID_Visual})"
    )
    return filepath, filename
