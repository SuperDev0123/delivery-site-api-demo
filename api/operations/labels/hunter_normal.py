# Python 3.6.6

import pysftp

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None
import sys, time
import os, base64
import errno
import datetime
import uuid
import redis
import urllib, requests
import pymysql, pymysql.cursors
import json
import logging
import time

from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter, landscape, A6, A4
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
from reportlab.platypus.flowables import Spacer, HRFlowable, PageBreak, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.graphics.barcode import code39, code128, code93, qrencoder
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.barcode import eanbc, qr, usps
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.lib import units
from reportlab.lib import colors
from reportlab.graphics.barcode import createBarcodeDrawing

from api.models import Booking_lines, FPRouting, Fp_freight_providers

from api.fp_apis.utils import gen_consignment_num

logger = logging.getLogger("dme_api")

styles = getSampleStyleSheet()
style_right = ParagraphStyle(name="right", parent=styles["Normal"], alignment=TA_RIGHT)
style_left = ParagraphStyle(
    name="left", parent=styles["Normal"], alignment=TA_LEFT, leading=12
)
style_center = ParagraphStyle(
    name="center", parent=styles["Normal"], alignment=TA_CENTER, leading=10
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


def gen_barcode(booking, booking_lines, j=0, label_index=0):
    consignment_num = gen_consignment_num(
        booking.vx_freight_provider, booking.b_bookingID_Visual
    )
    item_index = str(label_index + j + 1).zfill(3)
    items_count = str(len(booking_lines)).zfill(3)
    postal_code = booking.de_To_Address_PostalCode

    return f"{consignment_num}{item_index}{items_count}{postal_code}"


from reportlab.platypus.flowables import Flowable


class verticalText(Flowable):

    """Rotates a text in a table cell."""

    def __init__(self, text):
        Flowable.__init__(self)
        self.text = text

    def draw(self):
        canvas = self.canv
        canvas.rotate(90)
        fs = canvas._fontsize
        canvas.translate(1, -fs / 1.2)  # canvas._leading?
        canvas.drawString(0, 0, self.text)

    def wrap(self, aW, aH):
        canv = self.canv
        fn, fs = canv._fontname, canv._fontsize
        return canv._leading, 1 + canv.stringWidth(self.text, fn, fs)


from reportlab.platypus.flowables import Image


class RotatedImage(Image):
    def wrap(self, availWidth, availHeight):
        h, w = Image.wrap(self, availHeight, availWidth)
        return w, h

    def draw(self):
        self.canv.rotate(90)
        Image.draw(self)


def build_label(
    booking, filepath, lines, label_index, sscc, sscc_cnt=1, one_page_label=True
):
    logger.info(
        f"#110 [HUNTER NORMAL LABEL] Started building label... (Booking ID: {booking.b_bookingID_Visual}, Lines: {lines})"
    )

    if not lines:
        lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    if not os.path.exists(filepath):
        os.makedirs(filepath)

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

    fp_color_code = (
        Fp_freight_providers.objects.get(fp_company_name="Hunter").hex_color_code
        or "ffffff"
    )
    style_right_bg = ParagraphStyle(
        name="right",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        leading=9,
        backColor=f"#{fp_color_code}",
    )

    file = open(f"{filepath}/{filename}", "w")

    date = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")

    label_settings = {
        "font_family": "Verdana",
        "font_size_extra_small": "4",
        "font_size_small": "6",
        "font_size_medium": "8",
        "font_size_large": "10",
        "font_size_extra_large": "13",
        "label_dimension_length": "100",
        "label_dimension_width": "145",
        "label_image_size_length": "85",
        "label_image_size_width": "130",
        "barcode_dimension_length": "85",
        "barcode_dimension_width": "30",
        "barcode_font_size": "18",
        "line_height_extra_small": "3",
        "line_height_small": "5",
        "line_height_medium": "6",
        "line_height_large": "8",
        "line_height_extra_large": "12",
        "margin_v": "5",
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

    document = []
    dme_logo = "./static/assets/dme_logo.png"
    dme_img = Image(dme_logo, 30 * mm, 7.7 * mm)

    Story = []

    de_suburb = booking.de_To_Address_Suburb
    de_postcode = booking.de_To_Address_PostalCode
    de_state = booking.de_To_Address_State
    fp_routing = FPRouting.objects.filter(
        suburb=de_suburb, dest_postcode=de_postcode, state=de_state
    )
    if fp_routing[0] and fp_routing[0].orig_depot:
        head_port = fp_routing[0].orig_depot
    else:
        head_port = ""

    if fp_routing[0] and fp_routing[0].gateway:
        port_code = fp_routing[0].gateway
    else:
        port_code = ""

    j = 1

    totalQty = 0
    if one_page_label:
        lines = [lines[0]]
        totalQty = 1
    else:
        for booking_line in lines:
            totalQty = totalQty + booking_line.e_qty

    totalWeight = 0
    totalCubic = 0
    if one_page_label:
        lines = [lines[0]]
        totalQty = 1
        totalWeight = lines[0].e_Total_KG_weight
        totalCubic = lines[0].e_1_Total_dimCubicMeter
    else:
        for line in lines:
            totalWeight = totalWeight + line.e_Total_KG_weight
            totalCubic = totalCubic + line.e_1_Total_dimCubicMeter

    if sscc:
        j = label_index
        totalQty = sscc_cnt

    for line in lines:
        for k in range(line.e_qty):
            if one_page_label and k > 0:
                continue

            print("@1 - ", line.e_dimWidth, line.e_dimWidth)

            data = [
                [
                    dme_img,
                    Paragraph(
                        "<font size=%s><b>%s</b><br/><br/></font>"
                        % (label_settings["font_size_extra_large"], "Hunter Express"),
                        style_right_bg,
                    ),
                ]
            ]

            t1_w = float(label_settings["label_image_size_length"]) * (2 / 5) * mm
            t2_w = float(label_settings["label_image_size_length"]) * (3 / 5) * mm

            header = Table(
                data,
                colWidths=[t1_w, t2_w],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMBORDER", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ],
            )
            Story.append(header)
            Story.append(Spacer(1, 3))

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s><b>Date: %s</b></font>"
                        % (
                            label_settings["font_size_large"],
                            booking.b_dateBookedDate.strftime("%d/%m/%Y")
                            if booking.b_dateBookedDate
                            else "",
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>Consignment: %s</b></font>"
                        % (
                            label_settings["font_size_large"],
                            gen_consignment_num(
                                booking.vx_freight_provider, booking.b_bookingID_Visual
                            ),
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>Service: %s</b></font>"
                        % (
                            label_settings["font_size_large"],
                            (booking.vx_serviceName)
                            if (booking.vx_serviceName)
                            else "",
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>Additional Services: %s</b></font>"
                        % (label_settings["font_size_large"], ""),
                        style_left,
                    ),
                ],
            ]

            t1 = Table(
                tbl_data1,
                colWidths=(
                    float(label_settings["label_image_size_length"]) * (3 / 4) * mm
                ),
                rowHeights=(float(label_settings["line_height_small"]) * mm),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (0, -1), "BOTTOM"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ],
            )

            tbl_data2 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (label_settings["font_size_large"], head_port),
                        style_center,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (label_settings["font_size_large"], port_code),
                        style_center,
                    )
                ],
            ]

            t2 = Table(
                tbl_data2,
                colWidths=(
                    float(label_settings["label_image_size_length"]) * (1 / 4) * mm
                ),
                rowHeights=(float(label_settings["line_height_large"]) * mm),
                style=[
                    ("BOX", (0, 0), (0, 0), 1, colors.black),
                    ("BOX", (0, 1), (0, 1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("SPAN", (0, 0), (0, 0)),
                ],
            )

            data = [[t1, t2]]

            t1_w = float(label_settings["label_image_size_length"]) * (3 / 4) * mm
            t2_w = float(label_settings["label_image_size_length"]) * (1 / 4) * mm

            shell_table = Table(
                data,
                colWidths=[t1_w, t2_w],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMBORDER", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ],
            )

            Story.append(shell_table)
            Story.append(Spacer(1, 3))

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s of %s</b></font>"
                        % (label_settings["font_size_large"], j + 1, totalQty),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>%s</font>"
                        % (
                            label_settings["font_size_medium"],
                            (booking.pu_Contact_F_L_Name)
                            if (booking.pu_Contact_F_L_Name)
                            else "",
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>%s</font>"
                        % (
                            label_settings["font_size_medium"],
                            (booking.pu_Address_Street_1)
                            if (booking.pu_Address_Street_1)
                            else "",
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>%s</font>"
                        % (
                            label_settings["font_size_medium"],
                            (booking.pu_Address_street_2)
                            if (booking.pu_Address_street_2)
                            else "",
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>Dims: %s x %s x %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            float(line.e_dimWidth),
                            float(line.e_dimHeight),
                            float(line.e_dimLength),
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s>Dead: %s kg</font>"
                        % (
                            label_settings["font_size_medium"],
                            line.e_Total_KG_weight if line.e_Total_KG_weight else "N/A",
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s>Cubic: %s M<super rise=4 size=4>3</super></font>"
                        % (
                            label_settings["font_size_medium"],
                            (line.e_1_Total_dimCubicMeter)
                            if (line.e_1_Total_dimCubicMeter)
                            else "",
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>Total Cubic: %s M<super rise=4 size=4>3</super></font>"
                        % (label_settings["font_size_medium"], totalCubic),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>Total Dead: %s kg</font>"
                        % (label_settings["font_size_medium"], totalWeight),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s>Sender Reference:%s</font>"
                        % (
                            label_settings["font_size_medium"],
                            (booking.b_clientReference_RA_Numbers)
                            if (booking.b_clientReference_RA_Numbers)
                            else "",
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s>Account:%s</font>"
                        % (
                            label_settings["font_size_medium"],
                            (booking.vx_account_code)
                            if (booking.vx_account_code)
                            else "",
                        ),
                        style_left,
                    )
                ],
            ]

            t1 = Table(
                tbl_data1,
                colWidths=(
                    float(label_settings["label_image_size_length"]) * (3 / 4) * mm
                ),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ],
            )

            barcode = gen_barcode(booking, lines, j, label_index)

            d = Drawing(100, 100)
            d.add(Rect(0, 0, 0, 0, strokeWidth=1, fillColor=None))
            d.add(QrCodeWidget(value=barcode))

            data = [[t1, d]]

            t1_w = float(label_settings["label_image_size_length"]) * (3 / 4) * mm
            t2_w = float(label_settings["label_image_size_length"]) * (1 / 4) * mm

            shell_table = Table(
                data,
                colWidths=[t1_w, t2_w],
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ],
            )
            Story.append(shell_table)
            Story.append(Spacer(1, 5))

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["font_size_extra_large"],
                            booking.de_to_Contact_F_LName,
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["font_size_extra_large"],
                            booking.deToCompanyName if booking.deToCompanyName else "",
                        ),
                        style_left,
                    )
                ],
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["font_size_extra_large"],
                            booking.de_To_Address_Street_1,
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font> "
                        % (
                            label_settings["font_size_extra_large"],
                            booking.de_To_Address_Street_2,
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>%s %s</b></font> "
                        % (
                            label_settings["font_size_extra_large"],
                            booking.de_To_Address_Suburb,
                            booking.de_To_Address_PostalCode,
                        ),
                        style_left,
                    ),
                ],
            ]

            t1 = Table(
                tbl_data1,
                colWidths=(float(label_settings["label_image_size_length"]) * mm),
                style=[
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ],
            )

            Story.append(t1)
            Story.append(Spacer(1, 8))

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (label_settings["font_size_medium"], "Instructions:"),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s><b>%s</b></font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.de_to_PickUp_Instructions_Address,
                        )
                        if booking.de_to_PickUp_Instructions_Address
                        else "",
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
                    ("VALIGN", (0, 0), (0, -1), "CENTER"),
                ],
            )

            Story.append(t1)

            tbl_data1 = [
                [
                    Paragraph(
                        "<font size=%s>Reference: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            booking.b_client_sales_inv_num
                            if booking.b_client_sales_inv_num
                            else "",
                        ),
                        style_left,
                    ),
                ],
                [
                    Paragraph(
                        "<font size=%s>Other Reference: %s</font>"
                        % (
                            label_settings["font_size_medium"],
                            line.sscc if line.sscc else "",
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

            Story.append(t1)

            tbl_data = [
                [
                    code128.Code128(
                        barcode, barHeight=15 * mm, barWidth=0.7, humanReadable=True
                    )
                ],
            ]

            t1 = Table(
                tbl_data,
                colWidths=((float(label_settings["label_image_size_length"])) * mm),
                style=[
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (0, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (0, -1), 0),
                    ("RIGHTPADDING", (0, 0), (0, -1), 0),
                    # ('BOX', (0, 0), (-1, -1), 1, colors.black)
                ],
            )

            Story.append(t1)

            Story.append(PageBreak())

            j += 1

    doc.build(Story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)

    # end writting data into pdf file
    file.close()
    return filepath, filename
