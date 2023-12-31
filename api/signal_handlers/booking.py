import logging
from datetime import datetime

from django.conf import settings

from api.models import (
    Bookings,
    Booking_lines,
    Api_booking_confirmation_lines,
    API_booking_quotes,
)
from api.fp_apis.utils import gen_consignment_num
from api.operations.labels.index import build_label as build_label_oper
from api.operations.pronto_xi.index import update_note as update_pronto_note
from api.operations.genesis.index import create_shared_booking, update_shared_booking
from api.operations.booking.quote import get_quote_again
from api.common.booking_quote import set_booking_quote
from api.common import trace_error
from api.helpers.list import *
from api.convertors.pdf import pdf_merge


logger = logging.getLogger(__name__)
IMPORTANT_FIELDS = [
    "pu_Address_State",
    "pu_Address_Suburb",
    "pu_Address_PostalCode",
    "pu_Address_Country",
    "de_To_Address_State",
    "de_To_Address_Suburb",
    "de_To_Address_PostalCode",
    "pu_Address_Type",
    "de_To_AddressType",
    "pu_no_of_assists",
    "de_no_of_assists",
    "pu_location",
    "de_to_location",
    "pu_access",
    "de_access",
    "pu_floor_number",
    "de_floor_number",
    "pu_floor_access_by",
    "de_to_floor_access_by",
    "pu_service",
    "de_service",
    "booking_type",
]

GENESIS_FIELDS = [
    "b_dateBookedDate",
    "v_FPBookingNumber",
    "b_client_name",
    "de_Deliver_By_Date",
    "vx_freight_provider",
    "vx_serviceName",
    "b_status",
    "de_To_Address_Street_1",
    "de_To_Address_Street_2",
    "de_To_Address_State",
    "de_To_Address_Suburb",
    "de_To_Address_PostalCode",
    "de_To_Address_Country",
    "de_to_Contact_F_LName",
    "de_Email",
    "de_to_Phone_Mobile",
    "de_to_Phone_Main",
    "booked_for_comm_communicate_via",
    "b_booking_Priority",
    "s_06_Latest_Delivery_Date_TimeSet",
    "s_06_Latest_Delivery_Date_Time_Override",
    "s_21_Actual_Delivery_TimeStamp",
]

if settings.ENV == "local":
    S3_URL = "./static"
elif settings.ENV == "dev":
    S3_URL = "/opt/s3_public"
elif settings.ENV == "prod":
    S3_URL = "/opt/s3_public"


def pre_save_handler(instance, update_fields):
    LOG_ID = "[BOOKING PRE SAVE]"

    if instance.id is None:  # new object will be created
        pass
    else:
        logger.info(f"{LOG_ID} Booking PK: {instance.id}")
        old = Bookings.objects.get(id=instance.id)

        if old.dme_status_detail != instance.dme_status_detail:  # field will be updated
            instance.dme_status_detail_updated_by = "user"
            instance.prev_dme_status_detail = old.dme_status_detail
            instance.dme_status_detail_updated_at = datetime.now()

        # Mail Genesis
        if old.b_dateBookedDate and intersection(GENESIS_FIELDS, update_fields or []):
            update_shared_booking(instance)

        if old.b_status != instance.b_status:
            if instance.b_status == "Booked":
                instance.b_dateBookedDate = datetime.now()

            # Mail Genesis
            if old.b_dateBookedDate is None and instance.b_dateBookedDate:
                create_shared_booking(instance)
                # pass
            elif instance.b_status == "In Transit":
                try:
                    booking_Lines_cnt = Booking_lines.objects.filter(
                        fk_booking_id=instance.pk_booking_id
                    ).count()
                    fp_scanned_cnt = Api_booking_confirmation_lines.objects.filter(
                        fk_booking_id=instance.pk_booking_id, tally__gt=0
                    ).count()

                    dme_status_detail = ""
                    if (
                        instance.b_given_to_transport_date_time
                        and not instance.fp_received_date_time
                    ):
                        dme_status_detail = "In transporter's depot"
                    if instance.fp_received_date_time:
                        dme_status_detail = "Good Received by Transport"

                    if fp_scanned_cnt > 0 and fp_scanned_cnt < booking_Lines_cnt:
                        dme_status_detail = dme_status_detail + " (Partial)"

                    instance.dme_status_detail = dme_status_detail
                    instance.dme_status_detail_updated_by = "user"
                    instance.prev_dme_status_detail = old.dme_status_detail
                    instance.dme_status_detail_updated_at = datetime.now()
                except Exception as e:
                    logger.info(f"#505 {LOG_ID} Error {e}")
                    pass
            elif instance.b_status == "Delivered":
                instance.dme_status_detail = ""
                instance.dme_status_detail_updated_by = "user"
                instance.prev_dme_status_detail = old.dme_status_detail
                instance.dme_status_detail_updated_at = datetime.now()

        # BSD
        if instance.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8":
            if old.z_label_url != instance.z_label_url:
                instance.status = "Ready for Booking"

        # JasonL
        if instance.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002":
            quote = instance.api_booking_quote

            if quote and (
                old.b_status != instance.b_status  # Status
                or (
                    instance.b_dateBookedDate
                    and old.b_dateBookedDate != instance.b_dateBookedDate  # BookedDate
                )
                or (
                    instance.v_FPBookingNumber
                    and old.v_FPBookingNumber
                    != instance.v_FPBookingNumber  # Consignment
                )
                or (old.api_booking_quote_id != instance.api_booking_quote_id)  # Quote
            ):
                update_pronto_note(quote, instance, [], "booking")

        if (
            instance.api_booking_quote
            and old.api_booking_quote_id != instance.api_booking_quote_id
        ):
            quote = instance.api_booking_quote

            if instance.api_booking_quote.vehicle:
                logger.info(f"#506 {LOG_ID} vehicle changed!")
                instance.v_vehicle_Type = (
                    quote.vehicle.description if quote.vehicle else None
                )

            if quote.packed_status == API_booking_quotes.SCANNED_PACK:
                instance.inv_booked_quoted = quote.client_mu_1_minimum_values
            else:
                instance.inv_sell_quoted = quote.client_mu_1_minimum_values


def post_save_handler(instance, created, update_fields):
    LOG_ID = "[BOOKING POST SAVE]"

    # if (
    #     not created
    #     and not instance.z_lock_status
    #     and intersection(IMPORTANT_FIELDS, update_fields or [])
    #     and instance.kf_client_id
    #     != "461162D2-90C7-BF4E-A905-000000000004"  # Ignore when plum scans
    # ):
    #     logger.info(f"{LOG_ID} Updated important field.")

    #     # Reset selected Quote and connected Quotes
    #     if instance.booking_type != "DMEA":
    #         set_booking_quote(instance, None)
    #         quotes = API_booking_quotes.objects.filter(
    #             fk_booking_id=instance.pk_booking_id,
    #             is_used=False,
    #         )
    #         for quote in quotes:
    #             quote.is_used = True
    #             quote.save()
    #     elif instance.booking_type == "DMEA":
    #         get_quote_again(instance)

    if (
        instance.vx_freight_provider
        and instance.z_label_url
        and "[REBUILD_REQUIRED]" in instance.z_label_url
    ):
        try:
            logger.info(f"{LOG_ID} Booking PK: {instance.id}")

            # Check if pricings exist for selected FP
            quotes = API_booking_quotes.objects.filter(
                fk_booking_id=instance.pk_booking_id,
                freight_provider__iexact=instance.vx_freight_provider,
                packed_status=Booking_lines.SCANNED_PACK,
                is_used=False,
            ).order_by("client_mu_1_minimum_values")

            if not quotes:
                instance.b_error_Capture = "Quote doen't exist"

                if instance.z_label_url:
                    instance.z_label_url = instance.z_label_url[18:]

                instance.save()
                return

            # Mapping Pircing info to Booking
            quote = quotes.first()
            instance.vx_account_code = quote.account_code
            instance.vx_serviceName = quote.service_name
            instance.v_service_Type = quote.service_code
            instance.inv_cost_quoted = quote.fee * (
                1 + (quote.mu_percentage_fuel_levy or 0)
            )

            if instance.b_status == Booking_lines.SCANNED_PACK:
                instance.inv_sell_quoted = quote.client_mu_1_minimum_values
            else:
                instance.inv_booked_quoted = quote.client_mu_1_minimum_values

            instance.v_vehicle_Type = (
                quote.vehicle.description if quote.vehicle else None
            )
            instance.api_booking_quote = quote

            # Build Label
            _fp_name = instance.vx_freight_provider.lower()
            file_path = f"{S3_URL}/pdfs/{_fp_name}_au"

            if instance.b_client_name == "Jason L":
                lines = Booking_lines.objects.filter(
                    fk_booking_id=instance.pk_booking_id,
                    is_deleted=False,
                )

                for line in lines:
                    if line.sscc and "NOSSCC_" in line.sscc:
                        line.sscc = None
                        line.save()

                scanned_lines = []
                for line in lines:
                    if line.packed_status == "scanned":
                        scanned_lines.append(line)

                original_lines = []
                for line in lines:
                    if line.packed_status == "original":
                        original_lines.append(line)

                if instance.api_booking_quote:
                    selected_lines = []

                    for line in lines:
                        if (
                            line.packed_status
                            == instance.api_booking_quote.packed_status
                        ):
                            selected_lines.append(line)

                    lines = selected_lines
                else:
                    if scanned_lines:
                        lines = scanned_lines
                    else:
                        lines = original_lines

                # Populate SSCC if doesn't exist
                for line in lines:
                    if not line.sscc:
                        line.sscc = f"NOSSCC_{instance.b_bookingID_Visual}_{line.pk}"
                        line.save()

                sscc_list = []
                sscc_lines = {}
                total_qty = 0
                for line in lines:
                    if line.sscc not in sscc_list:
                        sscc_list.append(line.sscc)
                        total_qty += line.e_qty
                        _lines = []

                        for line1 in lines:
                            if line1.sscc == line.sscc:
                                _lines.append(line1)

                        sscc_lines[line.sscc] = _lines
                logger.info(
                    f"{LOG_ID} \nsscc_list: {sscc_list}\nsscc_lines: {sscc_lines}\nTotal QTY: {total_qty}"
                )

                # Build label with SSCC - one sscc should have one page label
                file_path = f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au"
                label_data = build_label_oper(
                    booking=instance,
                    file_path=file_path,
                    total_qty=total_qty,
                    sscc_list=sscc_list,
                    sscc_lines=sscc_lines,
                    sscc_cnt=total_qty,
                    need_zpl=False,
                )

                if label_data["urls"]:
                    entire_label_url = (
                        f"{file_path}/DME{instance.b_bookingID_Visual}.pdf"
                    )
                    pdf_merge(label_data["urls"], entire_label_url)

                instance.z_label_url = f"{settings.WEB_SITE_URL}/label/{instance.b_client_booking_ref_num}/"
                logger.info(
                    f"@370 {LOG_ID} Rebuilt Label Successfully - {instance.z_label_url}"
                )
            else:
                _fp_name = instance.vx_freight_provider.lower()
                file_path = f"{S3_URL}/pdfs/{_fp_name}_au/"
                file_path, file_name = build_label_oper(
                    booking=instance, file_path=file_path
                )
                instance.z_label_url = f"{_fp_name}_au/{file_name}"

            # Set consignment number
            instance.v_FPBookingNumber = gen_consignment_num(
                instance.vx_freight_provider,
                instance.b_bookingID_Visual,
                instance.kf_client_id,
                instance,
            )
            instance.save()
        except Exception as e:
            trace_error.print()
