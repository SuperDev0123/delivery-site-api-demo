import os
import logging
import shutil
import xlsxwriter as xlsxwriter
from datetime import datetime

from django.conf import settings

from api.models import *

logger = logging.getLogger("dme_api")


def build_xls(bookings, xls_type, username, start_date, end_date, show_field_name):
    if settings.ENV == "local":
        production = False  # Local
    else:
        production = True  # Dev

    # start check if xmls folder exists
    if production:
        local_filepath = "/opt/s3_private/xlss/"
    else:
        local_filepath = "./static/xlss/"

    if not os.path.exists(local_filepath):
        os.makedirs(local_filepath)
    # end check if xmls folder exists

    if start_date and end_date:
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
    else:
        filename = (
            username
            + "__"
            + xls_type
            + "__"
            + str(len(bookings))
            + "__"
            + str(datetime.now().strftime("%d-%m-%Y %H_%M_%S"))
            + ".xlsx"
        )

    date_range = (
        f"{str(start_date.strftime('%d-%m-%Y'))}__{str(end_date.strftime('%d-%m-%Y'))}"
    )
    if xls_type == "booked_bookings":
        filename = f"Shipments Booked ({date_range}).xlsx"
    elif xls_type == "picked_up_bookings":
        filename = f"Shipments PickedUp ({date_range}).xlsx"
    elif xls_type == "box":
        filename = f"Bookings to Send Boxes ({date_range}).xlsx"
    elif xls_type == "futile":
        filename = f"Futile Bookings ({date_range}).xlsx"
    elif xls_type == "goods_delivered":
        filename = f"Bookings Delivered ({date_range}).xlsx"

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
        worksheet.set_column(18, 40, width=25)

        if show_field_name:
            worksheet.write("A1", "b_dateBookedDate(Date)", bold)
            worksheet.write("B1", "b_dateBookedDate(Time)", bold)
            worksheet.write(
                "C1", "fp_received_date_time/b_given_to_transport_date_time", bold
            )
            worksheet.write("D1", "pu_Address_State", bold)
            worksheet.write("E1", "business_group", bold)
            worksheet.write("F1", "deToCompanyName", bold)
            worksheet.write("G1", "de_To_Address_Suburb", bold)
            worksheet.write("H1", "de_To_Address_State", bold)
            worksheet.write("I1", "de_To_Address_PostalCode", bold)
            worksheet.write("J1", "b_client_sales_inv_num", bold)
            worksheet.write("K1", "b_client_order_num", bold)
            worksheet.write("L1", "vx_freight_provider", bold)
            worksheet.write("M1", "v_FPBookingNumber", bold)
            worksheet.write("N1", "b_status", bold)
            worksheet.write("O1", "Total Qty", bold)
            worksheet.write("P1", "Total Scanned Qty", bold)
            worksheet.write("Q1", "Booked to Scanned Variance", bold)
            worksheet.write("R1", "b_fp_qty_delivered", bold)
            worksheet.write("S1", "dme_status_detail", bold)
            worksheet.write("T1", "dme_status_action", bold)
            worksheet.write("U1", "dme_status_history_notes", bold)
            worksheet.write("V1", "s_21_ActualDeliveryTimeStamp", bold)
            worksheet.write("W1", "zc_pod_or_no_pod", bold)
            worksheet.write("X1", "z_pod_url", bold)
            worksheet.write("Y1", "z_pod_signed_url", bold)
            worksheet.write("Z1", "delivery_kpi_days", bold)
            worksheet.write("AA1", "delivery_days_from_booked", bold)
            worksheet.write("AB1", "delivery_actual_kpi_days", bold)
            worksheet.write("AC1", "z_calculated_ETA", bold)
            worksheet.write("AD1", "fp_store_event_date", bold)
            worksheet.write("AE1", "fp_store_event_time", bold)
            worksheet.write("AF2", "fp_store_event_desc", bold)
            worksheet.write("AG1", "inv_billing_status", bold)
            worksheet.write("AH1", "inv_billing_status_note", bold)
            worksheet.write("AI1", "b_booking_project", bold)
            worksheet.write("AJ1", "b_project_due_date", bold)
            worksheet.write("AK1", "delivery_booking", bold)
            # worksheet.write("AI1", '=IF(N1="In Transit",IF(Z1=7,C1+5,C1+12),"")', bold)
            # worksheet.write("AJ1", '=IF(AD1="";AK1-TODAY;"Store Booked")', bold)

            worksheet.write("A2", "Booked Date", bold)
            worksheet.write("B2", "Booked Time", bold)
            worksheet.write("C2", "Given to / Received by Transport", bold)
            worksheet.write("D2", "From State", bold)
            worksheet.write("E2", "To Entity Group Name", bold)
            worksheet.write("F2", "To Entity", bold)
            worksheet.write("G2", "To Suburb", bold)
            worksheet.write("H2", "To State", bold)
            worksheet.write("I2", "To Postal Code", bold)
            worksheet.write("J2", "Client Sales Invoice", bold)
            worksheet.write("K2", "Client Order Number", bold)
            worksheet.write("L2", "Freigth Provider", bold)
            worksheet.write("M2", "Consignment No", bold)
            worksheet.write("N2", "Status", bold)
            worksheet.write("O2", "Total Qty", bold)
            worksheet.write("P2", "Total Scanned Qty", bold)
            worksheet.write("Q2", "Booked to Scanned Variance", bold)
            worksheet.write("R2", "Total Delivered", bold)
            worksheet.write("S2", "Status Detail", bold)
            worksheet.write("T2", "Status Action", bold)
            worksheet.write("U2", "Status History Note", bold)
            worksheet.write("V2", "Actual Delivery", bold)
            worksheet.write("W2", "POD?", bold)
            worksheet.write("X2", "POD LINK", bold)
            worksheet.write("Y2", "POD Signed on Glass Link", bold)
            worksheet.write("Z2", "Target Delivery KPI (Days)", bold)
            worksheet.write("AA2", "Delivery Days from Booked", bold)
            worksheet.write("AB2", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AC2", "Calculated ETA", bold)
            worksheet.write("AD2", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AE2", "1st Contact For Delivery Booking Time", bold)
            worksheet.write("AF2", "FP Store Activity Description", bold)
            worksheet.write("AG2", "Invoice Billing Status", bold)
            worksheet.write("AH2", "Invoice Billing Status Note", bold)
            worksheet.write("AI2", "Project Name", bold)
            worksheet.write("AJ2", "Project Due Date", bold)
            worksheet.write("AK2", "Delivery Booking Date", bold)
            # worksheet.write("AI2", "Delivery Booking Target Date", bold)
            # worksheet.write("AJ2", "Delivery Booking - Days To Target", bold)

            row = 2
        else:
            worksheet.write("A1", "Booked Date", bold)
            worksheet.write("B1", "Booked Time", bold)
            worksheet.write("C1", "Given to / Received by Transport", bold)
            worksheet.write("D1", "From State", bold)
            worksheet.write("E1", "To Entity Group Name", bold)
            worksheet.write("F1", "To Entity", bold)
            worksheet.write("G1", "To Suburb", bold)
            worksheet.write("H1", "To State", bold)
            worksheet.write("I1", "To Postal Code", bold)
            worksheet.write("J1", "Client Sales Invoice", bold)
            worksheet.write("K1", "Client Order Number", bold)
            worksheet.write("L1", "Freigth Provider", bold)
            worksheet.write("M1", "Consignment No", bold)
            worksheet.write("N1", "Status", bold)
            worksheet.write("O1", "Total Qty", bold)
            worksheet.write("P1", "Total Scanned Qty", bold)
            worksheet.write("Q1", "Booked to Scanned Variance", bold)
            worksheet.write("R1", "Total Delivered", bold)
            worksheet.write("S1", "Status Detail", bold)
            worksheet.write("T1", "Status Action", bold)
            worksheet.write("U1", "Status History Note", bold)
            worksheet.write("V1", "Actual Delivery", bold)
            worksheet.write("W1", "POD?", bold)
            worksheet.write("X1", "POD LINK", bold)
            worksheet.write("Y1", "POD Signed on Glass Link", bold)
            worksheet.write("Z1", "Target Delivery KPI (Days)", bold)
            worksheet.write("AA1", "Delivery Days from Booked", bold)
            worksheet.write("AB1", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AC1", "Calculated ETA", bold)
            worksheet.write("AD1", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AE1", "1st Contact For Delivery Booking Time", bold)
            worksheet.write("AF1", "FP Store Activity Description", bold)
            worksheet.write("AG1", "Invoice Billing Status", bold)
            worksheet.write("AH1", "Invoice Billing Status Note", bold)
            worksheet.write("AI1", "Project Name", bold)
            worksheet.write("AJ1", "Project Due Date", bold)
            worksheet.write("AK1", "Delivery Booking Date", bold)
            # worksheet.write("AI1", "Delivery Booking Target Date", bold)
            # worksheet.write("AJ1", "Delivery Booking - Days To Target", bold)

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
                    row, col + 0, booking.b_dateBookedDate.date(), date_format
                )
                worksheet.write_datetime(
                    row, col + 1, booking.b_dateBookedDate, time_format
                )

            if booking.fp_received_date_time:
                worksheet.write_datetime(
                    row, col + 2, booking.fp_received_date_time, date_format
                )
            elif booking.b_given_to_transport_date_time:
                worksheet.write_datetime(
                    row, col + 2, booking.b_given_to_transport_date_time, date_format
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
            worksheet.write(row, col + 11, booking.vx_freight_provider)
            worksheet.write(row, col + 12, booking.v_FPBookingNumber)
            worksheet.write(row, col + 13, booking.b_status)
            worksheet.write(row, col + 14, e_qty_total)
            worksheet.write(row, col + 15, e_qty_scanned_fp_total)
            worksheet.write(row, col + 16, e_qty_total - e_qty_scanned_fp_total)
            worksheet.write(row, col + 17, booking.b_fp_qty_delivered)

            cell_format = workbook.add_format({"text_wrap": True})
            worksheet.write(row, col + 18, booking.dme_status_detail, cell_format)
            worksheet.write(row, col + 19, booking.dme_status_action, cell_format)
            worksheet.write(
                row, col + 20, booking.dme_status_history_notes, cell_format
            )

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

            if booking.z_calculated_ETA:
                worksheet.write_datetime(
                    row, col + 28, booking.z_calculated_ETA, date_format
                )

            if booking.fp_store_event_date:
                worksheet.write_datetime(
                    row, col + 29, booking.fp_store_event_date, date_format
                )

            if booking.fp_store_event_time:
                worksheet.write_datetime(
                    row, col + 30, booking.fp_store_event_time, time_format
                )

            worksheet.write(row, col + 31, booking.fp_store_event_desc)
            worksheet.write(row, col + 32, booking.inv_billing_status)
            worksheet.write(row, col + 33, booking.inv_billing_status_note)
            worksheet.write(row, col + 34, booking.b_booking_project)
            worksheet.write(row, col + 35, booking.b_project_due_date, date_format)

            # Store Scheduled Date
            worksheet.write(row, col + 36, booking.delivery_booking, date_format)

            # # Store Booking Date Due By
            # if booking.b_status == "In Transit" and booking.delivery_kpi_days:
            #     if int(booking.delivery_kpi_days) == 7:
            #         time_delta = 5
            #     else:
            #         time_delta = 12

            #     if booking.fp_received_date_time:
            #         worksheet.write_datetime(
            #             row,
            #             col + 34,
            #             booking.fp_received_date_time + timedelta(days=int(time_delta)),
            #             date_format,
            #         )
            #     elif booking.b_given_to_transport_date_time:
            #         worksheet.write_datetime(
            #             row,
            #             col + 34,
            #             booking.b_given_to_transport_date_time
            #             + timedelta(days=int(time_delta)),
            #             date_format,
            #         )

            # # Store Booking Early Late
            # if not booking.fp_store_event_date:
            #     store_booking_early_late = ""
            #     if int(booking.delivery_kpi_days) == 7:
            #         time_delta = 5
            #     else:
            #         time_delta = 12

            #     if booking.fp_received_date_time:
            #         store_booking_early_late = (
            #             sydney_today - booking.fp_received_date_time
            #         ).days + time_delta
            #     elif booking.b_given_to_transport_date_time:
            #         store_booking_early_late = (
            #             sydney_today - booking.b_given_to_transport_date_time
            #         ).days + time_delta
            #     worksheet.write(row, col + 35, str(store_booking_early_late))
            # else:
            #     worksheet.write(row, col + 35, "Store Booked")

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#395 Finished - `Bookings` XLS")
    elif xls_type == "BookingLines":
        logger.error(f"#380 Get started to build `BookingLines` XLS")
        worksheet.set_column(0, 40, width=25)
        if show_field_name:
            worksheet.write("A1", "dme_bookings:v_FPBookingNumber", bold)
            worksheet.write("B1", "dme_bookings:b_dateBookedDate(Date)", bold)
            worksheet.write(
                "C1", "fp_received_date_time/b_given_to_transport_date_time", bold
            )
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
            worksheet.write("U1", "z_calculated_ETA", bold)
            worksheet.write("V1", "Dispatch Date", bold)
            worksheet.write("W1", "ETA Into Store", bold)
            worksheet.write("X1", "b_status", bold)
            worksheet.write("Y1", "dme_bookings: dme_status_detail", bold)
            worksheet.write("Z1", "dme_bookings: dme_status_action", bold)
            worksheet.write("AA1", "POD Available", bold)
            worksheet.write("AB1", "e_qty_awaiting_inventory", bold)
            worksheet.write("AC1", "e_qty_collected", bold)
            worksheet.write("AD1", "e_qty_scanned_fp", bold)
            worksheet.write("AE1", "e_qty_scanned_depot", bold)
            worksheet.write("AF1", "e_qty_delivered", bold)
            worksheet.write("AG1", "e_qty_damaged", bold)
            worksheet.write("AH1", "e_qty_returned", bold)
            worksheet.write("AI1", "e_qty_shortages", bold)
            worksheet.write("AJ1", "e_qty_adjusted_delivered", bold)
            worksheet.write("AK1", "b_booking_project", bold)
            worksheet.write("AL1", "b_project_due_date", bold)

            worksheet.write("A2", "Consignment No", bold)
            worksheet.write("B2", "Booked Date", bold)
            worksheet.write("C2", "Given to / Received by Transport", bold)
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
            worksheet.write("U2", "Calculated ETA", bold)
            worksheet.write("V2", "Dispatch Date", bold)
            worksheet.write("W2", "ETA Into Store", bold)
            worksheet.write("X2", "Status", bold)
            worksheet.write("Y2", "Status Detail", bold)
            worksheet.write("Z2", "Status Action", bold)
            worksheet.write("AA2", "POD?", bold)
            worksheet.write("AB2", "Inventory on Back Order", bold)
            worksheet.write("AC2", "Qty Confimred Collected by Pickup Entity", bold)
            worksheet.write("AD2", "Qty Scanned at Transporter Depot", bold)
            worksheet.write("AE2", "Same as Col T?", bold)
            worksheet.write("AF2", "Qty Delivered", bold)
            worksheet.write("AG2", "Qty Damaged", bold)
            worksheet.write("AH2", "Qty Returned", bold)
            worksheet.write("AI2", "Qty Short", bold)
            worksheet.write("AJ2", "Adjusted Delivered Qty", bold)
            worksheet.write("AK2", "Project Name", bold)
            worksheet.write("AL2", "Project Due Date", bold)

            row = 2
        else:
            worksheet.write("A1", "Consignment No", bold)
            worksheet.write("B1", "Booked Date", bold)
            worksheet.write("C1", "Given to / Received by Transport", bold)
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
            worksheet.write("U1", "Calculated ETA", bold)
            worksheet.write("V1", "Dispatch Date", bold)
            worksheet.write("W1", "ETA Into Store", bold)
            worksheet.write("X1", "Status", bold)
            worksheet.write("Y1", "Status Detail", bold)
            worksheet.write("Z1", "Status Action", bold)
            worksheet.write("AA1", "POD?", bold)
            worksheet.write("AB1", "Inventory on Back Order", bold)
            worksheet.write("AC1", "Qty Confimred Collected by Pickup Entity", bold)
            worksheet.write("AD1", "Qty Scanned at Transporter Depot", bold)
            worksheet.write("AE1", "Same as Col T?", bold)
            worksheet.write("AF1", "Qty Delivered", bold)
            worksheet.write("AG1", "Qty Damaged", bold)
            worksheet.write("AH1", "Qty Returned", bold)
            worksheet.write("AI1", "Qty Short", bold)
            worksheet.write("AJ1", "Adjusted Delivered Qty", bold)
            worksheet.write("AK1", "Project Name", bold)
            worksheet.write("AL1", "Project Due Date", bold)

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
                            row, col + 1, booking.b_dateBookedDate.date(), date_format
                        )

                    if booking.fp_received_date_time:
                        worksheet.write_datetime(
                            row, col + 2, booking.fp_received_date_time, date_format
                        )
                    elif booking.b_given_to_transport_date_time:
                        worksheet.write_datetime(
                            row,
                            col + 2,
                            booking.b_given_to_transport_date_time,
                            date_format,
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

                    if booking.z_calculated_ETA:
                        worksheet.write_datetime(
                            row, col + 20, booking.z_calculated_ETA, date_format
                        )

                    if booking.de_Deliver_By_Date:
                        worksheet.write_datetime(
                            row, col + 21, booking.de_Deliver_By_Date, date_format
                        )

                    if booking.de_Deliver_By_Date:
                        delivery_kpi_days = 0

                        if booking.delivery_kpi_days:
                            delivery_kpi_days = booking.delivery_kpi_days

                        worksheet.write(
                            row,
                            col + 22,
                            (
                                booking.de_Deliver_By_Date
                                + timedelta(days=int(delivery_kpi_days))
                            ).strftime("%d-%m-%Y"),
                        )
                    else:
                        worksheet.write(row, col + 22, "")

                    worksheet.write(row, col + 23, booking.b_status)
                    worksheet.write(row, col + 24, booking.dme_status_detail)
                    worksheet.write(row, col + 25, booking.dme_status_action)

                    if (
                        booking.z_pod_url is not None and len(booking.z_pod_url) > 0
                    ) or (
                        booking.z_pod_signed_url is not None
                        and len(booking.z_pod_signed_url) > 0
                    ):
                        worksheet.write(row, col + 26, "Y")
                    else:
                        worksheet.write(row, col + 26, "")

                    worksheet.write(
                        row, col + 27, booking_line.e_qty_awaiting_inventory
                    )
                    worksheet.write(row, col + 28, booking_line.e_qty_collected)
                    worksheet.write(row, col + 29, booking_line.e_qty_scanned_fp)
                    worksheet.write(row, col + 30, booking_line.e_qty_scanned_depot)
                    worksheet.write(row, col + 31, booking_line.e_qty_delivered)
                    worksheet.write(row, col + 32, booking_line.e_qty_damaged)
                    worksheet.write(row, col + 33, booking_line.e_qty_returned)
                    worksheet.write(row, col + 34, booking_line.e_qty_shortages)
                    worksheet.write(
                        row, col + 35, booking_line.e_qty_adjusted_delivered
                    )
                    worksheet.write(row, col + 36, booking.b_booking_project)
                    worksheet.write(
                        row, col + 37, booking.b_project_due_date, date_format
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

        worksheet.write(row, col + 18, e_qty_total)
        worksheet.write(row, col + 30, e_qty_scanned_fp_total)

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#385 Finished - `Booking Lines` XLS")
    elif xls_type == "BookingsWithGaps":
        logger.error(f"#370 Get started to build `BookingsWithGaps` XLS")
        worksheet.set_column(0, 27, width=25)
        if show_field_name:
            worksheet.write("A1", "b_dateBookedDate(Date)", bold)
            worksheet.write("B1", "b_dateBookedDate(Time)", bold)
            worksheet.write(
                "C1", "fp_received_date_time/b_given_to_transport_date_time", bold
            )
            worksheet.write("D1", "pu_Address_State", bold)
            worksheet.write("E1", "business_group", bold)
            worksheet.write("F1", "deToCompanyName", bold)
            worksheet.write("G1", "de_To_Address_Suburb", bold)
            worksheet.write("H1", "de_To_Address_State", bold)
            worksheet.write("I1", "de_To_Address_PostalCode", bold)
            worksheet.write("J1", "b_client_sales_inv_num", bold)
            worksheet.write("K1", "b_client_order_num", bold)
            worksheet.write("L1", "vx_freight_provider", bold)
            worksheet.write("M1", "v_FPBookingNumber", bold)
            worksheet.write("N1", "b_status", bold)
            worksheet.write("O1", "Total Qty", bold)
            worksheet.write("P1", "Total Scanned Qty", bold)
            worksheet.write("Q1", "Booked to Scanned Variance", bold)
            worksheet.write("R1", "b_fp_qty_delivered", bold)
            worksheet.write("S1", "dme_status_detail", bold)
            worksheet.write("T1", "dme_status_action", bold)
            worksheet.write("U1", "dme_status_history_notes", bold)
            worksheet.write("V1", "s_21_ActualDeliveryTimeStamp", bold)
            worksheet.write("W1", "zc_pod_or_no_pod", bold)
            worksheet.write("X1", "z_pod_url", bold)
            worksheet.write("Y1", "z_pod_signed_url", bold)
            worksheet.write("Z1", "delivery_kpi_days", bold)
            worksheet.write("AA1", "delivery_days_from_booked", bold)
            worksheet.write("AB1", "delivery_actual_kpi_days", bold)
            worksheet.write("AC1", "z_calculated_ETA", bold)
            worksheet.write("AD1", "fp_store_event_date", bold)
            worksheet.write("AE1", "fp_store_event_time", bold)
            worksheet.write("AE1", "fp_store_event_desc", bold)
            worksheet.write("AF1", "client_item_reference", bold)

            worksheet.write("A2", "Booked Date", bold)
            worksheet.write("B2", "Booked Time", bold)
            worksheet.write("C2", "Given to / Received by Transport", bold)
            worksheet.write("D2", "From State", bold)
            worksheet.write("E2", "To Entity Group Name", bold)
            worksheet.write("F2", "To Entity", bold)
            worksheet.write("G2", "To Suburb", bold)
            worksheet.write("H2", "To State", bold)
            worksheet.write("I2", "To Postal Code", bold)
            worksheet.write("J2", "Client Sales Invoice", bold)
            worksheet.write("K2", "Client Order Number", bold)
            worksheet.write("L2", "Freight Provider", bold)
            worksheet.write("M2", "Consignment No", bold)
            worksheet.write("N2", "Status", bold)
            worksheet.write("O2", "Total Qty", bold)
            worksheet.write("P2", "Total Scanned Qty", bold)
            worksheet.write("Q2", "Booked to Scanned Variance", bold)
            worksheet.write("R2", "Total Delivered", bold)
            worksheet.write("S2", "Status Detail", bold)
            worksheet.write("T2", "Status Action", bold)
            worksheet.write("U2", "Status History Note", bold)
            worksheet.write("V2", "Actual Delivery", bold)
            worksheet.write("W2", "POD?", bold)
            worksheet.write("X2", "POD LINK", bold)
            worksheet.write("Y2", "POD Signed on Glass Link", bold)
            worksheet.write("Z2", "Target Delivery KPI (Days)", bold)
            worksheet.write("AA2", "Delivery Days from Booked", bold)
            worksheet.write("AB2", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AC2", "Calculated ETA", bold)
            worksheet.write("AD2", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AE2", "1st Contact For Delivery Booking Time", bold)
            worksheet.write("AF2", "FP Store Activity Description", bold)
            worksheet.write("AG2", "Gaps", bold)

            row = 2
        else:
            worksheet.write("A1", "Booked Date", bold)
            worksheet.write("B1", "Booked Time", bold)
            worksheet.write("C1", "Given to / Received by Transport", bold)
            worksheet.write("D1", "From State", bold)
            worksheet.write("E1", "To Entity Group Name", bold)
            worksheet.write("F1", "To Entity", bold)
            worksheet.write("G1", "To Suburb", bold)
            worksheet.write("H1", "To State", bold)
            worksheet.write("I1", "To Postal Code", bold)
            worksheet.write("J1", "Client Sales Invoice", bold)
            worksheet.write("K1", "Client Order Number", bold)
            worksheet.write("L1", "Freight Provider", bold)
            worksheet.write("M1", "Consignment No", bold)
            worksheet.write("N1", "Status", bold)
            worksheet.write("O1", "Total Qty", bold)
            worksheet.write("P1", "Total Scanned Qty", bold)
            worksheet.write("Q1", "Booked to Scanned Variance", bold)
            worksheet.write("R1", "Total Delivered", bold)
            worksheet.write("S1", "Status Detail", bold)
            worksheet.write("T1", "Status Action", bold)
            worksheet.write("U1", "Status History Note", bold)
            worksheet.write("V1", "Actual Delivery", bold)
            worksheet.write("W1", "POD?", bold)
            worksheet.write("X1", "POD LINK", bold)
            worksheet.write("Y1", "POD Signed on Glass Link", bold)
            worksheet.write("Z1", "Target Delivery KPI (Days)", bold)
            worksheet.write("AA1", "Delivery Days from Booked", bold)
            worksheet.write("AB1", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AC1", "Calculated ETA", bold)
            worksheet.write("AD1", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AE1", "1st Contact For Delivery Booking Time", bold)
            worksheet.write("AF1", "FP Store Activity Description", bold)
            worksheet.write("AG1", "Gaps", bold)

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
                    row, col + 0, booking.b_dateBookedDate.date(), date_format
                )
                worksheet.write_datetime(
                    row, col + 1, booking.b_dateBookedDate, time_format
                )

            if booking.fp_received_date_time:
                worksheet.write_datetime(
                    row, col + 2, booking.fp_received_date_time, date_format
                )
            elif booking.b_given_to_transport_date_time:
                worksheet.write_datetime(
                    row, col + 2, booking.b_given_to_transport_date_time, date_format
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
            worksheet.write(row, col + 11, booking.vx_freight_provider)
            worksheet.write(row, col + 12, booking.v_FPBookingNumber)
            worksheet.write(row, col + 13, booking.b_status)
            worksheet.write(row, col + 14, e_qty_total)
            worksheet.write(row, col + 15, e_qty_scanned_fp_total)
            worksheet.write(row, col + 16, e_qty_total - e_qty_scanned_fp_total)
            worksheet.write(row, col + 17, booking.b_fp_qty_delivered)
            worksheet.write(row, col + 18, booking.dme_status_detail)
            worksheet.write(row, col + 19, booking.dme_status_action)
            worksheet.write(row, col + 20, booking.dme_status_history_notes)

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

            if booking.z_calculated_ETA:
                worksheet.write_datetime(
                    row, col + 28, booking.z_calculated_ETA, date_format
                )

            if booking.fp_store_event_date:
                worksheet.write_datetime(
                    row, col + 29, booking.fp_store_event_date, date_format
                )

            if booking.fp_store_event_time:
                worksheet.write_datetime(
                    row, col + 30, booking.fp_store_event_time, time_format
                )

            worksheet.write(row, col + 31, booking.fp_store_event_desc)
            worksheet.write(row, col + 32, gaps)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#375 Finished - `BookingsWithGaps` XLS")
    elif xls_type == "DMEBookingsWithGaps":
        logger.error(f"#370 Get started to build `BookingsWithGaps` XLS")
        worksheet.set_column(0, 27, width=25)
        if show_field_name:
            worksheet.write("A1", "b_bookingID_Visual", bold)
            worksheet.write("B1", "b_client_name", bold)
            worksheet.write("C1", "b_client_name_sub", bold)
            worksheet.write("D1", "b_dateBookedDate(Date)", bold)
            worksheet.write("E1", "b_dateBookedDate(Time)", bold)
            worksheet.write(
                "F1", "fp_received_date_time/b_given_to_transport_date_time", bold
            )
            worksheet.write("G1", "pu_Address_State", bold)
            worksheet.write("H1", "business_group", bold)
            worksheet.write("I1", "deToCompanyName", bold)
            worksheet.write("J1", "de_To_Address_Suburb", bold)
            worksheet.write("K1", "de_To_Address_State", bold)
            worksheet.write("L1", "de_To_Address_PostalCode", bold)
            worksheet.write("M1", "b_client_sales_inv_num", bold)
            worksheet.write("N1", "b_client_order_num", bold)
            worksheet.write("O1", "vx_freight_provider", bold)
            worksheet.write("P1", "v_FPBookingNumber", bold)
            worksheet.write("Q1", "b_status", bold)
            worksheet.write("R1", "fp_invoice_no", bold)
            worksheet.write("S1", "inv_cost_quoted", bold)
            worksheet.write("T1", "inv_cost_actual", bold)
            worksheet.write("U1", "inv_sell_quoted", bold)
            worksheet.write("V1", "inv_sell_actual", bold)
            worksheet.write("W1", "dme_status_linked_reference_from_fp", bold)
            worksheet.write("X1", "inv_billing_status", bold)
            worksheet.write("Y1", "inv_billing_status_note", bold)
            worksheet.write("Z1", "Total Qty", bold)
            worksheet.write("AA1", "Total Scanned Qty", bold)
            worksheet.write("AB1", "Booked to Scanned Variance", bold)
            worksheet.write("AC1", "b_fp_qty_delivered", bold)
            worksheet.write("AD1", "dme_status_detail", bold)
            worksheet.write("AE1", "dme_status_action", bold)
            worksheet.write("AF1", "dme_status_history_notes", bold)
            worksheet.write("AG1", "s_21_ActualDeliveryTimeStamp", bold)
            worksheet.write("AH1", "zc_pod_or_no_pod", bold)
            worksheet.write("AI1", "z_pod_url", bold)
            worksheet.write("AJ1", "z_pod_signed_url", bold)
            worksheet.write("AK1", "delivery_kpi_days", bold)
            worksheet.write("AL1", "delivery_days_from_booked", bold)
            worksheet.write("AM1", "delivery_actual_kpi_days", bold)
            worksheet.write("AN1", "z_calculated_ETA", bold)
            worksheet.write("AO1", "fp_store_event_date", bold)
            worksheet.write("AP1", "fp_store_event_time", bold)
            worksheet.write("AQ1", "fp_store_event_desc", bold)
            worksheet.write("AR1", "client_item_reference", bold)

            worksheet.write("A2", "Booking ID", bold)
            worksheet.write("B2", "Client Name", bold)
            worksheet.write("C2", "Sub Client Name", bold)
            worksheet.write("D2", "Booked Date", bold)
            worksheet.write("E2", "Booked Time", bold)
            worksheet.write("F2", "Given to / Received by Transport", bold)
            worksheet.write("G2", "From State", bold)
            worksheet.write("H2", "To Entity Group Name", bold)
            worksheet.write("I2", "To Entity", bold)
            worksheet.write("J2", "To Suburb", bold)
            worksheet.write("K2", "To State", bold)
            worksheet.write("L2", "To Postal Code", bold)
            worksheet.write("M2", "Client Sales Invoice", bold)
            worksheet.write("N2", "Client Order Number", bold)
            worksheet.write("O2", "Freight Provider", bold)
            worksheet.write("P2", "Consignment No", bold)
            worksheet.write("Q2", "Status", bold)
            worksheet.write("R2", "FP Invoice No", bold)
            worksheet.write("S2", "Quoted Cost", bold)
            worksheet.write("T2", "Actual Cost", bold)
            worksheet.write("U2", "Quoted Sell", bold)
            worksheet.write("V2", "Actual Sell", bold)
            worksheet.write("W2", "Linked Reference", bold)
            worksheet.write("X2", "Invoice Billing Status", bold)
            worksheet.write("Y2", "Invoice Billing Status Note", bold)
            worksheet.write("Z2", "Total Qty", bold)
            worksheet.write("AA2", "Total Scanned Qty", bold)
            worksheet.write("AB2", "Booked to Scanned Variance", bold)
            worksheet.write("AC2", "Total Delivered", bold)
            worksheet.write("AD2", "Status Detail", bold)
            worksheet.write("AE2", "Status Action", bold)
            worksheet.write("AF2", "Status History Note", bold)
            worksheet.write("AG2", "Actual Delivery", bold)
            worksheet.write("AH2", "POD?", bold)
            worksheet.write("AI2", "POD LINK", bold)
            worksheet.write("AJ2", "POD Signed on Glass Link", bold)
            worksheet.write("AK2", "Target Delivery KPI (Days)", bold)
            worksheet.write("AL2", "Delivery Days from Booked", bold)
            worksheet.write("AM2", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AN2", "Calculated ETA", bold)
            worksheet.write("AO2", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AP2", "1st Contact For Delivery Booking Time", bold)
            worksheet.write("AQ2", "FP Store Activity Description", bold)
            worksheet.write("AR2", "Gaps", bold)

            row = 2
        else:
            worksheet.write("A1", "Booking ID", bold)
            worksheet.write("B1", "Client Name", bold)
            worksheet.write("C1", "Sub Client Name", bold)
            worksheet.write("D1", "Booked Date", bold)
            worksheet.write("E1", "Booked Time", bold)
            worksheet.write("F1", "Given to / Received by Transport", bold)
            worksheet.write("G1", "From State", bold)
            worksheet.write("H1", "To Entity Group Name", bold)
            worksheet.write("I1", "To Entity", bold)
            worksheet.write("J1", "To Suburb", bold)
            worksheet.write("K1", "To State", bold)
            worksheet.write("L1", "To Postal Code", bold)
            worksheet.write("M1", "Client Sales Invoice", bold)
            worksheet.write("N1", "Client Order Number", bold)
            worksheet.write("O1", "Freight Provider", bold)
            worksheet.write("P1", "Consignment No", bold)
            worksheet.write("Q1", "Status", bold)
            worksheet.write("R1", "FP Invoice No", bold)
            worksheet.write("S1", "Quoted Cost", bold)
            worksheet.write("T1", "Actual Cost", bold)
            worksheet.write("U1", "Quoted Sell", bold)
            worksheet.write("V1", "Actual Sell", bold)
            worksheet.write("W1", "Linked Reference", bold)
            worksheet.write("X1", "Invoice Billing Status", bold)
            worksheet.write("Y1", "Invoice Billing Status Note", bold)
            worksheet.write("Z1", "Total Qty", bold)
            worksheet.write("AA1", "Total Scanned Qty", bold)
            worksheet.write("AB1", "Booked to Scanned Variance", bold)
            worksheet.write("AC1", "Total Delivered", bold)
            worksheet.write("AD1", "Status Detail", bold)
            worksheet.write("AE1", "Status Action", bold)
            worksheet.write("AF1", "Status History Note", bold)
            worksheet.write("AG1", "Actual Delivery", bold)
            worksheet.write("AH1", "POD?", bold)
            worksheet.write("AI1", "POD LINK", bold)
            worksheet.write("AJ1", "POD Signed on Glass Link", bold)
            worksheet.write("AK1", "Target Delivery KPI (Days)", bold)
            worksheet.write("AL1", "Delivery Days from Booked", bold)
            worksheet.write("AM1", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AN1", "Calculated ETA", bold)
            worksheet.write("AO1", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AP1", "1st Contact For Delivery Booking Time", bold)
            worksheet.write("AQ1", "FP Store Activity Description", bold)
            worksheet.write("AR1", "Gaps", bold)

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

            worksheet.write(row, col + 0, booking.b_bookingID_Visual)
            worksheet.write(row, col + 1, booking.b_client_name)
            worksheet.write(row, col + 2, booking.b_client_name_sub)

            if booking.b_dateBookedDate and booking.b_dateBookedDate:
                worksheet.write_datetime(
                    row, col + 3, booking.b_dateBookedDate.date(), date_format
                )
                worksheet.write_datetime(
                    row, col + 4, booking.b_dateBookedDate, time_format
                )

            if booking.fp_received_date_time:
                worksheet.write_datetime(
                    row, col + 5, booking.fp_received_date_time, date_format
                )
            elif booking.b_given_to_transport_date_time:
                worksheet.write_datetime(
                    row, col + 5, booking.b_given_to_transport_date_time, date_format
                )

            worksheet.write(row, col + 6, booking.pu_Address_State)

            customer_group_name = ""
            customer_groups = Dme_utl_client_customer_group.objects.all()
            for customer_group in customer_groups:
                if (
                    customer_group.name_lookup.lower()
                    in booking.deToCompanyName.lower()
                ):
                    customer_group_name = customer_group.group_name
            worksheet.write(row, col + 7, customer_group_name)

            worksheet.write(row, col + 8, booking.deToCompanyName)
            worksheet.write(row, col + 9, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 10, booking.de_To_Address_State)
            worksheet.write(row, col + 11, booking.de_To_Address_PostalCode)
            worksheet.write(row, col + 12, booking.b_client_sales_inv_num)
            worksheet.write(row, col + 13, booking.b_client_order_num)
            worksheet.write(row, col + 14, booking.vx_freight_provider)
            worksheet.write(row, col + 15, booking.v_FPBookingNumber)
            worksheet.write(row, col + 16, booking.b_status)

            worksheet.write(row, col + 17, booking.fp_invoice_no)
            worksheet.write(row, col + 18, booking.inv_cost_quoted)
            worksheet.write(row, col + 19, booking.inv_cost_actual)
            worksheet.write(row, col + 20, booking.inv_sell_quoted)
            worksheet.write(row, col + 21, booking.inv_sell_actual)
            worksheet.write(row, col + 22, booking.dme_status_linked_reference_from_fp)
            worksheet.write(row, col + 23, booking.inv_billing_status)
            worksheet.write(row, col + 24, booking.inv_billing_status_note)

            worksheet.write(row, col + 25, e_qty_total)
            worksheet.write(row, col + 26, e_qty_scanned_fp_total)
            worksheet.write(row, col + 27, e_qty_total - e_qty_scanned_fp_total)
            worksheet.write(row, col + 28, booking.b_fp_qty_delivered)
            worksheet.write(row, col + 29, booking.dme_status_detail)
            worksheet.write(row, col + 30, booking.dme_status_action)
            worksheet.write(row, col + 31, booking.dme_status_history_notes)

            if (
                booking.s_21_ActualDeliveryTimeStamp
                and booking.s_21_ActualDeliveryTimeStamp
            ):
                worksheet.write_datetime(
                    row, col + 32, booking.s_21_ActualDeliveryTimeStamp, date_format
                )

            if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (
                booking.z_pod_signed_url is not None
                and len(booking.z_pod_signed_url) > 0
            ):
                worksheet.write(row, col + 33, "Y")
            else:
                worksheet.write(row, col + 33, "")

            if settings.ENV == "dev":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 34,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 35,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )
            elif settings.ENV == "prod":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 34,
                        settings.S3_URL + "/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 35,
                        settings.S3_URL + "/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )

            worksheet.write(row, col + 36, booking.delivery_kpi_days)

            if (
                booking.b_status is not None
                and booking.b_status == "Delivered"
                and booking.s_21_ActualDeliveryTimeStamp is not None
                and booking.b_dateBookedDate is not None
            ):
                worksheet.write(
                    row,
                    col + 37,
                    (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )
                worksheet.write(
                    row,
                    col + 38,
                    booking.delivery_kpi_days
                    - (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )

            if booking.z_calculated_ETA:
                worksheet.write_datetime(
                    row, col + 39, booking.z_calculated_ETA, date_format
                )

            if booking.fp_store_event_date:
                worksheet.write_datetime(
                    row, col + 40, booking.fp_store_event_date, date_format
                )

            if booking.fp_store_event_time:
                worksheet.write_datetime(
                    row, col + 41, booking.fp_store_event_time, time_format
                )

            worksheet.write(row, col + 42, booking.fp_store_event_desc)
            worksheet.write(row, col + 43, gaps)

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
            worksheet.write(
                "B1", "fp_received_date_time/b_given_to_transport_date_time", bold
            )
            worksheet.write("C1", "Pickup Days Late", cell_format)
            worksheet.write("D1", "Delivery Days Early / Late", cell_format)
            worksheet.write("E1", "Query With", bold)
            worksheet.write("F1", "b_client_sales_inv_num", bold)
            worksheet.write("G1", "vx_freight_provider", bold)
            worksheet.write("H1", "v_FPBookingNumber", bold)
            worksheet.write("I1", "b_status", bold)
            worksheet.write("J1", "dme_status_detail", bold)
            worksheet.write("K1", "dme_status_action", bold)
            worksheet.write("L1", "dme_status_history_notes", bold)
            worksheet.write("M1", "", cell_format)
            worksheet.write("N1", "e_qty", bold)
            worksheet.write("O1", "e_qty_scanned_fp_total", bold)
            worksheet.write("P1", "Booked to Scanned Variance", bold)
            worksheet.write("Q1", "b_fp_qty_delivered", bold)
            worksheet.write("R1", "pu_Address_State", bold)
            worksheet.write("S1", "business_group", bold)
            worksheet.write("T1", "deToCompanyName", bold)
            worksheet.write("U1", "de_To_Address_Suburb", bold)
            worksheet.write("V1", "de_To_Address_State", bold)
            worksheet.write("W1", "de_To_Address_PostalCode", bold)
            worksheet.write("X1", "b_client_order_num", bold)
            worksheet.write("U1", "s_21_ActualDeliveryTimeStamp", bold)
            worksheet.write("Z1", "zc_pod_or_no_pod", bold)
            worksheet.write("AA1", "z_pod_url", bold)
            worksheet.write("AB1", "z_pod_signed_url", bold)
            worksheet.write("AC1", "delivery_kpi_days", bold)
            worksheet.write("AD1", "delivery_days_from_booked", bold)
            worksheet.write("AE1", "delivery_actual_kpi_days", bold)
            worksheet.write("AF1", "z_calculated_ETA", bold)
            worksheet.write("AG1", "fp_store_event_date", bold)
            worksheet.write("AH1", "fp_store_event_desc", bold)

            worksheet.write("A2", "Booked Date", bold)
            worksheet.write("B2", "Given to / Received by Transport", bold)
            worksheet.write("C2", "Pickup Days Late", cell_format)
            worksheet.write("D2", "Delivery Days Early / Late", cell_format)
            worksheet.write("E2", "Query With", bold)
            worksheet.write("F2", "Client Sales Invoice", bold)
            worksheet.write("G2", "Freight Provider", bold)
            worksheet.write("H2", "Consignment No", bold)
            worksheet.write("I2", "Status", bold)
            worksheet.write("J2", "Status Detail", bold)
            worksheet.write("K2", "Status Action", bold)
            worksheet.write("L2", "Status History Note", bold)
            worksheet.write(
                "M2",
                "Please put your Feedback / updates in the column if different to Column G, H and / or I",
                cell_format,
            )
            worksheet.write("N2", "Qty Booked", bold)
            worksheet.write("O2", "Qty Scanned", bold)
            worksheet.write("P2", "Booked to Scanned Variance", bold)
            worksheet.write("Q2", "Total Delivered", bold)
            worksheet.write("R2", "From State", bold)
            worksheet.write("S2", "To Entity Group Name", bold)
            worksheet.write("T2", "To Entity", bold)
            worksheet.write("U2", "To Suburb", bold)
            worksheet.write("V2", "To State", bold)
            worksheet.write("W2", "To Postal Code", bold)
            worksheet.write("X2", "Client Order Number", bold)
            worksheet.write("Y2", "Actual Delivery", bold)
            worksheet.write("Z2", "POD?", bold)
            worksheet.write("AA2", "POD LINK", bold)
            worksheet.write("AB2", "POD Signed on Glass Link", bold)
            worksheet.write("AC2", "Target Delivery KPI (Days)", bold)
            worksheet.write("AD2", "Delivery Days from Booked", bold)
            worksheet.write("AE2", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AF2", "Calculated ETA", bold)
            worksheet.write("AG2", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AH2", "FP Store Activity Description", bold)

            row = 2
        else:
            worksheet.write("A1", "Booked Date", bold)
            cell_format = workbook.add_format(
                {"font_color": "red", "bold": 1, "align": "left"}
            )
            worksheet.write("B1", "Given to / Received by Transport", bold)
            worksheet.write("C1", "Pickup Days Late", cell_format)
            worksheet.write("D1", "Delivery Days Early / Late", cell_format)
            worksheet.write("E1", "Query With", bold)
            worksheet.write("F1", "Client Sales Invoice", bold)
            worksheet.write("G1", "Freight Provider", bold)
            worksheet.write("H1", "Consignment No", bold)
            worksheet.write("I1", "Status", bold)
            worksheet.write("J1", "Status Detail", bold)
            worksheet.write("K1", "Status Action", bold)
            worksheet.write("L1", "Status History Note", bold)
            worksheet.write(
                "M1",
                "Please put your Feedback / updates in the column if different to Column G, H and / or I",
                cell_format,
            )
            worksheet.write("N1", "Qty Booked", bold)
            worksheet.write("O1", "Qty Scanned", bold)
            worksheet.write("P1", "Booked to Scanned Variance", bold)
            worksheet.write("Q1", "Total Delivered", bold)
            worksheet.write("R1", "From State", bold)
            worksheet.write("S1", "To Entity Group Name", bold)
            worksheet.write("T1", "To Entity", bold)
            worksheet.write("U1", "To Suburb", bold)
            worksheet.write("V1", "To State", bold)
            worksheet.write("W1", "To Postal Code", bold)
            worksheet.write("X1", "Client Order Number", bold)
            worksheet.write("Y1", "Actual Delivery", bold)
            worksheet.write("Z1", "POD?", bold)
            worksheet.write("AA1", "POD LINK", bold)
            worksheet.write("AB1", "POD Signed on Glass Link", bold)
            worksheet.write("AC1", "Target Delivery KPI (Days)", bold)
            worksheet.write("AD1", "Delivery Days from Booked", bold)
            worksheet.write("AE1", "Actual Delivery KPI (Days)", bold)
            worksheet.write("AF1", "Calculated ETA", bold)
            worksheet.write("AG1", "1st Contact For Delivery Booking Date", bold)
            worksheet.write("AH1", "FP Store Activity Description", bold)

            row = 1

        from api.utils import get_sydney_now_time

        sydney_now = get_sydney_now_time("datetime")
        logger.error(f"#361 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            if booking_ind % 500 == 0:
                logger.error(f"#362 Current index: {booking_ind}")

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

            if booking.b_dateBookedDate and booking.b_dateBookedDate:
                worksheet.write_datetime(
                    row, col + 0, booking.b_dateBookedDate.date(), date_format
                )

            if booking.fp_received_date_time:
                worksheet.write_datetime(
                    row, col + 1, booking.fp_received_date_time, date_format
                )
            elif booking.b_given_to_transport_date_time:
                worksheet.write_datetime(
                    row, col + 1, booking.b_given_to_transport_date_time, date_format
                )

            if (
                booking.b_dateBookedDate is not None
                and booking.b_status is not None
                and "booked" in booking.b_status.lower()
            ):
                pickup_days_late = (
                    booking.b_dateBookedDate.date()
                    + timedelta(days=2)
                    - sydney_now.date()
                ).days

                if pickup_days_late < 0:
                    cell_format = workbook.add_format({"font_color": "red"})
                    worksheet.write(
                        row,
                        col + 2,
                        "(" + str(pickup_days_late * -1) + ")",
                        cell_format,
                    )
                else:
                    worksheet.write(row, col + 2, pickup_days_late)

            if booking.b_status is not None and booking.b_dateBookedDate is not None:
                delivery_kpi_days = 0
                days_early_late = "None - not booked"

                if booking.delivery_kpi_days is not None:
                    delivery_kpi_days = int(booking.delivery_kpi_days)

                if booking.b_dateBookedDate is not None:
                    days_early_late = (
                        booking.b_dateBookedDate.date()
                        + timedelta(days=delivery_kpi_days)
                        - sydney_now.date()
                    ).days

                if days_early_late < 0:
                    cell_format = workbook.add_format({"font_color": "red"})
                    worksheet.write(
                        row, col + 3, "(" + str(days_early_late * -1) + ")", cell_format
                    )
                else:
                    worksheet.write(row, col + 3, days_early_late)

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

            worksheet.write(row, col + 4, query_with)
            worksheet.write(row, col + 5, booking.b_client_sales_inv_num)
            worksheet.write(row, col + 6, booking.vx_freight_provider)
            worksheet.write(row, col + 7, booking.v_FPBookingNumber)
            worksheet.write(row, col + 8, booking.b_status)

            cell_format = workbook.add_format({"text_wrap": True})
            worksheet.write(row, col + 9, booking.dme_status_detail, cell_format)
            worksheet.write(row, col + 10, booking.dme_status_action, cell_format)
            worksheet.write(
                row, col + 11, booking.dme_status_history_notes, cell_format
            )
            worksheet.write(row, col + 12, "", cell_format)
            worksheet.write(row, col + 13, e_qty_total)
            worksheet.write(row, col + 14, e_qty_scanned_fp_total)
            worksheet.write(row, col + 15, e_qty_total - e_qty_scanned_fp_total)
            worksheet.write(row, col + 16, booking.b_fp_qty_delivered)
            worksheet.write(row, col + 17, booking.pu_Address_State)

            customer_group_name = ""
            customer_groups = Dme_utl_client_customer_group.objects.all()
            for customer_group in customer_groups:
                if (
                    customer_group.name_lookup.lower()
                    in booking.deToCompanyName.lower()
                ):
                    customer_group_name = customer_group.group_name
            worksheet.write(row, col + 18, customer_group_name)

            worksheet.write(row, col + 19, booking.deToCompanyName)
            worksheet.write(row, col + 20, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 21, booking.de_To_Address_State)
            worksheet.write(row, col + 22, booking.de_To_Address_PostalCode)
            worksheet.write(row, col + 23, booking.b_client_order_num)

            if (
                booking.s_21_ActualDeliveryTimeStamp
                and booking.s_21_ActualDeliveryTimeStamp
            ):
                worksheet.write_datetime(
                    row, col + 24, booking.s_21_ActualDeliveryTimeStamp, date_format
                )

            if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (
                booking.z_pod_signed_url is not None
                and len(booking.z_pod_signed_url) > 0
            ):
                worksheet.write(row, col + 25, "Y")
            else:
                worksheet.write(row, col + 25, "")

            if settings.ENV == "dev":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 26,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 27,
                        "http://3.105.62.128/static/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )
            elif settings.ENV == "prod":
                if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                    worksheet.write_url(
                        row,
                        col + 26,
                        settings.S3_URL + "/imgs/" + booking.z_pod_url,
                        string=booking.z_pod_url,
                    )

                if (
                    booking.z_pod_signed_url is not None
                    and len(booking.z_pod_signed_url) > 0
                ):
                    worksheet.write_url(
                        row,
                        col + 27,
                        settings.S3_URL + "/imgs/" + booking.z_pod_signed_url,
                        string=booking.z_pod_signed_url,
                    )

            worksheet.write(row, col + 28, booking.delivery_kpi_days)

            if (
                booking.b_status is not None
                and booking.b_status == "Delivered"
                and booking.s_21_ActualDeliveryTimeStamp is not None
                and booking.b_dateBookedDate is not None
            ):
                worksheet.write(
                    row,
                    col + 29,
                    (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )
                worksheet.write(
                    row,
                    col + 30,
                    booking.delivery_kpi_days
                    - (
                        booking.s_21_ActualDeliveryTimeStamp.date()
                        - booking.b_dateBookedDate.date()
                    ).days,
                )

            if booking.z_calculated_ETA:
                worksheet.write_datetime(
                    row, col + 31, booking.z_calculated_ETA, date_format
                )

            if booking.fp_store_event_date:
                worksheet.write_datetime(
                    row, col + 32, booking.fp_store_event_date, date_format
                )

            worksheet.write(row, col + 33, booking.fp_store_event_desc)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#365 Finished - `Whse` XLS")
    elif xls_type == "booked_bookings":
        logger.error("#310 Get started to build `Booked Bookings` XLS")
        worksheet.set_column(0, 10, width=25)

        if show_field_name:
            worksheet.write("A1", "b_bookingID_Visual", bold)
            worksheet.write("B1", "b_dateBookedDate", bold)
            worksheet.write("C1", "s_05_LatestPickUpDateTimeFinal", bold)
            worksheet.write("D1", "b_status", bold)
            worksheet.write("E1", "b_booking_Category", bold)
            worksheet.write("F1", "line_data/gap_ra", bold)
            worksheet.write("G1", "puCompany", bold)
            worksheet.write("H1", "deToCompanyName ", bold)
            worksheet.write("I1", "", bold)
            worksheet.write("J1", "", bold)

            worksheet.write("A2", "DeliverME Booking Ref", bold)
            worksheet.write("B2", "Date Time Booked", bold)
            worksheet.write("C2", "Latest Pickup Date 4 Service", bold)
            worksheet.write("D2", "Booking Status", bold)
            worksheet.write("E2", "Booking Category", bold)
            worksheet.write("F2", "GAP/RA numbers", bold)
            worksheet.write("G2", "Pickup Entity", bold)
            worksheet.write("H2", "Deliver to Entity", bold)
            worksheet.write("I2", "Return email with consignment sent", bold)
            worksheet.write("J2", "Booking email with consignment sent", bold)

            row = 2
        else:
            worksheet.write("A1", "DeliverME Booking Ref", bold)
            worksheet.write("B1", "Date Time Booked", bold)
            worksheet.write("C1", "Latest Pickup Date 4 Service", bold)
            worksheet.write("D1", "Booking Status", bold)
            worksheet.write("E1", "Booking Category", bold)
            worksheet.write("F1", "GAP/RA numbers", bold)
            worksheet.write("G1", "Pickup Entity", bold)
            worksheet.write("H1", "Deliver to Entity", bold)
            worksheet.write("I1", "Return email with consignment sent", bold)
            worksheet.write("J1", "Booking email with consignment sent", bold)

            row = 1

        logger.error(f"#311 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            worksheet.write(row, col + 0, booking.b_bookingID_Visual)

            if booking.b_dateBookedDate:
                worksheet.write_datetime(
                    row, col + 1, booking.b_dateBookedDate.date(), date_format
                )

            if booking.s_05_LatestPickUpDateTimeFinal:
                worksheet.write_datetime(
                    row,
                    col + 2,
                    booking.s_05_LatestPickUpDateTimeFinal.date(),
                    date_format,
                )

            worksheet.write(row, col + 3, booking.b_status)
            worksheet.write(row, col + 4, booking.b_booking_Category)
            worksheet.write(row, col + 5, booking.gap_ras)
            worksheet.write(row, col + 6, booking.puCompany)
            worksheet.write(row, col + 7, booking.deToCompanyName)

            general_emails = EmailLogs.objects.filter(
                emailName="General Booking", booking_id=booking.id
            )
            return_emails = EmailLogs.objects.filter(
                emailName="Return Booking", booking_id=booking.id
            )
            worksheet.write(row, col + 8, "Yes" if general_emails else "No")
            worksheet.write(row, col + 9, "Yes" if return_emails else "No")

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#319 Finished - `Booked Bookings` XLS")
    elif xls_type == "picked_up_bookings":
        logger.error("#320 Get started to build `Picked Up Bookings` XLS")
        worksheet.set_column(0, 10, width=25)

        if show_field_name:
            worksheet.write("A1", "b_bookingID_Visual", bold)
            worksheet.write("B1", "s_20_Actual_Pickup_TimeStamp", bold)
            worksheet.write("C1", "b_booking_Category", bold)
            worksheet.write("D1", "line_data/clientRefNumber", bold)
            worksheet.write("E1", "puCompany", bold)
            worksheet.write("F1", "deToCompanyName ", bold)

            worksheet.write("A2", "DeliverME Booking Ref", bold)
            worksheet.write("B2", "Actual Pickup Date", bold)
            worksheet.write("C2", "Booking Category", bold)
            worksheet.write("D2", "Client Reference No's", bold)
            worksheet.write("E2", "Pickup Entity", bold)
            worksheet.write("F2", "Deliver to Entity", bold)

            row = 2
        else:
            worksheet.write("A1", "DeliverME Booking Ref", bold)
            worksheet.write("B1", "Actual Pickup Date", bold)
            worksheet.write("C1", "Booking Category", bold)
            worksheet.write("D1", "Client Reference No's", bold)
            worksheet.write("E1", "Pickup Entity", bold)
            worksheet.write("F1", "Deliver to Entity", bold)

            row = 1

        logger.error(f"#321 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            worksheet.write(row, col + 0, booking.b_bookingID_Visual)

            if booking.s_20_Actual_Pickup_TimeStamp:
                worksheet.write_datetime(
                    row,
                    col + 1,
                    booking.s_20_Actual_Pickup_TimeStamp.date(),
                    date_format,
                )

            worksheet.write(row, col + 2, booking.b_booking_Category)
            worksheet.write(row, col + 3, booking.clientRefNumbers)
            worksheet.write(row, col + 4, booking.puCompany)
            worksheet.write(row, col + 5, booking.deToCompanyName)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#329 Finished - `Picked Up Bookings` XLS")
    elif xls_type == "box":
        logger.error("#330 Get started to build `Box Bookings` XLS")
        worksheet.set_column(0, 15, width=25)

        if show_field_name:
            worksheet.write("A1", "b_bookingID_Visual", bold)
            worksheet.write("B1", "b_dateBookedDate", bold)
            worksheet.write("C1", "s_20_Actual_Pickup_TimeStamp", bold)
            worksheet.write("D1", "line_data/clientRefNumber", bold)
            worksheet.write("E1", "puCompany", bold)
            worksheet.write("F1", "pu_Address_Suburb", bold)
            worksheet.write("G1", "pu_Address_State", bold)
            worksheet.write("H1", "pu_Address_PostalCode", bold)
            worksheet.write("I1", "deToCompanyName ", bold)
            worksheet.write("J1", "de_To_Address_Suburb ", bold)
            worksheet.write("K1", "de_To_Address_State ", bold)
            worksheet.write("L1", "de_To_Address_PostalCode ", bold)

            worksheet.write("A2", "DeliverME Booking Ref", bold)
            worksheet.write("B2", "Date Time Booked", bold)
            worksheet.write("C2", "Actual Pickup Date Time", bold)
            worksheet.write("D2", "Client Reference No's", bold)
            worksheet.write("E2", "Pickup Entity", bold)
            worksheet.write("F2", "Pickup Address Suburb", bold)
            worksheet.write("G2", "Pickup Address State", bold)
            worksheet.write("H2", "Pickup Address Postal Code", bold)
            worksheet.write("I2", "Deliver to Entity", bold)
            worksheet.write("J2", "Delivery Address Suburb", bold)
            worksheet.write("K2", "Delivery Address State", bold)
            worksheet.write("L2", "Delivery Address Postal Code", bold)

            row = 2
        else:
            worksheet.write("A1", "DeliverME Booking Ref", bold)
            worksheet.write("B1", "Date Time Booked", bold)
            worksheet.write("C1", "Actual Pickup Date Time", bold)
            worksheet.write("D1", "Client Reference No's", bold)
            worksheet.write("E1", "Pickup Entity", bold)
            worksheet.write("F1", "Pickup Address Suburb", bold)
            worksheet.write("G1", "Pickup Address State", bold)
            worksheet.write("H1", "Pickup Address Postal Code", bold)
            worksheet.write("I1", "Deliver to Entity", bold)
            worksheet.write("J1", "Delivery Address Suburb", bold)
            worksheet.write("K1", "Delivery Address State", bold)
            worksheet.write("L1", "Delivery Address Postal Code", bold)

            row = 1

        logger.error(f"#331 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            worksheet.write(row, col + 0, booking.b_bookingID_Visual)

            if booking.b_dateBookedDate:
                worksheet.write_datetime(
                    row, col + 1, booking.b_dateBookedDate.date(), date_format,
                )

            if booking.s_20_Actual_Pickup_TimeStamp:
                worksheet.write_datetime(
                    row,
                    col + 2,
                    booking.s_20_Actual_Pickup_TimeStamp.date(),
                    date_format,
                )

            worksheet.write(row, col + 3, booking.clientRefNumbers)
            worksheet.write(row, col + 4, booking.puCompany)
            worksheet.write(row, col + 5, booking.pu_Address_Suburb)
            worksheet.write(row, col + 6, booking.pu_Address_State)
            worksheet.write(row, col + 7, booking.pu_Address_PostalCode)
            worksheet.write(row, col + 8, booking.deToCompanyName)
            worksheet.write(row, col + 9, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 10, booking.de_To_Address_State)
            worksheet.write(row, col + 11, booking.de_To_Address_PostalCode)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#339 Finished - `Box Bookings` XLS")
    elif xls_type == "futile":
        logger.error("#340 Get started to build `Futile Bookings` XLS")
        worksheet.set_column(0, 15, width=25)

        if show_field_name:
            worksheet.write("A1", "b_bookingID_Visual", bold)
            worksheet.write("B1", "dme_status_history/event_time_stamp", bold)
            worksheet.write("C1", "b_booking_Category", bold)
            worksheet.write("D1", "line_data/gap_ra & clientRefNumber", bold)
            worksheet.write("E1", "puCompany", bold)
            worksheet.write("F1", "pu_Address_Suburb", bold)
            worksheet.write("G1", "pu_Address_State", bold)
            worksheet.write("H1", "pu_Address_PostalCode", bold)
            worksheet.write("I1", "deToCompanyName", bold)
            worksheet.write("J1", "de_To_Address_Suburb", bold)
            worksheet.write("K1", "de_To_Address_State ", bold)
            worksheet.write("L1", "de_To_Address_PostalCode", bold)
            worksheet.write("M1", "vx_futile_Booking_Notes", bold)
            worksheet.write("N1", "b_status", bold)
            worksheet.write("O1", "dme_status_history/notes", bold)

            worksheet.write("A2", "DeliverME Booking Ref", bold)
            worksheet.write("B2", "Futile Event Date", bold)
            worksheet.write("C2", "Booking Category", bold)
            worksheet.write("D2", "Client Reference No's", bold)
            worksheet.write("E2", "Pickup Entity", bold)
            worksheet.write("F2", "Pickup Address Suburb", bold)
            worksheet.write("G2", "Pickup Address State", bold)
            worksheet.write("H2", "Pickup Address Postal Code", bold)
            worksheet.write("I2", "Deliver to Entity", bold)
            worksheet.write("J2", "Delivery Address Suburb", bold)
            worksheet.write("K2", "Delivery Address State", bold)
            worksheet.write("L2", "Delivery Address Postal Code", bold)
            worksheet.write("M2", "Futile Booking Notes", bold)
            worksheet.write("N2", "Current Booking State", bold)
            worksheet.write("O2", "Status Note", bold)

            row = 2
        else:
            worksheet.write("A1", "DeliverME Booking Ref", bold)
            worksheet.write("B1", "Futile Event Date", bold)
            worksheet.write("C1", "Booking Category", bold)
            worksheet.write("D1", "Client Reference No's", bold)
            worksheet.write("E1", "Pickup Entity", bold)
            worksheet.write("F1", "Pickup Address Suburb", bold)
            worksheet.write("G1", "Pickup Address State", bold)
            worksheet.write("H1", "Pickup Address Postal Code", bold)
            worksheet.write("I1", "Deliver to Entity", bold)
            worksheet.write("J1", "Delivery Address Suburb", bold)
            worksheet.write("K1", "Delivery Address State", bold)
            worksheet.write("L1", "Delivery Address Postal Code", bold)
            worksheet.write("M1", "Futile Booking Notes", bold)
            worksheet.write("N1", "Current Booking State", bold)
            worksheet.write("O1", "Status Note", bold)

            row = 1

        logger.error(f"#341 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            if not booking.had_status("futile"):
                continue

            worksheet.write(row, col + 0, booking.b_bookingID_Visual)

            status_histories = booking.get_status_histories("futile")
            if status_histories and status_histories[0].event_time_stamp:
                worksheet.write_datetime(
                    row,
                    col + 1,
                    status_histories[0].event_time_stamp.date(),
                    date_format,
                )

            worksheet.write(row, col + 2, booking.b_booking_Category)
            worksheet.write(
                row, col + 3, f"{booking.clientRefNumbers} {booking.gap_ras}"
            )
            worksheet.write(row, col + 4, booking.puCompany)
            worksheet.write(row, col + 5, booking.pu_Address_Suburb)
            worksheet.write(row, col + 6, booking.pu_Address_State)
            worksheet.write(row, col + 7, booking.pu_Address_PostalCode)
            worksheet.write(row, col + 8, booking.deToCompanyName)
            worksheet.write(row, col + 9, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 10, booking.de_To_Address_State)
            worksheet.write(row, col + 11, booking.de_To_Address_PostalCode)
            worksheet.write(row, col + 12, booking.vx_futile_Booking_Notes)
            worksheet.write(row, col + 13, booking.b_status)

            if status_histories and status_histories[0].event_time_stamp:
                worksheet.write(row, col + 14, status_histories[0].notes)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#349 Finished - `Futile Bookings` XLS")
    elif xls_type == "goods_delivered":
        logger.error("#350 Get started to build `Goods Delivered Bookings` XLS")
        worksheet.set_column(0, 15, width=25)

        if show_field_name:
            worksheet.write("A1", "b_bookingID_Visual", bold)
            worksheet.write("B1", "line_data/gap_ra", bold)
            worksheet.write("C1", "b_status", bold)
            worksheet.write("D1", "delivery_booking", bold)
            worksheet.write("E1", "b_booking_Category", bold)
            worksheet.write("F1", "puCompany", bold)
            worksheet.write("G1", "pu_Address_Suburb", bold)
            worksheet.write("H1", "pu_Address_State", bold)
            worksheet.write("I1", "pu_Address_PostalCode", bold)
            worksheet.write("J1", "deToCompanyName", bold)
            worksheet.write("K1", "de_To_Address_Suburb", bold)
            worksheet.write("L1", "de_To_Address_State ", bold)
            worksheet.write("M1", "de_To_Address_PostalCode", bold)
            worksheet.write("N1", "b_booking_Notes", bold)
            worksheet.write("O1", "line_data/gap_ra", bold)

            worksheet.write("A2", "DeliverME Booking Ref", bold)
            worksheet.write("B2", "Gap/ra - from line_data", bold)
            worksheet.write("C2", "Booking Status", bold)
            worksheet.write("D2", "Actual Delivery Date", bold)
            worksheet.write("E2", "Booking Category", bold)
            worksheet.write("F2", "Pickup Entity", bold)
            worksheet.write("G2", "Pickup Address Suburb", bold)
            worksheet.write("H2", "Pickup Address State", bold)
            worksheet.write("I2", "Pickup Address Postal Code", bold)
            worksheet.write("J2", "Deliver to Entity", bold)
            worksheet.write("K2", "Delivery Address Suburb", bold)
            worksheet.write("L2", "Delivery Address State", bold)
            worksheet.write("M2", "Delivery Address Postal Code", bold)
            worksheet.write("N2", "Booking Notes", bold)
            worksheet.write("O2", "Client Reference No's", bold)

            row = 2
        else:
            worksheet.write("A1", "DeliverME Booking Ref", bold)
            worksheet.write("B1", "Gap/ra - from line_data", bold)
            worksheet.write("C1", "Booking Status", bold)
            worksheet.write("D1", "Actual Delivery Date", bold)
            worksheet.write("E1", "Booking Category", bold)
            worksheet.write("F1", "Pickup Entity", bold)
            worksheet.write("G1", "Pickup Address Suburb", bold)
            worksheet.write("H1", "Pickup Address State", bold)
            worksheet.write("I1", "Pickup Address Postal Code", bold)
            worksheet.write("J1", "Deliver to Entity", bold)
            worksheet.write("K1", "Delivery Address Suburb", bold)
            worksheet.write("L1", "Delivery Address State", bold)
            worksheet.write("M1", "Delivery Address Postal Code", bold)
            worksheet.write("N1", "Booking Notes", bold)
            worksheet.write("O1", "Client Reference No's", bold)

            row = 1

        logger.error(f"#351 Total cnt: {len(bookings)}")
        for booking_ind, booking in enumerate(bookings):
            if not booking.had_status("delivered"):
                continue

            worksheet.write(row, col + 0, booking.b_bookingID_Visual)
            worksheet.write(row, col + 1, booking.gap_ras)
            worksheet.write(row, col + 2, booking.b_status)

            if booking.delivery_booking:
                worksheet.write_datetime(
                    row, col + 3, booking.delivery_booking, date_format
                )

            worksheet.write(row, col + 4, booking.b_booking_Category)
            worksheet.write(row, col + 5, booking.puCompany)
            worksheet.write(row, col + 6, booking.pu_Address_Suburb)
            worksheet.write(row, col + 7, booking.pu_Address_State)
            worksheet.write(row, col + 8, booking.pu_Address_PostalCode)
            worksheet.write(row, col + 9, booking.deToCompanyName)
            worksheet.write(row, col + 10, booking.de_To_Address_Suburb)
            worksheet.write(row, col + 11, booking.de_To_Address_State)
            worksheet.write(row, col + 12, booking.de_To_Address_PostalCode)
            worksheet.write(row, col + 13, booking.b_booking_Notes)
            worksheet.write(row, col + 14, booking.clientRefNumbers)

            row += 1

        workbook.close()
        shutil.move(filename, local_filepath + filename)
        logger.error("#359 Finished - `Goods Delivered Bookings` XLS")

    return local_filepath + filename
