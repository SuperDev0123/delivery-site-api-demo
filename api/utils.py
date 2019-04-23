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

redis_host = "localhost"
redis_port = 6379
redis_password = ""

production = True  # Dev
production = False # Local

if production:
    DB_HOST = 'fm-dev-database.cbx3p5w50u7o.us-west-2.rds.amazonaws.com'
    DB_USER = 'fmadmin'
    DB_PASS = 'Fmadmin1'
    DB_PORT = 3306
    DB_NAME = 'dme_db_dev'  # Dev
    # DB_NAME = 'dme_db_prod'  # Prod
else:
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASS = 'root'
    DB_PORT = 3306
    DB_NAME = 'deliver_me'

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

            # Populate `v_FPBookingNumber`
            sql = "Update `dme_bookings` set v_FPBookingNumber=%s where id=%s"
            cursor.execute(sql, (h0, booking.id))
            mysqlcon.commit()

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
    f = open("/home/cope_au/dme_sftp/cope_au/pickup_ext/" + csv_name, "w")
    csv_write(f, bookings, mysqlcon)
    f.close()

    # print('#901 - Finished %s' % datetime.datetime.now())
    mysqlcon.close()

    return csv_name

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
        filepath = "/var/www/html/dme_api/static/xmls/"
    else:
        filepath = "/Users/admin/work/goldmine/dme_api/static/xmls/"
    
    if not os.path.exists(filepath):
            os.makedirs(filepath)
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
                ItemType.text = str(booking_line['e_item_type'])
                ItemDescription = xml.SubElement(Item, "ItemDescription")
                ItemDescription.text = booking_line['e_item']
                Width = xml.SubElement(Item, "Width")
                Width.text = str(booking_line['e_dimWidth'])
                Length = xml.SubElement(Item, "Length")
                Length.text = str(booking_line['e_dimLength'])
                Height = xml.SubElement(Item, "Height")
                Height.text = str(booking_line['e_dimHeight'])
                DeadWeight = xml.SubElement(Item, "DeadWeight")
                DeadWeight.text = str(booking_line['e_Total_KG_weight']/booking_line['e_qty'])

                SSCCs = xml.SubElement(Item, "SSCCs")
                SSCC = xml.SubElement(SSCCs, "SSCC")
                SSCC.text = booking['pk_booking_id']
            #end formatting xml file and putting data from db tables

            # start writting data into xml files
            tree = xml.ElementTree(root)
            with open(filepath+filename, "wb") as fh:
                tree.write(fh, encoding='UTF-8', xml_declaration=True)

            #     #start copying xml files to sftp server
            #     srv = pysftp.Connection(host="localhost", username="tapas", password="tapas@123", cnopts=cnopts)
            #     #srv = pysftp.Connection(host="edi.alliedexpress.com.au", username="delvme.external", password="987899e64", cnopts=cnopts)
            #     path = 'www'
            #     #path = 'indata'
            #     with srv.cd(path):
            #         srv.put(filepath+filename) 

            #     # Closes the connection
            #     srv.close()
            #     #end copying xml files to sftp server

            #start update booking status in dme_booking table
            sql2 = "UPDATE dme_bookings set b_status = %s, b_dateBookedDate = %s WHERE pk_booking_id = %s"
            adr2 = ('Booked XML', str(datetime.datetime.utcnow()), booking['pk_booking_id'])
            mycursor.execute(sql2, adr2)
            mysqlcon.commit()
        except Exception as e:
            return e
        
    mysqlcon.close()
