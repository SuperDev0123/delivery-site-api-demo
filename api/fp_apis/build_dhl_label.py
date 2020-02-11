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

import time
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter, landscape, A6, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, NextPageTemplate, Frame, PageTemplate
from reportlab.platypus.flowables import Spacer, HRFlowable, PageBreak, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code39, code128, code93, qrencoder
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.barcode import eanbc, qr, usps
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.lib import units
from reportlab.lib import colors
from reportlab.graphics.barcode import createBarcodeDrawing

styles = getSampleStyleSheet()
style_right = ParagraphStyle(name='right', parent=styles['Normal'], alignment=TA_RIGHT)
style_left = ParagraphStyle(name='left', parent=styles['Normal'], alignment=TA_LEFT, leading = 12)
style_center = ParagraphStyle(name='center', parent=styles['Normal'], alignment=TA_CENTER, leading=10)
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))


if os.environ["ENV"] == "local":
    filepath = "/home/administrator/Documents/projects/dme_api/static/dhl_au/"
elif os.environ["ENV"] == "dev":
    filepath = "/var/www/html/dme_api/static/dhl_au/labels/"
elif os.environ["ENV"] == "prod":
    filepath = "/var/www/html/dme_api/static/dhl_au/labels/"

DB_HOST = os.environ["DB_HOST"]
DB_USER = os.environ["DB_USER"]
DB_PASS = os.environ["DB_PASSWORD"]
DB_PORT = os.environ["DB_PORT"]
DB_NAME = os.environ["DB_NAME"]


def get_booking(mysqlcon, id):
    with mysqlcon.cursor() as cursor:
        sql = f"SELECT pk_booking_id, b_bookingID_Visual, v_FPBookingNumber, b_clientReference_RA_Numbers, b_client_warehouse_code, b_dateBookedDate, vx_freight_provider, puCompany, pu_Contact_F_L_Name, pu_Phone_Main, pu_Address_Street_1, pu_Address_Street_2, pu_Address_Suburb, pu_Address_State, pu_Address_PostalCode, pu_Address_Country, deToCompanyName, puPickUpAvailFrom_Date, pu_PickUp_By_Date, vx_serviceName, de_to_Contact_F_LName, de_to_PickUp_Instructions_Address, de_to_Pick_Up_Instructions_Contact,  de_To_Address_Street_1, de_To_Address_Street_2, de_To_Address_Suburb, de_To_Address_State, de_To_Address_PostalCode, de_To_Address_Country, de_to_Contact_FName, de_to_Contact_Lname, de_to_Phone_Main, vx_account_code, s_06_LatestDeliveryDateTimeFinal, vx_fp_pu_eta_time, vx_fp_del_eta_time FROM `dme_bookings` WHERE id={id}  ORDER BY dme_bookings.pk_booking_id ASC LIMIT 0,1"
        cursor.execute(sql)
        result = cursor.fetchall()
        if result is None:
            print('@102 - booking empty')
            return None
        else:
            if len(result) > 0:
                return result[0]
            else:
                return None

def get_booking_lines(mysqlcon, booking_id):
    with mysqlcon.cursor() as cursor:
        sql = "SELECT e_qty, e_item_type, e_item, e_dimWidth, e_dimLength, e_dimHeight, e_Total_KG_weight, client_item_reference, e_dangerousGoods, e_1_Total_dimCubicMeter, e_weightUOM FROM dme_booking_lines WHERE fk_booking_id = %s"
        adr = (booking_id, )
        cursor.execute(sql, adr)
        result = cursor.fetchall()
        if result is None:
            print('@102 - booking empty')
            return None
        else:
            return result

def get_label_settings( dimension_length, dimension_width ):
    with mysqlcon.cursor() as cursor:
        sql = "SELECT font_family, font_size_small, font_size_medium, font_size_large, label_dimension_length, label_dimension_width, label_image_size_length, label_image_size_width, barcode_dimension_length, barcode_dimension_width FROM label_settings WHERE label_dimension_length = %s AND label_dimension_width = %s"
        adr = ( dimension_length, dimension_width )
        cursor.execute(sql, adr)
        result = cursor.fetchone()
        if result is None:
            sql = "INSERT INTO label_settings (font_family, font_size_small, font_size_medium, font_size_large, label_dimension_length, label_dimension_width, label_image_size_length, label_image_size_width, barcode_dimension_length, barcode_dimension_width) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            adr = ( dimension_length, dimension_width )
            cursor.execute(sql, adr)
            return None
        else:
            return result

def myFirstPage(canvas, doc):
    canvas.saveState()
    canvas.rotate(180)
    canvas.restoreState()


def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.rotate(90)
    canvas.restoreState()

from reportlab.platypus.flowables import Flowable
from reportlab.platypus.flowables import Image

class RotatedImage(Image):

    def wrap(self,availWidth,availHeight):
        h, w = Image.wrap(self,availHeight,availWidth)
        return w, h
    def draw(self):
        self.canv.rotate(90)
        Image.draw(self)

def build_dhl_label(booking_id):
    mysqlcon = None
    filename = ""
    try:
        mysqlcon = pymysql.connect(host=DB_HOST,
                                   port=DB_PORT,
                                   user=DB_USER,
                                   password=DB_PASS,
                                   db=DB_NAME,
                                   charset='utf8mb4',
                                   cursorclass=pymysql.cursors.DictCursor)
        if not os.path.exists(filepath):
            os.makedirs(filepath)

        
        booking = get_booking(mysqlcon, booking_id)
        print(booking)
        print(booking['pk_booking_id'])
        booking_lines = get_booking_lines(mysqlcon, booking['pk_booking_id'])
        # print('ASC')
                #end db query for fetching data from dme_booking_lines table
        totalQty = 0
        for booking_line in booking_lines:
            totalQty = totalQty + booking_line['e_qty']
        #start pdf file name using naming convention
        #date = datetime.datetime.now().strftime("%Y%m%d")+"_"+datetime.datetime.now().strftime("")
        filename = booking['pu_Address_State'] + "_" + str(booking['v_FPBookingNumber']) + "_"  + str(booking['b_bookingID_Visual']) + ".pdf"
        file = open(filepath+filename, "w") 
        #file.write("Your text goes here") 
        
        #end pdf file name using naming convention

        date = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")

        # label_settings = get_label_settings( 146, 104 )[0]
        # print(label_settings)

        label_settings = {'font_family' : 'Verdana', 'font_size_extra_small' : '5', 'font_size_small' : '7.5', 'font_size_medium' : '9', 'font_size_large': '11', 'font_size_extra_large': '13', 'label_dimension_length': '100', 'label_dimension_width': '150', 'label_image_size_length': '95', 'label_image_size_width': '145', 'barcode_dimension_length': '85', 'barcode_dimension_width': '30', 'barcode_font_size': '18', 'line_height_extra_small':'3', 'line_height_small':'5', 'line_height_medium':'6', 'line_height_large':'8'}

        doc = SimpleDocTemplate(filepath+filename, pagesize = ( float(label_settings['label_dimension_length']) * mm, float(label_settings['label_dimension_width']) * mm ), rightMargin = float(float(label_settings['label_dimension_width']) - float(label_settings['label_image_size_width'])) * mm, leftMargin = float(float(label_settings['label_dimension_width']) - float(label_settings['label_image_size_width'])) * mm, topMargin = float(float(label_settings['label_dimension_length']) - float(label_settings['label_image_size_length'])) * mm, bottomMargin = float(float(label_settings['label_dimension_length']) - float(label_settings['label_image_size_length'])) * mm)

        document = []

        dme_logo = "/home/administrator/Documents/projects/dme_api/static/DME-LOGO.png"
        dme_im = Image(dme_logo, 30 * mm, 8 * mm)

        Story=[]
        j = 1
        for booking_line in booking_lines:
            for k in range(booking_line["e_qty"]):

                tbl_data1 = [
                    [
                        dme_im
                    ],
                    [
                        Paragraph('<font size=%s><b>Pickup up by :</b> %s </font>' % (label_settings['font_size_extra_small'], (booking["vx_freight_provider"]) if (booking["vx_freight_provider"]) else ''), style_left)
                    ]
                ]

                t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ), rowHeights=(  float(label_settings['line_height_large']) * mm, float(label_settings['line_height_extra_small']) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ('VALIGN',(0,0),(0,-1),'TOP'),
                    ])

                tbl_data2 = [
                    [
                        Paragraph('<font size=%s><b>%s:</b></font>' % (label_settings['font_size_small'], 'CONNOTE'), style_left)
                    ],
                    [
                        Paragraph('<font size=%s> %s</font>' % (label_settings['font_size_medium'], booking["v_FPBookingNumber"]), style_left)
                    ]
                ]

                t2 = Table(tbl_data2, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ), rowHeights=(  float(label_settings['line_height_medium']) * mm, float(label_settings['line_height_large']) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ('VALIGN',(0,0),(0,-1),'TOP'),
                    ])
                barcode = str(j).zfill(2)

                tbl_data3 = [
                    [
                        Paragraph('<font size=%s><b>%s</b></font>' % (label_settings['font_size_small'], 'AUTHORITY TO LEAVE'), style_center)
                    ],
                    [
                        code128.Code128( barcode, barHeight = 6 * mm, barWidth = 1.2, humanReadable = True)
                    ]
                ]

                t3 = Table(tbl_data3, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ), rowHeights=( float(label_settings['line_height_medium']) * mm, float(label_settings['line_height_large']) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ('VALIGN',(0,0),(0,-1),'TOP'),
                    ])

                data = [[t1, t2, t3]]

                t1_w = float(label_settings['label_image_size_length'])*(1/3) * mm
                t2_w = float(label_settings['label_image_size_length'])*(1/3) * mm
                t3_w = float(label_settings['label_image_size_length'])*(1/3) * mm

                shell_table = Table(data, colWidths=[t1_w, t2_w, t2_w], style = [
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ])

                Story.append(shell_table)

                Story.append(Spacer(1, 20))
                

                tbl_data1 = [
                    [
                        Paragraph('<font size=%s><b>TO:</b> %s %s</font>' % (label_settings['font_size_medium'], booking["de_to_Contact_F_LName"],  (booking["puCompany"]) if (booking["puCompany"]) else ''), style_left)
                    ],
                    [
                        Paragraph('<font size=%s>  %s</font>' % (label_settings['font_size_medium'],booking["de_To_Address_Street_1"]), style_left),
                        Paragraph('<font size=%s>  %s</font>' % (label_settings['font_size_medium'],booking["de_To_Address_Street_2"]), style_left)
                    ],
                    [
                        Paragraph('<font size=%s>  %s</font> ' % (label_settings['font_size_medium'], ''), style_left)
                    ],
                    [
                        Paragraph('<font size=%s>  %s</font> ' % (label_settings['font_size_medium'], booking["de_To_Address_Suburb"]), style_left),
                        Paragraph('<font size=%s>  %s</font> ' % (label_settings['font_size_medium'], booking["de_To_Address_State"]), style_left),
                        Paragraph('<font size=%s>  %s</font> ' % (label_settings['font_size_medium'], booking["de_To_Address_PostalCode"]), style_left)
                    ]
                ]

                t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ),  rowHeights=( float(label_settings['line_height_extra_small']) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ])

                Story.append(t1)
                Story.append(Spacer(1, 5))

                tbl_data1 = [
                    [
                        Paragraph('<font size=%s><b>PH:</b> %s</font>' % (label_settings['font_size_medium'], booking["de_to_Phone_Main"]), style_left)
                    ]
                ]

                t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ])

                tbl_data2 = [
                    [
                        Paragraph('<font size=%s>%s</font>' % (label_settings['font_size_extra_large'], booking["de_To_Address_Suburb"]), style_left),
                        Paragraph('<font size=%s>%s</font>' % (label_settings['font_size_extra_large'], booking["de_To_Address_PostalCode"]), style_left)
                    ]
                ]

                t2 = Table(tbl_data2, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    
                    ])

                data = [[t1, t2]]

                t1_w = float(label_settings['label_image_size_length'])*(1/2) * mm
                t2_w = float(label_settings['label_image_size_length'])*(1/2) * mm

                shell_table = Table(data, colWidths=[t1_w, t2_w], style = [
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ])

                Story.append(shell_table)

                Story.append(Spacer(1, 5))

                tbl_data1 = [
                    [
                        Paragraph('<font size=%s><b>AU</b></font>' % (label_settings['font_size_extra_large']), style_left),
                        Paragraph('<font size=%s><b>R1</b></font>' % (label_settings['font_size_extra_large']), style_left),
                        Paragraph('<font size=%s><b>R2</b></font>' % (label_settings['font_size_extra_large']), style_left),
                        Paragraph('<font size=%s><b>TT</b></font>' % (label_settings['font_size_extra_large']), style_left),
                        Paragraph('<font size=%s><b>RTE</b></font>' % (label_settings['font_size_extra_large']), style_left)
                    ]
                ]

                t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (1/5) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ])

                Story.append(t1)
                Story.append(Spacer(1, 5))

                barcode = 'PRD'+booking["de_To_Address_PostalCode"]+'R1'

                tbl_data1 = [
                    [
                        code128.Code128( barcode, barHeight = 22 * mm, barWidth = 1.3, humanReadable = True)
                    ]
                ]

                t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (2/3) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ])

                d = Drawing(80,80)
                d.add(Rect(0,0,0,0,strokeWidth=1,fillColor=None))
                d.add(QrCodeWidget(value='01234567'))
                
                tbl_data2 = [
                    [d],
                ]
                t2 = Table(tbl_data2, colWidths = ( float(label_settings['label_image_size_length']) * (1/3) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ])

                data = [[t1, t2]]

                t1_w = float(label_settings['label_image_size_length']) * (2/3) * mm
                t2_w = float(label_settings['label_image_size_length']) * (1/3) * mm

                shell_table = Table(data, colWidths=[t1_w, t2_w], style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ])
                Story.append(shell_table)

                Story.append(Spacer(1, 5))

                tbl_data1 = [
                    [
                        Paragraph('<font size=%s><b>FROM:</b> %s <b>PH:</b> %s</font>' % ( label_settings['font_size_medium'], (booking["pu_Contact_F_L_Name"]) if (booking["pu_Contact_F_L_Name"]) else '', str(booking['pu_Phone_Main']) if booking['pu_Phone_Main'] else '' ), style_left)
                    ],
                    [
                        Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], str(booking['pu_Address_Street_1']) if booking['pu_Address_Street_1'] else '', str(booking['pu_Address_Street_2']) if booking['pu_Address_Street_2'] else ''), style_left),
                        
                    ],
                    [
                        Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_medium'], str(booking['pu_Address_Suburb']) if booking['pu_Address_Suburb'] else '', str(booking['pu_Address_PostalCode']) if booking['pu_Address_PostalCode'] else ''), style_left),
                        
                    ]
                ]
                t1 = Table(tbl_data1, colWidths=( ( float(label_settings['label_image_size_length']) ) * mm ), rowHeights=( float(label_settings['line_height_medium']) * mm ), style = [
                    ('VALIGN',(0, 0),(0, -1),'TOP'),
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    # ('BOX', (0, 0), (-1, -1), 1, colors.black)
                    ])

                Story.append(t1)

                tbl_data1 = [
                    [
                        Paragraph('<font size=%s>%s %s</font>' % (label_settings['font_size_extra_small'], str(booking['de_to_PickUp_Instructions_Address']) if booking['de_to_PickUp_Instructions_Address'] else '', str(booking['de_to_Pick_Up_Instructions_Contact']) if booking['de_to_Pick_Up_Instructions_Contact'] else ''), style_left)
                    ]
                ]

                t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * (2/3) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ])

                tbl_data2 = [
                    [
                        Paragraph('<font size=%s>BOOK-IN:</font>' % (label_settings['font_size_medium']), style_left),
                    ],
                    [
                        Paragraph('<font size=%s>NOT BEFORE: %s</font>' % (label_settings['font_size_medium'], booking["vx_fp_pu_eta_time"].strftime("%d/%m/%y") if booking["vx_fp_pu_eta_time"] else 'N/A'), style_left),
                    ],
                    [
                        Paragraph('<font size=%s>NOT AFTER: %s</font>' % (label_settings['font_size_medium'], booking["vx_fp_del_eta_time"].strftime("%d/%m/%y") if booking["vx_fp_del_eta_time"] else 'N/A'), style_left)
                    ]
                ]

                t2 = Table(tbl_data2, colWidths=( float(label_settings['label_image_size_length']) * (1/3) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    
                    ])

                data = [[t1, t2]]

                t1_w = float(label_settings['label_image_size_length'])*(2/3) * mm
                t2_w = float(label_settings['label_image_size_length'])*(1/3) * mm

                shell_table = Table(data, colWidths=[t1_w, t2_w], style = [
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    # ('SPAN',(0,0),(0,-1)),
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    # ('BOX', (0, 0), (-1, -1), 1, colors.black)
                    ])

                Story.append(shell_table)
                
                tbl_data1 = [
                    [
                        Paragraph('<font size=%s>DATE: %s UNIT: %s ITEM: %s OF %s WEIGHT: %s CUBE: %s</font>' % (label_settings['font_size_small'], booking["b_dateBookedDate"].strftime("%d/%m/%y") if booking["b_dateBookedDate"] else 'N/A', booking_line["e_weightUOM"],j, totalQty, booking_line['e_Total_KG_weight'], booking_line["e_1_Total_dimCubicMeter"]), style_center)
                    ]
                ]

                t1 = Table(tbl_data1, colWidths=( float(label_settings['label_image_size_length']) * mm ), style = [
                    ('TOPPADDING',(0,0),(-1,-1), 0),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 0),
                    ('LEFTPADDING',(0,0),(-1,-1), 0),
                    ('RIGHTPADDING',(0,0),(-1,-1), 0),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ])

                Story.append(t1)

                barcode = booking["v_FPBookingNumber"]+'DESC'+str(k+1).zfill(10)+booking["de_To_Address_PostalCode"]

                tbl_data = [
                    [
                        code128.Code128( barcode, barHeight = 20 * mm, barWidth = .9, humanReadable = True )
                    ],
                ]

                t1 = Table(tbl_data, colWidths=( ( float(label_settings['label_image_size_length']) ) * mm ), style = [
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ('VALIGN',(0,0),(0,-1),'TOP'),
                    ('TOPPADDING',(0,0),(-1,-1), 5),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 5),
                    ('LEFTPADDING',(0,0),(0,-1), 0),
                    ('RIGHTPADDING',(0,0),(0,-1), 0),
                    # ('BOX', (0, 0), (-1, -1), 1, colors.black)
                    ])
                
                Story.append(t1)

                Story.append(PageBreak())
            
                j+= 1
                doc.build(Story, onFirstPage = myFirstPage, onLaterPages=myLaterPages)
                file.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(dir(exc_type), fname, exc_tb.tb_lineno)
        #print("Error: unable to fecth data")
        print("Error1: "+str(e))

    print('#901 - Finished %s' % datetime.datetime.now())

    if mysqlcon is not None:
        mysqlcon.close()
    return filename