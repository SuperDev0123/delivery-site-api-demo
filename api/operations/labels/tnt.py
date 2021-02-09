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
    leading=12,
)
style_center = ParagraphStyle(
    name="center",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    leading=10,
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
        f"#110 Started building label... (Booking ID:{booking.b_bookingID_Visual}, Format: TNT)"
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

    file = open(filepath + filename, "w")
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
    dme_im = Image(path_relative_to_file(__file__, dme_logo), 30 * mm, 8 * mm)

    Story = []
    j = 1

    """
    Let's assume service group EXP
    Using the D records relating to that service group, establish the origin depot thaservices the consignment’s origin postcode.
    This should appear in section 3 of the routing label preceded by “Ex “.
    """
    crecords = FPRouting.objects.filter(
        suburb=booking.de_To_Address_Suburb,
        dest_postcode=booking.de_To_Address_PostalCode,
        state=booking.de_To_Address_State,
        service_group="EXP",
    )

    if crecords.exists():
        drecord = FPRouting.objects.filter(
            orig_postcode=booking.de_To_Address_PostalCode, service_group="EXP"
        ).first()
        routing = FPRouting.objects.filter(
            suburb=booking.de_To_Address_Suburb,
            dest_postcode=booking.de_To_Address_PostalCode,
            state=booking.de_To_Address_State,
            service_group="EXP",
            orig_depot_except=drecord.orig_depot,
        ).first()
        if not routing:
            routing = FPRouting.objects.filter(
                suburb=booking.de_To_Address_Suburb,
                dest_postcode=booking.de_To_Address_PostalCode,
                state=booking.de_To_Address_State,
                service_group="EXP",
            ).first()

    for booking_line in lines:
        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        22,
                        (booking.de_To_Address_PostalCode)
                        if (booking.de_To_Address_PostalCode)
                        else "",
                    ),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>via %s to %s</b></font>"
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
                float(label_settings["label_image_size_length"]) * (1 / 2) * mm,
                float(label_settings["label_image_size_length"]) * (1 / 2) * mm,
            ),
            rowHeights=(float(label_settings["line_height_small"]) * mm),
            style=[
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
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
            ],
        )

        hr = HRFlowable(
            width=(float(label_settings["label_image_size_length"]) * mm),
            thickness=1,
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
        Story.append(Spacer(1, 2))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_extra_large"], "Road Express"),
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
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMBORDER", (0, 0), (-1, -1), 0),
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
                    "<font size=%s><b>%s of %s</b></font>"
                    % (label_settings["font_size_medium"], j, totalQty),
                    style_left,
                ),
                Paragraph(
                    "<font size=%s><b>Item Wt.: %s %s.</b></font>"
                    % (
                        label_settings["font_size_medium"],
                        booking_line.e_Total_KG_weight
                        if booking_line.e_Total_KG_weight
                        else "",
                        booking_line.e_weightUOM if booking_line.e_weightUOM else "",
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
            ],
        )

        Story.append(shell_table)

        Story.append(hr)
        Story.append(Spacer(1, 2))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s>%s</font>"
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
                        booking.de_to_Contact_F_LName,
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_large"],
                        booking.deToCompanyName if booking.deToCompanyName else "",
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_large"],
                        booking.de_To_Address_Street_1,
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font> "
                    % (
                        label_settings["font_size_large"],
                        booking.de_To_Address_Street_2,
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s %s</b></font> "
                    % (
                        label_settings["font_size_large"],
                        booking.de_To_Address_Suburb,
                        booking.de_To_Address_PostalCode,
                    ),
                    style_left,
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
        Story.append(hr)
        Story.append(Spacer(1, 5))

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
                        (booking.pu_Contact_F_L_Name)
                        if (booking.pu_Contact_F_L_Name)
                        else "",
                        str(booking.pu_Address_Street_1)
                        if booking.pu_Address_Street_1
                        else "",
                        str(booking.pu_Address_street_2)
                        if booking.pu_Address_street_2
                        else "",
                        str(booking.pu_Address_Suburb)
                        if booking.pu_Address_Suburb
                        else "",
                        str(booking.pu_Address_State)
                        if booking.pu_Address_State
                        else "",
                    ),
                    style_left,
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
        Story.append(Spacer(1, 10))

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
                        booking.de_to_PickUp_Instructions_Address,
                    )
                    if booking.de_to_PickUp_Instructions_Address
                    else "",
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
            ],
        )

        Story.append(shell_table)
        Story.append(Spacer(1, 2))

        tbl_data1 = [
            [
                Paragraph(
                    "<font size=%s><b>CN: %s</b></font>"
                    % (
                        label_settings["font_size_medium"],
                        (booking.v_FPBookingNumber)
                        if (booking.v_FPBookingNumber)
                        else "",
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>Itm:%s</b></font>"
                    % (label_settings["font_size_medium"], "00132214000166765001"),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s of %s</b></font>"
                    % (label_settings["font_size_medium"], j, totalQty),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_medium"], "TO:"),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_medium"],
                        booking.de_to_Contact_F_LName
                        if booking.de_to_Contact_F_LName
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
                        booking.deToCompanyName if booking.deToCompanyName else "",
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_medium"],
                        booking.de_To_Address_Street_1
                        if booking.de_To_Address_Street_1
                        else "",
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_medium"],
                        booking.de_To_Address_Street_2
                        if booking.de_To_Address_Street_2
                        else "",
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_medium"],
                        booking.de_To_Address_Suburb
                        if booking.de_To_Address_Suburb
                        else "",
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s %s</font> "
                    % (
                        label_settings["font_size_medium"],
                        booking.de_To_Address_State
                        if booking.de_To_Address_State
                        else "",
                        booking.de_To_Address_PostalCode
                        if booking.de_To_Address_PostalCode
                        else "",
                    ),
                    style_left,
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
                    % (label_settings["font_size_medium"], "Road Express"),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>Con Note Wt.: :%s %s.</b></font>"
                    % (
                        label_settings["font_size_medium"],
                        booking_line.e_Total_KG_weight
                        if booking_line.e_Total_KG_weight
                        else "",
                        booking_line.e_weightUOM if booking_line.e_weightUOM else "",
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (label_settings["font_size_medium"], ""),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (label_settings["font_size_medium"], "FROM:"),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_medium"],
                        booking.pu_Contact_F_L_Name
                        if booking.pu_Contact_F_L_Name
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
                        booking.deToCompanyName if booking.deToCompanyName else "",
                    ),
                    style_left,
                )
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font>"
                    % (
                        label_settings["font_size_medium"],
                        booking.pu_Address_Street_1
                        if booking.pu_Address_Street_1
                        else "",
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_medium"],
                        booking.pu_Address_street_2
                        if booking.pu_Address_street_2
                        else "",
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s</font> "
                    % (
                        label_settings["font_size_medium"],
                        booking.pu_Address_Suburb if booking.pu_Address_Suburb else "",
                    ),
                    style_left,
                ),
            ],
            [
                Paragraph(
                    "<font size=%s>%s %s</font> "
                    % (
                        label_settings["font_size_medium"],
                        booking.pu_Address_State if booking.pu_Address_State else "",
                        booking.pu_Address_PostalCode
                        if booking.pu_Address_PostalCode
                        else "",
                    ),
                    style_left,
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

        # barcode = booking.v_FPBookingNumber+'DESC'+str(k+1).zfill(10)+booking.de_To_Address_PostalCode
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
        Story.append(Spacer(1, 5))

        tbl_data1 = [
            [dme_im],
        ]

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
            ],
        )

        tbl_data2 = [
            [
                Paragraph(
                    "<font size=%s><b>%s</b></font>"
                    % (
                        label_settings["font_size_extra_large"],
                        (booking.vx_freight_provider)
                        if (booking.vx_freight_provider)
                        else "",
                    ),
                    style_left,
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
            ],
        )
        Story.append(shell_table)

        Story.append(PageBreak())

        j += 1

    doc.build(Story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)
    file.close()
    logger.info(
        f"#119 Finished building label... (Booking ID: {booking.b_bookingID_Visual}, Format: TNT)"
    )
    return filepath, filename
