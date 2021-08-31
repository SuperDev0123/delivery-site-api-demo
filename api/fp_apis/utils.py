import logging
from datetime import datetime

from django.conf import settings

from api.models import *
from api.common import ratio
from api.common.booking_quote import set_booking_quote
from api.fp_apis.constants import FP_CREDENTIALS, FP_UOM
from api.operations.email_senders import send_email_to_admins
from api.helpers.etd import get_etd

logger = logging.getLogger(__name__)


def _convert_UOM(value, uom, type, fp_name):
    _fp_name = fp_name.lower()

    try:
        converted_value = value * ratio.get_ratio(uom, FP_UOM[_fp_name][type], type)
        return round(converted_value, 2)
    except Exception as e:
        message = f"#408 Error - FP: {_fp_name}, value: {value}, uom: {uom}, type: {type}, standard_uom: {FP_UOM[_fp_name][type]}"
        logger.info(message)
        raise Exception(message)


def gen_consignment_num(fp_name, uid):
    """
    generate consignment

    uid: can be `booking_visual_id` or `b_client_order_num`
    """

    _fp_name = fp_name.lower()

    if _fp_name == "hunter":
        digit_len = 6
        limiter = "1"

        for i in range(digit_len):
            limiter += "0"

        limiter = int(limiter)

        prefix_index = int(int(uid) / limiter) + 1
        prefix = chr(int((prefix_index - 1) / 26) + 65) + chr(
            ((prefix_index - 1) % 26) + 65
        )

        return prefix + str(uid)[-digit_len:].zfill(digit_len)
    elif _fp_name == "tnt":
        return f"DME{str(uid).zfill(9)}"
    # elif _fp_name == "century": # Deactivated
    #     return f"D_jasonl_{str(uid)}"
    else:
        return f"DME{str(uid)}"


def get_dme_status_from_fp_status(fp_name, b_status_API, booking=None):
    try:
        if fp_name.lower() == "allied":
            status_info = None
            rules = Dme_utl_fp_statuses.objects.filter(fp_name__iexact=fp_name)

            for rule in rules:
                if "XXX" in rule.fp_lookup_status:
                    fp_lookup_status = rule.fp_lookup_status.replace("XXX", "")

                    if fp_lookup_status in b_status_API:
                        status_info = rule
                elif rule.fp_lookup_status == b_status_API:
                    status_info = rule
        else:
            status_info = Dme_utl_fp_statuses.objects.get(
                fp_name__iexact=fp_name, fp_lookup_status=b_status_API
            )

        return status_info.dme_status
    except:
        return None


def get_status_category_from_status(status):
    if not status:
        return None

    try:
        utl_dme_status = Utl_dme_status.objects.get(dme_delivery_status=status)
        return utl_dme_status.dme_delivery_status_category
    except Exception as e:
        message = f"#819 Category not found with this status: {status}"
        logger.error(message)
        send_email_to_admins("Category for Status not Found", message)
        return None


def get_status_time_from_category(booking_id, category):
    if not category:
        return None

    try:
        statuses = Utl_dme_status.objects.filter(
            dme_delivery_status_category=category
        ).values_list("dme_delivery_status", flat=True)
        status_times = (
            Dme_status_history.objects.filter(
                fk_booking_id=booking_id, status_last__in=statuses
            )
            .order_by("event_time_stamp")
            .values_list("event_time_stamp", flat=True)
        )
        return status_times[0] if status_times else None
    except Exception as e:
        message = f"#819 Timestamp not found with this category: {category}"
        logger.error(message)
        send_email_to_admins("Timestamp for Category not Found", message)
        return None


# Get ETD of Pricing in `hours` unit
def get_etd_in_hour(pricing):
    try:
        # logger.info(f"[GET_ETD_IN_HOUR] {pricing.etd}")
        etd, unit = get_etd(pricing.etd)

        if unit == "Days":
            etd *= 24

        return etd
    except:
        try:
            fp = Fp_freight_providers.objects.get(
                fp_company_name__iexact=pricing.freight_provider
            )
            etd = FP_Service_ETDs.objects.get(
                freight_provider_id=fp.id,
                fp_delivery_time_description=pricing.etd,
                fp_delivery_service_code=pricing.service_name,
            )

            return etd.fp_03_delivery_hours
        except Exception as e:
            message = f"#810 [get_etd_in_hour] Missing ETD - {pricing.freight_provider}, {pricing.service_name}, {pricing.etd}"
            logger.info(message)
            # raise Exception(message)
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
            delta_min -= booking.pu_PickUp_By_Time_Minutes

        delta_min = timeDelta.total_seconds() / 60 + delta_min
        etd = get_etd_in_hour(pricing)

        if not etd:
            return False
        elif delta_min > etd * 60:
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
                etd
                and fastest_pricing["etd_in_hour"]
                and fastest_pricing["etd_in_hour"] == etd
                and fastest_pricing["pricing"].client_mu_1_minimum_values
                < pricing.client_mu_1_minimum_values
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
            lowest_pricing["etd"] = get_etd_in_hour(pricing)
        elif lowest_pricing and pricing.client_mu_1_minimum_values:
            if float(lowest_pricing["pricing"].client_mu_1_minimum_values) > float(
                pricing.client_mu_1_minimum_values
            ):
                lowest_pricing["pricing"] = pricing
                lowest_pricing["etd"] = get_etd_in_hour(pricing)
            elif float(lowest_pricing["pricing"].client_mu_1_minimum_values) == float(
                pricing.client_mu_1_minimum_values
            ):
                etd = get_etd_in_hour(pricing)

                if lowest_pricing["etd"] and etd and lowest_pricing["etd"] > etd:
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
        return [lowest_pricing, fastest_pricing]


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
        set_booking_quote(booking, filtered_pricing)
        return True
    else:
        logger.info("#855 - Could not find proper pricing")
        return False


def auto_select_pricing_4_bok(bok_1, pricings, auto_select_type=1):
    if len(pricings) == 0:
        logger.info("#855 - Could not find proper pricing")
        return None

    non_air_freight_pricings = []
    for pricing in pricings:
        if not pricing.service_name or (
            pricing.service_name and pricing.service_name != "Air Freight"
        ):
            non_air_freight_pricings.append(pricing)

    # Check booking.pu_PickUp_By_Date and booking.de_Deliver_By_Date and Pricings etd
    # deliverable_pricings = []
    # for pricing in non_air_freight_pricings:
    #     if _is_deliverable_price(pricing, booking):
    #         deliverable_pricings.append(pricing)

    deliverable_pricings = non_air_freight_pricings
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
        bok_1.quote = filtered_pricing
        bok_1.save()
        return True
    else:
        logger.info("#855 - Could not find proper pricing")
        return False
