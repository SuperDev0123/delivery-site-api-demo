from tkinter import CENTER
from unittest import result
import mysql.connector
import xlsxwriter as xlsxwriter
from api.outputs.email import send_email

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="dme_db_prod"
)
cursor = mydb.cursor(dictionary=True)
sqlQuery = '''SELECT 
                puPickUpAvailFrom_Date, puCompany, pu_Address_Street_1, pu_Address_Suburb, pu_Address_PostalCode,
                pu_Address_State, pu_Phone_Main , pu_Contact_F_L_Name , v_FPBookingNumber, deToCompanyName, de_to_Contact_F_Lname,
                de_To_Address_Street_1 , de_To_Address_Suburb , de_To_Address_State, de_To_Address_PostalCode, de_to_Phone_Mobile,
                de_Email, e_item, e_qty, e_weightUOM, total_Cubic_Meter_override, de_to_pick_up_instructions_contact, b_092_booking_type, b_010_b_notes
                FROM
                dme_bookings LEFT JOIN dme_booking_lines ON dme_bookings.pk_booking_id = dme_booking_lines.fk_booking_id
                LEFT JOIN bok_1_headers ON dme_bookings.pk_booking_id = bok_1_headers.pk_header_id
                LIMIT 4'''

cursor.execute(sqlQuery)
result = cursor.fetchone()

def fetch_bookings(booking_ids):
    return

def export_wefleet(result):

    workbook = xlsxwriter.Workbook("1.xlsx", {"remove_timezone": True})
    worksheet = workbook.add_worksheet()
    worksheet.set_column(1, 20, width=20)
    worksheet.set_default_row(20)
    worksheet.hide_gridlines(option=2)

    dme_info = ["Company Name: ", "Address", "Suburb", "Postcode", "State"]

    # worksheet.merge_range(2, 2, 2, 3)
    dme_info_format = workbook.add_format()
    dme_info_format.set_align(CENTER)
    dme_info_format.set_bg_color('#b9d7ea')
    dme_info_format.set_border(1)

    worksheet.write(1, 1, "Pickup Date:", dme_info_format)
    worksheet.write_column(3, 1, dme_info, dme_info_format)
    worksheet.write(9, 1, "Contact Phone No.", dme_info_format)
    worksheet.write(11, 1, "Contact Name", dme_info_format)

    dme_date_fmt = workbook.add_format()
    dme_date_fmt.set_num_format("mmm d yyyy")
    dme_date_fmt.set_border(1)
    dme_date_fmt.set_align(CENTER)

    dme_value_fmt = workbook.add_format()
    dme_value_fmt.set_border(1)
    dme_value_fmt.set_align(CENTER)

    worksheet.merge_range(1, 2, 1, 3, result["puPickUpAvailFrom_Date"], dme_date_fmt)
    worksheet.merge_range(3, 2, 3, 3, result["puCompany"], dme_value_fmt)
    worksheet.merge_range(4, 2, 4, 3, result["pu_Address_Street_1"], dme_value_fmt)
    worksheet.merge_range(5, 2, 5, 3, result["pu_Address_Suburb"], dme_value_fmt)

    worksheet.write(6, 2, result["pu_Address_PostalCode"], dme_value_fmt)
    worksheet.write(7, 2, result["pu_Address_State"], dme_value_fmt)

    worksheet.merge_range(9, 2, 9, 3, result["pu_Phone_Main"], dme_value_fmt)
    worksheet.merge_range(11, 2, 11, 3, result["pu_Contact_F_L_Name"], dme_value_fmt)

    fp_info = ["Consignment Reference","Company Name", "Delivery Name", "Street Address", "Suburb", 
                "State", "Postcode", "Delivery Mobile Phone", "Delivery Email", "Item", "QTY", 
                "Weight (Kg)", "Cubic", "Special Instructions", "Consignment Type", "Notes"]

    fp_info_format = workbook.add_format()
    fp_info_format.set_align(CENTER)
    fp_info_format.set_bg_color('#b9d7ea')
    fp_info_format.set_border(1)

    worksheet.write_row(15, 1, fp_info, fp_info_format)

    results = cursor.fetchall()
    for index, res in enumerate(results):
        fp_value = list(res.values())[8:]
        worksheet.write_row(16 + index, 1, fp_value, dme_value_fmt)

    dme_title_fmt = workbook.add_format()
    dme_title_fmt.set_font_size(20)
    dme_title_fmt.set_align(CENTER)
    dme_title_fmt.set_bold()

    dme_sub_fmt = workbook.add_format()
    dme_sub_fmt.set_align(CENTER)

    worksheet.merge_range(1, 4, 1, 11, "WEFLEET BOOKING FORM", dme_title_fmt)
    worksheet.merge_range(3, 4, 3, 11, "Email file to: bookings+WeFleet@in.cartoncloud.com.au", dme_sub_fmt)
    worksheet.merge_range(5, 4, 5, 11, "Please be aware that this form is used to import data directly into the system, be sure that information provided is accurate.", dme_sub_fmt)

    worksheet.insert_image(8, 7, 'logo.png')
    # worksheet.merge_range(5, 4, 5, 11, "Please be aware that this form is used to import data directly into the system, be sure that information provided is accurate.", dme_value_fmt)

    workbook.close()
    return

def send_email_wefleet():
    # filepath = build_xls(
    #     bookings,
    #     "picked_up_bookings",
    #     username,
    #     start_date,
    #     end_date,
    #     show_field_name,
    # )
    
    send_email(
        [],
        [],
        "This is wefleet booking",  # Subject of email
        "Here is the excel report you generated from Deliver-Me.",  # Message of email
        [filepath],  # Attachment file path(list)
    )
    return