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

styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY))


def myFirstPage(canvas, doc):
    canvas.saveState()
    canvas.rotate(180)
    canvas.restoreState()


def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.rotate(90)
    canvas.restoreState()


def get_barcode_rotated(
    value,
    width,
    barHeight=27.6 * mm,
    barWidth=1,
    fontSize=18,
    humanReadable=True,
):
    barcode = createBarcodeDrawing(
        "Code128",
        value=value,
        barHeight=barHeight,
        barWidth=barWidth,
        fontSize=fontSize,
        humanReadable=humanReadable,
    )

    drawing_width = width
    barcode_scale = drawing_width / barcode.width
    drawing_height = barcode.height * barcode_scale

    drawing = Drawing(drawing_width, drawing_height)
    drawing.scale(barcode_scale, barcode_scale)
    drawing.add(barcode, name="barcode")

    drawing_rotated = Drawing(drawing_height, drawing_width)
    drawing_rotated.rotate(90)
    drawing_rotated.translate(10, -drawing_height)
    drawing_rotated.add(drawing, name="drawing")

    return drawing_rotated


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


class RotatedImage(Image):
    def wrap(self, availWidth, availHeight):
        h, w = Image.wrap(self, availHeight, availWidth)
        return w, h

    def draw(self):
        self.canv.rotate(90)
        Image.draw(self)


def gen_barcode(booking, booking_lines, line_index=0, label_index=0):
    consignment_num = gen_consignment_num(
        booking.vx_freight_provider, booking.b_bookingID_Visual
    )
    item_index = str(label_index + line_index + 1).zfill(3)
    items_count = str(len(booking_lines)).zfill(3)
    postal_code = booking.de_To_Address_PostalCode

    return f"{consignment_num}{item_index}{items_count}{postal_code}"


import os.path


def path_relative_to_file(base_file_path, relative_path):
    base_dir = os.path.dirname(os.path.abspath(base_file_path))
    return os.path.normpath(os.path.join(base_dir, relative_path))


def build_label(booking, filepath, lines=[], label_index=0):
    logger.info(
        f"#110 [TNT LABEL] Started building label... (Booking ID: {booking.b_bookingID_Visual}, Lines: {lines}, Format: TNT)"
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
            + str(booking.v_FPBookingNumber)
            + "_"
            + str(booking.b_bookingID_Visual)
            + ".pdf"
        )

    file = open(f"{filepath}/{filename}", "w")
    logger.info(f"#111 [TNT LABEL] File full path: {filepath}/{filename}")
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
        "margin_v": "5",
        "margin_h": "0",
    }

    width = float(label_settings["label_dimension_length"]) * mm
    height = float(label_settings["label_dimension_width"]) * mm
    doc = SimpleDocTemplate(
        filepath + filename,
        pagesize=(width, height),
        rightMargin=float(label_settings["margin_h"]) * mm,
        leftMargin=float(label_settings["margin_h"]) * mm,
        topMargin=float(label_settings["margin_v"]) * mm,
        bottomMargin=float(label_settings["margin_v"]) * mm,
    )

    dme_logo = "./static/assets/dme_logo.png"
    dme_img = Image(dme_logo, 30 * mm, 8 * mm)

    Story = []
    j = 1

    # Get routing_group with vx_service_name
    routing_group = None
    if booking.vx_serviceName == "Road Express":
        routing_group = "EXP"
    elif booking.vx_serviceName in [
        "09:00 Express",
        "10:00 Express",
        "12:00 Express",
        "Overnight Express",
        "PAYU - Satchel",
        "ONFC Satchel",
    ]:
        routing_group = "PRI"
    elif booking.vx_serviceName in [
        "Technology Express - Sensitive Express",
        "Sensitive Express",
        "Fashion Delivery",
    ]:
        routing_group = "TE"

    """
    Let's assume service group EXP
    Using the D records relating to that service group, establish the origin depot thaservices the consignment’s origin postcode.
    This should appear in section 3 of the routing label preceded by “Ex “.
    """
    crecords = FPRouting.objects.filter(
        suburb=booking.de_To_Address_Suburb,
        dest_postcode=booking.de_To_Address_PostalCode,
        state=booking.de_To_Address_State,
        routing_group=routing_group,
    ).only("orig_depot_except", "gateway", "onfwd", "sort_bin")

    if crecords.exists():
        drecord = (
            FPRouting.objects.filter(
                orig_postcode=booking.de_To_Address_PostalCode,
                routing_group=routing_group,
            )
            .only("orig_depot")
            .first()
        )
        routing = None

        for crecord in crecords:
            if crecord.orig_depot_except == drecord.orig_depot:
                routing = crecord
                break

        if not routing:
            routing = crecords.first()

    for booking_line in lines:
        tbl_data1 = [
            [
                Paragraph(
                    "<p style='vertical-align: top; padding: 0px; line-height: 0px'><font size=%s><b> %s </b></font></p>"
                    % (35, booking.de_To_Address_PostalCode or ""),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>via %s  &#160 &#160 to &#160  &#160  %s </b></font>"
                    % (
                        label_settings["font_size_extra_large"],
                        routing.gateway,
                        routing.onfwd,
                    ),
                    style_right,
                ),
            ],
        ]
        t1 = Table(
            tbl_data1,
            colWidths=(
                90,
                float(label_settings["label_image_size_length"]) * mm - 90,
            ),
            rowHeights=(float(label_settings["line_height_small"]) * mm),
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMBORDER", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
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
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        Story.append(shell_table)

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (label_settings["font_size_medium"], ""),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_extra_large"],
                        (booking.v_FPBookingNumber)
                        if (booking.v_FPBookingNumber)
                        else "",
                    ),
                    style_right,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_extra_large"],
                        (booking.de_To_Address_Suburb)
                        if (booking.de_To_Address_Suburb)
                        else "",
                    ),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s>Itm:%s</font> "
                    % (label_settings["font_size_small"], booking_line.sscc),
                    style_right,
                ),
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(
                float(label_settings["label_image_size_length"]) * (1 / 2) * mm,
                float(label_settings["label_image_size_length"]) * (1 / 2) * mm,
            ),
            rowHeights=(float(label_settings["line_height_medium"]) * mm),
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
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        hr = HRFlowable(
            width=(float(label_settings["label_image_size_length"]) * mm),
            thickness=0.2,
            lineCap="square",
            color=colors.black,
            spaceBefore=0,
            spaceAfter=0,
            hAlign="CENTER",
            vAlign="BOTTOM",
            dash=None,
        )

        Story.append(shell_table)
        Story.append(Spacer(1, 5))
        Story.append(hr)

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_extra_large"], booking.vx_serviceName),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_extra_large"], routing.sort_bin),
                    style_right,
                ),
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(
                float(label_settings["label_image_size_length"]) * (1 / 2) * mm,
                float(label_settings["label_image_size_length"]) * (1 / 2) * mm,
            ),
            rowHeights=(float(label_settings["line_height_small"]) * mm),
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
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMBORDER", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        Story.append(shell_table)
        Story.append(Spacer(1, 5))
        Story.append(hr)
        Story.append(Spacer(1, 2))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_medium"],
                        booking.b_dateBookedDate.strftime("%d-%m-%Y")
                        if booking.b_dateBookedDate
                        else "N/A",
                    ),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>%s &#160 of &#160 %s</b></font>"
                    % (label_settings["font_size_medium"], j, totalQty),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>Item Wt.: %s %s.</b></font>"
                    % (
                        label_settings["font_size_medium"],
                        booking_line.e_Total_KG_weight or "",
                        booking_line.e_weightUOM or "KG",
                    ),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_medium"], "Ex " + routing.gateway),
                    style_right,
                ),
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(
                float(label_settings["label_image_size_length"]) * (1 / 4) * mm,
                float(label_settings["label_image_size_length"]) * (1 / 4) * mm,
                float(label_settings["label_image_size_length"]) * (1 / 3) * mm,
                float(label_settings["label_image_size_length"]) * (1 / 6) * mm,
            ),
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
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        Story.append(shell_table)

        Story.append(hr)
        Story.append(Spacer(1, 2))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_medium"],
                        "Does not Contain Dangerous Goods",
                    ),
                    style_center,
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
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        Story.append(shell_table)

        Story.append(hr)
        Story.append(Spacer(1, 2))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_medium"], "To:"),
                    style_left,
                )
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(30),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        tbl_data2 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_large"],
                        booking.de_to_Contact_F_LName or "",
                    ),
                    style_uppercase,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_large"],
                        booking.deToCompanyName or "",
                    ),
                    style_uppercase,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_large"],
                        booking.de_To_Address_Street_1 or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font> "
                    % (
                        label_settings["font_size_large"],
                        booking.de_To_Address_Street_2 or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s %s</b></font> "
                    % (
                        label_settings["font_size_large"],
                        booking.de_To_Address_Suburb or "",
                        booking.de_To_Address_PostalCode or "",
                    ),
                    style_uppercase,
                ),
            ],
        ]

        t2 = Table(
            tbl_data2,
            colWidths=(float(label_settings["label_image_size_length"]) * mm - 30),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        data = [[t1, t2]]

        t1_w = 30
        t2_w = float(label_settings["label_image_size_length"]) * mm - 30

        shell_table = Table(
            data,
            colWidths=[t1_w, t2_w],
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )
        Story.append(shell_table)
        Story.append(Spacer(1, 2))
        Story.append(hr)

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b> %s </b></font>"
                    % (label_settings["font_size_medium"], "From:"),
                    style_left,
                )
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(30),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        tbl_data2 = [
            [
                Paragraph(
                    "<font size=%s>%s, %s, %s, %s, %s</font>"
                    % (
                        label_settings["font_size_medium"],
                        booking.pu_Contact_F_L_Name or "",
                        booking.pu_Address_Street_1 or "",
                        booking.pu_Address_street_2 or "",
                        booking.pu_Address_Suburb or "",
                        booking.pu_Address_State or "",
                    ),
                    style_uppercase,
                )
            ],
        ]

        t2 = Table(
            tbl_data2,
            colWidths=(float(label_settings["label_image_size_length"]) * mm - 30),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        data = [[t1, t2]]

        t1_w = 30
        t2_w = float(label_settings["label_image_size_length"]) * mm - 30

        shell_table = Table(
            data,
            colWidths=[t1_w, t2_w],
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
                    "<font size=%s><b>Senders Ref:</b> %s %s</font>"
                    % (
                        label_settings["font_size_medium"],
                        str(booking.de_to_PickUp_Instructions_Address)
                        if booking.de_to_PickUp_Instructions_Address
                        else "",
                        str(booking.de_to_Pick_Up_Instructions_Contact)
                        if booking.de_to_Pick_Up_Instructions_Contact
                        else "",
                    ),
                    style_left,
                )
            ]
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(float(label_settings["label_image_size_length"]) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )
        Story.append(t1)
        Story.append(Spacer(1, 5))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_medium"], "Special Instructions:"),
                    style_center,
                ),
            ],
            [
                Paragraph(
                    "font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_medium"],
                        booking.de_to_PickUp_Instructions_Address or "",
                    ),
                    style_center,
                ),
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(float(label_settings["label_image_size_length"]) * mm),
            # rowHeights=(float(label_settings["line_height_extra_small"]) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (0, -1), "TOP"),
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
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        Story.append(shell_table)

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_medium"],
                        "Please collect from warehouse",
                    ),
                    style_center,
                )
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(float(label_settings["label_image_size_length"]) * (1 / 2) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        tbl_data2 = [
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_medium"],
                        "Deliver to Special Orders Desk",
                    ),
                    style_center,
                )
            ],
        ]

        t2 = Table(
            tbl_data2,
            colWidths=(float(label_settings["label_image_size_length"]) * (1 / 2) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        data = [[t1, t2]]

        t1_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm
        t2_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm

        shell_table = Table(
            data,
            colWidths=[t1_w, t2_w],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        Story.append(shell_table)
        Story.append(Spacer(1, 5))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>CN: %s</b></font>"
                    % (
                        label_settings["font_size_normal"],
                        booking.v_FPBookingNumber or "",
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>Itm:%s</b></font>"
                    % (label_settings["font_size_normal"], booking_line.sscc),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s &#160 of &#160 %s</b></font>"
                    % (label_settings["font_size_normal"], j, totalQty),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_normal"], "TO:"),
                    style_uppercase,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_normal"],
                        booking.de_to_Contact_F_LName or "",
                    ),
                    style_uppercase,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_normal"],
                        booking.deToCompanyName or "",
                    ),
                    style_uppercase,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_normal"],
                        booking.de_To_Address_Street_1 or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_normal"],
                        booking.de_To_Address_Street_2 or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_normal"],
                        booking.de_To_Address_Suburb or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s %s</font> "
                    % (
                        label_settings["font_size_normal"],
                        booking.de_To_Address_State or "",
                        booking.de_To_Address_PostalCode or "",
                    ),
                    style_uppercase,
                ),
            ],
        ]

        t1 = Table(
            tbl_data1,
            colWidths=(float(label_settings["label_image_size_length"]) * (1 / 2) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ('LEFTPADDING',(0,0),(-1,-1), 0),
                # ('RIGHTPADDING',(0,0),(-1,-1), 0),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ],
        )

        tbl_data2 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_normal"], booking.vx_serviceName),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>Con Note Wt.: %s %s.</b></font>"
                    % (
                        label_settings["font_size_normal"],
                        booking_line.e_Total_KG_weight or "",
                        booking_line.e_weightUOM or "KG",
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (label_settings["font_size_normal"], ""),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_normal"], "FROM:"),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_normal"],
                        booking.pu_Contact_F_L_Name or "",
                    ),
                    style_uppercase,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_normal"],
                        booking.deToCompanyName or "",
                    ),
                    style_uppercase,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_normal"],
                        booking.pu_Address_Street_1 or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_normal"],
                        booking.pu_Address_street_2 or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_normal"],
                        booking.pu_Address_Suburb or "",
                    ),
                    style_uppercase,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s %s</font> "
                    % (
                        label_settings["font_size_normal"],
                        booking.pu_Address_State or "",
                        booking.pu_Address_PostalCode or "",
                    ),
                    style_uppercase,
                ),
            ],
        ]

        t2 = Table(
            tbl_data2,
            colWidths=(float(label_settings["label_image_size_length"]) * (1 / 2) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ('LEFTPADDING',(0,0),(-1,-1), 0),
                # ('RIGHTPADDING',(0,0),(-1,-1), 0),
            ],
        )

        data = [[t1, t2]]

        t1_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm
        t2_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm

        shell_table = Table(
            data,
            colWidths=[t1_w, t2_w],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("SPAN", (0, 0), (0, -1)),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ],
        )

        Story.append(shell_table)

        barcode = gen_barcode(booking, lines, 0, label_index)

        tbl_data = [
            [
                code128.Code128(
                    barcode, barHeight=15 * mm, barWidth=0.7, humanReadable=False
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
        # Story.append(Spacer(1, 5))

        tbl_data1 = [[dme_img]]

        t1 = Table(
            tbl_data1,
            colWidths=(float(label_settings["label_image_size_length"]) * (1 / 2) * mm),
            rowHeights=(float(label_settings["line_height_large"]) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (0, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )

        tbl_data2 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_extra_large"],
                        booking.vx_freight_provider or "",
                    ),
                    style_center,
                )
            ]
        ]

        t2 = Table(
            tbl_data2,
            colWidths=(float(label_settings["label_image_size_length"]) * (1 / 2) * mm),
            rowHeights=(float(label_settings["line_height_medium"]) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (0, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )
        barcode = str(j).zfill(2)

        data = [[t1, t2]]

        t1_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm
        t2_w = float(label_settings["label_image_size_length"]) * (1 / 2) * mm

        shell_table = Table(
            data,
            colWidths=[t1_w, t2_w],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMBORDER", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )
        Story.append(shell_table)

        Story.append(PageBreak())

        j += 1

    doc.build(Story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)
    file.close()
    logger.info(
        f"#119 [TNT LABEL] Finished building label... (Booking ID: {booking.b_bookingID_Visual}, Format: TNT)"
    )
    return filepath, filename
