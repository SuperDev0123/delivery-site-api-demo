import logging
from datetime import datetime

from django.conf import settings

from api.models import *
from api.common import ratio
from .constants import FP_UOM

logger = logging.getLogger("dme_api")


def _convert_UOM(value, uom, type, fp_name):
    try:
        converted_value = value * ratio.get_ratio(uom, FP_UOM[fp_name][type], type)
        return round(converted_value, 2)
    except Exception as e:
        raise Exception(
            f"#408 Error: value: {value}, uom: {uom}, type: {type}, standard_uom: {FP_UOM[fp_name][type]}"
        )
        logger.info(
            f"#408 Error: value: {value}, uom: {uom}, type: {type}, standard_uom: {FP_UOM[fp_name][type]}"
        )


def gen_consignment_num(booking_visual_id, prefix_len, digit_len):
    limiter = "1"

    for i in range(digit_len):
        limiter += "0"

    limiter = int(limiter)

    prefix_index = int(booking_visual_id / limiter) + 1
    prefix = chr(int((prefix_index - 1) / 26) + 65) + chr(
        ((prefix_index - 1) % 26) + 65
    )

    return prefix + str(booking_visual_id)[-digit_len:].zfill(digit_len)


def get_dme_status_from_fp_status(fp_name, b_status_API, booking=None):
    try:
        status_info = Dme_utl_fp_statuses.objects.get(
            fp_name__iexact=fp_name, fp_lookup_status=b_status_API
        )
        return status_info.dme_status
    except Dme_utl_fp_statuses.DoesNotExist:
        logger.info(f"#818 New FP status: {b_status_API}")

        if booking:
            booking.b_errorCapture = f"New FP status: {booking.b_status_API}"
            booking.save()
        return None


def get_status_category_from_status(status):
    try:
        utl_dme_status = Utl_dme_status.objects.get(dme_delivery_status=status)
        return utl_dme_status.dme_delivery_status_category
    except Exception as e:
        logger.info(f"#819 Status Category not found!: {status}")
        # print('Exception: ', e)
        return ""


def get_account_code_key(booking, fp_name):
    from .payload_builder import ACCOUNT_CODES

    # Exceptional case for Bunnings
    if (
        "SWYTEMPBUN" in booking.fk_client_warehouse.client_warehouse_code
        and fp_name.lower() == "hunter"
    ):
        if booking.pu_Address_State == "QLD":
            return "live_bunnings_0"
        elif booking.pu_Address_State == "NSW":
            return "live_bunnings_1"
        else:
            booking.b_errorCapture = f"Not supported State"
            booking.save()
            return None

    if fp_name.lower() not in ACCOUNT_CODES:
        booking.b_errorCapture = f"Not supported FP"
        booking.save()
        return None
    elif booking.api_booking_quote:
        account_code = booking.api_booking_quote.account_code
        account_code_key = None

        for key in ACCOUNT_CODES[fp_name.lower()]:
            if ACCOUNT_CODES[fp_name.lower()][key] == account_code:
                account_code_key = key
                return account_code_key

        if not account_code_key:
            booking.b_errorCapture = f"Not supported ACCOUNT CODE"
            booking.save()
            return None
    elif not booking.api_booking_quote:
        return "live_0"


# Get ETD of Pricing in `hours` unit
def get_etd_in_hour(pricing):
    fp = Fp_freight_providers.objects.get(
        fp_company_name__iexact=pricing.fk_freight_provider_id
    )

    if fp.fp_company_name.lower() == "tnt":
        return float(pricing.etd) * 24

    try:
        etd = FP_Service_ETDs.objects.get(
            freight_provider_id=fp.id,
            fp_delivery_time_description=pricing.etd,
            fp_delivery_service_code=pricing.service_name,
        )
        return etd.fp_03_delivery_hours
    except Exception as e:
        logger.info(
            f"#810 Missing ETD - {fp.fp_company_name}({fp.id}), {pricing.service_name}, {pricing.etd}"
        )
        return None


def _is_deliverable_price(pricing, booking):
    if booking.pu_PickUp_By_Date and booking.de_Deliver_By_Date:
        timeDelta = booking.de_Deliver_By_Date - booking.puPickUpAvailFrom_Date
        delta_min = 0

        if booking.de_Deliver_By_Hours:
            delta_min += booking.de_Deliver_By_Hours * 60
        if booking.de_Deliver_By_Minutes:
            delta_min += booking.de_Deliver_By_Minutes
        if booking.pu_PickUp_By_Time_Hours:
            delta_min -= booking.pu_PickUp_By_Time_Hours * 60
        if booking.pu_PickUp_By_Time_Minutes:
            delta_min -= pu_PickUp_By_Time_Minutes

        delta_min = timeDelta.total_seconds() / 60 + delta_min
        eta = get_etd_in_hour(pricing)

        if not eta:
            return False
        elif delta_min > eta * 60:
            return True
    else:
        return False


# ######################## #
#       Fastest ($$$)      #
# ######################## #
def _get_fastest_price(pricings):
    fastest_pricing = {}
    for pricing in pricings:
        etd = get_etd_in_hour(pricing)

        if not fastest_pricing:
            fastest_pricing["pricing"] = pricing
            fastest_pricing["etd_in_hour"] = etd
        elif etd and fastest_pricing and fastest_pricing["etd_in_hour"]:
            if fastest_pricing["etd_in_hour"] > etd:
                fastest_pricing["pricing"] = pricing
                fastest_pricing["etd_in_hour"] = etd
            elif (
                fastest_pricing["etd_in_hour"] == etd
                and fastest_pricing["pricing"].fee > pricing.fee
            ):
                fastest_pricing["pricing"] = pricing

    return fastest_pricing["pricing"]


# ######################## #
#        Lowest ($$$)      #
# ######################## #
def _get_lowest_price(pricings):
    lowest_pricing = {}
    for pricing in pricings:
        if not lowest_pricing:
            lowest_pricing["pricing"] = pricing
        elif lowest_pricing and pricing.fee:
            if float(lowest_pricing["pricing"].fee) > float(pricing.fee):
                lowest_pricing["pricing"] = pricing
                lowest_pricing["etd"] = get_etd_in_hour(pricing)
            elif float(lowest_pricing["pricing"].fee) == float(pricing.fee):
                etd = get_etd_in_hour(pricing)

                if lowest_pricing["etd"] > etd:
                    lowest_pricing["pricing"] = pricing
                    lowest_pricing["etd"] = pricing

    return lowest_pricing["pricing"]


def select_best_options(pricings):
    logger.info(f"#860 Select best options from {len(pricings)} pricings")

    if not pricings:
        return []

    lowest_pricing = _get_lowest_price(pricings)
    fastest_pricing = _get_fastest_price(pricings)

    if lowest_pricing.pk == fastest_pricing.pk:
        return [lowest_pricing]
    else:
        return [fastest_pricing, lowest_pricing]


def auto_select_pricing(booking, pricings, auto_select_type):
    if len(pricings) == 0:
        booking.b_errorCapture = "No Freight Provider is available"
        booking.save()
        return None

    non_air_freight_pricings = []
    for pricing in pricings:
        if not pricing.service_name or (
            pricing.service_name and pricing.service_name != "Air Freight"
        ):
            non_air_freight_pricings.append(pricing)

    # Check booking.pu_PickUp_By_Date and booking.de_Deliver_By_Date and Pricings etd
    deliverable_pricings = []
    for pricing in non_air_freight_pricings:
        if _is_deliverable_price(pricing, booking):
            deliverable_pricings.append(pricing)

    filtered_pricing = {}
    if int(auto_select_type) == 1:  # Lowest
        if deliverable_pricings:
            filtered_pricing = _get_lowest_price(deliverable_pricings)
        elif non_air_freight_pricings:
            filtered_pricing = _get_lowest_price(non_air_freight_pricings)
    else:  # Fastest
        if deliverable_pricings:
            filtered_pricing = _get_fastest_price(deliverable_pricings)
        elif non_air_freight_pricings:
            filtered_pricing = _get_fastest_price(non_air_freight_pricings)

    if filtered_pricing:
        logger.info(f"#854 Filtered Pricing - {filtered_pricing}")
        booking.api_booking_quote = filtered_pricing
        booking.vx_freight_provider = filtered_pricing.fk_freight_provider_id
        booking.vx_account_code = filtered_pricing.account_code
        booking.vx_serviceName = filtered_pricing.service_name
        booking.inv_cost_quoted = filtered_pricing.fee * (
            1 + filtered_pricing.mu_percentage_fuel_levy
        )
        booking.inv_sell_quoted = filtered_pricing.client_mu_1_minimum_values

        fp = Fp_freight_providers.objects.get(
            fp_company_name__iexact=filtered_pricing.fk_freight_provider_id
        )

        if fp and fp.service_cutoff_time:
            booking.s_02_Booking_Cutoff_Time = fp.service_cutoff_time
        else:
            booking.s_02_Booking_Cutoff_Time = "12:00:00"

        booking.save()
        return True
    else:
        logger.info("#855 - Could not find proper pricing")
        return False
