import sys, time
import os
import errno
import datetime
import uuid
import redis
import urllib, requests
import json
import pymysql, pymysql.cursors
import redis
import xml.etree.ElementTree as xml
import pysftp
import shutil
import xlsxwriter as xlsxwriter
import smtplib
import pytz
import logging
from pytz import timezone
from datetime import timedelta
from os.path import basename

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter, landscape, A6
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
    Table,
)
from reportlab.platypus.flowables import Spacer, HRFlowable, PageBreak, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.graphics.barcode import (
    code39,
    code128,
    code93,
    createBarcodeDrawing,
    eanbc,
    qr,
    usps,
)
from reportlab.graphics.shapes import Drawing
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.lib import colors

from django.core.mail import send_mail
from django.conf import settings
from .models import *

if settings.ENV == "local":
    production = False  # Local
else:
    production = True  # Dev

if production:
    DB_HOST = "deliverme-db.cgc7xojhvzjl.ap-southeast-2.rds.amazonaws.com"
    DB_USER = "fmadmin"
    DB_PASS = "oU8pPQxh"
    DB_PORT = 3306

    if settings.ENV == "dev":
        DB_NAME = "dme_db_dev"  # Dev
    elif settings.ENV == "prod":
        DB_NAME = "dme_db_prod"  # Prod
else:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASS = "root"
    DB_PORT = 3306
    DB_NAME = "deliver_me"

logger = logging.getLogger("dme_api")

redis_host = "localhost"
redis_port = 6379
redis_password = ""

### TAS constants ###
# ACCOUNT_CODE = "AATEST"
ACCOUNT_CODE = "SEAWAPO"
styles = getSampleStyleSheet()
style_right = ParagraphStyle(name="right", parent=styles["Normal"], alignment=TA_RIGHT)
style_left = ParagraphStyle(name="left", parent=styles["Normal"], alignment=TA_LEFT)
style_center = ParagraphStyle(
    name="center", parent=styles["Normal"], alignment=TA_CENTER
)
style_cell = ParagraphStyle(name="smallcell", fontSize=6, leading=6)
styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY))
ROWS_PER_PAGE = 20
#####################


def redis_con():
    try:
        redisCon = redis.StrictRedis(
            host=redis_host, port=redis_port, password=redis_password
        )
    except:
        # print('Redis DB connection error!')
        exit(1)

    return redisCon


def save2Redis(key, value):
    redisCon = redis_con()
    redisCon.set(key, value)


def clearFileCheckHistory(filename):
    redisCon = redis_con()
    errorCnt = redisCon.get(filename)
    redisCon.delete(filename)

    if errorCnt is not None:
        for index in range(int(errorCnt)):
            redisCon.delete(filename + str(index))


def getFileCheckHistory(filename):
    redisCon = redis_con()
    errorCnt = redisCon.get(filename)
    errors = []

    if errorCnt is None:
        return 0
    else:
        if int(errorCnt) > 0:
            for index in range(int(errorCnt)):
                errors.append(redisCon.get(filename + str(index)).decode("utf-8"))
        elif int(errorCnt) == 0:
            return "success"

        return error


def send_email(send_to, subject, text, files=None, server="localhost", use_tls=True):
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_HOST_USER
    msg["To"] = COMMASPACE.join(send_to)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject

    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(fil.read(), Name=basename(f))
        part["Content-Disposition"] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)

    if use_tls:
        smtp.starttls()

    smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    smtp.sendmail(settings.EMAIL_HOST_USER, send_to, msg.as_string())
    smtp.close()


def upload_sftp(
    host,
    username,
    password,
    sftp_filepath,
    local_filepath,
    local_filepath_dup,
    filename,
):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(
        host="edi.alliedexpress.com.au",
        username="delvme.external",
        password="987899e64",
        cnopts=cnopts,
    ) as sftp_con:
        with sftp_con.cd(sftp_filepath):
            sftp_con.put(local_filepath + filename)
            sftp_file_size = sftp_con.lstat(sftp_filepath + filename).st_size
            local_file_size = os.stat(local_filepath + filename).st_size

            if sftp_file_size == local_file_size:
                if not os.path.exists(local_filepath_dup):
                    os.makedirs(local_filepath_dup)
                shutil.move(local_filepath + filename, local_filepath_dup + filename)

        sftp_con.close()


def get_sydney_now_time(return_type="char"):
    sydney_tz = pytz.timezone("Australia/Sydney")
    sydney_now = sydney_tz.localize(datetime.utcnow())
    sydney_now = sydney_now + timedelta(hours=10)

    if return_type == "char":
        return sydney_now.strftime("%Y-%m-%d %H:%M:%S")
    elif return_type == "datetime":
        return sydney_now


def get_available_bookings(mysqlcon, booking_ids):
    where_clause = " WHERE "
    for id in booking_ids:
        where_clause = where_clause + "id = " + str(id) + " OR "
    where_clause = where_clause[:-4]

    with mysqlcon.cursor() as cursor:
        sql = "SELECT * FROM `dme_bookings` " + where_clause + " ORDER BY `id` ASC"
        cursor.execute(sql)
        result = cursor.fetchall()
        return result


def get_available_booking_lines(mysqlcon, booking):
    with mysqlcon.cursor() as cursor:
        sql = "SELECT * FROM `dme_booking_lines` WHERE `fk_booking_id`=%s"
        cursor.execute(sql, (booking["pk_booking_id"]))
        result = cursor.fetchall()
        # print('Avaliable Booking Lines cnt: ', len(result))
        return result


def make_3digit(num):
    if num > 0 and num < 10:
        return "00" + str(num)
    elif num > 9 and num < 100:
        return "0" + str(num)
    elif num > 99 and num < 1000:
        return str(num)
    else:
        return str("ERROR: Number is bigger than 999")


def wrap_in_quote(string):
    return '"' + str(string) + '"'


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
                booking_lines = get_available_booking_lines(mysqlcon, booking)
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

                if booking["de_to_PickUp_Instructions_Address"] is None:
                    h26 = ""
                else:
                    h26 = wrap_in_quote(
                        booking.get("de_to_PickUp_Instructions_Address")
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
            "unique_identifier, ref1, ref2, receiver_name, receiver_address1, \
            receiver_address2, receiver_address3, receiver_address4, receiver_locality, receiver_state, \
            receiver_postcode, weight, length, width, height, \
            receiver_contact, receiver_phone_no, receiver_email, pack_unit_code, pack_unit_description, \
            items, special_instructions, consignment_prefix, consignment_number, transporter_code, \
            service_code, sender_code, sender_warehouse_code, freight_payer, freight_label_number, \
            barcode\n"
        )

        # Write Each Line
        comma = ","
        newLine = "\n"
        fp_info = Fp_freight_providers.objects.get(fp_company_name="DHL")
        fp_carriers = FP_carriers.objects.filter(fk_fp=fp_info.id)

        if len(bookings) > 0:
            for booking in bookings:
                booking_lines = get_available_booking_lines(mysqlcon, booking)

                if booking["b_client_order_num"] is None:
                    h00 = ""
                else:
                    h00 = str(booking.get("b_client_order_num"))

                if booking["b_clientReference_RA_Numbers"] is None:
                    h01 = ""
                else:
                    h01 = str(booking.get("b_clientReference_RA_Numbers"))

                h02 = "ref2"

                if booking["deToCompanyName"] is None:
                    h03 = ""
                else:
                    h03 = str(booking.get("deToCompanyName"))

                if booking["de_To_Address_Street_1"] is None:
                    h04 = ""
                else:
                    h04 = str(booking.get("de_To_Address_Street_1"))

                if booking["de_To_Address_Street_2"] is None:
                    h05 = ""
                else:
                    h05 = str(booking.get("de_To_Address_Street_2"))

                h06 = ""
                h07 = ""

                if booking["de_To_Address_Suburb"] is None:
                    h08 = ""
                else:
                    h08 = str(booking.get("de_To_Address_Suburb"))

                if booking["de_To_Address_State"] is None:
                    h09 = ""
                else:
                    h09 = str(booking.get("de_To_Address_State"))

                if booking["de_To_Address_PostalCode"] is None:
                    h10 = ""
                else:
                    h10 = str(booking.get("de_To_Address_PostalCode"))

                h15 = "receiver_contact"

                if booking["de_to_Phone_Main"] is None:
                    h16 = ""
                else:
                    h16 = str(booking.get("de_to_Phone_Main"))

                if booking["de_Email"] is None:
                    h17 = ""
                else:
                    h17 = str(booking.get("de_Email"))

                if booking["de_to_PickUp_Instructions_Address"] is None:
                    h21 = ""
                else:
                    h21 = wrap_in_quote(
                        booking.get("de_to_PickUp_Instructions_Address")
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
                    h22 = "DMS" if fp_zone.carrier == "DHLSFS" else "DMB"

                    h24 = fp_zone.carrier
                    h25 = fp_zone.service
                    h26 = fp_zone.sender_code
                    h27 = "OWNSITE"  # HARDCODED - "sender_warehouse_code"
                    h28 = "S"

                    if len(booking_lines) > 0:
                        for booking_line in booking_lines:
                            eachLineText = ""
                            h11 = ""
                            if (
                                booking_line["e_weightUOM"] is not None
                                and booking_line["e_weightPerEach"] is not None
                            ):
                                if (
                                    booking_line["e_weightUOM"].upper() == "GRAM"
                                    or booking_line["e_weightUOM"].upper() == "GRAMS"
                                ):
                                    h11 = str(
                                        booking_line["e_qty"]
                                        * booking_line["e_weightPerEach"]
                                        / 1000
                                    )
                                elif (
                                    booking_line["e_weightUOM"].upper() == "TON"
                                    or booking_line["e_weightUOM"].upper() == "TONS"
                                ):
                                    h11 = str(
                                        booking_line["e_qty"]
                                        * booking_line["e_weightPerEach"]
                                        * 1000
                                    )
                                else:
                                    h11 = str(
                                        booking_line["e_qty"]
                                        * booking_line["e_weightPerEach"]
                                    )

                            if booking_line["e_dimLength"] is None:
                                h12 = ""
                            else:
                                h12 = str(booking_line.get("e_dimLength"))

                            if booking_line["e_dimWidth"] is None:
                                h13 = ""
                            else:
                                h13 = str(booking_line.get("e_dimWidth"))

                            if booking_line["e_dimHeight"] is None:
                                h14 = ""
                            else:
                                h14 = str(booking_line.get("e_dimHeight"))

                            # if booking_line["e_pallet_type"] is None:
                            #     h18 = ""
                            # else:
                            #     h18 = str(booking_line.get("e_pallet_type"))

                            # if booking_line["e_type_of_packaging"] is None:
                            #     h19 = ""
                            # else:
                            #     h19 = str(booking_line.get("e_type_of_packaging"))

                            h18 = "PAL"  # Hardcoded
                            h19 = "Pallet"  # Hardcoded

                            if booking_line["e_qty"] is None:
                                h20 = ""
                            else:
                                h20 = str(booking_line.get("e_qty"))

                            fp_carrier = fp_carriers.get(carrier=fp_zone.carrier)
                            h23 = h22 + str(
                                fp_carrier.connote_start_value
                                + fp_carrier.current_value
                            )

                            # Update booking while build CSV for DHL
                            with mysqlcon.cursor() as cursor:
                                sql2 = "UPDATE dme_bookings \
                                        SET v_FPBookingNumber = %s, vx_freight_provider_carrier = %s, b_error_Capture = %s \
                                        WHERE id = %s"
                                adr2 = (h23, fp_zone.carrier, None, booking["id"])
                                cursor.execute(sql2, adr2)
                                mysqlcon.commit()

                            h29 = (
                                h22
                                + "L00"
                                + str(
                                    fp_carrier.label_start_value
                                    + fp_carrier.current_value
                                )
                            )

                            # Update fp_carrier current value
                            fp_carrier.current_value += 1
                            fp_carrier.save()

                            h30 = h23 + h29 + booking["de_To_Address_PostalCode"]

                            eachLineText += (
                                h00
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
                                + comma
                                + h30
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

    return has_error


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

    bookings = get_available_bookings(mysqlcon, booking_ids)

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

    if production:
        if vx_freight_provider == "cope":
            f = open(
                "/home/cope_au/dme_sftp/cope_au/pickup_ext/cope_au/" + csv_name, "w"
            )
        elif vx_freight_provider == "dhl":
            f = open(
                "/home/cope_au/dme_sftp/cope_au/pickup_ext/dhl_au/" + csv_name, "w"
            )
    else:
        f = open("/Users/admin/Documents/" + csv_name, "w")

    has_error = csv_write(f, bookings, vx_freight_provider, mysqlcon)
    f.close()

    if has_error:
        os.remove(f.name)

    # print('#901 - Finished %s' % datetime.datetime.now())
    mysqlcon.close()
    return has_error


def get_booked_list(bookings):
    booked_list = []

    for booking in bookings:
        if booking["b_dateBookedDate"] and booking["b_dateBookedDate"] != "":
            booked_list.append(booking["b_bookingID_Visual"])

    return booked_list


def get_manifested_list(bookings):
    manifested_list = []

    for booking in bookings:
        if booking["manifest_timestamp"] is not None:
            manifested_list.append(booking["b_bookingID_Visual"])

    return manifested_list


def get_item_type(i):
    if i:
        if "UHP" in i:
            return "PCR"
        elif "PCR" in i:
            return "PCR"
        elif "LTR" in i:
            return "LTR"
        elif "TBR" in i:
            return "TBR"
        else:
            return "ERROR"
    else:
        return "ERROR"


def build_xml(booking_ids, vx_freight_provider, one_manifest_file):
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

    bookings = get_available_bookings(mysqlcon, booking_ids)
    booked_list = get_booked_list(bookings)

    if len(booked_list) > 0:
        return booked_list

    if vx_freight_provider == "allied":
        # start check if xmls folder exists
        if production:
            local_filepath = "/opt/s3_private/xmls/allied_au/"
            local_filepath_dup = (
                "/opt/s3_private/xmls/allied_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )
        else:
            local_filepath = "/Users/admin/work/goldmine/dme_api/static/xmls/allied_au/"
            local_filepath_dup = (
                "/Users/admin/work/goldmine/dme_api/static/xmls/allied_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )

        if not os.path.exists(local_filepath):
            os.makedirs(local_filepath)
        # end check if xmls folder exists

        i = 1
        for booking in bookings:
            try:
                # start db query for fetching data from dme_booking_lines table
                sql1 = "SELECT pk_lines_id, e_qty, e_item_type, e_item, e_dimWidth, e_dimLength, e_dimHeight, e_Total_KG_weight \
                        FROM dme_booking_lines \
                        WHERE fk_booking_id = %s"
                adr1 = (booking["pk_booking_id"],)
                mycursor.execute(sql1, adr1)
                booking_lines = mycursor.fetchall()

                # start calculate total item quantity and total item weight
                totalQty = 0
                totalWght = 0
                for booking_line in booking_lines:
                    totalQty = totalQty + booking_line["e_qty"]
                    totalWght = totalWght + booking_line["e_Total_KG_weight"]
                # start calculate total item quantity and total item weight

                # start xml file name using naming convention
                date = (
                    datetime.now().strftime("%Y%m%d")
                    + "_"
                    + datetime.now().strftime("%H%M%S")
                )
                filename = "AL_HANALT_" + date + "_" + str(i) + ".xml"
                i += 1
                # end xml file name using naming convention

                # start formatting xml file and putting data from db tables
                root = xml.Element(
                    "AlTransportData",
                    **{"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"},
                )
                consignmentHeader = xml.Element("ConsignmentHeader")
                root.append(consignmentHeader)
                chargeAccount = xml.SubElement(consignmentHeader, "ChargeAccount")
                chargeAccount.text = "HANALT"
                senderName = xml.SubElement(consignmentHeader, "SenderName")
                senderName.text = "Hankook"
                senderAddressLine1 = xml.SubElement(
                    consignmentHeader, "SenderAddressLine1"
                )
                senderAddressLine1.text = booking["pu_Address_Street_1"]
                senderLocality = xml.SubElement(consignmentHeader, "SenderLocality")
                senderLocality.text = booking["pu_Address_Suburb"]
                senderState = xml.SubElement(consignmentHeader, "SenderState")
                senderState.text = booking["pu_Address_State"]
                senderPostcode = xml.SubElement(consignmentHeader, "SenderPostcode")
                senderPostcode.text = booking["pu_Address_PostalCode"]

                companyName = booking["deToCompanyName"].replace("<", "")
                companyName = companyName.replace(">", "")
                companyName = companyName.replace('"', "")
                companyName = companyName.replace("'", "")
                companyName = companyName.replace("&", "and")

                consignmentShipments = xml.Element("ConsignmentShipments")
                root.append(consignmentShipments)
                consignmentShipment = xml.SubElement(
                    consignmentShipments, "ConsignmentShipment"
                )
                ConsignmentNumber = xml.SubElement(
                    consignmentShipment, "ConsignmentNumber"
                )
                ConsignmentNumber.text = booking["pk_booking_id"]
                DespatchDate = xml.SubElement(consignmentShipment, "DespatchDate")
                DespatchDate.text = str(booking["puPickUpAvailFrom_Date"])
                CarrierService = xml.SubElement(consignmentShipment, "CarrierService")
                CarrierService.text = booking["vx_serviceName"]
                totalQuantity = xml.SubElement(consignmentShipment, "totalQuantity")
                totalQuantity.text = str(totalQty)
                totalWeight = xml.SubElement(consignmentShipment, "totalWeight")
                totalWeight.text = str(totalWght)
                ReceiverName = xml.SubElement(consignmentShipment, "ReceiverName")
                ReceiverName.text = companyName
                ReceiverAddressLine1 = xml.SubElement(
                    consignmentShipment, "ReceiverAddressLine1"
                )
                ReceiverAddressLine1.text = booking["de_To_Address_Street_1"]
                ReceiverLocality = xml.SubElement(
                    consignmentShipment, "ReceiverLocality"
                )
                ReceiverLocality.text = booking["de_To_Address_Suburb"]
                ReceiverState = xml.SubElement(consignmentShipment, "ReceiverState")
                ReceiverState.text = booking["de_To_Address_State"]
                ReceiverPostcode = xml.SubElement(
                    consignmentShipment, "ReceiverPostcode"
                )
                ReceiverPostcode.text = booking["de_To_Address_PostalCode"]
                ItemsShipment = xml.SubElement(consignmentShipment, "ItemsShipment")

                for booking_line in booking_lines:
                    Item = xml.SubElement(ItemsShipment, "Item")
                    Quantity = xml.SubElement(Item, "Quantity")
                    Quantity.text = str(booking_line["e_qty"])
                    ItemType = xml.SubElement(Item, "ItemType")
                    ItemType.text = get_item_type(booking_line["e_item_type"])
                    ItemDescription = xml.SubElement(Item, "ItemDescription")
                    ItemDescription.text = booking_line["e_item"]

                    Width = xml.SubElement(Item, "Width")
                    if (
                        booking_line["e_dimWidth"] == None
                        or booking_line["e_dimWidth"] == ""
                        or booking_line["e_dimWidth"] == 0
                    ):
                        Width.text = str("1")

                        sql2 = "UPDATE dme_booking_lines set e_dimWidth = %s WHERE pk_lines_id = %s"
                        adr2 = (1, booking_line["pk_lines_id"])
                        mycursor.execute(sql2, adr2)
                        mysqlcon.commit()
                    else:
                        Width.text = str(booking_line["e_dimWidth"])

                    Length = xml.SubElement(Item, "Length")
                    if (
                        booking_line["e_dimLength"] == None
                        or booking_line["e_dimLength"] == ""
                        or booking_line["e_dimLength"] == 0
                    ):
                        Length.text = str("1")

                        sql2 = "UPDATE dme_booking_lines set e_dimLength = %s WHERE pk_lines_id = %s"
                        adr2 = (1, booking_line["pk_lines_id"])
                        mycursor.execute(sql2, adr2)
                        mysqlcon.commit()
                    else:
                        Length.text = str(booking_line["e_dimLength"])

                    Height = xml.SubElement(Item, "Height")
                    if (
                        booking_line["e_dimHeight"] == None
                        or booking_line["e_dimHeight"] == ""
                        or booking_line["e_dimHeight"] == 0
                    ):
                        Height.text = str("1")

                        sql2 = "UPDATE dme_booking_lines set e_dimHeight = %s WHERE pk_lines_id = %s"
                        adr2 = (1, booking_line["pk_lines_id"])
                        mycursor.execute(sql2, adr2)
                        mysqlcon.commit()
                    else:
                        Height.text = str(booking_line["e_dimHeight"])

                    DeadWeight = xml.SubElement(Item, "DeadWeight")
                    DeadWeight.text = (
                        format(
                            booking_line["e_Total_KG_weight"] / booking_line["e_qty"],
                            ".2f",
                        )
                        if booking_line["e_qty"] > 0
                        else 0
                    )

                    SSCCs = xml.SubElement(Item, "SSCCs")
                    SSCC = xml.SubElement(SSCCs, "SSCC")
                    SSCC.text = booking["pk_booking_id"]
                # end formatting xml file and putting data from db tables

                # start writting data into xml files
                tree = xml.ElementTree(root)
                with open(local_filepath + filename, "wb") as fh:
                    tree.write(fh, encoding="UTF-8", xml_declaration=True)

                # start copying xml files to sftp server
                # sftp_filepath = "/home/NSW/delvme.external/indata/"
                # cnopts = pysftp.CnOpts()
                # cnopts.hostkeys = None
                # with pysftp.Connection(host="edi.alliedexpress.com.au", username="delvme.external", password="987899e64", cnopts=cnopts) as sftp_con:
                #     with sftp_con.cd(sftp_filepath):
                #         sftp_con.put(local_filepath + filename)
                #         sftp_file_size = sftp_con.lstat(sftp_filepath + filename).st_size
                #         local_file_size = os.stat(local_filepath + filename).st_size

                #         if sftp_file_size == local_file_size:
                #             if not os.path.exists(local_filepath_dup):
                #                 os.makedirs(local_filepath_dup)
                #             shutil.move(local_filepath + filename, local_filepath_dup + filename)

                #     sftp_con.close()
                # end copying xml files to sftp server

                # start update booking status in dme_booking table
                sql2 = "UPDATE dme_bookings set b_status = %s, b_dateBookedDate = %s WHERE pk_booking_id = %s"
                adr2 = ("Booked", get_sydney_now_time(), booking["pk_booking_id"])
                mycursor.execute(sql2, adr2)
                mysqlcon.commit()
            except Exception as e:
                # print('@300 Allied XML - ', e)
                return e
    elif vx_freight_provider == "TASFR":
        # start check if xmls folder exists
        if production:
            local_filepath = "/opt/s3_private/xmls/tas_au/"
            local_filepath_dup = (
                "/opt/s3_private/xmls/tas_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )
        else:
            local_filepath = "/Users/admin/work/goldmine/dme_api/static/xmls/tas_au/"
            local_filepath_dup = (
                "/Users/admin/work/goldmine/dme_api/static/xmls/tas_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )

        if not os.path.exists(local_filepath):
            os.makedirs(local_filepath)
        # end check if xmls folder exists

        # start loop through data fetched from dme_bookings table
        i = 1
        if one_manifest_file == 0:
            for booking in bookings:
                try:
                    dme_manifest_log = Dme_manifest_log.objects.filter(
                        fk_booking_id=booking["pk_booking_id"]
                    ).last()
                    manifest_number = dme_manifest_log.manifest_number
                    fp_info = Fp_freight_providers.objects.get(fp_company_name="Tas")
                    initial_connot_index = int(fp_info.new_connot_index) - len(bookings)
                    # start db query for fetching data from dme_booking_lines table
                    booking_lines = get_available_booking_lines(mysqlcon, booking)
                    # end db query for fetching data from dme_booking_lines table

                    # start calculate total item quantity and total item weight
                    totalQty = 0
                    totalWght = 0
                    for booking_line in booking_lines:
                        totalQty = totalQty + booking_line["e_qty"]
                        totalWght = totalWght + booking_line["e_Total_KG_weight"]
                    # start calculate total item quantity and total item weight

                    # start xml file name using naming convention
                    filename = (
                        "TAS_FP_"
                        + str(datetime.now().strftime("%d-%m-%Y %H_%M_%S"))
                        + "_"
                        + str(i)
                        + ".xml"
                    )

                    # end xml file name using naming convention

                    # start formatting xml file and putting data from db tables
                    root = xml.Element(
                        "fd:Manifest",
                        **{
                            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                            "xmlns:fd": "http://www.ezysend.com/FreightDescription/2.0",
                            "Version": "2.0",
                            "Action": "Submit",
                            "Number": manifest_number,
                            "Type": "Outbound",
                            "xsi:schemaLocation": "http://www.ezysend.com/FreightDescription/2.0 http://www.ezysend.com/EDI/FreightDescription/2.0/schema.xsd",
                        },
                    )

                    # IndependentContainers = xml.Element("fd:IndependentContainers")
                    # root.append(IndependentContainers)
                    # xml.SubElement(IndependentContainers, "fd:Container", **{'Identifier': "IC"+ ACCOUNT_CODE +"00001", 'Volume': "1.02", 'Weight': "200", 'Commodity': "Pallet"})
                    connote_number = ACCOUNT_CODE + str(
                        initial_connot_index + i - 1
                    ).zfill(5)

                    # consignment = xml.Element("fd:Consignment", **{'Number': "DME"+str(booking['b_bookingID_Visual'])})
                    consignment = xml.Element(
                        "fd:Consignment", **{"Number": connote_number}
                    )
                    root.append(consignment)

                    Carrier = xml.SubElement(consignment, "fd:Carrier")
                    Carrier.text = booking["vx_freight_provider"]
                    AccountCode = xml.SubElement(consignment, "fd:AccountCode")
                    AccountCode.text = ACCOUNT_CODE

                    senderName = xml.SubElement(
                        consignment, "fd:Sender", **{"Name": ACCOUNT_CODE}
                    )
                    senderAddress = xml.SubElement(senderName, "fd:Address")
                    senderAddressLine1 = xml.SubElement(senderAddress, "fd:Address1")
                    senderAddressLine1.text = booking["pu_Address_Street_1"]
                    senderLocality = xml.SubElement(senderAddress, "fd:Locality")
                    senderLocality.text = booking["pu_Address_Suburb"]
                    senderState = xml.SubElement(senderAddress, "fd:Territory")
                    senderState.text = booking["pu_Address_State"]
                    senderPostcode = xml.SubElement(senderAddress, "fd:PostCode")
                    senderPostcode.text = booking["pu_Address_PostalCode"]
                    senderCountry = xml.SubElement(senderAddress, "fd:Country")
                    senderCountry.text = booking["pu_Address_Country"]

                    companyName = booking["deToCompanyName"].replace("<", "")
                    companyName = companyName.replace(">", "")
                    companyName = companyName.replace('"', "")
                    companyName = companyName.replace("'", "")
                    companyName = companyName.replace("&", "and")

                    ReceiverName = xml.SubElement(
                        consignment,
                        "fd:Receiver",
                        **{"Name": companyName, "Reference": "CUST0001"},
                    )
                    ReceiverAddress = xml.SubElement(ReceiverName, "fd:Address")
                    ReceiverAddressLine1 = xml.SubElement(
                        ReceiverAddress, "fd:Address1"
                    )
                    ReceiverAddressLine1.text = booking["de_To_Address_Street_1"]
                    ReceiverLocality = xml.SubElement(ReceiverAddress, "fd:Locality")
                    ReceiverLocality.text = booking["de_To_Address_Suburb"]
                    ReceiverState = xml.SubElement(ReceiverAddress, "fd:Territory")
                    ReceiverState.text = booking["de_To_Address_State"]
                    ReceiverPostcode = xml.SubElement(ReceiverAddress, "fd:PostCode")
                    ReceiverPostcode.text = booking["de_To_Address_PostalCode"]
                    ReceiverCountry = xml.SubElement(ReceiverAddress, "fd:Country")
                    ReceiverCountry.text = booking["de_To_Address_Country"]

                    ContactName = xml.SubElement(ReceiverName, "fd:ContactName")
                    ContactName.text = (
                        str(booking["de_to_Contact_FName"])
                        if booking["de_to_Contact_FName"]
                        else ""
                    ) + (
                        " " + str(booking["de_to_Contact_Lname"])
                        if booking["de_to_Contact_Lname"]
                        else ""
                    )
                    PhoneNumber = xml.SubElement(ReceiverName, "fd:PhoneNumber")
                    PhoneNumber.text = (
                        str(booking["de_to_Phone_Main"])
                        if booking["de_to_Phone_Main"]
                        else ""
                    )

                    FreightForwarderName = xml.SubElement(
                        consignment, "fd:FreightForwarder", **{"Name": companyName}
                    )
                    FreightForwarderAddress = xml.SubElement(
                        FreightForwarderName, "fd:Address"
                    )
                    FreightForwarderAddressLine1 = xml.SubElement(
                        FreightForwarderAddress, "fd:Address1"
                    )
                    FreightForwarderAddressLine1.text = booking[
                        "de_To_Address_Street_1"
                    ]
                    FreightForwarderLocality = xml.SubElement(
                        FreightForwarderAddress, "fd:Locality"
                    )
                    FreightForwarderLocality.text = booking["de_To_Address_Suburb"]
                    FreightForwarderState = xml.SubElement(
                        FreightForwarderAddress, "fd:Territory"
                    )
                    FreightForwarderState.text = booking["de_To_Address_State"]
                    FreightForwarderPostcode = xml.SubElement(
                        FreightForwarderAddress, "fd:PostCode"
                    )
                    FreightForwarderPostcode.text = booking["de_To_Address_PostalCode"]
                    FreightForwarderCountry = xml.SubElement(
                        FreightForwarderAddress, "fd:Country"
                    )
                    FreightForwarderCountry.text = booking["de_To_Address_Country"]

                    Fragile = xml.SubElement(consignment, "fd:Fragile")
                    Fragile.text = "true"

                    ServiceType = xml.SubElement(consignment, "fd:ServiceType")
                    ServiceType.text = booking["vx_serviceName"]

                    DeliveryWindow = xml.SubElement(
                        consignment,
                        "fd:DeliveryWindow",
                        **{
                            "From": (
                                booking["puPickUpAvailFrom_Date"].strftime("%Y-%m-%d")
                                + "T09:00:00"
                            ),
                            "To": (
                                booking["pu_PickUp_By_Date"].strftime("%Y-%m-%d")
                                + "T17:00:00"
                            )
                            if booking["pu_PickUp_By_Date"] is not None
                            else (
                                booking["puPickUpAvailFrom_Date"].strftime("%Y-%m-%d")
                                + "T17:00:00"
                            ),
                        },
                    )

                    DeliveryInstructions = xml.SubElement(
                        consignment, "fd:DeliveryInstructions"
                    )
                    DeliveryInstructions.text = (
                        str(booking["de_to_PickUp_Instructions_Address"])
                        + " "
                        + str(booking["de_to_Pick_Up_Instructions_Contact"])
                    )

                    # FPBookingNumber = xml.SubElement(consignment, "fd:FPBookingNumber")
                    # FPBookingNumber.text = booking['v_FPBookingNumber']

                    # BulkPricing = xml.SubElement(consignment, "fd:BulkPricing")
                    # xml.SubElement(BulkPricing, "fd:Container", **{ 'Weight': "500", 'Identifier': "C"+ ACCOUNT_CODE +"00003", 'Volume': "0.001", 'Commodity': "PALLET" })

                    for booking_line in booking_lines:
                        FreightDetails = xml.SubElement(
                            consignment,
                            "fd:FreightDetails",
                            **{
                                "Reference": str(booking_line["client_item_reference"])
                                if booking_line["client_item_reference"]
                                else "",
                                "Quantity": str(booking_line["e_qty"]),
                                "Commodity": (
                                    get_item_type(booking_line["e_item_type"])
                                    if booking_line["e_item_type"]
                                    else ""
                                ),
                                "CustomDescription": str(booking_line["e_item"])
                                if booking_line["e_item"]
                                else "",
                            },
                        )
                        if booking_line["e_dangerousGoods"]:
                            DangerousGoods = xml.SubElement(
                                FreightDetails,
                                "fd:DangerousGoods",
                                **{"Class": "1", "UNNumber": "1003"},
                            )

                        ItemDimensions = xml.SubElement(
                            FreightDetails,
                            "fd:ItemDimensions",
                            **{
                                "Length": str("1")
                                if booking_line["e_dimLength"] == None
                                or booking_line["e_dimLength"] == ""
                                or booking_line["e_dimLength"] == 0
                                else str(booking_line["e_dimLength"]),
                                "Width": str("1")
                                if booking_line["e_dimWidth"] == None
                                or booking_line["e_dimWidth"] == ""
                                or booking_line["e_dimWidth"] == 0
                                else str(booking_line["e_dimWidth"]),
                                "Height": str("1")
                                if booking_line["e_dimHeight"] == None
                                or booking_line["e_dimHeight"] == ""
                                or booking_line["e_dimHeight"] == 0
                                else str(booking_line["e_dimHeight"]),
                            },
                        )

                        if (
                            booking_line["e_dimWidth"] == None
                            or booking_line["e_dimWidth"] == ""
                            or booking_line["e_dimWidth"] == 0
                        ):
                            sql2 = "UPDATE dme_booking_lines set e_dimWidth = %s WHERE pk_lines_id = %s"
                            adr2 = (1, booking_line["pk_lines_id"])
                            mycursor.execute(sql2, adr2)
                            mysqlcon.commit()

                        if (
                            booking_line["e_dimLength"] == None
                            or booking_line["e_dimLength"] == ""
                            or booking_line["e_dimLength"] == 0
                        ):
                            sql2 = "UPDATE dme_booking_lines set e_dimLength = %s WHERE pk_lines_id = %s"
                            adr2 = (1, booking_line["pk_lines_id"])
                            mycursor.execute(sql2, adr2)
                            mysqlcon.commit()

                        if (
                            booking_line["e_dimHeight"] == None
                            or booking_line["e_dimHeight"] == ""
                            or booking_line["e_dimHeight"] == 0
                        ):
                            sql2 = "UPDATE dme_booking_lines set e_dimHeight = %s WHERE pk_lines_id = %s"
                            adr2 = (1, booking_line["pk_lines_id"])
                            mycursor.execute(sql2, adr2)
                            mysqlcon.commit()

                        ItemWeight = xml.SubElement(FreightDetails, "fd:ItemWeight")
                        ItemWeight.text = (
                            format(
                                booking_line["e_Total_KG_weight"]
                                / booking_line["e_qty"],
                                ".2f",
                            )
                            if booking_line["e_qty"] > 0
                            else 0
                        )

                        # ItemVolume = xml.SubElement(FreightDetails, "fd:ItemVolume")
                        # if booking_line['e_1_Total_dimCubicMeter'] is not None:
                        #     ItemVolume.text = format(booking_line['e_1_Total_dimCubicMeter'], '.2f')

                        Items = xml.SubElement(FreightDetails, "fd:Items")
                        for j in range(1, booking_line["e_qty"] + 1):
                            Item = xml.SubElement(
                                Items,
                                "fd:Item",
                                **{" Container": "IC" + ACCOUNT_CODE + str(i).zfill(5)},
                            )
                            Item.text = "S" + connote_number + str(j).zfill(3)

                    i += 1
                    # end formatting xml file and putting data from db tables

                    # start writting data into xml files
                    tree = xml.ElementTree(root)

                    with open(local_filepath + filename, "wb") as fh:
                        tree.write(fh, encoding="UTF-8", xml_declaration=True)

                    # start update booking status in dme_booking table
                    sql2 = "UPDATE dme_bookings set b_status=%s, b_dateBookedDate=%s, v_FPBookingNumber=%s WHERE pk_booking_id = %s"
                    adr2 = (
                        "Booked",
                        get_sydney_now_time(),
                        connote_number,
                        booking["pk_booking_id"],
                    )
                    mycursor.execute(sql2, adr2)
                    mysqlcon.commit()
                except Exception as e:
                    logger.error(f"@300 TAS XML - {e}")
                    # print("@300 TAS XML - ", e)
                    return e
        elif one_manifest_file == 1:
            try:
                dme_manifest_log = Dme_manifest_log.objects.filter(
                    fk_booking_id=bookings[0]["pk_booking_id"]
                ).last()
                manifest_number = dme_manifest_log.manifest_number
                fp_info = Fp_freight_providers.objects.get(fp_company_name="Tas")
                initial_connot_index = int(fp_info.new_connot_index) - len(bookings)
                # start xml file name using naming convention
                filename = (
                    "TAS_FP_"
                    + str(datetime.now().strftime("%d-%m-%Y %H_%M_%S"))
                    + "_multiple connots in one.xml"
                )
                # end xml file name using naming convention

                # start formatting xml file and putting data from db tables
                root = xml.Element(
                    "fd:Manifest",
                    **{
                        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                        "xmlns:fd": "http://www.ezysend.com/FreightDescription/2.0",
                        "Version": "2.0",
                        "Action": "Submit",
                        "Number": manifest_number,
                        "Type": "Outbound",
                        "xsi:schemaLocation": "http://www.ezysend.com/FreightDescription/2.0 http://www.ezysend.com/EDI/FreightDescription/2.0/schema.xsd",
                    },
                )

                # IndependentContainers = xml.Element("fd:IndependentContainers")
                # root.append(IndependentContainers)
                # xml.SubElement(IndependentContainers, "fd:Container", **{'Identifier': "IC"+ ACCOUNT_CODE +"00001", 'Volume': "1.02", 'Weight': "200", 'Commodity': "Pallet"})

                for booking in bookings:
                    # start db query for fetching data from dme_booking_lines table
                    booking_lines = get_available_booking_lines(mysqlcon, booking)
                    # end db query for fetching data from dme_booking_lines table

                    # start calculate total item quantity and total item weight
                    totalQty = 0
                    totalWght = 0
                    for booking_line in booking_lines:
                        totalQty = totalQty + booking_line["e_qty"]
                        totalWght = totalWght + booking_line["e_Total_KG_weight"]
                    # start calculate total item quantity and total item weight

                    connote_number = ACCOUNT_CODE + str(
                        initial_connot_index + i - 1
                    ).zfill(5)

                    # consignment = xml.Element("fd:Consignment", **{'Number': "DME"+str(booking['b_bookingID_Visual'])})
                    consignment = xml.Element(
                        "fd:Consignment", **{"Number": connote_number}
                    )
                    root.append(consignment)

                    Carrier = xml.SubElement(consignment, "fd:Carrier")
                    Carrier.text = booking["vx_freight_provider"]
                    AccountCode = xml.SubElement(consignment, "fd:AccountCode")
                    AccountCode.text = ACCOUNT_CODE

                    senderName = xml.SubElement(
                        consignment, "fd:Sender", **{"Name": ACCOUNT_CODE}
                    )
                    senderAddress = xml.SubElement(senderName, "fd:Address")
                    senderAddressLine1 = xml.SubElement(senderAddress, "fd:Address1")
                    senderAddressLine1.text = booking["pu_Address_Street_1"]
                    senderLocality = xml.SubElement(senderAddress, "fd:Locality")
                    senderLocality.text = booking["pu_Address_Suburb"]
                    senderState = xml.SubElement(senderAddress, "fd:Territory")
                    senderState.text = booking["pu_Address_State"]
                    senderPostcode = xml.SubElement(senderAddress, "fd:PostCode")
                    senderPostcode.text = booking["pu_Address_PostalCode"]
                    senderCountry = xml.SubElement(senderAddress, "fd:Country")
                    senderCountry.text = booking["pu_Address_Country"]

                    companyName = booking["deToCompanyName"].replace("<", "")
                    companyName = companyName.replace(">", "")
                    companyName = companyName.replace('"', "")
                    companyName = companyName.replace("'", "")
                    companyName = companyName.replace("&", "and")

                    ReceiverName = xml.SubElement(
                        consignment,
                        "fd:Receiver",
                        **{"Name": companyName, "Reference": "CUST0001"},
                    )
                    ReceiverAddress = xml.SubElement(ReceiverName, "fd:Address")
                    ReceiverAddressLine1 = xml.SubElement(
                        ReceiverAddress, "fd:Address1"
                    )
                    ReceiverAddressLine1.text = booking["de_To_Address_Street_1"]
                    ReceiverLocality = xml.SubElement(ReceiverAddress, "fd:Locality")
                    ReceiverLocality.text = booking["de_To_Address_Suburb"]
                    ReceiverState = xml.SubElement(ReceiverAddress, "fd:Territory")
                    ReceiverState.text = booking["de_To_Address_State"]
                    ReceiverPostcode = xml.SubElement(ReceiverAddress, "fd:PostCode")
                    ReceiverPostcode.text = booking["de_To_Address_PostalCode"]
                    ReceiverCountry = xml.SubElement(ReceiverAddress, "fd:Country")
                    ReceiverCountry.text = booking["de_To_Address_Country"]

                    ContactName = xml.SubElement(ReceiverName, "fd:ContactName")
                    ContactName.text = (
                        str(booking["de_to_Contact_FName"])
                        if booking["de_to_Contact_FName"]
                        else ""
                    ) + (
                        " " + str(booking["de_to_Contact_Lname"])
                        if booking["de_to_Contact_Lname"]
                        else ""
                    )
                    PhoneNumber = xml.SubElement(ReceiverName, "fd:PhoneNumber")
                    PhoneNumber.text = (
                        str(booking["de_to_Phone_Main"])
                        if booking["de_to_Phone_Main"]
                        else ""
                    )

                    FreightForwarderName = xml.SubElement(
                        consignment, "fd:FreightForwarder", **{"Name": companyName}
                    )
                    FreightForwarderAddress = xml.SubElement(
                        FreightForwarderName, "fd:Address"
                    )
                    FreightForwarderAddressLine1 = xml.SubElement(
                        FreightForwarderAddress, "fd:Address1"
                    )
                    FreightForwarderAddressLine1.text = booking[
                        "de_To_Address_Street_1"
                    ]
                    FreightForwarderLocality = xml.SubElement(
                        FreightForwarderAddress, "fd:Locality"
                    )
                    FreightForwarderLocality.text = booking["de_To_Address_Suburb"]
                    FreightForwarderState = xml.SubElement(
                        FreightForwarderAddress, "fd:Territory"
                    )
                    FreightForwarderState.text = booking["de_To_Address_State"]
                    FreightForwarderPostcode = xml.SubElement(
                        FreightForwarderAddress, "fd:PostCode"
                    )
                    FreightForwarderPostcode.text = booking["de_To_Address_PostalCode"]
                    FreightForwarderCountry = xml.SubElement(
                        FreightForwarderAddress, "fd:Country"
                    )
                    FreightForwarderCountry.text = booking["de_To_Address_Country"]

                    Fragile = xml.SubElement(consignment, "fd:Fragile")
                    Fragile.text = "true"

                    ServiceType = xml.SubElement(consignment, "fd:ServiceType")
                    ServiceType.text = booking["vx_serviceName"]

                    DeliveryWindow = xml.SubElement(
                        consignment,
                        "fd:DeliveryWindow",
                        **{
                            "From": (
                                booking["puPickUpAvailFrom_Date"].strftime("%Y-%m-%d")
                                + "T09:00:00"
                            ),
                            "To": (
                                booking["pu_PickUp_By_Date"].strftime("%Y-%m-%d")
                                + "T17:00:00"
                            )
                            if booking["pu_PickUp_By_Date"] is not None
                            else (
                                booking["puPickUpAvailFrom_Date"].strftime("%Y-%m-%d")
                                + "T17:00:00"
                            ),
                        },
                    )

                    DeliveryInstructions = xml.SubElement(
                        consignment, "fd:DeliveryInstructions"
                    )
                    DeliveryInstructions.text = (
                        str(booking["de_to_PickUp_Instructions_Address"])
                        + " "
                        + str(booking["de_to_Pick_Up_Instructions_Contact"])
                    )

                    # FPBookingNumber = xml.SubElement(consignment, "fd:FPBookingNumber")
                    # FPBookingNumber.text = booking['v_FPBookingNumber']

                    # BulkPricing = xml.SubElement(consignment, "fd:BulkPricing")
                    # xml.SubElement(BulkPricing, "fd:Container", **{ 'Weight': "500", 'Identifier': "C"+ ACCOUNT_CODE +"00003", 'Volume': "0.001", 'Commodity': "PALLET" })

                    serial_index = 0
                    for booking_line in booking_lines:
                        FreightDetails = xml.SubElement(
                            consignment,
                            "fd:FreightDetails",
                            **{
                                "Reference": str(booking_line["client_item_reference"])
                                if booking_line["client_item_reference"]
                                else "",
                                "Quantity": str(booking_line["e_qty"]),
                                "Commodity": (
                                    get_item_type(booking_line["e_item_type"])
                                    if booking_line["e_item_type"]
                                    else ""
                                ),
                                "CustomDescription": str(booking_line["e_item"])
                                if booking_line["e_item"]
                                else "",
                            },
                        )
                        if booking_line["e_dangerousGoods"]:
                            DangerousGoods = xml.SubElement(
                                FreightDetails,
                                "fd:DangerousGoods",
                                **{"Class": "1", "UNNumber": "1003"},
                            )

                        ItemDimensions = xml.SubElement(
                            FreightDetails,
                            "fd:ItemDimensions",
                            **{
                                "Length": str("1")
                                if booking_line["e_dimLength"] == None
                                or booking_line["e_dimLength"] == ""
                                or booking_line["e_dimLength"] == 0
                                else str(booking_line["e_dimLength"]),
                                "Width": str("1")
                                if booking_line["e_dimWidth"] == None
                                or booking_line["e_dimWidth"] == ""
                                or booking_line["e_dimWidth"] == 0
                                else str(booking_line["e_dimWidth"]),
                                "Height": str("1")
                                if booking_line["e_dimHeight"] == None
                                or booking_line["e_dimHeight"] == ""
                                or booking_line["e_dimHeight"] == 0
                                else str(booking_line["e_dimHeight"]),
                            },
                        )

                        if (
                            booking_line["e_dimWidth"] == None
                            or booking_line["e_dimWidth"] == ""
                            or booking_line["e_dimWidth"] == 0
                        ):
                            sql2 = "UPDATE dme_booking_lines set e_dimWidth = %s WHERE pk_lines_id = %s"
                            adr2 = (1, booking_line["pk_lines_id"])
                            mycursor.execute(sql2, adr2)
                            mysqlcon.commit()

                        if (
                            booking_line["e_dimLength"] == None
                            or booking_line["e_dimLength"] == ""
                            or booking_line["e_dimLength"] == 0
                        ):
                            sql2 = "UPDATE dme_booking_lines set e_dimLength = %s WHERE pk_lines_id = %s"
                            adr2 = (1, booking_line["pk_lines_id"])
                            mycursor.execute(sql2, adr2)
                            mysqlcon.commit()

                        if (
                            booking_line["e_dimHeight"] == None
                            or booking_line["e_dimHeight"] == ""
                            or booking_line["e_dimHeight"] == 0
                        ):
                            sql2 = "UPDATE dme_booking_lines set e_dimHeight = %s WHERE pk_lines_id = %s"
                            adr2 = (1, booking_line["pk_lines_id"])
                            mycursor.execute(sql2, adr2)
                            mysqlcon.commit()

                        ItemWeight = xml.SubElement(FreightDetails, "fd:ItemWeight")
                        ItemWeight.text = (
                            format(
                                booking_line["e_Total_KG_weight"]
                                / booking_line["e_qty"],
                                ".2f",
                            )
                            if booking_line["e_qty"] > 0
                            else 0
                        )

                        # ItemVolume = xml.SubElement(FreightDetails, "fd:ItemVolume")
                        # if booking_line['e_1_Total_dimCubicMeter'] is not None:
                        #     ItemVolume.text = format(booking_line['e_1_Total_dimCubicMeter'], '.2f')

                        Items = xml.SubElement(FreightDetails, "fd:Items")
                        for j in range(1, booking_line["e_qty"] + 1):
                            serial_index += 1
                            Item = xml.SubElement(
                                Items,
                                "fd:Item",
                                **{" Container": "IC" + ACCOUNT_CODE + str(i).zfill(5)},
                            )
                            Item.text = (
                                "S" + connote_number + str(serial_index).zfill(3)
                            )

                    i += 1
                    # end formatting xml file and putting data from db tables

                    # start writting data into xml files
                    tree = xml.ElementTree(root)

                    with open(local_filepath + filename, "wb") as fh:
                        tree.write(fh, encoding="UTF-8", xml_declaration=True)

                    # start update booking status in dme_booking table
                    sql2 = "UPDATE dme_bookings set b_status=%s, b_dateBookedDate=%s, v_FPBookingNumber=%s WHERE pk_booking_id = %s"
                    adr2 = (
                        "Booked",
                        get_sydney_now_time(),
                        connote_number,
                        booking["pk_booking_id"],
                    )
                    mycursor.execute(sql2, adr2)
                    mysqlcon.commit()
            except Exception as e:
                logger.error(f"@301 TAS XML - {e}")
                # print("@301 TAS XML - ", e)
                return e

    mysqlcon.close()


def build_manifest(booking_ids, vx_freight_provider, user_name):
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

    bookings = get_available_bookings(mysqlcon, booking_ids)
    # manifested_list = get_manifested_list(bookings)

    # if len(manifested_list) > 0:
    #     return manifested_list

    if vx_freight_provider.upper() == "TAS":
        fp_info = Fp_freight_providers.objects.get(fp_company_name="Tas")
        new_manifest_index = fp_info.fp_manifest_cnt
        new_connot_index = fp_info.new_connot_index

        # start check if pdfs folder exists
        if production:
            local_filepath = "/opt/s3_public/pdfs/tas_au/"
            local_filepath_dup = (
                "/opt/s3_public/pdfs/tas_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )
        else:
            local_filepath = "/Users/admin/work/goldmine/dme_api/static/pdfs/tas_au/"
            local_filepath_dup = (
                "/Users/admin/work/goldmine/dme_api/static/pdfs/tas_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )

        if not os.path.exists(local_filepath):
            os.makedirs(local_filepath)
        # end check if pdfs folder exists

        # start loop through data fetched from dme_bookings table
        filenames = []
        date = (
            datetime.now().strftime("%Y%m%d") + "_" + datetime.now().strftime("%H%M%S")
        )
        filename = "TAS_MANIFEST_" + date + "_m.pdf"
        filenames.append(filename)
        file = open(local_filepath + filenames[0], "a")
        doc = SimpleDocTemplate(
            local_filepath + filename,
            pagesize=(297 * mm, 210 * mm),
            rightMargin=10,
            leftMargin=10,
            topMargin=10,
            bottomMargin=10,
        )
        Story = []
        manifest = "M" + ACCOUNT_CODE + str(new_manifest_index).zfill(4)

        for k in range(2):
            i = 1
            row_cnt = 0
            page_cnt = 1

            ent_qty = 0
            ent_weight = 0
            ent_vol = 0
            ent_rows = 0
            for booking in bookings:
                booking_lines = get_available_booking_lines(mysqlcon, booking)
                totalQty = 0
                totalWght = 0
                totalVol = 0

                for booking_line in booking_lines:
                    totalQty = (
                        totalQty + booking_line["e_qty"]
                        if booking_line["e_qty"] is not None
                        else 0
                    )
                    totalWght = (
                        totalWght + booking_line["e_Total_KG_weight"]
                        if booking_line["e_Total_KG_weight"] is not None
                        else 0
                    )
                    totalVol = (
                        totalVol + booking_line["e_1_Total_dimCubicMeter"]
                        if booking_line["e_1_Total_dimCubicMeter"] is not None
                        else 0
                    )
                ent_qty = ent_qty + totalQty
                ent_weight = ent_weight + totalWght
                ent_vol = ent_vol + totalVol
                ent_rows = ent_rows + len(booking_lines)

                sql2 = "UPDATE dme_bookings set manifest_timestamp=%s WHERE pk_booking_id = %s"
                adr2 = (str(datetime.utcnow()), booking["pk_booking_id"])
                mycursor.execute(sql2, adr2)
                mysqlcon.commit()

            for booking_ind, booking in enumerate(bookings):
                try:
                    booking_lines = get_available_booking_lines(mysqlcon, booking)

                    carrierName = "TAS FREIGHT"
                    senderName = ACCOUNT_CODE
                    ConNote = ACCOUNT_CODE + str(new_connot_index + i - 1).zfill(5)
                    Reference = "TEST123"
                    created_date = str(datetime.now().strftime("%d/%m/%Y"))
                    printed_timestamp = str(
                        datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
                    )
                    barcode = manifest
                    barcode128 = code128.Code128(
                        barcode, barHeight=30 * mm, barWidth=0.8
                    )

                    if k == 0:
                        ptext = "Customer Copy - Detail"
                    else:
                        ptext = "Driver Copy - Detail"

                    col1_w = 20
                    col2_w = 70
                    col3_w = 70
                    col4_w = 140
                    col5_w = 100
                    col6_w = 80
                    col7_w = 60
                    col8_w = 60
                    col9_w = 40
                    col10_w = 55
                    col11_w = 55
                    col12_w = 60

                    j = 1
                    totalQty = 0
                    totalWght = 0
                    totalVol = 0

                    for booking_line_ind, booking_line in enumerate(booking_lines):
                        if row_cnt == 0:  # Add page header and table header
                            paragraph = Paragraph(
                                "<font size=12><b>%s</b></font>" % ptext,
                                styles["Normal"],
                            )
                            Story.append(paragraph)
                            Story.append(Spacer(1, 5))

                            tbl_data = [
                                [
                                    Paragraph(
                                        '<font size=8 color="white"><b>MANIFEST DETAILS</b></font>',
                                        style_left,
                                    )
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Carrier:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s</font>" % carrierName,
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Manifest:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s</font>" % manifest,
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Accounts:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s</font>" % senderName,
                                        styles["BodyText"],
                                    ),
                                ]
                                # [Paragraph('<font size=8><b>Total Qty:</b></font>', styles["BodyText"]), Paragraph('<font size=8>%s</font>' %  str(ent_qty), styles["BodyText"])],
                                # [Paragraph('<font size=8><b>Total Kgs:</b></font>', styles["BodyText"]), Paragraph('<font size=8>%s</font>' % str("{0:.2f}".format(ent_weight)), styles["BodyText"])],
                                # [Paragraph('<font size=8><b>Total VOL:</b></font>', styles["BodyText"]), Paragraph('<font size=8>%s</font>' % str(ent_vol), styles["BodyText"])],
                            ]
                            t1 = Table(
                                tbl_data,
                                colWidths=(20 * mm, 60 * mm),
                                rowHeights=18,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                style=[
                                    ("BACKGROUND", (0, 0), (0, 0), colors.black),
                                    ("COLOR", (0, 0), (-1, -1), colors.white),
                                    ("SPAN", (0, 0), (1, 0)),
                                    ("BOX", (0, 0), (-1, -1), 0.5, (0, 0, 0)),
                                ],
                            )

                            tbl_data = [[barcode128]]
                            t2 = Table(
                                tbl_data,
                                colWidths=(127 * mm),
                                rowHeights=(30 * mm),
                                hAlign="CENTER",
                                vAlign="BOTTOM",
                                style=[("ALIGN", (0, 0), (0, 0), "CENTER")],
                            )

                            tbl_data = [
                                [
                                    Paragraph(
                                        '<font size=8 color="white"><b>GENERAL DETAILS</b></font>',
                                        style_left,
                                    )
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Created:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s <b>Printed:</b> %s</font>"
                                        % (created_date, printed_timestamp),
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Page:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s of %s</font>"
                                        % (page_cnt, int(ent_rows / ROWS_PER_PAGE) + 1),
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Sender:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s, %s</font>"
                                        % (senderName, booking["pu_Address_Street_1"]),
                                        styles["Normal"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b></b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s, %s, %s</font>"
                                        % (
                                            booking["pu_Address_Suburb"],
                                            booking["pu_Address_PostalCode"],
                                            booking["pu_Address_State"],
                                        ),
                                        styles["Normal"],
                                    ),
                                ],
                            ]
                            t3 = Table(
                                tbl_data,
                                colWidths=(17 * mm, 63 * mm),
                                rowHeights=16,
                                hAlign="RIGHT",
                                vAlign="MIDDLE",
                                style=[
                                    ("BACKGROUND", (0, 0), (0, 0), colors.black),
                                    ("COLOR", (0, 0), (-1, -1), colors.white),
                                    ("SPAN", (0, 0), (1, 0)),
                                    ("BOX", (0, 0), (-1, -1), 0.5, (0, 0, 0)),
                                ],
                            )

                            data = [[t1, t2, t3]]
                            # adjust the length of tables
                            t1_w = 80 * mm
                            t2_w = 127 * mm
                            t3_w = 80 * mm
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

                            tbl_data = [
                                [
                                    Paragraph(
                                        '<font size=10 color="white"></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>CONNOTE</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>REF</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>DESCRIPTION</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>RECEIVER</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>SUBURB</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>STATE</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>PCODE</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>QTY</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>KG</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>VOL</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>ROUTE</b></font>',
                                        styles["Normal"],
                                    ),
                                ]
                            ]
                            tbl = Table(
                                tbl_data,
                                colWidths=(
                                    col1_w,
                                    col2_w,
                                    col3_w,
                                    col4_w,
                                    col5_w,
                                    col6_w,
                                    col7_w,
                                    col8_w,
                                    col9_w,
                                    col10_w,
                                    col11_w,
                                    col12_w,
                                ),
                                rowHeights=20,
                                hAlign="LEFT",
                                style=[("BACKGROUND", (0, 0), (11, 1), colors.black)],
                            )
                            Story.append(tbl)

                        totalQty = (
                            totalQty + booking_line["e_qty"]
                            if booking_line["e_qty"] is not None
                            else 0
                        )
                        totalWght = (
                            totalWght + booking_line["e_Total_KG_weight"]
                            if booking_line["e_Total_KG_weight"] is not None
                            else 0
                        )
                        totalVol = (
                            totalVol + booking_line["e_1_Total_dimCubicMeter"]
                            if booking_line["e_1_Total_dimCubicMeter"] is not None
                            else 0
                        )

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=6>%s</font>" % j, styles["Normal"]
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>" % ConNote, style_cell
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % (
                                        str(booking_line["client_item_reference"])
                                        if booking_line["client_item_reference"]
                                        else ""
                                    ),
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % (
                                        str(booking_line["e_item"])
                                        if booking_line["e_item"]
                                        else ""
                                    ),
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_to_Contact_F_LName"],
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_To_Address_Suburb"],
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_To_Address_State"],
                                    styles["Normal"],
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_To_Address_PostalCode"],
                                    styles["Normal"],
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % str(booking_line["e_qty"]),
                                    styles["Normal"],
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % str(
                                        "{0:,.2f}".format(
                                            booking_line["e_Total_KG_weight"]
                                            if booking_line["e_Total_KG_weight"]
                                            is not None
                                            else ""
                                        )
                                    ),
                                    styles["Normal"],
                                ),
                                Paragraph("<font size=6></font>", styles["Normal"]),
                                Paragraph("<font size=6></font>", styles["Normal"]),
                            ]
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(
                                col1_w,
                                col2_w,
                                col3_w,
                                col4_w,
                                col5_w,
                                col6_w,
                                col7_w,
                                col8_w,
                                col9_w,
                                col10_w,
                                col11_w,
                                col12_w,
                            ),
                            rowHeights=18,
                            hAlign="LEFT",
                            style=[("GRID", (0, 0), (-1, -1), 0.5, colors.black)],
                        )
                        Story.append(tbl)

                        j += 1
                        row_cnt += 1

                        if (
                            booking_ind == len(bookings) - 1
                            and booking_line_ind == len(booking_lines) - 1
                        ):  # Add Total
                            tbl_data = [
                                [
                                    Paragraph(
                                        "<font size=10><b>Total Per Booking:</b></font>",
                                        style_right,
                                    ),
                                    Paragraph(
                                        "<font size=10>%s</font>"
                                        % str("{:,}".format(ent_qty)),
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        "<font size=10>%s</font>"
                                        % str("{0:,.2f}".format(ent_weight)),
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        "<font size=10>%s</font>"
                                        % str("{0:,.2f}".format(ent_vol)),
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        "<font size=10><b>Freight:</b></font>",
                                        styles["Normal"],
                                    ),
                                ]
                            ]
                            tbl = Table(
                                tbl_data,
                                colWidths=(
                                    col1_w
                                    + col2_w
                                    + col3_w
                                    + col4_w
                                    + col5_w
                                    + col6_w
                                    + col7_w
                                    + col8_w,
                                    col9_w,
                                    col10_w,
                                    col11_w,
                                    col12_w,
                                ),
                                rowHeights=18,
                                hAlign="LEFT",
                                style=[("GRID", (1, 0), (-2, 0), 0.5, colors.black)],
                            )
                            Story.append(tbl)

                            if k == 0:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Driver Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Driver Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]
                            else:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Customer Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Customer Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]

                            tbl = Table(
                                tbl_data,
                                colWidths=350,
                                rowHeights=(ROWS_PER_PAGE - row_cnt) * 20,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                style=[
                                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ],
                            )
                            Story.append(tbl)
                            Story.append(
                                HRFlowable(
                                    width="100%",
                                    thickness=1,
                                    lineCap="round",
                                    color="#000000",
                                    spaceBefore=1,
                                    spaceAfter=1,
                                    hAlign="CENTER",
                                    vAlign="BOTTOM",
                                    dash=None,
                                )
                            )

                            Story.append(PageBreak())

                        if row_cnt == ROWS_PER_PAGE:  # Add Sign area
                            if k == 0:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Driver Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Driver Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]
                            else:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Customer Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Customer Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]

                            tbl = Table(
                                tbl_data,
                                colWidths=350,
                                rowHeights=30,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                style=[
                                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ],
                            )
                            Story.append(tbl)

                            Story.append(
                                HRFlowable(
                                    width="100%",
                                    thickness=1,
                                    lineCap="round",
                                    color="#000000",
                                    spaceBefore=1,
                                    spaceAfter=1,
                                    hAlign="CENTER",
                                    vAlign="BOTTOM",
                                    dash=None,
                                )
                            )
                            Story.append(PageBreak())
                            row_cnt = 0
                            page_cnt += 1

                    sql = "INSERT INTO `dme_manifest_log` \
                    (`fk_booking_id`, `manifest_url`, `manifest_number`, `bookings_cnt`, `is_one_booking`, \
                    `z_createdByAccount`, `z_createdTimeStamp`, `z_modifiedTimeStamp`) \
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                    mycursor.execute(
                        sql,
                        (
                            booking["pk_booking_id"],
                            filename,
                            manifest,
                            "1",
                            "1",
                            user_name,
                            str(datetime.utcnow()),
                            str(datetime.utcnow()),
                        ),
                    )
                    mysqlcon.commit()
                    i += 1

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    # print(dir(exc_type), fname, exc_tb.tb_lineno)
                    # print("Error: unable to fecth data")
                    # print("Error1: " + str(e))
                    logger.error(f"ERROR @303 - {str(e)}")

            k += 1
        doc.build(Story)
        file.close()

        sql = "INSERT INTO `dme_manifest_log` \
            (`manifest_url`, `manifest_number`, `bookings_cnt`, `is_one_booking`, `z_createdTimeStamp`, \
            `z_modifiedTimeStamp`, `z_createdByAccount`) \
            VALUES (%s, %s, %s, %s, %s, %s, %s)"
        mycursor.execute(
            sql,
            (
                filename,
                manifest,
                str(len(bookings)),
                "1",
                str(datetime.utcnow()),
                str(datetime.utcnow()),
                user_name,
            ),
        )
        mysqlcon.commit()

        fp_info.fp_manifest_cnt = fp_info.fp_manifest_cnt + 1
        fp_info.new_connot_index = fp_info.new_connot_index + len(bookings)
        fp_info.save()
    elif vx_freight_provider.upper() == "DHL":
        fp_info = Fp_freight_providers.objects.get(fp_company_name="DHL")
        new_manifest_index = fp_info.fp_manifest_cnt
        new_connot_index = fp_info.new_connot_index

        # start check if pdfs folder exists
        if production:
            local_filepath = "/opt/s3_public/pdfs/dhl_au/"
            local_filepath_dup = (
                "/opt/s3_public/pdfs/dhl_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )
        else:
            local_filepath = "/Users/admin/work/goldmine/dme_api/static/pdfs/dhl_au/"
            local_filepath_dup = (
                "/Users/admin/work/goldmine/dme_api/static/pdfs/dhl_au/archive/"
                + str(datetime.now().strftime("%Y_%m_%d"))
                + "/"
            )

        if not os.path.exists(local_filepath):
            os.makedirs(local_filepath)
        # end check if pdfs folder exists

        # start loop through data fetched from dme_bookings table
        filenames = []
        date = (
            datetime.now().strftime("%Y%m%d") + "_" + datetime.now().strftime("%H%M%S")
        )
        filename = "DHL_MANIFEST_" + date + "_m.pdf"
        filenames.append(filename)
        file = open(local_filepath + filenames[0], "a")
        doc = SimpleDocTemplate(
            local_filepath + filename,
            pagesize=(297 * mm, 210 * mm),
            rightMargin=10,
            leftMargin=10,
            topMargin=10,
            bottomMargin=10,
        )
        Story = []
        manifest = "M" + ACCOUNT_CODE + str(new_manifest_index).zfill(4)

        for k in range(2):
            i = 1
            row_cnt = 0
            page_cnt = 1

            ent_qty = 0
            ent_weight = 0
            ent_vol = 0
            ent_rows = 0
            for booking in bookings:
                booking_lines = get_available_booking_lines(mysqlcon, booking)
                totalQty = 0
                totalWght = 0
                totalVol = 0

                for booking_line in booking_lines:
                    totalQty = (
                        totalQty + booking_line["e_qty"]
                        if booking_line["e_qty"] is not None
                        else 0
                    )
                    totalWght = (
                        totalWght + booking_line["e_Total_KG_weight"]
                        if booking_line["e_Total_KG_weight"] is not None
                        else 0
                    )
                    totalVol = (
                        totalVol + booking_line["e_1_Total_dimCubicMeter"]
                        if booking_line["e_1_Total_dimCubicMeter"] is not None
                        else 0
                    )
                ent_qty = ent_qty + totalQty
                ent_weight = ent_weight + totalWght
                ent_vol = ent_vol + totalVol
                ent_rows = ent_rows + len(booking_lines)

                sql2 = "UPDATE dme_bookings set manifest_timestamp=%s WHERE pk_booking_id = %s"
                adr2 = (str(datetime.utcnow()), booking["pk_booking_id"])
                mycursor.execute(sql2, adr2)
                mysqlcon.commit()

            for booking_ind, booking in enumerate(bookings):
                try:
                    booking_lines = get_available_booking_lines(mysqlcon, booking)

                    carrierName = booking["vx_freight_provider_carrier"]
                    senderName = ACCOUNT_CODE
                    ConNote = ACCOUNT_CODE + str(new_connot_index + i - 1).zfill(5)
                    Reference = "TEST123"
                    created_date = str(datetime.now().strftime("%d/%m/%Y"))
                    printed_timestamp = str(
                        datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
                    )
                    barcode = manifest
                    barcode128 = code128.Code128(
                        barcode, barHeight=30 * mm, barWidth=0.8
                    )

                    if k == 0:
                        ptext = "Customer Copy - Detail"
                    else:
                        ptext = "Driver Copy - Detail"

                    col1_w = 20
                    col2_w = 70
                    col3_w = 70
                    col4_w = 140
                    col5_w = 100
                    col6_w = 80
                    col7_w = 60
                    col8_w = 60
                    col9_w = 40
                    col10_w = 55
                    col11_w = 55
                    col12_w = 60

                    j = 1
                    totalQty = 0
                    totalWght = 0
                    totalVol = 0

                    for booking_line_ind, booking_line in enumerate(booking_lines):
                        if row_cnt == 0:  # Add page header and table header
                            paragraph = Paragraph(
                                "<font size=12><b>%s</b></font>" % ptext,
                                styles["Normal"],
                            )
                            Story.append(paragraph)
                            Story.append(Spacer(1, 5))

                            tbl_data = [
                                [
                                    Paragraph(
                                        '<font size=8 color="white"><b>MANIFEST DETAILS</b></font>',
                                        style_left,
                                    )
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Carrier:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s</font>" % carrierName,
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Manifest:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s</font>" % manifest,
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Accounts:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s</font>" % senderName,
                                        styles["BodyText"],
                                    ),
                                ]
                                # [Paragraph('<font size=8><b>Total Qty:</b></font>', styles["BodyText"]), Paragraph('<font size=8>%s</font>' %  str(ent_qty), styles["BodyText"])],
                                # [Paragraph('<font size=8><b>Total Kgs:</b></font>', styles["BodyText"]), Paragraph('<font size=8>%s</font>' % str("{0:.2f}".format(ent_weight)), styles["BodyText"])],
                                # [Paragraph('<font size=8><b>Total VOL:</b></font>', styles["BodyText"]), Paragraph('<font size=8>%s</font>' % str(ent_vol), styles["BodyText"])],
                            ]
                            t1 = Table(
                                tbl_data,
                                colWidths=(20 * mm, 60 * mm),
                                rowHeights=18,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                style=[
                                    ("BACKGROUND", (0, 0), (0, 0), colors.black),
                                    ("COLOR", (0, 0), (-1, -1), colors.white),
                                    ("SPAN", (0, 0), (1, 0)),
                                    ("BOX", (0, 0), (-1, -1), 0.5, (0, 0, 0)),
                                ],
                            )

                            tbl_data = [[barcode128]]
                            t2 = Table(
                                tbl_data,
                                colWidths=(127 * mm),
                                rowHeights=(30 * mm),
                                hAlign="CENTER",
                                vAlign="BOTTOM",
                                style=[("ALIGN", (0, 0), (0, 0), "CENTER")],
                            )

                            tbl_data = [
                                [
                                    Paragraph(
                                        '<font size=8 color="white"><b>GENERAL DETAILS</b></font>',
                                        style_left,
                                    )
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Created:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s <b>Printed:</b> %s</font>"
                                        % (created_date, printed_timestamp),
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Page:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s of %s</font>"
                                        % (page_cnt, int(ent_rows / ROWS_PER_PAGE) + 1),
                                        styles["BodyText"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b>Sender:</b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s, %s</font>"
                                        % (senderName, booking["pu_Address_Street_1"]),
                                        styles["Normal"],
                                    ),
                                ],
                                [
                                    Paragraph(
                                        "<font size=8><b></b></font>",
                                        styles["BodyText"],
                                    ),
                                    Paragraph(
                                        "<font size=8>%s, %s, %s</font>"
                                        % (
                                            booking["pu_Address_Suburb"],
                                            booking["pu_Address_PostalCode"],
                                            booking["pu_Address_State"],
                                        ),
                                        styles["Normal"],
                                    ),
                                ],
                            ]
                            t3 = Table(
                                tbl_data,
                                colWidths=(17 * mm, 63 * mm),
                                rowHeights=16,
                                hAlign="RIGHT",
                                vAlign="MIDDLE",
                                style=[
                                    ("BACKGROUND", (0, 0), (0, 0), colors.black),
                                    ("COLOR", (0, 0), (-1, -1), colors.white),
                                    ("SPAN", (0, 0), (1, 0)),
                                    ("BOX", (0, 0), (-1, -1), 0.5, (0, 0, 0)),
                                ],
                            )

                            data = [[t1, t2, t3]]
                            # adjust the length of tables
                            t1_w = 80 * mm
                            t2_w = 127 * mm
                            t3_w = 80 * mm
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

                            tbl_data = [
                                [
                                    Paragraph(
                                        '<font size=10 color="white"></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>CONNOTE</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>REF</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>DESCRIPTION</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>RECEIVER</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>SUBURB</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>STATE</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>PCODE</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>QTY</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>KG</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>VOL</b></font>',
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        '<font size=10 color="white"><b>ROUTE</b></font>',
                                        styles["Normal"],
                                    ),
                                ]
                            ]
                            tbl = Table(
                                tbl_data,
                                colWidths=(
                                    col1_w,
                                    col2_w,
                                    col3_w,
                                    col4_w,
                                    col5_w,
                                    col6_w,
                                    col7_w,
                                    col8_w,
                                    col9_w,
                                    col10_w,
                                    col11_w,
                                    col12_w,
                                ),
                                rowHeights=20,
                                hAlign="LEFT",
                                style=[("BACKGROUND", (0, 0), (11, 1), colors.black)],
                            )
                            Story.append(tbl)

                        totalQty = (
                            totalQty + booking_line["e_qty"]
                            if booking_line["e_qty"] is not None
                            else 0
                        )
                        totalWght = (
                            totalWght + booking_line["e_Total_KG_weight"]
                            if booking_line["e_Total_KG_weight"] is not None
                            else 0
                        )
                        totalVol = (
                            totalVol + booking_line["e_1_Total_dimCubicMeter"]
                            if booking_line["e_1_Total_dimCubicMeter"] is not None
                            else 0
                        )

                        tbl_data = [
                            [
                                Paragraph(
                                    "<font size=6>%s</font>" % j, styles["Normal"]
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>" % ConNote, style_cell
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % (
                                        str(booking_line["client_item_reference"])
                                        if booking_line["client_item_reference"]
                                        else ""
                                    ),
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % (
                                        str(booking_line["e_item"])
                                        if booking_line["e_item"]
                                        else ""
                                    ),
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_to_Contact_F_LName"],
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_To_Address_Suburb"],
                                    style_cell,
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_To_Address_State"],
                                    styles["Normal"],
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % booking["de_To_Address_PostalCode"],
                                    styles["Normal"],
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % str(booking_line["e_qty"]),
                                    styles["Normal"],
                                ),
                                Paragraph(
                                    "<font size=6>%s</font>"
                                    % str(
                                        "{0:,.2f}".format(
                                            booking_line["e_Total_KG_weight"]
                                            if booking_line["e_Total_KG_weight"]
                                            is not None
                                            else ""
                                        )
                                    ),
                                    styles["Normal"],
                                ),
                                Paragraph("<font size=6></font>", styles["Normal"]),
                                Paragraph("<font size=6></font>", styles["Normal"]),
                            ]
                        ]
                        tbl = Table(
                            tbl_data,
                            colWidths=(
                                col1_w,
                                col2_w,
                                col3_w,
                                col4_w,
                                col5_w,
                                col6_w,
                                col7_w,
                                col8_w,
                                col9_w,
                                col10_w,
                                col11_w,
                                col12_w,
                            ),
                            rowHeights=18,
                            hAlign="LEFT",
                            style=[("GRID", (0, 0), (-1, -1), 0.5, colors.black)],
                        )
                        Story.append(tbl)

                        j += 1
                        row_cnt += 1

                        if (
                            booking_ind == len(bookings) - 1
                            and booking_line_ind == len(booking_lines) - 1
                        ):  # Add Total
                            tbl_data = [
                                [
                                    Paragraph(
                                        "<font size=10><b>Total Per Booking:</b></font>",
                                        style_right,
                                    ),
                                    Paragraph(
                                        "<font size=10>%s</font>"
                                        % str("{:,}".format(ent_qty)),
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        "<font size=10>%s</font>"
                                        % str("{0:,.2f}".format(ent_weight)),
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        "<font size=10>%s</font>"
                                        % str("{0:,.2f}".format(ent_vol)),
                                        styles["Normal"],
                                    ),
                                    Paragraph(
                                        "<font size=10><b>Freight:</b></font>",
                                        styles["Normal"],
                                    ),
                                ]
                            ]
                            tbl = Table(
                                tbl_data,
                                colWidths=(
                                    col1_w
                                    + col2_w
                                    + col3_w
                                    + col4_w
                                    + col5_w
                                    + col6_w
                                    + col7_w
                                    + col8_w,
                                    col9_w,
                                    col10_w,
                                    col11_w,
                                    col12_w,
                                ),
                                rowHeights=18,
                                hAlign="LEFT",
                                style=[("GRID", (1, 0), (-2, 0), 0.5, colors.black)],
                            )
                            Story.append(tbl)

                            if k == 0:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Driver Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Driver Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]
                            else:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Customer Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Customer Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]

                            tbl = Table(
                                tbl_data,
                                colWidths=350,
                                rowHeights=(ROWS_PER_PAGE - row_cnt) * 20,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                style=[
                                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ],
                            )
                            Story.append(tbl)
                            Story.append(
                                HRFlowable(
                                    width="100%",
                                    thickness=1,
                                    lineCap="round",
                                    color="#000000",
                                    spaceBefore=1,
                                    spaceAfter=1,
                                    hAlign="CENTER",
                                    vAlign="BOTTOM",
                                    dash=None,
                                )
                            )

                            Story.append(PageBreak())

                        if row_cnt == ROWS_PER_PAGE:  # Add Sign area
                            if k == 0:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Driver Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Driver Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]
                            else:
                                tbl_data = [
                                    [
                                        Paragraph(
                                            "<font size=12><b>Customer Name:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Customer Sig:</b></font>",
                                            styles["BodyText"],
                                        ),
                                        Paragraph(
                                            "<font size=12><b>Date:</b></font>",
                                            styles["BodyText"],
                                        ),
                                    ]
                                ]

                            tbl = Table(
                                tbl_data,
                                colWidths=350,
                                rowHeights=30,
                                hAlign="LEFT",
                                vAlign="BOTTOM",
                                style=[
                                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ],
                            )
                            Story.append(tbl)

                            Story.append(
                                HRFlowable(
                                    width="100%",
                                    thickness=1,
                                    lineCap="round",
                                    color="#000000",
                                    spaceBefore=1,
                                    spaceAfter=1,
                                    hAlign="CENTER",
                                    vAlign="BOTTOM",
                                    dash=None,
                                )
                            )
                            Story.append(PageBreak())
                            row_cnt = 0
                            page_cnt += 1
                    i += 1

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    # print(dir(exc_type), fname, exc_tb.tb_lineno)
                    # print("Error: unable to fecth data")
                    # print("Error1: " + str(e))
                    logger.error(f"ERROR @303 - {str(e)}")

            k += 1
        doc.build(Story)
        file.close()

        sql = "INSERT INTO `dme_manifest_log` \
            (`manifest_url`, `manifest_number`, `bookings_cnt`, `is_one_booking`, `z_createdTimeStamp`, \
            `z_modifiedTimeStamp`, `z_createdByAccount`) \
            VALUES (%s, %s, %s, %s, %s, %s, %s)"
        mycursor.execute(
            sql,
            (
                filename,
                manifest,
                str(len(bookings)),
                "1",
                str(datetime.utcnow()),
                str(datetime.utcnow()),
                user_name,
            ),
        )
        mysqlcon.commit()

        fp_info.fp_manifest_cnt = fp_info.fp_manifest_cnt + 1
        fp_info.new_connot_index = fp_info.new_connot_index + len(bookings)
        fp_info.save()

    mysqlcon.close()
    return filenames


def myFirstPage(canvas, doc):
    print(canvas)
    canvas.saveState()
    canvas.rotate(180)
    canvas.restoreState()


def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.rotate(90)
    canvas.restoreState()


def get_barcode_rotated(
    value, width, barWidth=0.01 * inch, fontSize=18, humanReadable=True
):
    barcode = createBarcodeDrawing(
        "Code128",
        value=value,
        barHeight=30 * mm,
        barWidth=1.3,
        fontSize=fontSize,
        humanReadable=humanReadable,
    )

    drawing_width = 2.5 * inch
    barcode_scale = drawing_width / barcode.width
    drawing_height = barcode.height * barcode_scale

    print(drawing_width, drawing_height)

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

    if vx_freight_provider == "TASFR":
        try:
            bookings = get_available_bookings(mysqlcon, booking_ids)

            # start check if pdfs folder exists
            if production:
                local_filepath = "/opt/s3_public/pdfs/tas_au/"
                local_filepath_dup = (
                    "/opt/s3_public/pdfs/tas_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )
            else:
                local_filepath = (
                    "/Users/admin/work/goldmine/dme_api/static/pdfs/tas_au/"
                )
                local_filepath_dup = (
                    "/Users/admin/work/goldmine/dme_api/static/pdfs/tas_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )

            if not os.path.exists(local_filepath):
                os.makedirs(local_filepath)
            # end check if pdfs folder exists

            # start loop through data fetched from dme_bookings table
            i = 1
            for booking in bookings:
                booking_lines = get_available_booking_lines(mysqlcon, booking)

                totalQty = 0
                for booking_line in booking_lines:
                    totalQty = totalQty + booking_line["e_qty"]

                # start pdf file name using naming convention
                filename = (
                    booking["pu_Address_State"]
                    + "_"
                    + str(booking["pk_booking_id"])
                    + "_"
                    + "DME_"
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
            # print(dir(exc_type), fname, exc_tb.tb_lineno)
            # print("#505 Error: " + str(e))
    elif vx_freight_provider.upper() == "DHL":
        try:
            bookings = get_available_bookings(mysqlcon, booking_ids)

            # start check if pdfs folder exists
            if production:
                local_filepath = "/opt/s3_public/pdfs/dhl_au/"
                local_filepath_dup = (
                    "/opt/s3_public/pdfs/dhl_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )
            else:
                local_filepath = (
                    "/Users/admin/work/goldmine/dme_api/static/pdfs/dhl_au/"
                )
                local_filepath_dup = (
                    "/Users/admin/work/goldmine/dme_api/static/pdfs/dhl_au/archive/"
                    + str(datetime.now().strftime("%Y_%m_%d"))
                    + "/"
                )

            if not os.path.exists(local_filepath):
                os.makedirs(local_filepath)
            # end check if pdfs folder exists

            # start loop through data fetched from dme_bookings table
            i = 1
            for booking in bookings:
                booking_lines = get_available_booking_lines(mysqlcon, booking)

                totalQty = 0
                for booking_line in booking_lines:
                    totalQty = totalQty + booking_line["e_qty"]

                # start pdf file name using naming convention
                filename = (
                    booking["pu_Address_State"]
                    + "_"
                    + str(booking["pk_booking_id"])
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
                    pagesize=(5 * inch, 3 * inch),
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
                                Paragraph("<font size=6>Item:</font>", style_right),
                                Paragraph(
                                    "<font size=6>%s - Of - %s</font>" % (j, totalQty),
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
                            [
                                Paragraph(
                                    "<font size=6>Date:&nbsp;&nbsp;&nbsp;&nbsp; %s</font>"
                                    % booking["b_dateBookedDate"].strftime("%d/%m/%Y"),
                                    style_left,
                                )
                            ],
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
            # print(dir(exc_type), fname, exc_tb.tb_lineno)
            print("#506 Error1: " + str(e))
    mysqlcon.close()
    return i - 1


def build_xls(bookings, xls_type, username, start_date, end_date, show_field_name):
    if settings.ENV == "local":
        production = False  # Local
    else:
        production = True  # Dev

    # start check if xmls folder exists
    if production:
        local_filepath = "/opt/s3_private/xlss/"
    else:
        local_filepath = "/Users/admin/work/goldmine/dme_api/static/xlss/"

    if not os.path.exists(local_filepath):
        os.makedirs(local_filepath)
    # end check if xmls folder exists

    filename = (
        username
        + "__"
        + xls_type
        + "__"
        + str(len(bookings))
        + "__"
        + str(start_date.strftime("%d-%m-%Y"))
        + "__"
        + str(end_date.strftime("%d-%m-%Y"))
        + "__"
        + str(datetime.now().strftime("%d-%m-%Y %H_%M_%S"))
        + ".xlsx"
    )
    workbook = xlsxwriter.Workbook(filename, {"remove_timezone": True})
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({"bold": 1, "align": "left"})
    date_format = workbook.add_format({"num_format": "dd/mm/yyyy"})
    time_format = workbook.add_format({"num_format": "hh:mm:ss"})
    col = 0

    if xls_type == "Bookings":
        logger.error("#390 Get started to build `Bookings` XLS")
        worksheet.set_column(15, 16, width=40)
        worksheet.set_column(17, 17, width=53)
        worksheet.set_column(0, 14, width=25)
        worksheet.set_column(18, 30, width=25)

        if show_field_name:
            worksheet.write("A1", "b_dateBookedDate(Date)", bold)
            worksheet.write("B1", "b_dateBookedDate(Time)", bold)
            worksheet.write("C1", "z_first_scan_label_date", bold)
            worksheet.write("D1", "pu_Address_State", bold)
            worksheet.write("E1", "business_group", bold)
            worksheet.write("F1", "deToCompanyName", bold)
            worksheet.write("G1", "de_To_Address_Suburb", bold)
            worksheet.write("H1", "de_To_Address_State", bold)
            worksheet.write("I1", "de_To_Address_PostalCode", bold)
            worksheet.write("J1", "b_client_sales_inv_num", bold)
            worksheet.write("K1", "b_client_order_num", bold)
            worksheet.write("L1", "v_FPBookingNumber", bold)
            worksheet.write("M1", "b_status", bold)
            worksheet.write("N1", "Total Qty", bold)
            worksheet.write("O1", "Total Scanned Qty", bold)
            worksheet.write("P1", "Booked to Scanned Variance", bold)
            worksheet.write("Q1", "dme_status_detail", bold)
            worksheet.write("R1", "dme_status_action", bold)
            worksheet.write("S1", "dme_status_history_notes", bold)
            worksheet.write("T1", "s_21_ActualDeliveryTimeStamp", bold)
            worksheet.write("U1", "zc_pod_or_no_pod", bold)
            worksheet.write("V1", "z_pod_url", bold)
            worksheet.write("W1", "z_pod_signed_url", bold)
            worksheet.write("X1", "delivery_kpi_days", bold)
            worksheet.write("Y1", "delivery_days_from_booked", bold)
            worksheet.write("Z1", "delivery_actual_kpi_days", bold)
            worksheet.write("AA1", "de_Deliver_By_Date(Date)", bold)
            worksheet.write("AB1", "de_Deliver_By_Date(Time)", bold)
            worksheet.write("AC1", "inv_billing_status", bold)
            worksheet.write("AD1", "inv_billing_status_note", bold)

            worksheet.write("A2", "Booked Date", bold)
            worksheet.write("B2", "Booked Time", bold)
            worksheet.write("C2", "WHS Sent Date", bold)
            worksheet.write("D2", "From State", bold)
            worksheet.write("E2", "To Entity Group Name", bold)
            worksheet.write("F2", "To Entity", bold)
            worksheet.write("G2", "To Suburb", bold)
            worksheet.write("H2", "To State", bold)
            worksheet.write("I2", "To Postal Code", bold)
            worksheet.write("J2", "Client Sales Invoice", bold)
            worksheet.write("K2", "Client Order Number", bold)
            worksheet.write("L2", "Consignment No", bold)
            worksheet.write("M2", "Status", bold)
            worksheet.write("N2", "Total Qty", bold)
            worksheet.write("O2", "Total Scanned Qty", bold)
            worksheet.write("P1", "Booked to Scanned Variance", bold)
            worksheet.write("Q2", "Status Detail", bold)
            worksheet.write("R2", "Status Action", bold)
            worksheet.write("S2", "Status History Note", bold)
            worksheet.write("T2", "Actual Delivery", bold)
            worksheet.write("U2", "POD?", bold)
            worksheet.write("V2", "POD LINK", bold)
            worksheet.write("W2", "POD Signed on Glass Link", bold)
            worksheet.write("X2", "Target Delivery KPI (Days)", bold)
            worksheet.write("Y2", "Delivery Days from Booked", bold)
            worksheet.write("Z2", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AA2", "Store Booking Date", bold)
            worksheet.write("AB2", "Store Booking Time", bold)
            worksheet.write("AC2", "Invoice Billing Status", bold)
            worksheet.write("AD2", "Invoice Billing Status Note", bold)

            row = 2
        else:
            worksheet.write("A1", "Booked Date", bold)
            worksheet.write("B1", "Booked Time", bold)
            worksheet.write("C1", "WHS Sent Date", bold)
            worksheet.write("D1", "From State", bold)
            worksheet.write("E1", "To Entity Group Name", bold)
            worksheet.write("F1", "To Entity", bold)
            worksheet.write("G1", "To Suburb", bold)
            worksheet.write("H1", "To State", bold)
            worksheet.write("I1", "To Postal Code", bold)
            worksheet.write("J1", "Client Sales Invoice", bold)
            worksheet.write("K1", "Client Order Number", bold)
            worksheet.write("L1", "Consignment No", bold)
            worksheet.write("M1", "Status", bold)
            worksheet.write("N1", "Total Qty", bold)
            worksheet.write("O1", "Total Scanned Qty", bold)
            worksheet.write("P1", "Booked to Scanned Variance", bold)
            worksheet.write("Q1", "Status Detail", bold)
            worksheet.write("R1", "Status Action", bold)
            worksheet.write("S1", "Status History Note", bold)
            worksheet.write("T1", "Actual Delivery", bold)
            worksheet.write("U1", "POD?", bold)
            worksheet.write("V1", "POD LINK", bold)
            worksheet.write("W1", "POD Signed on Glass Link", bold)
            worksheet.write("X1", "Target Delivery KPI (Days)", bold)
            worksheet.write("Y1", "Delivery Days from Booked", bold)
            worksheet.write("Z1", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AA1", "Store Booking Date", bold)
            worksheet.write("AB1", "Store Booking Time", bold)
            worksheet.write("AC1", "Invoice Billing Status", bold)
            worksheet.write("AD1", "Invoice Billing Status Note", bold)

            row = 1

        logger.error(f"#391 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            if booking_ind % 500 == 0:
                logger.error(f"#392 Current index: {booking_ind}")

            booking_lines = Booking_lines.objects.only(
                "e_qty", "e_qty_scanned_fp", "pk_lines_id"
            ).filter(fk_booking_id=booking.pk_booking_id)
            e_qty_total = 0
            e_qty_scanned_fp_total = 0

            for booking_line in booking_lines:
                if booking_line.e_qty is not None:
                    e_qty_total = e_qty_total + booking_line.e_qty

                if booking_line.e_qty_scanned_fp is not None:
                    e_qty_scanned_fp_total = (
                        e_qty_scanned_fp_total + booking_line.e_qty_scanned_fp
                    )

            if booking.b_dateBookedDate:
                worksheet.write_datetime(
                    row, col + 0, booking.b_dateBookedDate, date_format
                )
                worksheet.write_datetime(
                    row, col + 1, booking.b_dateBookedDate, time_format
                )

            if booking.z_first_scan_label_date:
                worksheet.write_datetime(
                    row, col + 2, booking.z_first_scan_label_date, date_format
                )

            worksheet.write(row, col + 3, booking.pu_Address_State)

            customer_group_name = ""
            customer_groups = Dme_utl_client_customer_group.objects.all()
            for customer_group in customer_groups:
                if (
                    customer_group.name_lookup.lower()
                    in booking.deToCompanyName.lower()
                ):
                    customer_group_name = customer_group.group_name
            worksheet.write(row, col + 4, customer_group_name)

            worksheet.write(row, col + 5, booking.deToCompanyName)
            worksheet.write(row, col + 6, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 7, booking.de_To_Address_State)
            worksheet.write(row, col + 8, booking.de_To_Address_PostalCode)
            worksheet.write(row, col + 9, booking.b_client_sales_inv_num)
            worksheet.write(row, col + 10, booking.b_client_order_num)
            worksheet.write(row, col + 11, booking.v_FPBookingNumber)
            worksheet.write(row, col + 12, booking.b_status)
            worksheet.write(row, col + 13, e_qty_total)
            worksheet.write(row, col + 14, e_qty_scanned_fp_total)
            worksheet.write(row, col + 15, e_qty_total - e_qty_scanned_fp_total)

            cell_format = workbook.add_format({"text_wrap": True})
            worksheet.write(row, col + 16, booking.dme_status_detail, cell_format)
            worksheet.write(row, col + 17, booking.dme_status_action, cell_format)
            worksheet.write(
                row, col + 18, booking.dme_status_history_notes, cell_format
            )

            if (
                booking.s_21_ActualDeliveryTimeStamp
                and booking.s_21_ActualDeliveryTimeStamp
            ):
                worksheet.write_datetime(
                    row, col + 19, booking.s_21_ActualDeliveryTimeStamp, date_format
                )

            if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (
                booking.z_pod_signed_url is not None
                and len(booking.z_pod_signed_url) > 0
            ):
                worksheet.write(row, col + 20, "Y")
            else:
                worksheet.write(row, col + 20, "")

            if settings.ENV == "dev":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 21,
                        settings.S3_URL + "/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 22,
                        settings.S3_URL + "/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )
            elif settings.ENV == "prod":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 21,
                        settings.S3_URL + "/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 22,
                        settings.S3_URL + "/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )

            worksheet.write(row, col + 23, booking.delivery_kpi_days)

            if (
                booking.b_status is not None
                and booking.b_status == "Delivered"
                and booking.s_21_ActualDeliveryTimeStamp is not None
                and booking.b_dateBookedDate is not None
            ):
                worksheet.write(
                    row,
                    col + 24,
                    (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )
                worksheet.write(
                    row,
                    col + 25,
                    booking.delivery_kpi_days
                    - (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )

            if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                worksheet.write_datetime(
                    row, col + 26, booking.de_Deliver_By_Date, date_format
                )
                worksheet.write_datetime(
                    row, col + 27, booking.de_Deliver_By_Date, time_format
                )
            worksheet.write(row, col + 28, booking.inv_billing_status)
            worksheet.write(row, col + 29, booking.inv_billing_status_note)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#395 Finished - `Bookings` XLS")
    elif xls_type == "BookingLines":
        logger.error(f"#380 Get started to build `BookingLines` XLS")
        worksheet.set_column(0, 27, width=25)
        if show_field_name:
            worksheet.write("A1", "dme_bookings:v_FPBookingNumber", bold)
            worksheet.write("B1", "dme_bookings:b_dateBookedDate(Date)", bold)
            worksheet.write("C1", "dme_bookings:b_dateBookedDate(Time)", bold)
            worksheet.write(
                "D1",
                "api_booking_confirmation_lines:fp_event_date and fp_event_time",
                bold,
            )
            worksheet.write("E1", "dme_bookings:vx_freight_provider", bold)
            worksheet.write("F1", "dme_bookings:puCompany", bold)
            worksheet.write("G1", "dme_bookings:pu_Address_Suburb", bold)
            worksheet.write("H1", "dme_bookings:deToCompanyName", bold)
            worksheet.write("I1", "dme_bookings:de_To_Address_Suburb", bold)
            worksheet.write("J1", "dme_bookings:de_To_Address_State", bold)
            worksheet.write("K1", "dme_bookings:de_To_Address_PostalCode", bold)
            worksheet.write("L1", "dme_bookings:b_client_order_num", bold)
            worksheet.write("M1", "dme_bookings:b_client_sales_inv_num", bold)
            worksheet.write("N1", "e_pallety_type", bold)
            worksheet.write("O1", "e_item", bold)
            worksheet.write("P1", "e_item_qty", bold)
            worksheet.write("Q1", "client_item_reference", bold)
            worksheet.write("R1", "Booking Ref ?? GAP", bold)
            worksheet.write("S1", "DD Received Date(Date)", bold)
            worksheet.write("T1", "DD Received Date(Time)", bold)
            worksheet.write("U1", "Dispatch Date", bold)
            worksheet.write("V1", "ETA Into Store", bold)
            worksheet.write("W1", "b_status", bold)
            worksheet.write("X1", "dme_bookings: dme_status_detail", bold)
            worksheet.write("Y1", "dme_bookings: dme_status_action", bold)
            worksheet.write("Z1", "POD Available", bold)
            worksheet.write("AA1", "e_qty_awaiting_inventory", bold)
            worksheet.write("AB1", "e_qty_collected", bold)
            worksheet.write("AC1", "e_qty_scanned_fp", bold)
            worksheet.write("AD1", "e_qty_scanned_depot", bold)
            worksheet.write("AE1", "e_qty_delivered", bold)
            worksheet.write("AF1", "e_qty_damaged", bold)
            worksheet.write("AG1", "e_qty_returned", bold)
            worksheet.write("AH1", "e_qty_shortages", bold)
            worksheet.write("AI1", "e_qty_adjusted_delivered", bold)

            worksheet.write("A2", "Consignment No", bold)
            worksheet.write("B2", "Booked Date", bold)
            worksheet.write("C2", "Booked Time", bold)
            worksheet.write("D2", "Date Scanned", bold)
            worksheet.write("E2", "Freight Provider", bold)
            worksheet.write("F2", "Pickup Entity", bold)
            worksheet.write("G2", "Pickup Suburb", bold)
            worksheet.write("H2", "To Entity", bold)
            worksheet.write("I2", "To Suburb", bold)
            worksheet.write("J2", "To State", bold)
            worksheet.write("K2", "To Postal Code", bold)
            worksheet.write("L2", "Customer Client Order No", bold)
            worksheet.write("M2", "Customer Invoice No", bold)
            worksheet.write("N2", "Model", bold)
            worksheet.write("O2", "Product Description", bold)
            worksheet.write("P2", "Booked Qty", bold)
            worksheet.write("Q2", "Client Item Reference", bold)
            worksheet.write("R2", "Booking Ref", bold)
            worksheet.write("S2", "DD Received Date", bold)
            worksheet.write("T2", "DD Received Time", bold)
            worksheet.write("U2", "Dispatch Date", bold)
            worksheet.write("V2", "ETA Into Store", bold)
            worksheet.write("W2", "Status", bold)
            worksheet.write("X2", "Status Detail", bold)
            worksheet.write("Y2", "Status Action", bold)
            worksheet.write("Z2", "POD?", bold)
            worksheet.write("AA2", "Inventory on Back Order", bold)
            worksheet.write("AB2", "Qty Confimred Collected by Pickup Entity", bold)
            worksheet.write("AC2", "Qty Scanned at Transporter Depot", bold)
            worksheet.write("AD2", "Same as Col T?", bold)
            worksheet.write("AE2", "Qty Delivered", bold)
            worksheet.write("AF2", "Qty Damaged", bold)
            worksheet.write("AG2", "Qty Returned", bold)
            worksheet.write("AH2", "Qty Short", bold)
            worksheet.write("AI2", "Adjusted Delivered Qty", bold)

            row = 2
        else:
            worksheet.write("A1", "Consignment No", bold)
            worksheet.write("B1", "Booked Date", bold)
            worksheet.write("C1", "Booked Time", bold)
            worksheet.write("D1", "Date Scanned", bold)
            worksheet.write("E1", "Freight Provider", bold)
            worksheet.write("F1", "Pickup Entity", bold)
            worksheet.write("G1", "Pickup Suburb", bold)
            worksheet.write("H1", "To Entity", bold)
            worksheet.write("I1", "To Suburb", bold)
            worksheet.write("J1", "To State", bold)
            worksheet.write("K1", "To Postal Code", bold)
            worksheet.write("L1", "Customer Client Order No", bold)
            worksheet.write("M1", "Customer Invoice No", bold)
            worksheet.write("N1", "Model", bold)
            worksheet.write("O1", "Product Description", bold)
            worksheet.write("P1", "Booked Qty", bold)
            worksheet.write("Q1", "Client Item Reference", bold)
            worksheet.write("R1", "Booking Ref", bold)
            worksheet.write("S1", "DD Received Date", bold)
            worksheet.write("T1", "DD Received Time", bold)
            worksheet.write("U1", "Dispatch Date", bold)
            worksheet.write("V1", "ETA Into Store", bold)
            worksheet.write("W1", "Status", bold)
            worksheet.write("X1", "Status Detail", bold)
            worksheet.write("Y1", "Status Action", bold)
            worksheet.write("Z1", "POD?", bold)
            worksheet.write("AA1", "Inventory on Back Order", bold)
            worksheet.write("AB1", "Qty Confimred Collected by Pickup Entity", bold)
            worksheet.write("AC1", "Qty Scanned at Transporter Depot", bold)
            worksheet.write("AD1", "Same as Col T?", bold)
            worksheet.write("AE1", "Qty Delivered", bold)
            worksheet.write("AF1", "Qty Damaged", bold)
            worksheet.write("AG1", "Qty Returned", bold)
            worksheet.write("AH1", "Qty Short", bold)
            worksheet.write("AI1", "Adjusted Delivered Qty", bold)

            row = 1

        e_qty_total = 0
        e_qty_scanned_fp_total = 0

        logger.error(f"#381 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            if booking_ind % 500 == 0:
                logger.error(f"#382 Current index: {booking_ind}")

            try:
                booking_lines = Booking_lines.objects.only(
                    "e_qty",
                    "e_qty_scanned_fp",
                    "pk_lines_id",
                    "e_item",
                    "e_pallet_type",
                    "client_item_reference",
                    "e_qty_awaiting_inventory",
                    "e_qty_collected",
                    "e_qty_scanned_fp",
                    "e_qty_scanned_depot",
                    "e_qty_delivered",
                    "e_qty_damaged",
                    "e_qty_returned",
                    "e_qty_shortages",
                    "e_qty_adjusted_delivered",
                ).filter(fk_booking_id=booking.pk_booking_id)

                for booking_line in booking_lines:
                    worksheet.write(row, col + 0, booking.v_FPBookingNumber)

                    if booking.b_dateBookedDate and booking.b_dateBookedDate:
                        worksheet.write_datetime(
                            row, col + 1, booking.b_dateBookedDate, date_format
                        )
                        worksheet.write_datetime(
                            row, col + 2, booking.b_dateBookedDate, time_format
                        )

                    api_bcl = Api_booking_confirmation_lines.objects.filter(
                        fk_booking_line_id=booking_line.pk_lines_id
                    ).first()
                    if api_bcl and api_bcl.fp_event_date and api_bcl.fp_event_time:
                        worksheet.write(
                            row,
                            col + 3,
                            api_bcl.fp_event_date.strftime("%d-%m-%Y")
                            + " "
                            + api_bcl.fp_event_time.strftime("%H:%M:%S"),
                        )

                    worksheet.write(row, col + 4, booking.vx_freight_provider)
                    worksheet.write(row, col + 5, booking.puCompany)
                    worksheet.write(row, col + 6, booking.pu_Address_Suburb)
                    worksheet.write(row, col + 7, booking.deToCompanyName)
                    worksheet.write(row, col + 8, booking.de_To_Address_Suburb)
                    worksheet.write(row, col + 9, booking.de_To_Address_State)
                    worksheet.write(row, col + 10, booking.de_To_Address_PostalCode)
                    worksheet.write(row, col + 11, booking.b_client_order_num)
                    worksheet.write(row, col + 12, booking.b_client_sales_inv_num)
                    worksheet.write(row, col + 13, booking_line.e_pallet_type)
                    worksheet.write(row, col + 14, booking_line.e_item)
                    worksheet.write(row, col + 15, booking_line.e_qty)
                    worksheet.write(row, col + 16, booking_line.client_item_reference)
                    worksheet.write(row, col + 17, booking.b_bookingID_Visual)

                    if api_bcl and api_bcl.fp_event_date and api_bcl.fp_event_time:
                        worksheet.write_datetime(
                            row, col + 18, api_bcl.fp_event_date, date_format
                        )
                        worksheet.write_datetime(
                            row, col + 19, api_bcl.fp_event_time, time_format
                        )

                    if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                        worksheet.write_datetime(
                            row, col + 20, booking.de_Deliver_By_Date, date_format
                        )

                    if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                        delivery_kpi_days = 0

                        if booking.delivery_kpi_days:
                            delivery_kpi_days = booking.delivery_kpi_days

                        worksheet.write(
                            row,
                            col + 21,
                            (
                                booking.de_Deliver_By_Date
                                + timedelta(days=int(delivery_kpi_days))
                            ).strftime("%d-%m-%Y"),
                        )
                    else:
                        worksheet.write(row, col + 21, "")

                    worksheet.write(row, col + 22, booking.b_status)
                    worksheet.write(row, col + 23, booking.dme_status_detail)
                    worksheet.write(row, col + 24, booking.dme_status_action)

                    if (
                        booking.z_pod_url is not None and len(booking.z_pod_url) > 0
                    ) or (
                        booking.z_pod_signed_url is not None
                        and len(booking.z_pod_signed_url) > 0
                    ):
                        worksheet.write(row, col + 25, "Y")
                    else:
                        worksheet.write(row, col + 25, "")

                    worksheet.write(
                        row, col + 26, booking_line.e_qty_awaiting_inventory
                    )
                    worksheet.write(row, col + 27, booking_line.e_qty_collected)
                    worksheet.write(row, col + 28, booking_line.e_qty_scanned_fp)
                    worksheet.write(row, col + 29, booking_line.e_qty_scanned_depot)
                    worksheet.write(row, col + 30, booking_line.e_qty_delivered)
                    worksheet.write(row, col + 31, booking_line.e_qty_damaged)
                    worksheet.write(row, col + 32, booking_line.e_qty_returned)
                    worksheet.write(row, col + 33, booking_line.e_qty_shortages)
                    worksheet.write(
                        row, col + 34, booking_line.e_qty_adjusted_delivered
                    )

                    if booking_line.e_qty is not None:
                        e_qty_total = e_qty_total + booking_line.e_qty

                    if booking_line.e_qty_scanned_fp is not None:
                        e_qty_scanned_fp_total = (
                            e_qty_scanned_fp_total + booking_line.e_qty_scanned_fp
                        )

                    row += 1

            except Booking_lines.DoesNotExist:
                continue

        worksheet.write(row, col + 16, e_qty_total)
        worksheet.write(row, col + 28, e_qty_scanned_fp_total)

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#385 Finished - `Booking Lines` XLS")
    elif xls_type == "BookingsWithGaps":
        logger.error(f"#370 Get started to build `BookingsWithGaps` XLS")
        worksheet.set_column(0, 27, width=25)
        if show_field_name:
            worksheet.write("A1", "b_dateBookedDate(Date)", bold)
            worksheet.write("B1", "b_dateBookedDate(Time)", bold)
            worksheet.write("C1", "pu_Address_State", bold)
            worksheet.write("D1", "business_group", bold)
            worksheet.write("E1", "deToCompanyName", bold)
            worksheet.write("F1", "de_To_Address_Suburb", bold)
            worksheet.write("G1", "de_To_Address_State", bold)
            worksheet.write("H1", "de_To_Address_PostalCode", bold)
            worksheet.write("I1", "b_client_sales_inv_num", bold)
            worksheet.write("J1", "b_client_order_num", bold)
            worksheet.write("K1", "v_FPBookingNumber", bold)
            worksheet.write("L1", "b_status", bold)
            worksheet.write("M1", "Total Qty", bold)
            worksheet.write("N1", "Total Scanned Qty", bold)
            worksheet.write("O1", "Booked to Scanned Variance", bold)
            worksheet.write("P1", "dme_status_detail", bold)
            worksheet.write("Q1", "dme_status_action", bold)
            worksheet.write("R1", "dme_status_history_notes", bold)
            worksheet.write("S1", "s_21_ActualDeliveryTimeStamp", bold)
            worksheet.write("T1", "zc_pod_or_no_pod", bold)
            worksheet.write("U1", "z_pod_url", bold)
            worksheet.write("V1", "z_pod_signed_url", bold)
            worksheet.write("W1", "delivery_kpi_days", bold)
            worksheet.write("X1", "delivery_days_from_booked", bold)
            worksheet.write("Y1", "delivery_actual_kpi_days", bold)
            worksheet.write("Z1", "de_Deliver_By_Date(Date)", bold)
            worksheet.write("AA1", "de_Deliver_By_Date(Time)", bold)
            worksheet.write("AB1", "client_item_reference", bold)

            worksheet.write("A2", "Booked Date", bold)
            worksheet.write("B2", "Booked Time", bold)
            worksheet.write("C2", "From State", bold)
            worksheet.write("D2", "To Entity Group Name", bold)
            worksheet.write("E2", "To Entity", bold)
            worksheet.write("F2", "To Suburb", bold)
            worksheet.write("G2", "To State", bold)
            worksheet.write("H2", "To Postal Code", bold)
            worksheet.write("I2", "Client Sales Invoice", bold)
            worksheet.write("J2", "Client Order Number", bold)
            worksheet.write("K2", "Consignment No", bold)
            worksheet.write("L2", "Status", bold)
            worksheet.write("M2", "Total Qty", bold)
            worksheet.write("N2", "Total Scanned Qty", bold)
            worksheet.write("O1", "Booked to Scanned Variance", bold)
            worksheet.write("P2", "Status Detail", bold)
            worksheet.write("Q2", "Status Action", bold)
            worksheet.write("R2", "Status History Note", bold)
            worksheet.write("S2", "Actual Delivery", bold)
            worksheet.write("T2", "POD?", bold)
            worksheet.write("U2", "POD LINK", bold)
            worksheet.write("V2", "POD Signed on Glass Link", bold)
            worksheet.write("W2", "Target Delivery KPI (Days)", bold)
            worksheet.write("X2", "Delivery Days from Booked", bold)
            worksheet.write("Y2", "Actual Delivery KPI (Days)", bold)
            worksheet.write("Z2", "Store Booking Date", bold)
            worksheet.write("AA2", "Store Booking Time", bold)
            worksheet.write("AB2", "Gaps", bold)

            row = 2
        else:
            worksheet.write("A1", "Booked Date", bold)
            worksheet.write("B1", "Booked Time", bold)
            worksheet.write("C1", "From State", bold)
            worksheet.write("D1", "To Entity Group Name", bold)
            worksheet.write("E1", "To Entity", bold)
            worksheet.write("F1", "To Suburb", bold)
            worksheet.write("G1", "To State", bold)
            worksheet.write("H1", "To Postal Code", bold)
            worksheet.write("I1", "Client Sales Invoice", bold)
            worksheet.write("J1", "Client Order Number", bold)
            worksheet.write("K1", "Consignment No", bold)
            worksheet.write("L1", "Status", bold)
            worksheet.write("M1", "Total Qty", bold)
            worksheet.write("N1", "Total Scanned Qty", bold)
            worksheet.write("O1", "Booked to Scanned Variance", bold)
            worksheet.write("P1", "Status Detail", bold)
            worksheet.write("Q1", "Status Action", bold)
            worksheet.write("R1", "Status History Note", bold)
            worksheet.write("S1", "Actual Delivery", bold)
            worksheet.write("T1", "POD?", bold)
            worksheet.write("U1", "POD LINK", bold)
            worksheet.write("V1", "POD Signed on Glass Link", bold)
            worksheet.write("W1", "Target Delivery KPI (Days)", bold)
            worksheet.write("X1", "Delivery Days from Booked", bold)
            worksheet.write("Y1", "Actual Delivery KPI (Days)", bold)
            worksheet.write("Z1", "Store Booking Date", bold)
            worksheet.write("AA1", "Store Booking Time", bold)
            worksheet.write("AB1", "Gaps", bold)

            row = 1

        logger.error(f"#371 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            if booking_ind % 500 == 0:
                logger.error(f"#372 Current index: {booking_ind}")

            booking_lines = Booking_lines.objects.only(
                "e_qty", "e_qty_scanned_fp", "pk_lines_id", "client_item_reference"
            ).filter(fk_booking_id=booking.pk_booking_id)
            e_qty_total = 0
            e_qty_scanned_fp_total = 0
            gaps = ""

            for booking_line in booking_lines:
                if booking_line.e_qty is not None:
                    e_qty_total = e_qty_total + booking_line.e_qty

                if booking_line.e_qty_scanned_fp is not None:
                    e_qty_scanned_fp_total = (
                        e_qty_scanned_fp_total + booking_line.e_qty_scanned_fp
                    )

                if booking_line.client_item_reference is not None:
                    if len(gaps) == 0:
                        gaps = gaps + booking_line.client_item_reference
                    else:
                        gaps = gaps + ", " + booking_line.client_item_reference

            if booking.b_dateBookedDate and booking.b_dateBookedDate:
                worksheet.write_datetime(
                    row, col + 0, booking.b_dateBookedDate, date_format
                )
                worksheet.write_datetime(
                    row, col + 1, booking.b_dateBookedDate, time_format
                )

            worksheet.write(row, col + 2, booking.pu_Address_State)

            customer_group_name = ""
            customer_groups = Dme_utl_client_customer_group.objects.all()
            for customer_group in customer_groups:
                if (
                    customer_group.name_lookup.lower()
                    in booking.deToCompanyName.lower()
                ):
                    customer_group_name = customer_group.group_name
            worksheet.write(row, col + 3, customer_group_name)

            worksheet.write(row, col + 4, booking.deToCompanyName)
            worksheet.write(row, col + 5, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 6, booking.de_To_Address_State)
            worksheet.write(row, col + 7, booking.de_To_Address_PostalCode)
            worksheet.write(row, col + 8, booking.b_client_sales_inv_num)
            worksheet.write(row, col + 9, booking.b_client_order_num)
            worksheet.write(row, col + 10, booking.v_FPBookingNumber)
            worksheet.write(row, col + 11, booking.b_status)
            worksheet.write(row, col + 12, e_qty_total)
            worksheet.write(row, col + 13, e_qty_scanned_fp_total)
            worksheet.write(row, col + 14, e_qty_total - e_qty_scanned_fp_total)
            worksheet.write(row, col + 15, booking.dme_status_detail)
            worksheet.write(row, col + 16, booking.dme_status_action)
            worksheet.write(row, col + 17, booking.dme_status_history_notes)

            if (
                booking.s_21_ActualDeliveryTimeStamp
                and booking.s_21_ActualDeliveryTimeStamp
            ):
                worksheet.write_datetime(
                    row, col + 18, booking.s_21_ActualDeliveryTimeStamp, date_format
                )

            if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (
                booking.z_pod_signed_url is not None
                and len(booking.z_pod_signed_url) > 0
            ):
                worksheet.write(row, col + 19, "Y")
            else:
                worksheet.write(row, col + 19, "")

            if settings.ENV == "dev":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 20,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 21,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )
            elif settings.ENV == "prod":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 20,
                        settings.S3_URL + "/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 21,
                        settings.S3_URL + "/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )

            worksheet.write(row, col + 22, booking.delivery_kpi_days)

            if (
                booking.b_status is not None
                and booking.b_status == "Delivered"
                and booking.s_21_ActualDeliveryTimeStamp is not None
                and booking.b_dateBookedDate is not None
            ):
                worksheet.write(
                    row,
                    col + 23,
                    (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )
                worksheet.write(
                    row,
                    col + 24,
                    booking.delivery_kpi_days
                    - (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )

            if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                worksheet.write_datetime(
                    row, col + 25, booking.de_Deliver_By_Date, date_format
                )
                worksheet.write_datetime(
                    row, col + 26, booking.de_Deliver_By_Date, time_format
                )

            worksheet.write(row, col + 27, gaps)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#375 Finished - `BookingsWithGaps` XLS")
    elif xls_type == "Whse":
        logger.error("#360 Get started to build `Whse` XLS")
        worksheet.set_column(7, 8, width=40)
        worksheet.set_column(9, 9, width=53)
        worksheet.set_column(10, 10, width=70)
        worksheet.set_column(0, 6, width=25)
        worksheet.set_column(11, 28, width=25)

        if show_field_name:
            worksheet.write("A1", "b_dateBookedDate(Date)", bold)
            cell_format = workbook.add_format(
                {"font_color": "red", "bold": 1, "align": "left"}
            )
            worksheet.write("B1", "Pickup Days Late", cell_format)
            worksheet.write("C1", "Delivery Days Early / Late", cell_format)
            worksheet.write("D1", "Query With", bold)
            worksheet.write("E1", "b_client_sales_inv_num", bold)
            worksheet.write("F1", "v_FPBookingNumber", bold)
            worksheet.write("G1", "b_status", bold)
            worksheet.write("H1", "dme_status_detail", bold)
            worksheet.write("I1", "dme_status_action", bold)
            worksheet.write("J1", "dme_status_history_notes", bold)
            worksheet.write("K1", "", cell_format)
            worksheet.write("L1", "e_qty", bold)
            worksheet.write("M1", "e_qty_scanned_fp_total", bold)
            worksheet.write("N1", "Booked to Scanned Variance", bold)
            worksheet.write("O1", "pu_Address_State", bold)
            worksheet.write("P1", "business_group", bold)
            worksheet.write("Q1", "deToCompanyName", bold)
            worksheet.write("R1", "de_To_Address_Suburb", bold)
            worksheet.write("S1", "de_To_Address_State", bold)
            worksheet.write("T1", "de_To_Address_PostalCode", bold)
            worksheet.write("U1", "b_client_order_num", bold)
            worksheet.write("V1", "s_21_ActualDeliveryTimeStamp", bold)
            worksheet.write("W1", "zc_pod_or_no_pod", bold)
            worksheet.write("X1", "z_pod_url", bold)
            worksheet.write("Y1", "z_pod_signed_url", bold)
            worksheet.write("Z1", "delivery_kpi_days", bold)
            worksheet.write("AA1", "delivery_days_from_booked", bold)
            worksheet.write("AB1", "delivery_actual_kpi_days", bold)
            worksheet.write("AC1", "de_Deliver_By_Date(Date)", bold)

            worksheet.write("A2", "Booked Date", bold)
            worksheet.write("B2", "Pickup Days Late", cell_format)
            worksheet.write("C2", "Delivery Days Early / Late", cell_format)
            worksheet.write("D2", "Query With", bold)
            worksheet.write("E2", "Client Sales Invoice", bold)
            worksheet.write("F2", "Consignment No", bold)
            worksheet.write("G2", "Status", bold)
            worksheet.write("H2", "Status Detail", bold)
            worksheet.write("I2", "Status Action", bold)
            worksheet.write("J2", "Status History Note", bold)
            worksheet.write(
                "K2",
                "Please put your Feedback / updates in the column if different to Column G, H and / or I",
                cell_format,
            )
            worksheet.write("L2", "Qty Booked", bold)
            worksheet.write("M2", "Qty Scanned", bold)
            worksheet.write("N2", "Booked to Scanned Variance", bold)
            worksheet.write("O2", "From State", bold)
            worksheet.write("P2", "To Entity Group Name", bold)
            worksheet.write("Q2", "To Entity", bold)
            worksheet.write("R2", "To Suburb", bold)
            worksheet.write("S2", "To State", bold)
            worksheet.write("T2", "To Postal Code", bold)
            worksheet.write("U2", "Client Order Number", bold)
            worksheet.write("V2", "Actual Delivery", bold)
            worksheet.write("W2", "POD?", bold)
            worksheet.write("X2", "POD LINK", bold)
            worksheet.write("Y2", "POD Signed on Glass Link", bold)
            worksheet.write("Z2", "Target Delivery KPI (Days)", bold)
            worksheet.write("AA2", "Delivery Days from Booked", bold)
            worksheet.write("AB2", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AC2", "Store Booking Date", bold)

            row = 2
        else:
            worksheet.write("A1", "Booked Date", bold)
            cell_format = workbook.add_format(
                {"font_color": "red", "bold": 1, "align": "left"}
            )
            worksheet.write("B1", "Pickup Days Late", cell_format)
            worksheet.write("C1", "Delivery Days Early / Late", cell_format)
            worksheet.write("D1", "Query With", bold)
            worksheet.write("E1", "Client Sales Invoice", bold)
            worksheet.write("F1", "Consignment No", bold)
            worksheet.write("G1", "Status", bold)
            worksheet.write("H1", "Status Detail", bold)
            worksheet.write("I1", "Status Action", bold)
            worksheet.write("J1", "Status History Note", bold)
            worksheet.write(
                "K1",
                "Please put your Feedback / updates in the column if different to Column G, H and / or I",
                cell_format,
            )
            worksheet.write("L1", "Qty Booked", bold)
            worksheet.write("M1", "Qty Scanned", bold)
            worksheet.write("N1", "Booked to Scanned Variance", bold)
            worksheet.write("O1", "From State", bold)
            worksheet.write("P1", "To Entity Group Name", bold)
            worksheet.write("Q1", "To Entity", bold)
            worksheet.write("R1", "To Suburb", bold)
            worksheet.write("S1", "To State", bold)
            worksheet.write("T1", "To Postal Code", bold)
            worksheet.write("U1", "Client Order Number", bold)
            worksheet.write("V1", "Actual Delivery", bold)
            worksheet.write("W1", "POD?", bold)
            worksheet.write("X1", "POD LINK", bold)
            worksheet.write("Y1", "POD Signed on Glass Link", bold)
            worksheet.write("Z1", "Target Delivery KPI (Days)", bold)
            worksheet.write("AA1", "Delivery Days from Booked", bold)
            worksheet.write("AB1", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AC1", "Store Booking Date", bold)

            row = 1

        logger.error(f"#361 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            if booking_ind % 500 == 0:
                logger.error(f"#362 Current index: {booking_ind}")

            booking_lines = Booking_lines.objects.only(
                "e_qty", "e_qty_scanned_fp", "pk_lines_id"
            ).filter(fk_booking_id=booking.pk_booking_id)
            sydney = pytz.timezone("Australia/Sydney")
            sydney_today = sydney.localize(datetime.now())
            sydney_today = sydney_today.replace(minute=0, hour=0, second=0)

            e_qty_total = 0
            e_qty_scanned_fp_total = 0

            for booking_line in booking_lines:
                if booking_line.e_qty is not None:
                    e_qty_total = e_qty_total + booking_line.e_qty

                if booking_line.e_qty_scanned_fp is not None:
                    e_qty_scanned_fp_total = (
                        e_qty_scanned_fp_total + booking_line.e_qty_scanned_fp
                    )

            if booking.b_dateBookedDate and booking.b_dateBookedDate:
                worksheet.write_datetime(
                    row, col + 0, booking.b_dateBookedDate, date_format
                )

            if booking.b_status is not None and "booked" in booking.b_status.lower():
                pickup_days_late = (
                    booking.b_dateBookedDate.date()
                    + timedelta(days=2)
                    - sydney_today.date()
                ).days

                if pickup_days_late < 0:
                    cell_format = workbook.add_format({"font_color": "red"})
                    worksheet.write(
                        row,
                        col + 1,
                        "(" + str(pickup_days_late * -1) + ")",
                        cell_format,
                    )
                else:
                    worksheet.write(row, col + 1, pickup_days_late)

            if booking.b_status is not None and booking.b_dateBookedDate is not None:
                delivery_kpi_days = 0
                days_early_late = "None - not booked"

                if booking.delivery_kpi_days is not None:
                    delivery_kpi_days = int(booking.delivery_kpi_days)

                if booking.b_dateBookedDate is not None:
                    days_early_late = (
                        booking.b_dateBookedDate.date()
                        + timedelta(days=delivery_kpi_days)
                        - sydney_today.date()
                    ).days

                if days_early_late < 0:
                    cell_format = workbook.add_format({"font_color": "red"})
                    worksheet.write(
                        row, col + 2, "(" + str(days_early_late * -1) + ")", cell_format
                    )
                else:
                    worksheet.write(row, col + 2, days_early_late)

            query_with = ""
            if booking.dme_status_action is None or booking.dme_status_action == "":
                query_with = booking.vx_freight_provider

                if e_qty_total == e_qty_scanned_fp_total:
                    query_with = "Freight Provider"
                elif e_qty_scanned_fp_total == 0:
                    query_with = (
                        "Warehouse: Nothing sent yet, warehouse to send "
                        + str(e_qty_total)
                    )
                elif e_qty_scanned_fp_total is not 0:
                    query_with = (
                        "Warehouse: Partial qty of "
                        + str(e_qty_total - e_qty_scanned_fp_total)
                        + " short, warehouse to send"
                    )
            else:
                query_with = booking.dme_status_action

            worksheet.write(row, col + 3, query_with)
            worksheet.write(row, col + 4, booking.b_client_sales_inv_num)
            worksheet.write(row, col + 5, booking.v_FPBookingNumber)
            worksheet.write(row, col + 6, booking.b_status)

            cell_format = workbook.add_format({"text_wrap": True})
            worksheet.write(row, col + 7, booking.dme_status_detail, cell_format)
            worksheet.write(row, col + 8, booking.dme_status_action, cell_format)
            worksheet.write(row, col + 9, booking.dme_status_history_notes, cell_format)
            worksheet.write(row, col + 10, "", cell_format)
            worksheet.write(row, col + 11, e_qty_total)
            worksheet.write(row, col + 12, e_qty_scanned_fp_total)
            worksheet.write(row, col + 13, e_qty_total - e_qty_scanned_fp_total)
            worksheet.write(row, col + 14, booking.pu_Address_State)

            customer_group_name = ""
            customer_groups = Dme_utl_client_customer_group.objects.all()
            for customer_group in customer_groups:
                if (
                    customer_group.name_lookup.lower()
                    in booking.deToCompanyName.lower()
                ):
                    customer_group_name = customer_group.group_name
            worksheet.write(row, col + 15, customer_group_name)

            worksheet.write(row, col + 16, booking.deToCompanyName)
            worksheet.write(row, col + 17, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 18, booking.de_To_Address_State)
            worksheet.write(row, col + 19, booking.de_To_Address_PostalCode)
            worksheet.write(row, col + 20, booking.b_client_order_num)

            if (
                booking.s_21_ActualDeliveryTimeStamp
                and booking.s_21_ActualDeliveryTimeStamp
            ):
                worksheet.write_datetime(
                    row, col + 21, booking.s_21_ActualDeliveryTimeStamp, date_format
                )

            if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (
                booking.z_pod_signed_url is not None
                and len(booking.z_pod_signed_url) > 0
            ):
                worksheet.write(row, col + 22, "Y")
            else:
                worksheet.write(row, col + 22, "")

            if settings.ENV == "dev":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 23,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 24,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )
            elif settings.ENV == "prod":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 23,
                        settings.S3_URL + "/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 24,
                        settings.S3_URL + "/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )

            worksheet.write(row, col + 25, booking.delivery_kpi_days)

            if (
                booking.b_status is not None
                and booking.b_status == "Delivered"
                and booking.s_21_ActualDeliveryTimeStamp is not None
                and booking.b_dateBookedDate is not None
            ):
                worksheet.write(
                    row,
                    col + 26,
                    (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )
                worksheet.write(
                    row,
                    col + 27,
                    booking.delivery_kpi_days
                    - (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )

            if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                worksheet.write_datetime(
                    row, col + 28, booking.de_Deliver_By_Date, date_format
                )

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#365 Finished - `Whse` XLS")
    elif xls_type == "old":
        logger.error(f"OLD")
        # body = literal_eval(request.body.decode('utf8'))
        # bookingIds = body["bookingIds"]

        # response = HttpResponse(content_type='application/vnd.ms-excel')
        # response['Content-Disposition'] = 'attachment; filename="bookings_seaway.xlsx"'

        # workbook = xlsxwriter.Workbook(response, {'in_memory': True})
        # worksheet = workbook.add_worksheet()
        # worksheet.set_column(0, 13, width=24)
        # bold = workbook.add_format({'bold': 1, 'align': 'left'})

        # worksheet.write('A1', 'b_bookingID_Visual', bold)
        # worksheet.write('B1', 'puPickUpAvailFrom_Date', bold)
        # worksheet.write('C1', 'b_dateBookedDate', bold)
        # worksheet.write('D1', 'puCompany', bold)
        # worksheet.write('E1', 'pu_Address_Suburb', bold)
        # worksheet.write('F1', 'pu_Address_State', bold)
        # worksheet.write('G1', 'pu_Address_PostalCode', bold)
        # worksheet.write('H1', 'deToCompanyName', bold)
        # worksheet.write('I1', 'de_To_Address_Suburb', bold)
        # worksheet.write('J1', 'de_To_Address_State', bold)
        # worksheet.write('K1', 'de_To_Address_PostalCode', bold)
        # worksheet.write('L1', 'b_clientReference_RA_Numbers', bold)
        # worksheet.write('M1', 'vx_freight_provider', bold)
        # worksheet.write('N1', 'vx_serviceName', bold)
        # worksheet.write('O1', 'v_FPBookingNumber', bold)
        # worksheet.write('P1', 'b_status', bold)
        # worksheet.write('Q1', 'b_status_API', bold)
        # worksheet.write('R1', 's_05_LatestPickUpDateTimeFinal', bold)
        # worksheet.write('S1', 's_06_LatestDeliveryDateTimeFinal', bold)
        # worksheet.write('T1', 's_20_Actual_Pickup_TimeStamp', bold)
        # worksheet.write('U1', 's_21_Actual_Delivery_TimeStamp', bold)
        # worksheet.write('V1', 'z_pod_url', bold)
        # worksheet.write('W1', 'z_pod_signed_url', bold)
        # worksheet.write('X1', 'vx_fp_pu_eta_time', bold)
        # worksheet.write('Y1', 'vx_fp_del_eta_time', bold)

        # row = 1
        # col = 0

        # for id in bookingIds:
        #     booking = Bookings.objects.get(id=id)
        #     worksheet.write(row, col, booking.b_bookingID_Visual)

        #     if booking.puPickUpAvailFrom_Date and booking.puPickUpAvailFrom_Date:
        #         worksheet.write(row, col + 1, booking.puPickUpAvailFrom_Date.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 1, "")

        #     if booking.b_dateBookedDate and booking.b_dateBookedDate:
        #         worksheet.write(row, col + 2, booking.b_dateBookedDate.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 2, "")

        #     worksheet.write(row, col + 3, booking.puCompany)
        #     worksheet.write(row, col + 4, booking.pu_Address_Suburb)
        #     worksheet.write(row, col + 5, booking.pu_Address_State)
        #     worksheet.write(row, col + 6, booking.pu_Address_PostalCode)
        #     worksheet.write(row, col + 7, booking.deToCompanyName)
        #     worksheet.write(row, col + 8, booking.de_To_Address_Suburb)
        #     worksheet.write(row, col + 9, booking.de_To_Address_State)
        #     worksheet.write(row, col + 10, booking.de_To_Address_PostalCode)
        #     worksheet.write(row, col + 11, booking.b_clientReference_RA_Numbers)
        #     worksheet.write(row, col + 12, booking.vx_freight_provider)
        #     worksheet.write(row, col + 13, booking.vx_serviceName)
        #     worksheet.write(row, col + 14, booking.v_FPBookingNumber)
        #     worksheet.write(row, col + 15, booking.b_status)
        #     worksheet.write(row, col + 16, booking.b_status_API)

        #     if booking.s_05_LatestPickUpDateTimeFinal and booking.s_05_LatestPickUpDateTimeFinal:
        #         worksheet.write(row, col + 17, booking.s_05_LatestPickUpDateTimeFinal.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 17, "")

        #     if booking.s_06_LatestDeliveryDateTimeFinal and booking.s_06_LatestDeliveryDateTimeFinal:
        #         worksheet.write(row, col + 18, booking.s_06_LatestDeliveryDateTimeFinal.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 18, "")

        #     if booking.s_20_Actual_Pickup_TimeStamp and booking.s_20_Actual_Pickup_TimeStamp:
        #         worksheet.write(row, col + 19, booking.s_20_Actual_Pickup_TimeStamp.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 19, "")

        #     if booking.s_21_Actual_Delivery_TimeStamp and booking.s_21_Actual_Delivery_TimeStamp:
        #         worksheet.write(row, col + 20, booking.s_21_Actual_Delivery_TimeStamp.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 20, "")

        #     worksheet.write(row, col + 21, booking.z_pod_url)
        #     worksheet.write(row, col + 22, booking.z_pod_signed_url)

        #     if booking.vx_fp_pu_eta_time and booking.vx_fp_pu_eta_time:
        #         worksheet.write(row, col + 23, booking.vx_fp_pu_eta_time.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 23, "")

        #     if booking.vx_fp_del_eta_time and booking.vx_fp_del_eta_time:
        #         worksheet.write(row, col + 24, booking.vx_fp_del_eta_time.strftime("%Y-%m-%d %H:%M:%S"))
        #     else:
        #         worksheet.write(row, col + 24, "")

        #     row += 1

        # workbook.close()
        # return respons

    return local_filepath + filename


def build_xls_and_send(
    bookings, email_addr, report_type, username, start_date, end_date, show_field_name
):
    if report_type == "booking":
        filepath = build_xls(
            bookings, "Bookings", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],  # Recipient email address(list)
            "Bookings XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Bookings) you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "booking_line":
        filepath = build_xls(
            bookings, "BookingLines", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],  # Recipient email address(list)
            "BookingLines XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Booking Lines) you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "booking_with_gaps":
        filepath = build_xls(
            bookings,
            "BookingsWithGaps",
            username,
            start_date,
            end_date,
            show_field_name,
        )
        send_email(
            [email_addr],  # Recipient email address(list)
            "Bookings with Gaps XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Booking With Gaps) you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "whse":
        filepath = build_xls(
            bookings, "Whse", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],  # Recipient email address(list)
            "Whse XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Whse) you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "all":
        filepath_booking = build_xls(
            bookings, "Bookings", username, start_date, end_date, show_field_name
        )
        filepath_booking_line = build_xls(
            bookings, "BookingLines", username, start_date, end_date, show_field_name
        )
        filepath_booking_with_gaps = build_xls(
            bookings,
            "BookingsWithGaps",
            username,
            start_date,
            end_date,
            show_field_name,
        )
        filepath_whse = build_xls(
            bookings, "Whse", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],  # Recipient email address(list)
            "All XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Bookings & Booking Lines & Booking With Gaps & Whse) you generated from Deliver-Me.",  # Message of email
            [
                filepath_booking,
                filepath_booking_line,
                filepath_booking_with_gaps,
                filepath_whse,
            ],  # Attachment file path(list)
        )
