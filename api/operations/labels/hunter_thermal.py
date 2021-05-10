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

from api.models import Booking_lines
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.utils import gen_consignment_num

logger = logging.getLogger("dme_api")

styles = getSampleStyleSheet()
style_right = ParagraphStyle(name='right', parent=styles['Normal'], alignment=TA_RIGHT)
style_left = ParagraphStyle(name='left', parent=styles['Normal'], alignment=TA_LEFT, leading = 12)
style_center = ParagraphStyle(name='center', parent=styles['Normal'], alignment=TA_CENTER, leading=10)
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

style_border = ParagraphStyle(name='center', parent=styles['Normal'], alignment=TA_CENTER, leading=14, borderWidth=1, borderColor='black')

def myFirstPage(canvas, doc):
    canvas.saveState()
    canvas.rotate(180)
    canvas.restoreState()

def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.rotate(90)
    canvas.restoreState()

def get_total_qty(lines):
    _total_qty = 0

    for booking_line in lines:
        _total_qty += booking_line.e_qty

    return _total_qty

def gen_barcode(booking, booking_lines, line_index=0, label_index=0):
    consignment_num = gen_consignment_num(
        booking.vx_freight_provider, booking.b_bookingID_Visual
    )
    item_index = str(label_index + line_index + 1).zfill(3)
    items_count = str(len(booking_lines)).zfill(3)
    postal_code = booking.de_To_Address_PostalCode

    return f"{consignment_num}{item_index}{items_count}{postal_code}"

def build_label(booking, filepath=None, lines=[], label_index=0):
    logger.info(
        f"#110 [HUNTER LABEL] Started building label... (Booking ID: {booking.b_bookingID_Visual}, Lines: {lines})"
    )

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
            + gen_consignment_num(
                booking.vx_freight_provider, booking.b_bookingID_Visual
            )
            + "_"
            + str(booking.b_bookingID_Visual)
            + ".pdf"
        )

    file = open(f"{filepath}/{filename}", "w")
    # end pdf file name using naming convention

    if not lines:
        lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    # start check if pdfs folder exists
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    # end check if pdfs folder exists

    label_settings = {
        'font_family' : 'Verdana', 
        'font_size_extra_small' : '5', 
        'font_size_small' : '7.5', 
        'font_size_medium' : '9', 
        'font_size_large': '11', 
        'font_size_extra_large': '13', 
        'label_dimension_length': '160', 
        'label_dimension_width': '110', 
        'label_image_size_length': '150', 
        'label_image_size_width': '102', 
        'barcode_dimension_length': '65', 
        'barcode_dimension_width': '30', 
        'barcode_font_size': '18', 
        'line_height_extra_small':'3', 
        'line_height_small':'5', 
        'line_height_medium':'6', 
        'line_height_large':'8'
    }

    doc = SimpleDocTemplate(filepath+filename, pagesize = ( float(label_settings['label_dimension_length']) * mm, float(label_settings['label_dimension_width']) * mm ), topMargin = float(float(label_settings['label_dimension_width']) - float(label_settings['label_image_size_width'])) * mm, bottomMargin = float(float(label_settings['label_dimension_width']) - float(label_settings['label_image_size_width'])) * mm, rightMargin = float(float(label_settings['label_dimension_length']) - float(label_settings['label_image_size_length'])) * mm, leftMargin = float(float(label_settings['label_dimension_length']) - float(label_settings['label_image_size_length'])) * mm)
    document = []

    totalQty = get_total_qty(lines)
    Story=[]
    line_index = 1

    print('booking_lines', lines)
    for line in lines:

        for k in range(line.e_qty):
            hr = HRFlowable(width=(float(label_settings['label_image_size_length']) * mm), thickness=1, lineCap='square', color=colors.black,
            spaceBefore=0, spaceAfter=0, hAlign='CENTER', vAlign='BOTTOM', dash=None)

            Story.append(hr)
            Story.append(Spacer(1, 2))
            tbl_data1 = [
                [
                    Paragraph('<font size=%s>To: %s</font>' % (label_settings['font_size_large'], booking.de_to_Contact_F_LName if booking.de_to_Contact_F_LName else ''), style_left)
                ],
                [
                    Paragraph('<font size=%s><b>%s</b></font>' % (label_settings['font_size_large'],booking.de_To_Address_Street_1 if booking.de_To_Address_Street_1 else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s><b>%s</b></font> ' % (label_settings['font_size_medium'], booking.de_To_Address_Street_2 if booking.de_To_Address_Street_2 else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s><b>%s %s %s</b></font> ' % (label_settings['font_size_medium'],  booking.de_To_Address_Suburb if booking.de_To_Address_Suburb else '', booking.de_To_Address_State if booking.de_To_Address_State else '', booking.de_To_Address_PostalCode if booking.de_To_Address_PostalCode else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], '0289682200', booking.de_to_Contact_F_LName if booking.de_to_Contact_F_LName else ''), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], 'Ref:', '3932555220003820'), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], 'Item Ref:', line.e_item if line.e_item else 'null'), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s %s<br/></font>' % (label_settings['font_size_large'], 'CONSIGNMENT', booking.v_FPBookingNumber if booking.v_FPBookingNumber else ''), style_left)
                ],
                
            ]

            t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (2/3) * mm ), style = [
                ('TOPPADDING',(0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
            ])

            tbl_data2 = [
                [
                    Paragraph('<font size=%s><b>%s</b></font>' % ( label_settings['font_size_large'], 'WA' ), style_border)
                ],
                [
                    Paragraph('<font size=%s><b>%s</b></font>' % ( label_settings['font_size_large'], 'WAC' ), style_border)
                ],
                [
                    Paragraph('<font size=%s>%s</font>' % ( label_settings['font_size_medium'], 'Print:' ), style_left)
                ],
                [
                    hr
                ],
                [
                    Paragraph('<font size=%s>%s</font>' % ( label_settings['font_size_medium'], 'Signature:' ), style_left)
                ],
                [
                    hr
                ],
                [
                    Paragraph('<font size=%s>%s</font>' % ( label_settings['font_size_medium'], 'Date/Time:' ), style_left)
                ],
                [
                    hr
                ],
                [
                    Paragraph('<font size=%s>%s %s</font>' % ( label_settings['font_size_medium'], 'Account:', 'DUMMY' ), style_center)
                ],
                [
                    Paragraph('<font size=%s>Item %s/%s Weight %s %s</font>' % (label_settings['font_size_medium'], line_index, totalQty, line.e_Total_KG_weight if line.e_Total_KG_weight else '' , line.e_weightUOM if line.e_weightUOM  else ''), style_center)
                ],
                [
                    Paragraph('<font size=%s><b>%s</b><br/></font>' % ( label_settings['font_size_medium'], 'Road Express' ), style_center)
                ]
            ]

            t2 = Table(tbl_data2, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ), style = [
                ('TOPPADDING',(0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                ])

            data = [[t1, t2]]

            t1_w = float(label_settings['label_image_size_length'])*(2/3) * mm
            t2_w = float(label_settings['label_image_size_length'])*(1/3) * mm

            shell_table = Table(data, colWidths=[t1_w, t2_w], style = [
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('SPAN',(0,0),(0,-1)),
                ('TOPPADDING',(0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                # ('LEFTPADDING',(0,0),(-1,-1), 0),
                # ('RIGHTPADDING',(0,0),(-1,-1), 0),
                ('BOX', (0, 0), (1, -1), 1, colors.black)
                ])
            
            Story.append(shell_table)


            barcode = gen_barcode(booking, lines, line_index, label_index)

            tbl_data = [
                [
                    code128.Code128( barcode, barHeight = 15 * mm, barWidth = 2.2, humanReadable = False )
                ],
            ]

            t1 = Table(tbl_data, colWidths=( ( float(label_settings['label_image_size_length']) ) * mm ), style = [
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('VALIGN',(0,0),(0,-1),'TOP'),
                ('TOPPADDING',(0,0),(-1,-1), 5),
                ('BOTTOMPADDING',(0,0),(-1,-1), 2),
                ('LEFTPADDING',(0,0),(0,-1), 0),
                ('RIGHTPADDING',(0,0),(0,-1), 0),
                # ('BOX', (0, 0), (-1, -1), 1, colors.black)
                ])
            
            Story.append(t1)

            human_readable = [
                [
                    Paragraph('<font size=%s>%s</font>' % (label_settings['font_size_medium'], barcode), style_center)
                ],
            ]

            t1 = Table(
                human_readable, colWidths=( float(label_settings['label_image_size_length']) * mm ), 
                style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                ]
            )

            Story.append(t1)
            Story.append(Spacer(1, 5))

            tbl_data1 = [
                [
                    Paragraph('<font size=%s>%s %s</font>' % ( label_settings['font_size_medium'], 'FROM:' , booking.puCompany if booking.puCompany else ''), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s</font>' % (label_settings['font_size_medium'],booking.pu_Address_Street_1 if booking.pu_Address_Street_1 else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s>%s</font> ' % (label_settings['font_size_medium'], booking.pu_Address_street_2 if booking.pu_Address_street_2 else ''), style_left),
                ],
                [
                    hr
                ],
                [
                    Paragraph('<font size=%s><b>%s %s %s</b></font> ' % (label_settings['font_size_medium'], booking.pu_Address_Suburb if booking.pu_Address_Suburb else '', booking.pu_Address_State if booking.pu_Address_State else '', booking.pu_Address_PostalCode if booking.pu_Address_PostalCode else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s>%s %s</font> ' % (label_settings['font_size_medium'], '288854000', booking.pu_Contact_F_L_Name if booking.pu_Contact_F_L_Name else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s>Item %s/%s Weight %s %s</font>' % (label_settings['font_size_medium'], line_index, totalQty, line.e_Total_KG_weight if line.e_Total_KG_weight else '' , line.e_weightUOM if line.e_weightUOM  else ''), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s</font> ' % (label_settings['font_size_medium'], datetime.datetime.now().strftime("%d/%m/%Y")), style_left),
                ],
            ]

            t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (3/8) * mm ), style = [
                ('TOPPADDING',(0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                ])


            tbl_data2 = [
                [
                    Paragraph('<font size=%s>To: %s</font>' % (label_settings['font_size_medium'], booking.de_to_Contact_F_LName if booking.de_to_Contact_F_LName else ''), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s</font>' % (label_settings['font_size_medium'],booking.de_To_Address_Street_1 if booking.de_To_Address_Street_1 else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s>%s</font> ' % (label_settings['font_size_medium'], booking.de_To_Address_Street_2 if booking.de_To_Address_Street_2 else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s><b>%s %s %s</b></font> ' % (label_settings['font_size_medium'],  booking.de_To_Address_Suburb if booking.de_To_Address_Suburb else '', booking.de_To_Address_State if booking.de_To_Address_State else '', booking.de_To_Address_PostalCode if booking.de_To_Address_PostalCode else ''), style_left),
                ],
                [
                    Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], '0289682200', booking.de_to_Contact_F_LName if booking.de_to_Contact_F_LName else ''), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], 'CON.', booking.v_FPBookingNumber if booking.v_FPBookingNumber else ''), style_left)
                ],
                [
                    Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], 'Item Ref:', line.e_item if line.e_item else 'null'), style_left)
                ],
                
            ]

            t2 = Table(tbl_data2, colWidths=( float(label_settings['label_image_size_length']) * (3/8) * mm ), style = [
                ('TOPPADDING',(0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                ])

            tbl_data3 = [
                [
                    Paragraph('<font size=%s>Instructions: %s</font>' % (label_settings['font_size_medium'], str(booking.de_to_Pick_Up_Instructions_Contact) if booking.de_to_Pick_Up_Instructions_Contact else ''), style_left)
                ],
            ]

            t3 = Table(tbl_data3, colWidths=( float(label_settings['label_image_size_length']) * (2/8) * mm ), style = [
                ('TOPPADDING',(0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                ])

            data = [[t1, t2, t3]]

            t1_w = float(label_settings['label_image_size_length'])*(3/8) * mm
            t2_w = float(label_settings['label_image_size_length'])*(3/8) * mm
            t3_w = float(label_settings['label_image_size_length'])*(2/8) * mm

            shell_table = Table(data, colWidths=[t1_w, t2_w, t3_w], style = [
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('SPAN',(0,0),(0,-1)),
                ('TOPPADDING',(0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                # ('LEFTPADDING',(0,0),(-1,-1), 0),
                # ('RIGHTPADDING',(0,0),(-1,-1), 0),
                ('BOX', (0, 0), (2, -1), 1, colors.black)
                ])
            
            Story.append(shell_table)   

            Story.append(PageBreak())
            
            line_index += 1

    doc.build(Story, onFirstPage = myFirstPage, onLaterPages=myLaterPages)
    file.close() 
    logger.info(
        f"#119 [HUNTER LABEL] Finished building label... (Booking ID: {booking.b_bookingID_Visual})"
    )
    return filepath, filename

                