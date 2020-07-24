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
import smtplib
import pytz
import logging
from dateutil.rrule import *
from pytz import timezone
from datetime import timedelta
from os.path import basename

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import COMMASPACE, formatdate

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
    Table,
)
from reportlab.platypus.flowables import Spacer, HRFlowable, PageBreak, Flowable

from reportlab.lib.units import inch, mm
from reportlab.graphics.barcode import createBarcodeDrawing

from reportlab.graphics.shapes import Drawing
from reportlab.pdfgen import canvas
import re

from django.conf import settings
from api.models import *
from api.common import trace_error
from api.operations.generate_xls_report import build_xls
from .models import *

from django.core import serializers, files

if settings.ENV == "local":
    production = False  # Local
else:
    production = True  # Dev

logger = logging.getLogger("dme_api")

redis_host = "localhost"
redis_port = 6379
redis_password = ""

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


def get_client_name(request):
    user_id = request.user.id
    dme_employee = (
        DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
    )

    if dme_employee is not None:
        return "dme"
    else:
        client_employee = (
            Client_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )
        client = DME_clients.objects.get(
            pk_id_dme_client=client_employee.fk_id_dme_client_id
        )
        return client.company_name


def calc_collect_after_status_change(pk_booking_id, status):
    booking_lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)

    for booking_line in booking_lines:
        if status == "Collected" and booking_line.e_qty_awaiting_inventory:
            booking_line.e_qty_collected = (
                booking_line.e_qty - booking_line.e_qty_awaiting_inventory
            )
        elif status == "In Transit" or (
            status == "Collected" and not booking_line.e_qty_awaiting_inventory
        ):
            booking_line.e_qty_collected = booking_line.e_qty

        booking_line.save()


def send_email(
    send_to,
    send_cc,
    subject,
    text,
    files=None,
    mime_type="plain",
    server="localhost",
    use_tls=True,
):
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_HOST_USER
    msg["To"] = COMMASPACE.join(send_to)
    msg["Cc"] = COMMASPACE.join(send_cc)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject
    msg.attach(MIMEText(text, mime_type))

    for f in files or []:
        file_content = open(f, "rb").read()

        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")):
            image = MIMEImage(file_content, name=os.path.basename(f))
            msg.attach(image)
        else:
            pdf = MIMEApplication(file_content, Name=basename(f))
            pdf["Content-Disposition"] = 'attachment; filename="%s"' % basename(f)
            msg.attach(pdf)

    smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)

    if use_tls:
        smtp.starttls()

    smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    smtp.sendmail(settings.EMAIL_HOST_USER, send_to + send_cc, msg.as_string())
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
    sydney_now = datetime.now().replace(microsecond=0).astimezone(sydney_tz)

    if return_type == "char":
        return sydney_now.strftime("%Y-%m-%d %H:%M:%S")
    elif return_type == "datetime":
        return sydney_now
    elif return_type == "date-char":
        return sydney_now.strftime("%Y-%m-%d")


def get_available_bookings(booking_ids):
    where_clause = " WHERE "
    for id in booking_ids:
        where_clause = where_clause + "id = " + str(id) + " OR "
    where_clause = where_clause[:-4]

    bookings = Bookings.objects.filter(id__in=booking_ids).order_by("id").values()
    return bookings

def get_available_booking_lines(booking):
    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking["pk_booking_id"]).values()
    return booking_lines

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

def myFirstPage(canvas, doc):
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

def build_xls_and_send(
    bookings,
    email_addr,
    report_type,
    username,
    start_date,
    end_date,
    show_field_name,
    clientname,
):
    if report_type == "booking":
        filepath = build_xls(
            bookings, "Bookings", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],  # Recipient email address(list)
            [],  # CC
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
            [],
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
            [email_addr],
            [],
            "Bookings with Gaps XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Booking With Gaps) you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "dme_booking_with_gaps":
        filepath = build_xls(
            bookings,
            "DMEBookingsWithGaps",
            username,
            start_date,
            end_date,
            show_field_name,
        )
        send_email(
            [email_addr],
            [],
            "Bookings with Gaps XLS Report from Deliver-Me(DME only can generate this report)",  # Subject of email
            "Here is the excel report(DME Booking With Gaps) you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "whse":
        filepath = build_xls(
            bookings, "Whse", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],
            [],
            "Whse XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Whse) you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "pending_bookings":
        filepath = build_xls(
            bookings,
            "pending_bookings",
            username,
            start_date,
            end_date,
            show_field_name,
        )
        send_email(
            [email_addr],
            [],
            "Pending Bookings XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "booked_bookings":
        filepath = build_xls(
            bookings, "booked_bookings", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],
            [],
            "Booked Bookings XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "picked_up_bookings":
        filepath = build_xls(
            bookings,
            "picked_up_bookings",
            username,
            start_date,
            end_date,
            show_field_name,
        )
        send_email(
            [email_addr],
            [],
            "PickedUp Bookings XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "box":
        filepath = build_xls(
            bookings, "box", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],
            [],
            "Box XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "futile":
        filepath = build_xls(
            bookings, "futile", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],
            [],
            "Futile XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report you generated from Deliver-Me.",  # Message of email
            [filepath],  # Attachment file path(list)
        )
    elif report_type == "goods_delivered":
        filepath = build_xls(
            bookings, "goods_delivered", username, start_date, end_date, show_field_name
        )
        send_email(
            [email_addr],
            [],
            "Goods Delivered Bookings XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report you generated from Deliver-Me.",  # Message of email
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
        attachments = [
            filepath_booking,
            filepath_booking_line,
            filepath_booking_with_gaps,
            filepath_whse,
        ]

        if clientname == "dme":
            filepath_dme_booking_with_gaps = build_xls(
                bookings,
                "DMEBookingsWithGaps",
                username,
                start_date,
                end_date,
                show_field_name,
            )
            attachments.append(filepath_dme_booking_with_gaps)

        send_email(
            [email_addr],
            [],
            "All XLS Report from Deliver-Me",  # Subject of email
            "Here is the excel report(Bookings & Booking Lines & Booking With Gaps & Whse) you generated from Deliver-Me.",  # Message of email
            attachments,  # Attachment file path(list)
        )


def tables_in_query(sql_str):

    # remove the /* */ comments
    q = re.sub(r"/\*[^*]*\*+(?:[^*/][^*]*\*+)*/", "", sql_str)

    # remove whole line -- and # comments
    lines = [line for line in q.splitlines() if not re.match("^\s*(--|#)", line)]

    # remove trailing -- and # comments
    q = " ".join([re.split("--|#", line)[0] for line in lines])

    # split on blanks, parens and semicolons
    tokens = re.split(r"[\s)(;]+", q)

    # scan the tokens. if we see a FROM or JOIN, we set the get_next
    # flag, and grab the next one (unless it's SELECT).

    result = []
    get_next = False
    for tok in tokens:
        if get_next:
            if tok.lower() not in ["", "select"]:
                result.append(tok)
            get_next = False
        get_next = tok.lower() in ["from", "join"]

    return result


def get_clientname(request):
    user_id = request.user.id
    dme_employee = (
        DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
    )
    if dme_employee is not None:
        return "dme"
    else:
        client_employee = (
            Client_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )
        client = DME_clients.objects.get(
            pk_id_dme_client=client_employee.fk_id_dme_client_id
        )
        return client.company_name


def next_business_day(start_day, business_days, HOLIDAYS):
    ONE_DAY = timedelta(days=1)
    temp_day = start_day
    for i in range(0, business_days):
        next_day = temp_day + ONE_DAY
        while next_day.weekday() in [5, 6] or next_day in HOLIDAYS:
            next_day += ONE_DAY
        temp_day = next_day
    return temp_day


def get_pu_by(booking):
    if booking.pu_PickUp_By_Date:
        pu_by = datetime.combine(
            booking.pu_PickUp_By_Date,
            time(
                int(
                    booking.pu_PickUp_By_Time_Hours
                    if booking.pu_PickUp_By_Time_Hours
                    else 0
                ),
                int(
                    booking.pu_PickUp_By_Time_Minutes
                    if booking.pu_PickUp_By_Time_Minutes
                    else 0
                ),
                0,
            ),
        )
        return pu_by
    else:
        return None


def get_eta_pu_by(booking):
    try:
        if get_pu_by(booking) is None:
            sydney_tz = pytz.timezone("Australia/Sydney")
            etd_pu_by = datetime.now().replace(microsecond=0).astimezone(sydney_tz)
            weekno = etd_pu_by.weekday()

            if weekno > 4:
                etd_pu_by = etd_pu_by + timedelta(days=7 - weekno)

            etd_pu_by = etd_pu_by.replace(minute=0, hour=17, second=0)

            return etd_pu_by
        else:
            return get_pu_by(booking)
    except Exception as e:
        trace_error.print()
        logger.info(f"Error #1001: {e}")
        return None


def get_eta_de_by(booking, quote):
    try:
        etd_de_by = get_eta_pu_by(booking)
        freight_provider = Fp_freight_providers.objects.get(
            fp_company_name=booking.vx_freight_provider
        )

        if freight_provider and quote:
            service_etd = FP_Service_ETDs.objects.filter(
                freight_provider_id=freight_provider.id,
                fp_delivery_time_description=quote.etd,
            ).first()

            if service_etd is not None:
                if service_etd.fp_service_time_uom.lower() == "days":
                    etd_de_by = next_business_day(
                        etd_de_by, round(service_etd.fp_03_delivery_hours / 24), [],
                    )

                if service_etd.fp_service_time_uom.lower() == "hours":
                    etd_de_by = etd_de_by + timedelta(
                        hours=service_etd.fp_03_delivery_hours
                    )
                    weekno = etd_de_by.weekday()
                    if weekno > 4:
                        etd_de_by = etd_de_by + timedelta(days=7 - weekno)
            else:
                if quote.fk_freight_provider_id == "TNT":
                    days = round(float(quote.etd))
                    etd_de_by = next_business_day(etd_de_by, days, [])

            return etd_de_by
        else:
            return None
    except Exception as e:
        trace_error.print()
        logger.info(f"Error #1002: {e}")
        return None


def get_b_bookingID_Visual(dme_file):
    b_bookingID_Visual = ""
    if dme_file.file_type == "xls import" and (
        dme_file.note and len(dme_file.note) == 36
    ):
        booking = Bookings.objects.filter(pk_booking_id=dme_file.note).first()

        if booking:
            b_bookingID_Visual = booking.b_bookingID_Visual

    return b_bookingID_Visual


def get_booking_id(dme_file):
    booking_id = ""
    if dme_file.file_type == "xls import" and (
        dme_file.note and len(dme_file.note) == 36
    ):
        booking = Bookings.objects.filter(pk_booking_id=dme_file.note).first()

        if booking:
            booking_id = booking.id

    return booking_id
