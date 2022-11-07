import logging
from datetime import datetime
from pydash import _
from django.db.models import Count, Aggregate, CharField

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (    
    IsAuthenticated,
)
from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from api.serializers import *
from api.models import *
from api.base.viewsets import *

logger = logging.getLogger(__name__)

class GroupConcat(Aggregate):
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s%(ordering)s%(separator)s)'

    def __init__(self, expression, distinct=False, ordering=None, separator=',', **extra):
        super(GroupConcat, self).__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            ordering=' ORDER BY %s' % ordering if ordering is not None else '',
            separator=' SEPARATOR "%s"' % separator,
            output_field=CharField(),
            **extra
        )

@api_view(["POST"])
@permission_classes((IsAuthenticated,))
def mapBokToBooking(request):
    LOG_ID = "[MAPPING]"
    
    try:
        option_value = DME_Options.objects.get(option_name='MoveSuccess2ToBookings')
        run_time = (datetime.now().replace(tzinfo=None) - option_value.start_time.replace(tzinfo=None)).seconds
        message = ''
        if not option_value.is_running or run_time > 0:
            option_value.is_running = 1
            option_value.start_time = datetime.now()
            option_value.save()
            max_id = Bookings.objects.filter().aggregate(max_id=Max('id')).get('max_id')
            max_id = max_id if max_id else 89600
            start_id = max_id + 1
            bok_headers = BOK_1_headers.objects.filter(success__in=[2,4,5])        
            headers_count = len(bok_headers)
            end_id = start_id + headers_count - 1
            
            if headers_count > 0:
                for idx, header in enumerate(bok_headers):
                    bookingStatus = ''
                    bookingStatusCategory = ''
                    if header.success == 2:
                        if header.b_000_3_consignment_number:
                            bookingStatus = 'Booked'
                            bookingStatusCategory = 'Booked'
                        else:
                            bookingStatus = 'Ready for booking'
                            bookingStatusCategory = 'Pre Booking'
                    elif header.success == 4:
                        bookingStatus = 'Picking'
                        bookingStatusCategory = 'Pre Booking'
                    elif header.success == 5:
                        bookingStatus = 'Imported / Integrated'
                        bookingStatusCategory = 'Pre Booking'
                    
                    dme_client = DME_clients.objects.filter(dme_account_num=header.fk_client_id).first()
                    delivery_time = Utl_fp_delivery_times.objects.filter(fp_name=header.b_001_b_freight_provider, postal_code_from__lte = header.b_059_b_del_address_postalcode, postal_code_to__gte = header.b_059_b_del_address_postalcode)
                    
                    Bookings.objects.create(
                        pk_booking_id = header.pk_header_id,
                        b_clientReference_RA_Numbers = header.b_000_1_b_clientReference_RA_Numbers,
                        total_lines_qty_override = header.b_000_b_total_lines,
                        vx_freight_provider = header.b_001_b_freight_provider,
                        v_vehicle_Type = header.b_002_b_vehicle_type,
                        booking_Created_For = header.b_005_b_created_for,                
                        booking_Created_For_Email = header.b_006_b_created_for_email,                
                        x_ReadyStatus = header.b_007_b_ready_status,                
                        b_booking_Priority = header.b_009_b_priority,                
                        b_handling_Instructions = header.b_014_b_pu_handling_instructions,                
                        pu_PickUp_Instructions_Contact = header.b_015_b_pu_instructions_contact,                
                        pu_pickup_instructions_address = header.b_016_b_pu_instructions_address,                
                        pu_WareHouse_Number = header.b_017_b_pu_warehouse_num,                
                        pu_WareHouse_Bay = header.b_018_b_pu_warehouse_bay,                
                        b_booking_tail_lift_pickup = header.b_019_b_pu_tail_lift,                
                        b_booking_no_operator_pickup = header.b_020_b_pu_num_operators,                
                        puPickUpAvailFrom_Date = header.b_021_b_pu_avail_from_date,                
                        pu_PickUp_Avail_Time_Hours = header.b_022_b_pu_avail_from_time_hour,                
                        pu_PickUp_Avail_Time_Minutes = header.b_023_b_pu_avail_from_time_minute,                
                        pu_PickUp_By_Date = header.b_024_b_pu_by_date,                
                        pu_PickUp_By_Time_Hours = header.b_025_b_pu_by_time_hour,                
                        pu_PickUp_By_Time_Minutes = header.b_026_b_pu_by_time_minute,                
                        pu_Address_Type = header.b_027_b_pu_address_type,                
                        pu_Address_Street_1 = header.b_029_b_pu_address_street_1,                
                        pu_Address_street_2 = header.b_030_b_pu_address_street_2,                
                        pu_Address_State = header.b_031_b_pu_address_state,                
                        pu_Address_Suburb = header.b_032_b_pu_address_suburb,                
                        pu_Address_PostalCode = header.b_033_b_pu_address_postalcode,                
                        pu_Address_Country = header.b_034_b_pu_address_country,                
                        pu_Contact_F_L_Name = header.b_035_b_pu_contact_full_name,                
                        pu_email_Group = header.b_036_b_pu_email_group,                
                        pu_Phone_Main = header.b_038_b_pu_phone_main,                
                        pu_Comm_Booking_Communicate_Via = header.b_040_b_pu_communicate_via,                
                        de_to_addressed_Saved = header.pu_addressed_saved,                
                        b_booking_tail_lift_deliver = header.b_041_b_del_tail_lift,                
                        b_bookingNoOperatorDeliver = header.b_042_b_del_num_operators,                
                        de_to_Pick_Up_Instructions_Contact = header.b_043_b_del_instructions_contact,                
                        de_to_PickUp_Instructions_Address = header.b_044_b_del_instructions_address,                
                        de_to_WareHouse_Bay = header.b_045_b_del_warehouse_bay,                
                        de_to_WareHouse_Number = header.b_046_b_del_warehouse_number,                
                        de_Deliver_From_Date = header.b_047_b_del_avail_from_date,                
                        de_Deliver_From_Hours = header.b_048_b_del_avail_from_time_hour,                
                        de_Deliver_By_Minutes = header.b_049_b_del_avail_from_time_minute,                
                        de_To_AddressType = header.b_053_b_del_address_type,                
                        deToCompanyName = header.b_054_b_del_company,                
                        de_To_Address_Street_1 = header.b_055_b_del_address_street_1,                
                        de_To_Address_Street_2 = header.b_056_b_del_address_street_2,                
                        de_To_Address_State = header.b_057_b_del_address_state,                
                        de_To_Address_Suburb = header.b_058_b_del_address_suburb,                
                        de_To_Address_PostalCode = header.b_059_b_del_address_postalcode,                
                        de_To_Address_Country = header.b_060_b_del_address_country,                
                        de_to_Contact_F_LName = header.b_061_b_del_contact_full_name,                
                        de_Email_Group_Emails = header.b_062_b_del_email_group,                
                        de_to_Phone_Main = header.b_064_b_del_phone_main,                
                        de_to_Phone_Mobile = header.b_065_b_del_phone_mobile,                
                        de_To_Comm_Delivery_Communicate_Via = header.b_066_b_del_communicate_via,                
                        total_1_KG_weight_override = header.total_kg,                
                        zb_002_client_booking_key = header.v_client_pk_consigment_num,                
                        z_CreatedTimestamp = header.z_createdTimeStamp,                
                        b_bookingID_Visual = start_id + idx,
                        fk_client_warehouse_id = header.fk_client_warehouse_id,                
                        kf_client_id = header.fk_client_id,                
                        vx_serviceName = header.b_003_b_service_name,                
                        b_booking_Category = header.b_008_b_category,                
                        b_booking_Notes = header.b_010_b_notes,                
                        puCompany = header.b_028_b_pu_company,                
                        pu_Email = header.b_037_b_pu_email,                
                        pu_Phone_Mobile = header.b_039_b_pu_phone_mobile,                
                        de_Email = header.b_063_b_del_email,                
                        v_service_Type = header.vx_serviceType_XXX,                
                        v_FPBookingNumber = header.b_000_3_consignment_number,                
                        b_status = bookingStatus,
                        b_status_category = bookingStatusCategory,
                        b_client_booking_ref_num = header.client_booking_id,
                        b_client_del_note_num = header.b_client_del_note_num,
                        b_client_order_num = header.b_client_order_num,
                        b_client_sales_inv_num = header.b_client_sales_inv_num,
                        b_client_warehouse_code = header.b_client_warehouse_code,
                        b_client_name = dme_client.company_name,
                        delivery_kpi_days = delivery_time.first().delivery_days if len(delivery_time) > 0 else 14,
                        z_api_issue_update_flag_500 = 1 if header.success == 2 else 0,
                        x_manual_booked_flag = 1 if header.success == 6 else 0,
                        x_booking_Created_With = header.x_booking_Created_With,
                        api_booking_quote_id = header.quote_id,
                        booking_type = header.b_092_booking_type,
                        vx_fp_order_id = '',
                        b_clientPU_Warehouse = header.b_clientPU_Warehouse,
                        b_promo_code = header.b_093_b_promo_code,
                        client_sales_total = header.b_094_client_sales_total,
                        is_quote_locked = header.b_092_is_quote_locked,
                    )
                message += f"Rows moved to dme_bookings = {headers_count}"
            
            pre_data = list(Bookings.objects.filter(b_bookingID_Visual__gte=start_id, b_bookingID_Visual__lte=end_id).values_list('kf_client_id', 'b_client_sales_inv_num'))
            kf_client_id_list = []
            b_client_sales_inv_num_list = []
            for data in pre_data:
                kf_client_id_list.append(data[0])
                b_client_sales_inv_num_list.append(data[1])
            error_bookings_1 = Bookings.objects.filter(b_bookingID_Visual__gt=start_id, kf_client_id__isnull=False, b_client_sales_inv_num__isnull=False, b_client_sales_inv_num__regex = r'.{0}.*', kf_client_id__in=kf_client_id_list, b_client_sales_inv_num__in=b_client_sales_inv_num_list).exclude(b_status__in=['Cancelled', 'Closed']).values('kf_client_id', 'b_client_sales_inv_num').annotate(id=Max('id'), b_bookingID_Visual_List=GroupConcat('b_bookingID_Visual', separator=', '))
            error_bookings_2 = Bookings.objects.filter(b_bookingID_Visual__gte=start_id, b_bookingID_Visual__lte=end_id, kf_client_id__isnull=False, b_client_sales_inv_num__isnull=False, b_client_sales_inv_num__regex = r'.{0}.*').values('kf_client_id', 'b_client_sales_inv_num').annotate(id=Max('id'), ctn=Count('*'), b_bookingID_Visual_List=GroupConcat('b_bookingID_Visual', separator=', ')).filter(ctn__gt=1)
            error_bookings = list(error_bookings_1) + list(error_bookings_2)
            for booking in error_bookings:
                Bookings.objects.filter(id=booking["id"]).update(b_error_Capture=('SINV is duplicated in bookingID = ' + booking['b_bookingID_Visual_List']), b_status='On Hold')
            
            bok_lines = BOK_2_lines.objects.filter(success__in=[2,4,5])
            
            lines_count = len(bok_lines)
            for line in bok_lines:
                total_cubic_meter = 0
                if line.l_004_dim_UOM.upper() == "CM":
                    total_cubic_meter = line.l_002_qty * (line.l_005_dim_length * line.l_006_dim_width * line.l_007_dim_height / 1000000)
                elif line.l_004_dim_UOM.upper() in ["METER", "M"]:
                    total_cubic_meter = line.l_002_qty * (line.l_005_dim_length * line.l_006_dim_width * line.l_007_dim_height)
                else:
                    total_cubic_meter = line.l_002_qty * (line.l_005_dim_length * line.l_006_dim_width * line.l_007_dim_height / 1000000000)                
                total_cubic_mass = total_cubic_meter * 250
                total_weight = 0
                if line.l_008_weight_UOM.lower() in ["g", "gram", "grams"]:
                    total_weight = line.l_002_qty * line.l_009_weight_per_each / 1000
                elif line.l_008_weight_UOM.lower() in ["kilogram", "kilograms", "kg", "kgs"]:
                    total_weight = line.l_002_qty * line.l_009_weight_per_each
                elif line.l_008_weight_UOM.lower() in ["t", "ton", "tons"]:
                    total_weight = line.l_002_qty * line.l_009_weight_per_each * 1000
                Booking_lines.objects.create(
                    e_spec_clientRMA_Number=line.client_booking_id,
                    e_weightPerEach=line.l_009_weight_per_each,
                    e_1_Total_dimCubicMeter=total_cubic_meter,
                    total_2_cubic_mass_factor_calc=total_cubic_mass,
                    e_Total_KG_weight=total_weight,
                    e_item=line.l_003_item,
                    e_qty=line.l_002_qty,
                    e_type_of_packaging=line.l_001_type_of_packaging,
                    e_item_type=line.e_item_type,
                    e_pallet_type=line.e_pallet_type,
                    fk_booking_id=line.v_client_pk_consigment_num,
                    e_dimLength=line.l_005_dim_length,
                    e_dimWidth=line.l_006_dim_width,
                    e_dimHeight=line.l_007_dim_height,
                    e_weightUOM=line.l_008_weight_UOM,
                    z_createdTimeStamp=line.z_createdTimeStamp,
                    e_dimUOM=line.l_004_dim_UOM,
                    client_item_reference=line.client_item_reference,
                    pk_booking_lines_id=line.pk_booking_lines_id,
                    zbl_121_integer_1=line.zbl_121_integer_1,
                    zbl_102_text_2=line.zbl_102_text_2,
                    is_deleted=0,
                    packed_status=line.b_093_packed_status,
                )
                message += f"Rows moved to dme_booking_lines = {lines_count}"
            BOK_2_lines.objects.filter(success__in=[2,4,5]).update(success=1)
            
            bok_lines_data = BOK_3_lines_data.objects.filter(success__in=[2,4,5])
            
            line_data_count = len(bok_lines_data)
            for line_data in bok_lines_data:
                Booking_lines_data.objects.create(
                    fk_booking_id=line_data.v_client_pk_consigment_num,
                    quantity=line_data.ld_001_qty,
                    modelNumber=line_data.ld_002_model_number,
                    itemDescription=line_data.ld_003_item_description,
                    itemFaultDescription=line_data.ld_004_fault_description,
                    itemSerialNumbers=line_data.ld_005_item_serial_number,
                    insuranceValueEach=line_data.ld_006_insurance_value,
                    gap_ra=line_data.ld_007_gap_ra,
                    clientRefNumber=line_data.ld_008_client_ref_number,
                    z_createdByAccount=line_data.z_createdByAccount,
                    z_createdTimeStamp=line_data.z_createdTimeStamp,
                    z_modifiedByAccount=line_data.z_modifiedByAccount,
                    z_modifiedTimeStamp=line_data.z_modifiedTimeStamp,
                    fk_booking_lines_id=line_data.fk_booking_lines_id,
                )
                message += f"Rows moved to dme_booking_lines_data = {line_data_count}"
            BOK_3_lines_data.objects.filter(success__in=[2,4,5]).update(success=1)
            
            bookingID_Visual = start_id
            while bookingID_Visual <= end_id:
                booking = Bookings.objects.filter(b_bookingID_Visual=bookingID_Visual)
                
                if(len(booking) > 0):
                    booking = booking[0]
                    dme_client = DME_clients.objects.filter(company_name=booking.b_client_name, dme_account_num=booking.kf_client_id).first()
                    booking_Created_For = booking.booking_Created_For
                    booking_Created_For = booking_Created_For if booking_Created_For else '' 
                    first_name = booking_Created_For.split(" ")[0]
                    last_name = booking_Created_For.replace(first_name, '').strip()
                    api_booking_quote_id = booking.api_booking_quote_id
                    pk_id_dme_client = dme_client.pk_id_dme_client if dme_client else None
                    if first_name == 'Bathroom':
                        booking.booking_Created_For_Email = "info@bathroomsalesdirect.com.au"
                        booking.save()
                    else:
                        booking_created_for_email = ''
                        if last_name == '':
                            booking_created_for_email = Client_employees.objects.filter(name_first=first_name, name_last__isnull=True, fk_id_dme_client_id=pk_id_dme_client).values_list("email")
                        else:
                            booking_created_for_email = Client_employees.objects.filter(name_first=last_name, name_last=first_name, fk_id_dme_client_id=pk_id_dme_client).values_list("email")
                        booking.booking_Created_For_Email = booking_created_for_email[0].email if len(booking_created_for_email) > 0 else ''
                        booking.save()                    
                    if api_booking_quote_id:
                        booking_quote = API_booking_quotes.objects.filter(id=booking.api_booking_quote_id).first()
                        booking.inv_sell_quoted = booking_quote.client_mu_1_minimum_values
                        booking.inv_cost_quoted = booking_quote.fee * (1 + booking_quote.mu_percentage_fuel_levy)
                        booking.save()
                bookingID_Visual += 1
            option_value.is_running = 0
            option_value.end_time = datetime.now()
            option_value.save()
        else:
            message += 'Procedure MoveSuccess2ToBookings is already running.'
        logger.info(f"{LOG_ID} Result: {str(e)}")
        return Response(message, status=status.HTTP_200_OK)        
    except Exception as e:
            logger.info(f"{LOG_ID} Error: {str(e)}")
            return Response(e.message, status=status.HTTP_400_BAD_REQUEST)