import sys, time
import os
import errno
import datetime
from datetime import timedelta
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
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

from django.core.mail import send_mail
from django.conf import settings
from .models import *

if settings.ENV == 'local':
    production = False # Local
else:
    production = True  # Dev

if production:
    DB_HOST = 'deliverme-db.cgc7xojhvzjl.ap-southeast-2.rds.amazonaws.com'
    DB_USER = 'fmadmin'
    DB_PASS = 'oU8pPQxh'
    DB_PORT = 3306

    if settings.ENV == 'dev':
        DB_NAME = 'dme_db_dev'  # Dev
    elif settings.ENV == 'prod':
        DB_NAME = 'dme_db_prod'  # Prod
else:
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASS = 'root'
    DB_PORT = 3306
    DB_NAME = 'deliver_me'

redis_host = "localhost"
redis_port = 6379
redis_password = ""

ACCOUNT_CODE = "AATEST"

def redis_con():
    try:
        redisCon = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password)
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
            return 'success'

        return error

def send_email(send_to, subject, text, files=None, server="localhost", use_tls=True):
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_HOST_USER
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)

    if use_tls:
        smtp.starttls()

    smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    smtp.sendmail(settings.EMAIL_HOST_USER, send_to, msg.as_string())
    smtp.close()

def upload_sftp(host, username, password, sftp_filepath, local_filepath, local_filepath_dup, filename):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(host="edi.alliedexpress.com.au", username="delvme.external", password="987899e64", cnopts=cnopts) as sftp_con:
        with sftp_con.cd(sftp_filepath):
            sftp_con.put(local_filepath + filename)
            sftp_file_size = sftp_con.lstat(sftp_filepath + filename).st_size
            local_file_size = os.stat(local_filepath + filename).st_size

            if sftp_file_size == local_file_size:
                if not os.path.exists(local_filepath_dup):
                    os.makedirs(local_filepath_dup)
                shutil.move(local_filepath + filename, local_filepath_dup + filename)

        sftp_con.close()

def get_available_bookings(mysqlcon, booking_ids):
    where_clause = ' WHERE '
    for id in booking_ids:
        where_clause = where_clause + 'id = ' + str(id) + ' OR '
    where_clause = where_clause[:-4]

    with mysqlcon.cursor() as cursor:
        sql = "SELECT * FROM `dme_bookings` " + where_clause + " ORDER BY `id` ASC"

        # print('@1 - sql: ', sql)
        cursor.execute(sql)
        result = cursor.fetchall()
        # print('Avaliable Bookings cnt: ', len(result))
        return result

def get_available_booking_lines(mysqlcon, booking):
    with mysqlcon.cursor() as cursor:
        sql = "SELECT * FROM `dme_booking_lines` WHERE `fk_booking_id`=%s"
        cursor.execute(sql, (booking['pk_booking_id']))
        result = cursor.fetchall()
        # print('Avaliable Booking Lines cnt: ', len(result))
        return result

def make_3digit(num):
    if num > 0 and num < 10:
        return '00' + str(num)
    elif num > 9 and num < 100:
        return '0' + str(num)
    elif num > 99 and num < 1000:
        return str(num)
    else:
        return str('ERROR: Number is bigger than 999')

def wrap_in_quote(string):
    return '"' + str(string) + '"'

def csv_write(fileHandler, bookings, mysqlcon):
    # Write Header
    fileHandler.write("userId,connoteNo,connoteDate,customer,senderName,senderAddress1,senderAddress2,senderSuburb,senderPostcode,senderState,\
    senderContact,senderPhone,pickupDate,pickupTime,receiverName,receiverAddress1,receiverAddress2,receiverSuburb,receiverPostcode,\
    receiverState,receiverContact,receiverPhone,deliveryDate,deliveryTime,totalQuantity,totalPallets,totalWeight,totalVolume,\
    senderReference,description,specialInstructions,notes,jobType,serviceType,priorityType,vehicleType,itemCode,scanCode,\
    freightCode,itemReference,description,quantity,pallets,labels,totalWeight,totalVolume,length,width,height,weight,docAmount,\
    senderCode,receiverCode,warehouseOrderType,freightline_serialNumber,freightline_wbDocket,senderAddress3,receiverAddress3,\
    senderEmail,receiverEmail,noConnote")

    # Write Each Line
    comma = ','
    newLine = '\n'
    if len(bookings) > 0:
        for booking in bookings:
            booking_lines = get_available_booking_lines(mysqlcon, booking)
            eachLineText = 'DVM0001'

            if booking['b_bookingID_Visual'] is None: h0 = ''
            else:
                h0 = wrap_in_quote('DME' + str(booking.get('b_bookingID_Visual')))

            if booking['puPickUpAvailFrom_Date'] is None: h1 = ''
            else:
                h1 = wrap_in_quote(str(booking.get('puPickUpAvailFrom_Date')))

            h2 = '009790'

            if booking['puCompany'] is None: h00 = ''
            else:
                h00 = wrap_in_quote(booking.get('puCompany'))

            if booking['pu_Address_Street_1'] is None: h01 = ''
            else:
                h01 = wrap_in_quote(booking.get('pu_Address_Street_1'))

            if booking['pu_Address_street_2'] is None: h02 = ''
            else:
                h02 = wrap_in_quote(booking.get('pu_Address_street_2'))

            if booking['pu_Address_Suburb'] is None: h03 = ''
            else:
                h03 = wrap_in_quote(booking.get('pu_Address_Suburb'))

            if booking['pu_Address_PostalCode'] is None: h04 = ''
            else:
                h04 = wrap_in_quote(booking.get('pu_Address_PostalCode'))

            if booking['pu_Address_State'] is None: h05 = ''
            else:
                h05 = wrap_in_quote(booking.get('pu_Address_State'))

            if booking['pu_Contact_F_L_Name'] is None: h06 = ''
            else:
                h06 = wrap_in_quote(booking.get('pu_Contact_F_L_Name'))

            if booking['pu_Phone_Main'] is None: h07 = ''
            else:
                h07 = str(booking.get('pu_Phone_Main'))

            if booking['pu_PickUp_Avail_From_Date_DME'] is None: h08 = ''
            else:
                h08 = wrap_in_quote(booking.get('pu_PickUp_Avail_From_Date_DME'))

            if booking['pu_PickUp_Avail_Time_Hours_DME'] is None: h09 = ''
            else:
                h09 = str(booking.get('pu_PickUp_Avail_Time_Hours_DME'))

            if booking['deToCompanyName'] is None: h10 = ''
            else:
                h10 = wrap_in_quote(booking.get('deToCompanyName'))

            if booking['de_To_Address_Street_1'] is None: h11 = ''
            else:
                h11 = wrap_in_quote(booking.get('de_To_Address_Street_1'))

            if booking['de_To_Address_Street_2'] is None: h12 = ''
            else:
                h12 = wrap_in_quote(booking.get('de_To_Address_Street_2'))

            if booking['de_To_Address_Suburb'] is None: h13 = ''
            else:
                h13 = wrap_in_quote(booking.get('de_To_Address_Suburb'))

            if booking['de_To_Address_PostalCode'] is None: h14 = ''
            else:
                h14 = wrap_in_quote(booking.get('de_To_Address_PostalCode'))

            if booking['de_To_Address_State'] is None: h15 = ''
            else:
                h15 = wrap_in_quote(booking.get('de_To_Address_State'))

            if booking['de_to_Contact_F_LName'] is None: h16 = ''
            else:
                h16 = wrap_in_quote(booking.get('de_to_Contact_F_LName'))

            if booking['de_to_Phone_Main'] is None: h17 = ''
            else:
                h17 = str(booking.get('de_to_Phone_Main'))

            if booking['de_Deliver_From_Date'] is None: h18 = ''
            else:
                h18 = wrap_in_quote(booking.get('de_Deliver_From_Date'))

            if booking['de_Deliver_From_Hours'] is None: h19 = ''
            else:
                h19 = str(booking.get('de_Deliver_From_Hours'))

            h20 = ''
            h21 = ''
            h22 = ''
            h23 = ''

            if booking['b_client_sales_inv_num'] is None: h24 = ''
            else:
                h24 = wrap_in_quote(booking.get('b_client_sales_inv_num'))
            
            if booking['b_client_order_num'] is None: h25 = ''
            else:
                h25 = wrap_in_quote(booking.get('b_client_order_num'))
            
            if booking['de_to_PickUp_Instructions_Address'] is None: h26 = ''
            else:
                h26 = wrap_in_quote(booking.get('de_to_PickUp_Instructions_Address'))
            
            h27 = ''

            if booking['vx_serviceName'] is None: h28 = ''
            else:
                h28 = wrap_in_quote(booking.get('vx_serviceName'))
            
            if booking['v_service_Type'] is None: h29 = ''
            else:
                h29 = wrap_in_quote(booking.get('v_service_Type'))

            h50 = h25
            h51 = ''

            if booking['pu_pickup_instructions_address'] is None: h52 = ''
            else:
                h52 = wrap_in_quote(booking.get('pu_pickup_instructions_address'))

            h53 = ''

            if booking['pu_Email'] is None: h54 = ''
            else:
                h54 = wrap_in_quote(booking.get('pu_Email'))
            if booking['de_Email'] is None: h55 = ''
            else:
                h55 = wrap_in_quote(booking.get('de_Email'))

            h56 = 'N'

            h30 = ''
            h31 = ''
            if (len(booking_lines) > 0):
                for booking_line in booking_lines:
                    if booking['b_clientReference_RA_Numbers'] is None: h32 = ''
                    else:
                        h32 = str(booking.get('b_clientReference_RA_Numbers'))

                    h33 = ''
                    if booking_line['e_type_of_packaging'] is None: h34 = ''
                    else:
                        h34 = wrap_in_quote(booking_line.get('e_type_of_packaging'))
                    if booking_line['client_item_reference'] is None: h35 = ''
                    else:
                        h35 = wrap_in_quote(booking_line.get('client_item_reference'))
                    if booking_line['e_item'] is None: h36 = ''
                    else:
                        h36 = wrap_in_quote(booking_line.get('e_item'))
                    if booking_line['e_qty'] is None: h37 = ''
                    else:
                        h37 = str(booking_line.get('e_qty'))
                    
                    h38 = ''
                    
                    if booking_line['e_qty'] is None: h39 = ''
                    else:
                        h39 = str(booking_line.get('e_qty'))

                    h40 = ''
                    h41 = ''
                    if booking_line['e_dimLength'] is None: h42 = ''
                    else:
                        h42 = str(booking_line.get('e_dimLength'))
                    if booking_line['e_dimWidth'] is None: h43 = ''
                    else:
                        h43 = str(booking_line.get('e_dimWidth'))
                    if booking_line['e_dimHeight'] is None: h44 = ''
                    else:
                        h44 = str(booking_line.get('e_dimHeight'))
                    if booking_line['e_weightPerEach'] is None: h45 = ''
                    else:
                        h45 = str(booking_line.get('e_weightPerEach'))
                    h46 = ''
                    h47 = ''
                    h48 = ''
                    h49 = ''

                    eachLineText += comma + h0 + comma + h1 + comma + h2
                    eachLineText += comma + h00 + comma + h01 + comma + h02 + comma + h03 + comma + h04 + comma + h05 + comma + h06 + comma + h07 + comma + h08 + comma + h09
                    eachLineText += comma + h10 + comma + h11 + comma + h12 + comma + h13 + comma + h14 + comma + h15 + comma + h16 + comma + h17 + comma + h18 + comma + h19
                    eachLineText += comma + h20 + comma + h21 + comma + h22 + comma + h23 + comma + h24 + comma + h25 + comma + h26 + comma + h27 + comma + h28 + comma + h29
                    eachLineText += comma + h30 + comma + h31 + comma + h32 + comma + h33 + comma + h34 + comma + h35 + comma + h36 + comma + h37 + comma + h38 + comma + h39
                    eachLineText += comma + h40 + comma + h41 + comma + h42 + comma + h43 + comma + h44 + comma + h45 + comma + h46 + comma + h47 + comma + h48 + comma + h49
                    eachLineText += comma + h50 + comma + h51 + comma + h52 + comma + h53 + comma + h54 + comma + h55 + comma + h56
                    fileHandler.write(newLine + eachLineText)
                    eachLineText = 'DVM0001'
            else:
                h32 = ''
                h33 = ''
                h34 = ''
                h35 = ''
                h36 = ''
                h37 = ''
                h38 = ''
                h39 = ''
                h40 = ''
                h41 = ''
                h42 = ''
                h43 = ''
                h44 = ''
                h45 = ''
                h46 = ''
                h47 = ''
                h48 = ''
                h49 = ''

                eachLineText += comma + h0 + comma + h1 + comma + h2
                eachLineText += comma + h00 + comma + h01 + comma + h02 + comma + h03 + comma + h04 + comma + h05 + comma + h06 + comma + h07 + comma + h08 + comma + h09
                eachLineText += comma + h10 + comma + h11 + comma + h12 + comma + h13 + comma + h14 + comma + h15 + comma + h16 + comma + h17 + comma + h18 + comma + h19
                eachLineText += comma + h20 + comma + h21 + comma + h22 + comma + h23 + comma + h24 + comma + h25 + comma + h26 + comma + h27 + comma + h28 + comma + h29
                eachLineText += comma + h30 + comma + h31 + comma + h32 + comma + h33 + comma + h34 + comma + h35 + comma + h36 + comma + h37 + comma + h38 + comma + h39
                eachLineText += comma + h40 + comma + h41 + comma + h42 + comma + h43 + comma + h44 + comma + h45 + comma + h46 + comma + h47 + comma + h48 + comma + h49
                eachLineText += comma + h50 + comma + h51 + comma + h52 + comma + h53 + comma + h54 + comma + h55 + comma + h56
                fileHandler.write(newLine + eachLineText)
                eachLineText = 'DVM0001'

def generate_csv(booking_ids):
    # print('#900 - Running %s' % datetime.datetime.now())

    try:
        mysqlcon = pymysql.connect(host=DB_HOST,
                                   port=DB_PORT,
                                   user=DB_USER,
                                   password=DB_PASS,
                                   db=DB_NAME,
                                   charset='utf8mb4',
                                   cursorclass=pymysql.cursors.DictCursor)
    except:
        # print('Mysql DB connection error!')
        exit(1)

    bookings = get_available_bookings(mysqlcon, booking_ids)

    csv_name = 'SEATEMP_' + str(len(booking_ids)) + "_" + str(datetime.utcnow()) + ".csv"
    
    if production:
        f = open("/home/cope_au/dme_sftp/cope_au/pickup_ext/" + csv_name, "w")
    else:
        f = open("/Users/admin/Documents/" + csv_name, "w")

    csv_write(f, bookings, mysqlcon)
    f.close()

    # CSV sftp server info
    host = 'esmart.cope.com.au'
    username = 'deliverme'
    password = 'C3n?7u4f'
    sftp_filepath = '/home/import/csvimport/upload or csvimport/upload/'
    local_filepath = '/home/cope_au/dme_sftp/cope_au/pickup_ext/'
    local_filepath_dup = '/home/cope_au/dme_sftp/cope_au/pickup_ext/'
    filename = csv_name

    # upload_sftp(host, username, password, sftp_filepath, local_filepath, local_filepath_dup, filename)

    # print('#901 - Finished %s' % datetime.datetime.now())
    mysqlcon.close()
    return csv_name

def get_booked_list(bookings):
    booked_list = []

    for booking in bookings:
        if booking['b_dateBookedDate'] and booking['b_dateBookedDate'] != '':
            booked_list.append(booking['b_bookingID_Visual'])

    return booked_list

def get_item_type(i):
    if i:
        if "UHP" in i:
            return 'PCR'
        elif "PCR" in i:
            return 'PCR'
        elif "LTR" in i:
            return 'LTR'
        elif "TBR" in i:
            return 'TBR'
        else:
            return 'ERROR'
    else:
        return 'ERROR'

def build_xml(booking_ids, vx_freight_provider):
    try:
        mysqlcon = pymysql.connect(host=DB_HOST,
                                   port=DB_PORT,
                                   user=DB_USER,
                                   password=DB_PASS,
                                   db=DB_NAME,
                                   charset='utf8mb4',
                                   cursorclass=pymysql.cursors.DictCursor)
    except:
        exit(1)
    mycursor = mysqlcon.cursor()

    bookings = get_available_bookings(mysqlcon, booking_ids)
    booked_list = get_booked_list(bookings)

    if len(booked_list) > 0:
        return booked_list
    
    if vx_freight_provider == 'allied':
        #start check if xmls folder exists
        if production:
            local_filepath = "/var/www/html/dme_api/static/xmls/allied_au/"
            local_filepath_dup = "/var/www/html/dme_api/static/xmls/allied_au/archive/" + str(datetime.now().strftime("%Y_%m_%d")) + "/"
        else:
            local_filepath = "/Users/admin/work/goldmine/dme_api/static/xmls/allied_au/"
            local_filepath_dup = "/Users/admin/work/goldmine/dme_api/static/xmls/allied_au/archive/" + str(datetime.now().strftime("%Y_%m_%d")) + "/"
        
        if not os.path.exists(local_filepath):
            os.makedirs(local_filepath)
        #end check if xmls folder exists

        i = 1
        for booking in bookings:
            try:
                #start db query for fetching data from dme_booking_lines table
                sql1 = "SELECT e_qty, e_item_type, e_item, e_dimWidth, e_dimLength, e_dimHeight, e_Total_KG_weight \
                        FROM dme_booking_lines \
                        WHERE fk_booking_id = %s"
                adr1 = (booking['pk_booking_id'], )
                mycursor.execute(sql1, adr1)
                booking_lines = mycursor.fetchall() 

                #start calculate total item quantity and total item weight
                totalQty = 0
                totalWght = 0
                for booking_line in booking_lines:
                    totalQty = totalQty + booking_line['e_qty']
                    totalWght = totalWght + booking_line['e_Total_KG_weight']
                #start calculate total item quantity and total item weight

                #start xml file name using naming convention
                date = datetime.now().strftime("%Y%m%d")+"_"+datetime.now().strftime("%H%M%S")
                filename = "AL_HANALT_"+date+"_"+str(i)+".xml"
                i+= 1
                #end xml file name using naming convention

                #start formatting xml file and putting data from db tables
                root = xml.Element("AlTransportData", **{'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'})
                consignmentHeader = xml.Element("ConsignmentHeader")
                root.append(consignmentHeader)
                chargeAccount = xml.SubElement(consignmentHeader, "ChargeAccount")
                chargeAccount.text = "HANALT"
                senderName = xml.SubElement(consignmentHeader, "SenderName")
                senderName.text = "Hankook"
                senderAddressLine1 = xml.SubElement(consignmentHeader, "SenderAddressLine1")
                senderAddressLine1.text = booking['pu_Address_Street_1']
                senderLocality = xml.SubElement(consignmentHeader, "SenderLocality")
                senderLocality.text = booking['pu_Address_Suburb']
                senderState = xml.SubElement(consignmentHeader, "SenderState")
                senderState.text = booking['pu_Address_State']
                senderPostcode = xml.SubElement(consignmentHeader, "SenderPostcode")
                senderPostcode.text = booking['pu_Address_PostalCode']

                companyName = booking['deToCompanyName'].replace("<", "")
                companyName = companyName.replace(">", "")
                companyName = companyName.replace("\"", "")
                companyName = companyName.replace("'", "")
                companyName = companyName.replace("&", "and")
                
                consignmentShipments = xml.Element("ConsignmentShipments")
                root.append(consignmentShipments)
                consignmentShipment = xml.SubElement(consignmentShipments, "ConsignmentShipment")
                ConsignmentNumber = xml.SubElement(consignmentShipment, "ConsignmentNumber")
                ConsignmentNumber.text = booking['pk_booking_id']
                DespatchDate = xml.SubElement(consignmentShipment, "DespatchDate")
                DespatchDate.text = str(booking['puPickUpAvailFrom_Date'])
                CarrierService = xml.SubElement(consignmentShipment, "CarrierService")
                CarrierService.text = booking['vx_serviceName']
                totalQuantity = xml.SubElement(consignmentShipment, "totalQuantity")
                totalQuantity.text = str(totalQty)
                totalWeight = xml.SubElement(consignmentShipment, "totalWeight")
                totalWeight.text = str(totalWght)
                ReceiverName = xml.SubElement(consignmentShipment, "ReceiverName")
                ReceiverName.text = companyName
                ReceiverAddressLine1 = xml.SubElement(consignmentShipment, "ReceiverAddressLine1")
                ReceiverAddressLine1.text = booking['de_To_Address_Street_1']
                ReceiverLocality = xml.SubElement(consignmentShipment, "ReceiverLocality")
                ReceiverLocality.text = booking['de_To_Address_Suburb']
                ReceiverState = xml.SubElement(consignmentShipment, "ReceiverState")
                ReceiverState.text = booking['de_To_Address_State']
                ReceiverPostcode = xml.SubElement(consignmentShipment, "ReceiverPostcode")
                ReceiverPostcode.text = booking['de_To_Address_PostalCode']
                ItemsShipment = xml.SubElement(consignmentShipment, "ItemsShipment")

                for booking_line in booking_lines:
                    Item = xml.SubElement(ItemsShipment, "Item")
                    Quantity = xml.SubElement(Item, "Quantity")
                    Quantity.text = str(booking_line['e_qty'])
                    ItemType = xml.SubElement(Item, "ItemType")
                    ItemType.text = get_item_type(booking_line['e_item_type'])
                    ItemDescription = xml.SubElement(Item, "ItemDescription")
                    ItemDescription.text = booking_line['e_item']

                    Width = xml.SubElement(Item, "Width")
                    if booking_line['e_dimWidth'] == None or booking_line['e_dimWidth'] == '':
                        Width.text = str('1')
                    else:
                        Width.text = str(booking_line['e_dimWidth'])

                    Length = xml.SubElement(Item, "Length")
                    if booking_line['e_dimLength'] == None or booking_line['e_dimLength'] == '':
                        Length.text = str('1')
                    else:
                        Length.text = str(booking_line['e_dimLength'])

                    Height = xml.SubElement(Item, "Height")
                    if booking_line['e_dimHeight'] == None or booking_line['e_dimHeight'] == '':
                        Height.text = str('1')
                    else:
                        Height.text = str(booking_line['e_dimHeight'])

                    DeadWeight = xml.SubElement(Item, "DeadWeight")
                    DeadWeight.text = str(booking_line['e_Total_KG_weight']/booking_line['e_qty'])

                    SSCCs = xml.SubElement(Item, "SSCCs")
                    SSCC = xml.SubElement(SSCCs, "SSCC")
                    SSCC.text = booking['pk_booking_id']
                #end formatting xml file and putting data from db tables

                # start writting data into xml files
                tree = xml.ElementTree(root)
                with open(local_filepath + filename, "wb") as fh:
                    tree.write(fh, encoding='UTF-8', xml_declaration=True)

                #start copying xml files to sftp server
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
                #end copying xml files to sftp server

                #start update booking status in dme_booking table
                sql2 = "UPDATE dme_bookings set b_status = %s, b_dateBookedDate = %s WHERE pk_booking_id = %s"
                adr2 = ('Booked XML', str(datetime.utcnow()), booking['pk_booking_id'])
                mycursor.execute(sql2, adr2)
                mysqlcon.commit()
            except Exception as e:
                # print('@300 Allied XML - ', e)
                return e
    elif vx_freight_provider == 'taz':
        #start check if xmls folder exists
        if production:
            local_filepath = "/var/www/html/dme_api/static/xmls/taz_au/"
            local_filepath_dup = "/var/www/html/dme_api/static/xmls/taz_au/archive/" + str(datetime.now().strftime("%Y_%m_%d")) + "/"
        else:
            local_filepath = "/Users/admin/work/goldmine/dme_api/static/xmls/taz_au/"
            local_filepath_dup = "/Users/admin/work/goldmine/dme_api/static/xmls/taz_au/archive/" + str(datetime.now().strftime("%Y_%m_%d")) + "/"
        
        if not os.path.exists(local_filepath):
            os.makedirs(local_filepath)
        #end check if xmls folder exists

        #start loop through data fetched from dme_bookings table         
        i = 1
        for booking in bookings:
            try:
                #start db query for fetching data from dme_booking_lines table
                booking_lines = get_available_booking_lines(mysqlcon, booking)
                #end db query for fetching data from dme_booking_lines table

                #start calculate total item quantity and total item weight
                totalQty = 0
                totalWght = 0
                for booking_line in booking_lines:
                    totalQty = totalQty + booking_line['e_qty']
                    totalWght = totalWght + booking_line['e_Total_KG_weight']
                #start calculate total item quantity and total item weight

                #start xml file name using naming convention
                date = datetime.now().strftime("%Y%m%d")+"_"+datetime.now().strftime("%H%M%S")
                filename = "TAZ_FP_"+date+"_"+str(i)+".xml"
                
                #end xml file name using naming convention

                #start formatting xml file and putting data from db tables
                root = xml.Element("fd:Manifest", **{'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'xmlns:fd': "http://www.ezysend.com/FreightDescription/2.0", 'Version': "2.0", 'Action': "Submit", 'Number': "M"+ ACCOUNT_CODE + str(i).zfill(4), 'Type': "Outbound", 'xsi:schemaLocation': "http://www.ezysend.com/FreightDescription/2.0 http://www.ezysend.com/EDI/FreightDescription/2.0/schema.xsd"})

                #IndependentContainers = xml.Element("fd:IndependentContainers")
                #root.append(IndependentContainers)
                #xml.SubElement(IndependentContainers, "fd:Container", **{'Identifier': "IC"+ ACCOUNT_CODE +"00001", 'Volume': "1.02", 'Weight': "200", 'Commodity': "Pallet"})                
                cannote_number = ACCOUNT_CODE +str(i).zfill(5)

                #consignment = xml.Element("fd:Consignment", **{'Number': "DME"+str(booking['b_bookingID_Visual'])})
                consignment = xml.Element("fd:Consignment", **{'Number': cannote_number })
                root.append(consignment)

                Carrier = xml.SubElement(consignment, "fd:Carrier")
                Carrier.text = booking['vx_serviceName']
                AccountCode = xml.SubElement(consignment, "fd:AccountCode")
                AccountCode.text = ACCOUNT_CODE

                senderName = xml.SubElement(consignment, "fd:Sender", **{'Name': ACCOUNT_CODE})
                senderAddress = xml.SubElement(senderName, "fd:Address")
                senderAddressLine1 = xml.SubElement(senderAddress, "fd:Address1")
                senderAddressLine1.text = booking['pu_Address_Street_1']
                senderLocality = xml.SubElement(senderAddress, "fd:Locality")
                senderLocality.text = booking['pu_Address_Suburb']
                senderState = xml.SubElement(senderAddress, "fd:Territory")
                senderState.text = booking['pu_Address_State']
                senderPostcode = xml.SubElement(senderAddress, "fd:PostCode")
                senderPostcode.text = booking['pu_Address_PostalCode']
                senderCountry = xml.SubElement(senderAddress, "fd:Country")
                senderCountry.text = booking['pu_Address_Country']

                companyName = booking['deToCompanyName'].replace("<", "")
                companyName = companyName.replace(">", "")
                companyName = companyName.replace("\"", "")
                companyName = companyName.replace("'", "")
                companyName = companyName.replace("&", "and")

                ReceiverName = xml.SubElement(consignment, "fd:Receiver", **{'Name': companyName, 'Reference': 'CUST0001'})
                ReceiverAddress = xml.SubElement(ReceiverName, "fd:Address")
                ReceiverAddressLine1 = xml.SubElement(ReceiverAddress, "fd:Address1")
                ReceiverAddressLine1.text = booking['de_To_Address_Street_1']
                ReceiverLocality = xml.SubElement(ReceiverAddress, "fd:Locality")
                ReceiverLocality.text = booking['de_To_Address_Suburb']
                ReceiverState = xml.SubElement(ReceiverAddress, "fd:Territory")
                ReceiverState.text = booking['de_To_Address_State']
                ReceiverPostcode = xml.SubElement(ReceiverAddress, "fd:PostCode")
                ReceiverPostcode.text = booking['de_To_Address_PostalCode']
                ReceiverCountry = xml.SubElement(ReceiverAddress, "fd:Country")
                ReceiverCountry.text = booking['de_To_Address_Country']

                ContactName = xml.SubElement(ReceiverName, "fd:ContactName")
                ContactName.text = (str(booking['de_to_Contact_FName']) if booking['de_to_Contact_FName'] else '') + (' ' + str(booking['de_to_Contact_Lname']) if booking['de_to_Contact_Lname'] else '')
                PhoneNumber = xml.SubElement(ReceiverName, "fd:PhoneNumber")
                PhoneNumber.text = (str(booking['de_to_Phone_Main']) if booking['de_to_Phone_Main'] else '')

                FreightForwarderName = xml.SubElement(consignment, "fd:FreightForwarder", **{'Name': companyName})
                FreightForwarderAddress = xml.SubElement(FreightForwarderName, "fd:Address")
                FreightForwarderAddressLine1 = xml.SubElement(FreightForwarderAddress, "fd:Address1")
                FreightForwarderAddressLine1.text = booking['de_To_Address_Street_1']
                FreightForwarderLocality = xml.SubElement(FreightForwarderAddress, "fd:Locality")
                FreightForwarderLocality.text = booking['de_To_Address_Suburb']
                FreightForwarderState = xml.SubElement(FreightForwarderAddress, "fd:Territory")
                FreightForwarderState.text = booking['de_To_Address_State']
                FreightForwarderPostcode = xml.SubElement(FreightForwarderAddress, "fd:PostCode")
                FreightForwarderPostcode.text = booking['de_To_Address_PostalCode']
                FreightForwarderCountry = xml.SubElement(FreightForwarderAddress, "fd:Country")
                FreightForwarderCountry.text = booking['de_To_Address_Country']

                Fragile = xml.SubElement(consignment, "fd:Fragile")
                Fragile.text = 'true'

                ServiceType = xml.SubElement(consignment, "fd:ServiceType")
                ServiceType.text = booking['vx_serviceName']

                DeliveryWindow = xml.SubElement(consignment, "fd:DeliveryWindow", **{'From': booking['puPickUpAvailFrom_Date'].strftime("%Y-%m-%dT%H:%M:%S") if booking['puPickUpAvailFrom_Date'] else '0000-00-00T00:00:00', 'To': booking['pu_PickUp_By_Date'].strftime("%Y-%m-%dT%H:%M:%S") if booking['pu_PickUp_By_Date'] else '0000-00-00T00:00:00'})

                DeliveryInstructions = xml.SubElement(consignment, "fd:DeliveryInstructions")
                DeliveryInstructions.text = str(booking['de_to_PickUp_Instructions_Address']) + ' ' + str(booking['de_to_Pick_Up_Instructions_Contact'])

                #BulkPricing = xml.SubElement(consignment, "fd:BulkPricing")
                #xml.SubElement(BulkPricing, "fd:Container", **{ 'Weight': "500", 'Identifier': "C"+ ACCOUNT_CODE +"00003", 'Volume': "0.001", 'Commodity': "PALLET" }) 
                
                for booking_line in booking_lines:
                    FreightDetails = xml.SubElement(consignment, "fd:FreightDetails", **{ 'Reference': str(booking_line['client_item_reference']) if booking_line['client_item_reference'] else '', 'Quantity': str(booking_line['e_qty']), 'Commodity': (item_type(booking_line['e_item_type']) if booking_line['e_item_type'] else ''), 'CustomDescription': str(booking_line['e_item']) if booking_line['e_item'] else '' })
                    if booking_line['e_dangerousGoods']:
                        DangerousGoods = xml.SubElement(FreightDetails, "fd:DangerousGoods",  **{ 'Class': "1", 'UNNumber': "1003" })
                    
                    ItemDimensions = xml.SubElement(FreightDetails, "fd:ItemDimensions",  **{ 'Length': str(booking_line['e_dimLength']), 'Width': str(booking_line['e_dimWidth']), 'Height': str(booking_line['e_dimHeight']) })

                    ItemWeight = xml.SubElement(FreightDetails, "fd:ItemWeight")
                    ItemWeight.text = (str(booking_line['e_Total_KG_weight']/booking_line['e_qty']) if booking_line['e_qty'] > 0 else 0)

                    ItemVolume = xml.SubElement(FreightDetails, "fd:ItemVolume")
                    ItemVolume.text = (str(booking_line['e_1_Total_dimCubicMeter']))

                    Items = xml.SubElement(FreightDetails, "fd:Items")
                    for j in range(1, booking_line['e_qty']+1):
                        Item = xml.SubElement(Items, "fd:Item", **{ ' Container': "IC" + ACCOUNT_CODE + str(i).zfill(5) })
                        Item.text = "S" + cannote_number + str(j).zfill(3)

                i+= 1
                #end formatting xml file and putting data from db tables

                #start writting data into xml files
                tree = xml.ElementTree(root)
                
                with open(local_filepath + filename, "wb") as fh:
                    tree.write(fh, encoding='UTF-8', xml_declaration=True)
                    
                #start update booking status in dme_booking table
                sql2 = "UPDATE dme_bookings set b_status = %s, b_dateBookedDate = %s WHERE pk_booking_id = %s"
                adr2 = ('Booked XML', str(datetime.utcnow()), booking['pk_booking_id'])
                mycursor.execute(sql2, adr2)
                mysqlcon.commit()
            except Exception as e:
                # print('@300 TAZ XML - ', e)
                return e

        #end loop through data fetched from dme_bookings table 

        
    mysqlcon.close()

def build_xls(bookings, xls_type, username, start_date, end_date, show_field_name):
    if settings.ENV == 'local':
        production = False # Local
    else:
        production = True  # Dev

    #start check if xmls folder exists
    if production:
        local_filepath = "/var/www/html/dme_api/static/xlss/"
    else:
        local_filepath = "/Users/admin/work/goldmine/dme_api/static/xlss/"
    
    if not os.path.exists(local_filepath):
        os.makedirs(local_filepath)
    #end check if xmls folder exists

    filename = username + '_' + xls_type + '_' + str(len(bookings)) + '_' + str(start_date.strftime("%d-%m-%Y")) + '_' + str(end_date.strftime("%d-%m-%Y")) + '_' + str(datetime.now().strftime("%d-%m-%Y %H_%M_%S")) + ".xlsx"
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()
    worksheet.set_column(0, 21, width=25)
    bold = workbook.add_format({'bold': 1, 'align': 'left'})
    col = 0

    if xls_type == 'Bookings':
        if show_field_name:
            worksheet.write('A1', 'b_dateBookedDate(Date)', bold)
            worksheet.write('B1', 'b_dateBookedDate(Time)', bold)
            worksheet.write('C1', 'pu_Address_State', bold)
            worksheet.write('D1', 'business_group', bold)
            worksheet.write('E1', 'deToCompanyName', bold)
            worksheet.write('F1', 'de_To_Address_Suburb', bold)
            worksheet.write('G1', 'de_To_Address_State', bold)
            worksheet.write('H1', 'de_To_Address_PostalCode', bold)
            worksheet.write('I1', 'b_client_sales_inv_num', bold)
            worksheet.write('J1', 'b_client_order_num', bold)
            worksheet.write('K1', 'v_FPBookingNumber', bold)
            worksheet.write('L1', 'b_status', bold)
            worksheet.write('M1', 'dme_status_detail', bold)
            worksheet.write('N1', 'dme_status_action', bold)
            worksheet.write('O1', 's_21_ActualDeliveryTimeStamp', bold)
            worksheet.write('P1', 'zc_pod_or_no_pod', bold)
            worksheet.write('Q1', 'z_pod_url', bold)
            worksheet.write('R1', 'z_pod_signed_url', bold)
            worksheet.write('S1', 'delivery_kpi_days', bold)
            worksheet.write('T1', 'delivery_days_from_booked', bold)
            worksheet.write('U1', 'delivery_actual_kpi_days', bold)
            worksheet.write('V1', 'de_Deliver_By_Date(Date)', bold)
            worksheet.write('W1', 'de_Deliver_By_Date(Time)', bold)

            worksheet.write('A2', 'Booked Date', bold)
            worksheet.write('B2', 'Booked Time', bold)
            worksheet.write('C2', 'From State', bold)
            worksheet.write('D2', 'To Entity Group Name', bold)
            worksheet.write('E2', 'To Entity', bold)
            worksheet.write('F2', 'To Suburb', bold)
            worksheet.write('G2', 'To State', bold)
            worksheet.write('H2', 'To Postal Code', bold)
            worksheet.write('I2', 'Client Sales Invoice', bold)
            worksheet.write('J2', 'Client Order Number', bold)
            worksheet.write('K2', 'Consignment No', bold)
            worksheet.write('L2', 'Status', bold)
            worksheet.write('M2', 'Status Detail', bold)
            worksheet.write('N2', 'Status Action', bold)
            worksheet.write('O2', 'Actual Delivery', bold)
            worksheet.write('P2', 'POD?', bold)
            worksheet.write('Q2', 'POD LINK', bold)
            worksheet.write('R2', 'POD Signed on Glass Link', bold)
            worksheet.write('S2', 'Target Delivery KPI (Days)', bold)
            worksheet.write('T2', 'Delivery Days from Booked', bold)
            worksheet.write('U2', 'Actual Delivery KPI (Days)', bold)
            worksheet.write('V2', 'Store Booking Date', bold)
            worksheet.write('W2', 'Store Booking Time', bold)
            row = 2
        else:
            worksheet.write('A1', 'Booked Date', bold)
            worksheet.write('B1', 'Booked Time', bold)
            worksheet.write('C1', 'From State', bold)
            worksheet.write('D1', 'To Entity Group Name', bold)
            worksheet.write('E1', 'To Entity', bold)
            worksheet.write('F1', 'To Suburb', bold)
            worksheet.write('G1', 'To State', bold)
            worksheet.write('H1', 'To Postal Code', bold)
            worksheet.write('I1', 'Client Sales Invoice', bold)
            worksheet.write('J1', 'Client Order Number', bold)
            worksheet.write('K1', 'Consignment No', bold)
            worksheet.write('L1', 'Status', bold)
            worksheet.write('M1', 'Status Detail', bold)
            worksheet.write('N1', 'Status Action', bold)
            worksheet.write('O1', 'Actual Delivery', bold)
            worksheet.write('P1', 'POD?', bold)
            worksheet.write('Q1', 'POD LINK', bold)
            worksheet.write('R1', 'POD Signed on Glass Link', bold)
            worksheet.write('S1', 'Target Delivery KPI (Days)', bold)
            worksheet.write('T1', 'Delivery Days from Booked', bold)
            worksheet.write('U1', 'Actual Delivery KPI (Days)', bold)
            worksheet.write('V1', 'Store Booking Date', bold)
            worksheet.write('W1', 'Store Booking Time', bold)
            row = 1

        for booking in bookings:
            if booking.b_dateBookedDate and booking.b_dateBookedDate:
                worksheet.write(row, col + 0, booking.b_dateBookedDate.strftime("%d-%m-%Y"))
                worksheet.write(row, col + 1, booking.b_dateBookedDate.strftime("%H:%M:%S"))
            else:
                worksheet.write(row, col + 0, "")
                worksheet.write(row, col + 1, "")

            worksheet.write(row, col + 2, booking.pu_Address_State)

            customer_group_name = ''
            customer_groups = Dme_utl_client_customer_group.objects.all()
            for customer_group in customer_groups:
              if customer_group.name_lookup.lower() in booking.deToCompanyName.lower():
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
            worksheet.write(row, col + 12, booking.dme_status_detail)
            worksheet.write(row, col + 13, booking.dme_status_action)

            if booking.s_21_ActualDeliveryTimeStamp and booking.s_21_ActualDeliveryTimeStamp:
                worksheet.write(row, col + 14, booking.s_21_ActualDeliveryTimeStamp.strftime("%d-%m-%Y"))
            else:
                worksheet.write(row, col + 14, "")

            if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
              worksheet.write(row, col + 15, "Y")
            else:
              worksheet.write(row, col + 15, "")

            if settings.ENV == 'dev':
              if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0):
                worksheet.write_url(row, col + 16, 'http://3.105.62.128/static/imgs/' + booking.z_pod_url, string=booking.z_pod_url)

              if (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
                worksheet.write_url(row, col + 17, 'http://3.105.62.128/static/imgs/' + booking.z_pod_signed_url, string=booking.z_pod_signed_url)
            elif settings.ENV == 'prod':
              if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0):
                worksheet.write_url(row, col + 16, 'http://13.55.64.102/static/imgs/' + booking.z_pod_url, string=booking.z_pod_url)

              if (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
                worksheet.write_url(row, col + 17, 'http://13.55.64.102/static/imgs/' + booking.z_pod_signed_url, string=booking.z_pod_signed_url)

            worksheet.write(row, col + 18, booking.delivery_kpi_days)
            worksheet.write(row, col + 19, booking.delivery_days_from_booked)
            worksheet.write(row, col + 20, booking.delivery_actual_kpi_days)

            if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                worksheet.write(row, col + 21, booking.de_Deliver_By_Date.strftime("%d-%m-%Y"))
                worksheet.write(row, col + 22, booking.de_Deliver_By_Date.strftime("%H:%M:%S"))
            else:
                worksheet.write(row, col + 21, "")
                worksheet.write(row, col + 22, "")

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
    elif xls_type == 'BookingLines':
        if show_field_name:
            worksheet.write('A1', 'dme_bookings:v_FPBookingNumber', bold)
            worksheet.write('B1', 'dme_bookings:b_dateBookedDate(Date)', bold)
            worksheet.write('C1', 'dme_bookings:b_dateBookedDate(Time)', bold)
            worksheet.write('D1', 'api_booking_confirmation_lines:fp_event_date and fp_event_time', bold)
            worksheet.write('E1', 'dme_bookings:vx_freight_provider', bold)
            worksheet.write('F1', 'dme_bookings:puCompany', bold)
            worksheet.write('G1', 'dme_bookings:pu_Address_Suburb', bold)
            worksheet.write('H1', 'dme_bookings:deToCompanyName', bold)
            worksheet.write('I1', 'dme_bookings:de_To_Address_Suburb', bold)
            worksheet.write('J1', 'dme_bookings:de_To_Address_State', bold)
            worksheet.write('K1', 'dme_bookings:de_To_Address_PostalCode', bold)
            worksheet.write('L1', 'dme_bookings:b_client_order_num', bold)
            worksheet.write('M1', 'dme_bookings:b_client_sales_inv_num', bold)
            worksheet.write('N1', 'client_item_reference', bold)
            worksheet.write('O1', 'e_pallety_type', bold)
            worksheet.write('P1', 'e_item', bold)
            worksheet.write('Q1', 'e_item_qty', bold)
            worksheet.write('R1', 'Booking Ref ?? GAP', bold)
            worksheet.write('S1', 'DD Received Date(Date)', bold)
            worksheet.write('T1', 'DD Received Date(Time)', bold)
            worksheet.write('U1', 'Dispatch Date', bold)
            worksheet.write('V1', 'ETA Into Store', bold)
            worksheet.write('W1', 'b_status', bold)
            worksheet.write('X1', 'dme_bookings: dme_status_detail', bold)
            worksheet.write('Y1', 'dme_bookings: dme_status_action', bold)
            worksheet.write('Z1', 'POD Available', bold)
            worksheet.write('AA1', 'e_qty_awaiting_inventory', bold)
            worksheet.write('AB1', 'e_qty_collected', bold)
            worksheet.write('AC1', 'e_qty_scanned_fp', bold)
            worksheet.write('AD1', 'e_qty_scanned_depot', bold)
            worksheet.write('AE1', 'e_qty_delivered', bold)
            worksheet.write('AF1', 'e_qty_damaged', bold)
            worksheet.write('AG1', 'e_qty_returned', bold)
            worksheet.write('AH1', 'e_qty_shortages', bold)
            worksheet.write('AI1', 'e_qty_adjusted_delivered', bold)

            worksheet.write('A2', 'Consignment No', bold)
            worksheet.write('B2', 'Booked Date', bold)
            worksheet.write('C2', 'Booked Time', bold)
            worksheet.write('D2', 'Date Scanned', bold)
            worksheet.write('E2', 'Freight Provider', bold)
            worksheet.write('F2', 'Pickup Entity', bold)
            worksheet.write('G2', 'Pickup Suburb', bold)
            worksheet.write('H2', 'To Entity', bold)
            worksheet.write('I2', 'To Suburb', bold)
            worksheet.write('J2', 'To State', bold)
            worksheet.write('K2', 'To Postal Code', bold)
            worksheet.write('L2', 'Customer Client Order No', bold)
            worksheet.write('M2', 'Customer Invoice No', bold)
            worksheet.write('N2', 'Client Reference No', bold)
            worksheet.write('O2', 'Model', bold)
            worksheet.write('P2', 'Product Description', bold)
            worksheet.write('Q2', 'Booked Qty', bold)
            worksheet.write('R2', 'Booking Ref', bold)
            worksheet.write('S2', 'DD Received Date', bold)
            worksheet.write('T2', 'DD Received Time', bold)
            worksheet.write('U2', 'Dispatch Date', bold)
            worksheet.write('V2', 'ETA Into Store', bold)
            worksheet.write('W2', 'Status', bold)
            worksheet.write('X2', 'Status Detail', bold)
            worksheet.write('Y2', 'Status Action', bold)
            worksheet.write('Z2', 'POD?', bold)
            worksheet.write('AA2', 'Inventory on Back Order', bold)
            worksheet.write('AB2', 'Qty Confimred Collected by Pickup Entity', bold)
            worksheet.write('AC2', 'Qty Scanned at Transporter Depot', bold)
            worksheet.write('AD2', 'Same as Col T?', bold)
            worksheet.write('AE2', 'Qty Delivered', bold)
            worksheet.write('AF2', 'Qty Damaged', bold)
            worksheet.write('AG2', 'Qty Returned', bold)
            worksheet.write('AH2', 'Qty Short', bold)
            worksheet.write('AI2', 'Adjusted Delivered Qty', bold)
            row = 2
        else:
            worksheet.write('A2', 'Consignment No', bold)
            worksheet.write('B2', 'Booked Date', bold)
            worksheet.write('C2', 'Booked Time', bold)
            worksheet.write('D2', 'Date Scanned', bold)
            worksheet.write('E2', 'Freight Provider', bold)
            worksheet.write('F2', 'Pickup Entity', bold)
            worksheet.write('G2', 'Pickup Suburb', bold)
            worksheet.write('H2', 'To Entity', bold)
            worksheet.write('I2', 'To Suburb', bold)
            worksheet.write('J2', 'To State', bold)
            worksheet.write('K2', 'To Postal Code', bold)
            worksheet.write('L2', 'Customer Client Order No', bold)
            worksheet.write('M2', 'Customer Invoice No', bold)
            worksheet.write('N2', 'Client Reference No', bold)
            worksheet.write('O2', 'Model', bold)
            worksheet.write('P2', 'Product Description', bold)
            worksheet.write('Q2', 'Booked Qty', bold)
            worksheet.write('R2', 'Booking Ref', bold)
            worksheet.write('S2', 'DD Received Date', bold)
            worksheet.write('T2', 'DD Received Time', bold)
            worksheet.write('U2', 'Dispatch Date', bold)
            worksheet.write('V2', 'ETA Into Store', bold)
            worksheet.write('W2', 'Status', bold)
            worksheet.write('X2', 'Status Detail', bold)
            worksheet.write('Y2', 'Status Action', bold)
            worksheet.write('Z2', 'POD?', bold)
            worksheet.write('AA2', 'Inventory on Back Order', bold)
            worksheet.write('AB2', 'Qty Confimred Collected by Pickup Entity', bold)
            worksheet.write('AC2', 'Qty Scanned at Transporter Depot', bold)
            worksheet.write('AD2', 'Same as Col T?', bold)
            worksheet.write('AE2', 'Qty Delivered', bold)
            worksheet.write('AF2', 'Qty Damaged', bold)
            worksheet.write('AG2', 'Qty Returned', bold)
            worksheet.write('AH2', 'Qty Short', bold)
            worksheet.write('AI2', 'Adjusted Delivered Qty', bold)
            row = 1

        for booking in bookings:
            try:
                booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

                for booking_line in booking_lines:
                    worksheet.write(row, col + 0, booking.v_FPBookingNumber)

                    if booking.b_dateBookedDate and booking.b_dateBookedDate:
                        worksheet.write(row, col + 1, booking.b_dateBookedDate.strftime("%d-%m-%Y"))
                        worksheet.write(row, col + 2, booking.b_dateBookedDate.strftime("%H:%M:%S"))
                    else:
                        worksheet.write(row, col + 1, "")
                        worksheet.write(row, col + 2, "")

                    api_bcl = Api_booking_confirmation_lines.objects.filter(fk_booking_line_id=booking_line.pk_lines_id).first()
                    if api_bcl and api_bcl.fp_event_date and api_bcl.fp_event_time:
                        worksheet.write(row, col + 3, api_bcl.fp_event_date.strftime("%d-%m-%Y") + ' ' + api_bcl.fp_event_time.strftime("%H:%M:%S"))
                    else:
                        worksheet.write(row, col + 3, "")

                    worksheet.write(row, col + 4, booking.vx_freight_provider)
                    worksheet.write(row, col + 5, booking.puCompany)
                    worksheet.write(row, col + 6, booking.pu_Address_Suburb)
                    worksheet.write(row, col + 7, booking.deToCompanyName)
                    worksheet.write(row, col + 8, booking.de_To_Address_Suburb)
                    worksheet.write(row, col + 9, booking.de_To_Address_State)
                    worksheet.write(row, col + 10, booking.de_To_Address_PostalCode)
                    worksheet.write(row, col + 11, booking.b_client_order_num)
                    worksheet.write(row, col + 12, booking.b_client_sales_inv_num)
                    worksheet.write(row, col + 13, booking_line.client_item_reference)
                    worksheet.write(row, col + 14, booking_line.e_pallet_type)
                    worksheet.write(row, col + 15, booking_line.e_item)
                    worksheet.write(row, col + 16, booking_line.e_qty)
                    worksheet.write(row, col + 17, booking.b_bookingID_Visual)

                    if api_bcl and api_bcl.fp_event_date and api_bcl.fp_event_time:
                        worksheet.write(row, col + 18, api_bcl.fp_event_date.strftime("%d-%m-%Y"))
                        worksheet.write(row, col + 19, api_bcl.fp_event_time.strftime("%H:%M:%S"))
                    else:
                        worksheet.write(row, col + 18, "")
                        worksheet.write(row, col + 19, "")

                    if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                        worksheet.write(row, col + 20, booking.de_Deliver_By_Date.strftime("%d-%m-%Y"))
                    else:
                        worksheet.write(row, col + 20, "")


                    if booking.de_Deliver_By_Date and booking.de_Deliver_By_Date:
                        delivery_kpi_days = 0

                        if booking.delivery_kpi_days:
                            delivery_kpi_days = booking.delivery_kpi_days

                        worksheet.write(row, col + 21, (booking.de_Deliver_By_Date+timedelta(days=int(delivery_kpi_days))).strftime("%d-%m-%Y"))
                    else:
                        worksheet.write(row, col + 21, "")

                    worksheet.write(row, col + 22, booking.b_status)
                    worksheet.write(row, col + 23, booking.dme_status_detail)
                    worksheet.write(row, col + 24, booking.dme_status_action)

                    if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
                      worksheet.write(row, col + 25, "Y")
                    else:
                      worksheet.write(row, col + 25, "")

                    worksheet.write(row, col + 26, booking_line.e_qty_awaiting_inventory)
                    worksheet.write(row, col + 27, booking_line.e_qty_collected)
                    worksheet.write(row, col + 28, booking_line.e_qty_scanned_fp)
                    worksheet.write(row, col + 29, booking_line.e_qty_scanned_depot)
                    worksheet.write(row, col + 30, booking_line.e_qty_delivered)
                    worksheet.write(row, col + 31, booking_line.e_qty_damaged)
                    worksheet.write(row, col + 32, booking_line.e_qty_returned)
                    worksheet.write(row, col + 33, booking_line.e_qty_shortages)
                    worksheet.write(row, col + 34, booking_line.e_qty_adjusted_delivered)

                    row += 1
            except Booking_lines.DoesNotExist:
                continue

        workbook.close()
        shutil.move(filename, local_filepath + filename)
    elif xls_type == 'old':
        print('Commented code')
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

def build_xls_and_send(bookings, email_addr, report_type, username, start_date, end_date, show_field_name):
    if report_type == 'booking':
        filepath = build_xls(bookings, 'Bookings', username, start_date, end_date, show_field_name)
        send_email(
            [email_addr], # Recipient email address(list)
            'XLS Report from Deliver-Me', # Subject of email
            'Here is the excel report(Bookings) you generated from Deliver-Me.', # Message of email
            [filepath] # Attachment file path(list)
        )
    elif report_type == 'booking_line':
        filepath = build_xls(bookings, 'BookingLines', username, start_date, end_date, show_field_name)
        send_email(
            [email_addr], # Recipient email address(list)
            'XLS Report from Deliver-Me', # Subject of email
            'Here is the excel report(Booking Lines) you generated from Deliver-Me.', # Message of email
            [filepath] # Attachment file path(list)
        )
    elif report_type == 'both':
        filepath_booking = build_xls(bookings, 'Bookings', username, start_date, end_date, show_field_name)
        filepath_booking_line = build_xls(bookings, 'BookingLines', username, start_date, end_date, show_field_name)
        send_email(
            [email_addr], # Recipient email address(list)
            'XLS Report from Deliver-Me', # Subject of email
            'Here is the excel report(Bookings & Booking Lines) you generated from Deliver-Me.', # Message of email
            [filepath_booking, filepath_booking_line] # Attachment file path(list)
        )
