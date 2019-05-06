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
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

from django.core.mail import send_mail
from django.conf import settings

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

def wrap_in_quote(string):
    return '"' + string + '"'

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

    csv_name = 'SEATEMP_' + str(len(booking_ids)) + "_" + str(datetime.datetime.utcnow()) + ".csv"
    
    if production:
        f = open("/home/cope_au/dme_sftp/cope_au/pickup_ext/" + csv_name, "w")
    else:
        f = open("/Users/admin/Documents/" + csv_name, "w")

    csv_write(f, bookings, mysqlcon)
    f.close()

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

def build_xml(booking_ids):
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

    # sql = "SELECT pk_booking_id, pu_Address_Street_1, pu_Address_Suburb, pu_Address_State, \
    #             pu_Address_PostalCode, v_FPBookingNumber, puPickUpAvailFrom_Date, vx_serviceName, \
    #             total_1_KG_weight_override, deToCompanyName, de_To_Address_Street_1, de_To_Address_Suburb,\
    #             de_To_Address_State, de_To_Address_PostalCode \
    #             FROM dme_bookings \
    #             WHERE b_client_name = %s AND b_status='Ready for XML' \
    #             GROUP BY dme_bookings.pk_booking_id"
    adr = ("Seaway", )
    
    #start check if xmls folder exists
    if production:
        local_filepath = "/var/www/html/dme_api/static/xmls/"
        local_filepath_dup = "/var/www/html/dme_api/static/xmls/archive/" + str(datetime.datetime.now().strftime("%Y_%m_%d")) + "/"
    else:
        local_filepath = "/Users/admin/work/goldmine/dme_api/static/xmls/"
        local_filepath_dup = "/Users/admin/work/goldmine/dme_api/static/xmls/archive/" + str(datetime.datetime.now().strftime("%Y_%m_%d")) + "/"
    
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
            date = datetime.datetime.now().strftime("%Y%m%d")+"_"+datetime.datetime.now().strftime("%H%M%S")
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
            adr2 = ('Booked XML', str(datetime.datetime.utcnow()), booking['pk_booking_id'])
            mycursor.execute(sql2, adr2)
            mysqlcon.commit()
        except Exception as e:
            return e
        
    mysqlcon.close()

def build_xls(bookings):
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

    filename = "bookings_seaway_" + str(datetime.now().strftime("%Y-%m-%d")) + "_" + str(uuid.uuid1()) + ".xlsx"
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()
    worksheet.set_column(0, 12, width=24)
    bold = workbook.add_format({'bold': 1, 'align': 'left'})

    worksheet.write('A1', 'b_bookingID_Visual', bold)
    worksheet.write('B1', 'b_dateBookedDate', bold)
    worksheet.write('C1', 'puPickUpAvailFrom_Date', bold)
    worksheet.write('D1', 'pu_Address_State', bold)
    worksheet.write('E1', 'business_group', bold)
    worksheet.write('F1', 'deToCompanyName', bold)
    worksheet.write('G1', 'de_To_Address_Suburb', bold)
    worksheet.write('H1', 'de_To_Address_State', bold)
    worksheet.write('I1', 'de_To_Address_PostalCode', bold)
    worksheet.write('J1', 'b_client_sales_inv_num', bold)
    worksheet.write('K1', 'b_client_order_num', bold)
    worksheet.write('L1', 'v_FPBookingNumber', bold)
    worksheet.write('M1', 'b_status', bold)
    worksheet.write('N1', 's_21_Actual_Delivery_TimeStamp', bold)
    worksheet.write('O1', 'event_time_stamp', bold)
    worksheet.write('P1', 'zc_pod_or_no_pod', bold)
    worksheet.write('Q1', 'z_pod_url', bold)
    worksheet.write('R1', 'z_pod_signed_url', bold)
    worksheet.write('S1', 'delivery_kpi_days', bold)
    worksheet.write('T1', 'delivery_days_from_booked', bold)
    worksheet.write('U1', 'delivery_actual_kpi_days', bold)

    row = 1
    col = 0

    for booking in bookings:
        worksheet.write(row, col, booking.b_bookingID_Visual)

        if booking.b_dateBookedDate and booking.b_dateBookedDate:
            worksheet.write(row, col + 1, booking.b_dateBookedDate.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            worksheet.write(row, col + 1, "")

        if booking.puPickUpAvailFrom_Date and booking.puPickUpAvailFrom_Date:
            worksheet.write(row, col + 2, booking.puPickUpAvailFrom_Date.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            worksheet.write(row, col + 2, "")

        worksheet.write(row, col + 3, booking.pu_Address_State)

        customer_group_name = ''
        customer_groups = Dme_utl_client_customer_group.objects.all()
        for customer_group in customer_groups:
          if customer_group.name_lookup.lower() in booking.deToCompanyName.lower():
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

        if booking.s_21_ActualDeliveryTimeStamp and booking.s_21_ActualDeliveryTimeStamp:
            worksheet.write(row, col + 13, booking.s_21_ActualDeliveryTimeStamp.strftime("%Y-%m-%d"))
        else:
            worksheet.write(row, col + 13, "")

        if booking.b_status != 'Delivered':
          status_histories = Dme_status_history.objects.filter(fk_booking_id=booking.pk_booking_id).order_by('-id')

          if status_histories and len(status_histories) > 0:
            event_time_stamp = status_histories[0].event_time_stamp
            worksheet.write(row, col + 14, event_time_stamp.strftime("%Y-%m-%d %H:%M:%S"))

        if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
          worksheet.write(row, col + 15, "Y")
        else:
          worksheet.write(row, col + 15, "N")

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

        row += 1

    workbook.close()
    shutil.move(filename, local_filepath + filename)

    return local_filepath + filename
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
