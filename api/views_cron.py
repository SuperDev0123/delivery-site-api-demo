import logging

from datetime import datetime
from pydash import _
from django.db.models import Count, Aggregate, CharField
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from api.common import trace_error
from api.serializers import *
from api.models import *
from api.base.viewsets import *

logger = logging.getLogger(__name__)


class GroupConcat(Aggregate):
    function = "GROUP_CONCAT"
    template = "%(function)s(%(distinct)s%(expressions)s%(ordering)s%(separator)s)"

    def __init__(
        self, expression, distinct=False, ordering=None, separator=",", **extra
    ):
        super(GroupConcat, self).__init__(
            expression,
            distinct="DISTINCT " if distinct else "",
            ordering=" ORDER BY %s" % ordering if ordering is not None else "",
            separator=' SEPARATOR "%s"' % separator,
            output_field=CharField(),
            **extra,
        )


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
def mapBokToBooking(request):
    LOG_ID = "[MAPPING]"

    try:
        option_value = DME_Options.objects.get(option_name="MoveSuccess2ToBookings")
        run_time = (
            datetime.now().replace(tzinfo=None)
            - option_value.end_time.replace(tzinfo=None)
        ).seconds
        message = "No booking is mapped!"

        if not option_value.is_running and run_time > 30:
            option_value.is_running = 1
            option_value.start_time = datetime.now()
            option_value.save()
            max_id = (
                Bookings.objects.filter()
                .aggregate(max_id=Max("b_bookingID_Visual"))
                .get("max_id")
            )
            max_id = max_id if max_id else 89600
            start_id = max_id + 1
            bok_headers = BOK_1_headers.objects.filter(success__in=[2, 4, 5])[:10]
            headers_count = len(bok_headers)
            logger.info(f"{LOG_ID} {headers_count} can be mapped.")
            end_id = start_id + headers_count - 1

            if headers_count > 0:
                for idx, header in enumerate(bok_headers):
                    mapBok(start_id + idx, header)
                message += f"Rows moved to dme_bookings = {headers_count}"

            # pre_data = list(
            #     Bookings.objects.filter(
            #         b_bookingID_Visual__gte=start_id, b_bookingID_Visual__lte=end_id
            #     ).values_list("kf_client_id", "b_client_sales_inv_num")
            # )
            # kf_client_id_list = []
            # b_client_sales_inv_num_list = []
            # for data in pre_data:
            #     kf_client_id_list.append(data[0])
            #     b_client_sales_inv_num_list.append(data[1])
            # error_bookings_1 = (
            #     Bookings.objects.filter(
            #         b_bookingID_Visual__gt=start_id,
            #         kf_client_id__isnull=False,
            #         b_client_sales_inv_num__isnull=False,
            #         b_client_sales_inv_num__regex=r".{0}.*",
            #         kf_client_id__in=kf_client_id_list,
            #         b_client_sales_inv_num__in=b_client_sales_inv_num_list,
            #     )
            #     .exclude(b_status__in=["Cancelled", "Closed"])
            #     .values("kf_client_id", "b_client_sales_inv_num")
            #     .annotate(
            #         id=Max("id"),
            #         b_bookingID_Visual_List=GroupConcat(
            #             "b_bookingID_Visual", separator=", "
            #         ),
            #     )
            # )
            # error_bookings_2 = (
            #     Bookings.objects.filter(
            #         b_bookingID_Visual__gte=start_id,
            #         b_bookingID_Visual__lte=end_id,
            #         kf_client_id__isnull=False,
            #         b_client_sales_inv_num__isnull=False,
            #         b_client_sales_inv_num__regex=r".{0}.*",
            #     )
            #     .values("kf_client_id", "b_client_sales_inv_num")
            #     .annotate(
            #         id=Max("id"),
            #         ctn=Count("*"),
            #         b_bookingID_Visual_List=GroupConcat(
            #             "b_bookingID_Visual", separator=", "
            #         ),
            #     )
            #     .filter(ctn__gt=1)
            # )
            # error_bookings = list(error_bookings_1) + list(error_bookings_2)

            # for booking in error_bookings:
            #     Bookings.objects.filter(id=booking["id"]).update(
            #         b_error_Capture=sliceString(
            #             (
            #                 "SINV is duplicated in bookingID = "
            #                 + booking["b_bookingID_Visual_List"]
            #             ),
            #             1000,
            #         ),
            #         b_status="On Hold",
            #     )

            option_value.is_running = 0
            option_value.end_time = datetime.now()
            option_value.save()
        else:
            message += "Procedure MoveSuccess2ToBookings is already running."

        return Response(message, status=status.HTTP_200_OK)
    except Exception as e:
        logger.info(f"{LOG_ID} Error: {str(e)}")
        trace_error.print()
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


def mapBok(id, header):
    LOG_ID = "[MAPPING]"
    sid = transaction.savepoint()

    try:
        dme_client = DME_clients.objects.get(dme_account_num=header.fk_client_id)
        delivery_times = []

        try:
            delivery_times = Utl_fp_delivery_times.objects.filter(
                fp_name=header.b_001_b_freight_provider,
                postal_code_from__lte=header.b_059_b_del_address_postalcode,
                postal_code_to__gte=header.b_059_b_del_address_postalcode,
            )
        except:
            pass

        # *** EDI solutions start ***#
        de_company = header.b_054_b_del_company
        de_street_1 = header.b_055_b_del_address_street_1
        de_street_2 = header.b_056_b_del_address_street_2
        de_phone_main = header.b_064_b_del_phone_main
        de_contact = header.b_061_b_del_contact_full_name

        if not de_street_1 and de_street_2:
            de_street_1 = de_street_2
            de_street_2 = ""

        if not de_phone_main:
            de_phone_main = "0267651109"
        else:
            de_phone_main = de_phone_main.replace(" ", "")
            de_phone_main = de_phone_main.replace("+", "")

        if not de_company and de_contact:
            de_company = de_contact

        if not de_contact and de_company:
            de_contact = de_company
        # *** EDI solutions end ***#

        bookingStatus = ""
        bookingStatusCategory = ""
        if header.success:
            success = int(header.success)
            if success == 2:
                if header.b_000_3_consignment_number:
                    bookingStatus = "Booked"
                    bookingStatusCategory = "Booked"
                else:
                    bookingStatus = "Ready for booking"
                    bookingStatusCategory = "Pre Booking"
            elif success == 4:
                bookingStatus = "Picking"
                bookingStatusCategory = "Pre Booking"
            elif success == 5:
                bookingStatus = "Imported / Integrated"
                bookingStatusCategory = "Pre Booking"

        with transaction.atomic():
            booking = Bookings.objects.create(
                pk_booking_id=header.pk_header_id,
                b_clientReference_RA_Numbers=sliceString(
                    header.b_000_1_b_clientReference_RA_Numbers, 100
                ),
                total_lines_qty_override=header.b_000_b_total_lines,
                vx_freight_provider=sliceString(header.b_001_b_freight_provider, 100),
                v_vehicle_Type=sliceString(header.b_002_b_vehicle_type, 64),
                booking_Created_For=sliceString(header.b_005_b_created_for, 64),
                booking_Created_For_Email=sliceString(
                    header.b_006_b_created_for_email, 64
                ),
                x_ReadyStatus=sliceString(header.b_007_b_ready_status, 32),
                b_booking_Priority=sliceString(header.b_009_b_priority, 32),
                b_handling_Instructions=sliceString(
                    header.b_014_b_pu_handling_instructions, 120
                ),
                pu_PickUp_Instructions_Contact=sliceString(
                    header.b_015_b_pu_instructions_contact, 512
                ),
                pu_pickup_instructions_address=sliceString(
                    header.b_016_b_pu_instructions_address, 512
                ),
                pu_WareHouse_Number=sliceString(header.b_017_b_pu_warehouse_num, 10),
                pu_WareHouse_Bay=sliceString(header.b_018_b_pu_warehouse_bay, 10),
                b_booking_tail_lift_pickup=header.b_019_b_pu_tail_lift,
                b_booking_no_operator_pickup=header.b_020_b_pu_num_operators,
                puPickUpAvailFrom_Date=header.b_021_b_pu_avail_from_date,
                pu_PickUp_Avail_Time_Hours=header.b_022_b_pu_avail_from_time_hour,
                pu_PickUp_Avail_Time_Minutes=header.b_023_b_pu_avail_from_time_minute,
                pu_PickUp_By_Date=header.b_024_b_pu_by_date,
                pu_PickUp_By_Time_Hours=header.b_025_b_pu_by_time_hour,
                pu_PickUp_By_Time_Minutes=header.b_026_b_pu_by_time_minute,
                pu_Address_Type=sliceString(header.b_027_b_pu_address_type, 25),
                pu_Address_Street_1=sliceString(header.b_029_b_pu_address_street_1, 30),
                pu_Address_street_2=sliceString(header.b_030_b_pu_address_street_2, 30),
                pu_Address_State=sliceString(header.b_031_b_pu_address_state, 25),
                pu_Address_Suburb=sliceString(header.b_032_b_pu_address_suburb, 50),
                pu_Address_PostalCode=header.b_033_b_pu_address_postalcode or None,
                pu_Address_Country=sliceString(header.b_034_b_pu_address_country, 50),
                pu_Contact_F_L_Name=sliceString(
                    header.b_035_b_pu_contact_full_name, 20
                ),
                pu_email_Group=sliceString(header.b_036_b_pu_email_group, 512),
                pu_Phone_Main=sliceString(header.b_038_b_pu_phone_main, 25),
                pu_Comm_Booking_Communicate_Via=sliceString(
                    header.b_040_b_pu_communicate_via, 25
                ),
                de_to_addressed_Saved=header.pu_addressed_saved,
                b_booking_tail_lift_deliver=header.b_041_b_del_tail_lift,
                b_bookingNoOperatorDeliver=header.b_042_b_del_num_operators,
                de_to_Pick_Up_Instructions_Contact=sliceString(
                    header.b_043_b_del_instructions_contact, 512
                ),
                de_to_PickUp_Instructions_Address=sliceString(
                    header.b_044_b_del_instructions_address, 512
                ),
                de_to_WareHouse_Bay=sliceString(header.b_045_b_del_warehouse_bay, 25),
                de_to_WareHouse_Number=sliceString(
                    header.b_046_b_del_warehouse_number, 30
                ),
                de_Deliver_From_Date=header.b_047_b_del_avail_from_date,
                de_Deliver_From_Hours=header.b_048_b_del_avail_from_time_hour,
                de_Deliver_By_Minutes=header.b_049_b_del_avail_from_time_minute,
                de_To_AddressType=sliceString(header.b_053_b_del_address_type, 20),
                deToCompanyName=sliceString(de_company, 40),
                de_To_Address_Street_1=sliceString(de_street_1, 40),
                de_To_Address_Street_2=sliceString(de_street_2, 40),
                de_To_Address_State=sliceString(header.b_057_b_del_address_state, 20),
                de_To_Address_Suburb=sliceString(header.b_058_b_del_address_suburb, 50),
                de_To_Address_PostalCode=header.b_059_b_del_address_postalcode,
                de_To_Address_Country=sliceString(
                    header.b_060_b_del_address_country, 12
                ),
                de_to_Contact_F_LName=sliceString(de_contact, 29),
                de_Email_Group_Emails=sliceString(header.b_062_b_del_email_group, 512),
                de_to_Phone_Main=sliceString(de_phone_main, 13),
                de_to_Phone_Mobile=sliceString(header.b_065_b_del_phone_mobile, 13),
                de_To_Comm_Delivery_Communicate_Via=sliceString(
                    header.b_066_b_del_communicate_via, 40
                ),
                total_1_KG_weight_override=header.total_kg,
                zb_002_client_booking_key=sliceString(
                    header.v_client_pk_consigment_num, 64
                ),
                z_CreatedTimestamp=header.z_createdTimeStamp,
                b_bookingID_Visual=id,
                fk_client_warehouse_id=header.fk_client_warehouse_id,
                kf_client_id=sliceString(header.fk_client_id, 64),
                vx_serviceName=sliceString(header.b_003_b_service_name, 50),
                b_booking_Category=sliceString(header.b_008_b_category, 64),
                b_booking_Notes=sliceString(header.b_010_b_notes, 400),
                puCompany=sliceString(header.b_028_b_pu_company, 40),
                pu_Email=sliceString(header.b_037_b_pu_email, 64),
                pu_Phone_Mobile=sliceString(header.b_039_b_pu_phone_mobile, 25),
                de_Email=sliceString(header.b_063_b_del_email, 64),
                v_service_Type=sliceString(header.vx_serviceType_XXX, 25),
                v_FPBookingNumber=sliceString(header.b_000_3_consignment_number, 40),
                b_status=sliceString(bookingStatus, 40),
                b_status_category=sliceString(bookingStatusCategory, 32),
                b_client_booking_ref_num=sliceString(header.client_booking_id, 64),
                b_client_del_note_num=sliceString(header.b_client_del_note_num, 64),
                b_client_order_num=sliceString(header.b_client_order_num, 64),
                b_client_sales_inv_num=sliceString(header.b_client_sales_inv_num, 64),
                b_client_warehouse_code=sliceString(header.b_client_warehouse_code, 64),
                b_client_name=sliceString(dme_client.company_name, 36),
                delivery_kpi_days=delivery_times.first().delivery_days
                if len(delivery_times) > 0
                else 14,
                z_api_issue_update_flag_500=1 if header.success == 2 else 0,
                x_manual_booked_flag=1 if header.success == 6 else 0,
                x_booking_Created_With=sliceString(header.x_booking_Created_With, 32),
                api_booking_quote_id=header.quote_id,
                booking_type=sliceString(header.b_092_booking_type, 4),
                vx_fp_order_id="",
                b_clientPU_Warehouse=sliceString(header.b_clientPU_Warehouse, 64),
                b_promo_code=sliceString(header.b_093_b_promo_code, 30),
                client_sales_total=header.b_094_client_sales_total,
                is_quote_locked=header.b_092_is_quote_locked,
            )
            logger.info(
                f"{LOG_ID} {booking.b_bookingID_Visual} is mapped! --- {booking.pk_booking_id}"
            )
            header.success = 1
            header.save()

            bok_lines = BOK_2_lines.objects.filter(
                success__in=[2, 4, 5], v_client_pk_consigment_num=header.pk_header_id
            )
            for line in bok_lines:
                total_cubic_meter = 0
                if line.l_004_dim_UOM.upper() == "CM":
                    total_cubic_meter = line.l_002_qty * (
                        line.l_005_dim_length
                        * line.l_006_dim_width
                        * line.l_007_dim_height
                        / 1000000
                    )
                elif line.l_004_dim_UOM.upper() in ["METER", "M"]:
                    total_cubic_meter = line.l_002_qty * (
                        line.l_005_dim_length
                        * line.l_006_dim_width
                        * line.l_007_dim_height
                    )
                else:
                    total_cubic_meter = line.l_002_qty * (
                        line.l_005_dim_length
                        * line.l_006_dim_width
                        * line.l_007_dim_height
                        / 1000000000
                    )

                total_cubic_mass = total_cubic_meter * 250
                total_weight = 0
                grams = ["g", "gram", "grams"]
                kgs = ["kilogram", "kilograms", "kg", "kgs"]
                tons = ["t", "ton", "tons"]
                if line.l_008_weight_UOM.lower() in grams:
                    total_weight = line.l_002_qty * line.l_009_weight_per_each / 1000
                elif line.l_008_weight_UOM.lower() in kgs:
                    total_weight = line.l_002_qty * line.l_009_weight_per_each
                elif line.l_008_weight_UOM.lower() in tons:
                    total_weight = line.l_002_qty * line.l_009_weight_per_each * 1000

                Booking_lines.objects.create(
                    e_spec_clientRMA_Number=sliceString(line.client_booking_id, 300),
                    e_weightPerEach=line.l_009_weight_per_each,
                    e_1_Total_dimCubicMeter=total_cubic_meter,
                    total_2_cubic_mass_factor_calc=total_cubic_mass,
                    e_Total_KG_weight=total_weight,
                    e_item=sliceString(line.l_003_item, 56),
                    e_qty=line.l_002_qty,
                    e_type_of_packaging=sliceString(line.l_001_type_of_packaging, 36),
                    e_item_type=sliceString(line.e_item_type, 64),
                    e_pallet_type=sliceString(line.e_pallet_type, 24),
                    fk_booking_id=sliceString(line.v_client_pk_consigment_num, 64),
                    e_dimLength=line.l_005_dim_length,
                    e_dimWidth=line.l_006_dim_width,
                    e_dimHeight=line.l_007_dim_height,
                    e_weightUOM=sliceString(line.l_008_weight_UOM, 56),
                    z_createdTimeStamp=line.z_createdTimeStamp,
                    e_dimUOM=sliceString(line.l_004_dim_UOM, 10),
                    client_item_reference=line.client_item_reference,
                    pk_booking_lines_id=sliceString(line.pk_booking_lines_id, 64),
                    zbl_121_integer_1=line.zbl_121_integer_1,
                    zbl_102_text_2=line.zbl_102_text_2,
                    is_deleted=0,
                    packed_status=sliceString(line.b_093_packed_status, 16),
                )
            bok_lines.update(success=1)

            bok_lines_data = BOK_3_lines_data.objects.filter(
                success__in=[2, 4, 5], v_client_pk_consigment_num=header.pk_header_id
            )
            for line_data in bok_lines_data:
                Booking_lines_data.objects.create(
                    fk_booking_id=sliceString(line_data.v_client_pk_consigment_num, 64),
                    quantity=line_data.ld_001_qty,
                    modelNumber=sliceString(line_data.ld_002_model_number, 50),
                    itemDescription=sliceString(line_data.ld_003_item_description, 200),
                    itemFaultDescription=sliceString(
                        line_data.ld_004_fault_description, 200
                    ),
                    itemSerialNumbers=sliceString(
                        line_data.ld_005_item_serial_number, 100
                    ),
                    insuranceValueEach=line_data.ld_006_insurance_value,
                    gap_ra=sliceString(line_data.ld_007_gap_ra, 300),
                    clientRefNumber=sliceString(line_data.ld_008_client_ref_number, 50),
                    z_createdByAccount=sliceString(line_data.z_createdByAccount, 64),
                    z_createdTimeStamp=line_data.z_createdTimeStamp,
                    z_modifiedByAccount=sliceString(line_data.z_modifiedByAccount, 64),
                    z_modifiedTimeStamp=line_data.z_modifiedTimeStamp,
                    fk_booking_lines_id=sliceString(line_data.fk_booking_lines_id, 64),
                )
            bok_lines_data.update(success=1)

            booking_Created_For = booking.booking_Created_For
            booking_Created_For = booking_Created_For if booking_Created_For else ""
            first_name = booking_Created_For.split(" ")[0]
            last_name = booking_Created_For.replace(first_name, "").strip()
            api_booking_quote_id = booking.api_booking_quote_id
            pk_id_dme_client = dme_client.pk_id_dme_client if dme_client else None

            if first_name == "Bathroom":
                booking.booking_Created_For_Email = "info@bathroomsalesdirect.com.au"
                booking.save()
            else:
                booking_created_for_emails = Client_employees.objects.filter(
                    fk_id_dme_client_id=pk_id_dme_client
                )

                if last_name == "":
                    booking_created_for_emails = booking_created_for_emails.filter(
                        name_first=first_name,
                        name_last__isnull=True,
                    )
                else:
                    booking_created_for_emails = booking_created_for_emails.filter(
                        name_first=last_name,
                        name_last=first_name,
                    )

                booking_created_for_emails = booking_created_for_emails.values("email")
                booking.booking_Created_For_Email = (
                    booking_created_for_emails.first()["email"][:64]
                    if len(booking_created_for_emails) > 0
                    else ""
                )
                booking.save()

            if api_booking_quote_id:
                booking_quote = API_booking_quotes.objects.filter(
                    id=booking.api_booking_quote_id
                ).first()
                booking.inv_sell_quoted = booking_quote.client_mu_1_minimum_values
                booking.inv_cost_quoted = booking_quote.fee * (
                    1 + booking_quote.mu_percentage_fuel_levy
                )
                booking.save()
    except Exception as e:
        logger.info(f"{LOG_ID} Error: {str(e)}\n Header: {header}")
        trace_error.print()
        transaction.savepoint_rollback(sid)

    return True


def sliceString(str, length):
    if str is None:
        return str
    else:
        return str[:length]
