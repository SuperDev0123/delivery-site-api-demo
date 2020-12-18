from api.models import Bookings, Fp_freight_providers
from api.operations.labels import ship_it, dhl, hunter


def populate_quote_info_to_booking(booking, quote):
    booking.api_booking_quote = quote
    booking.vx_freight_provider = quote.freight_provider
    booking.vx_account_code = quote.account_code
    booking.vx_serviceName = quote.service_name
    booking.inv_cost_quoted = quote.fee * (1 + quote.mu_percentage_fuel_levy)
    booking.inv_sell_quoted = quote.client_mu_1_minimum_values

    fp = Fp_freight_providers.objects.get(
        fp_company_name__iexact=quote.freight_provider
    )

    if fp and fp.service_cutoff_time:
        booking.s_02_Booking_Cutoff_Time = fp.service_cutoff_time
    else:
        booking.s_02_Booking_Cutoff_Time = "12:00:00"

    booking.save()
    return booking


def build_label(booking, file_path, lines=[]):
    result = None
    _booking = booking

    if not booking.api_booking_quote:
        raise Exception("Booking doens't have quote.")

    if booking.vx_freight_provider:
        _booking = populate_quote_info_to_booking(booking, booking.api_booking_quote)

    fp_name = booking.api_booking_quote.freight_provider.lower()

    if fp_name == "auspost":
        result = ship_it.build_label(booking, file_path, lines)
    elif fp_name == "dhl":
        result = dhl.build_label(booking, file_path, lines)
    elif fp_name == "hunter":
        result = hunter.build_label(booking, file_path, lines)

    return result


def get_barcode(booking, booking_lines):
    if not booking.api_booking_quote:
        raise Exception("Booking doens't have quote.")

    result = None
    fp_name = booking.api_booking_quote.freight_provider.lower()

    if fp_name == "auspost":
        result = ship_it.gen_barcode(booking, booking_lines)
    # elif fp_name == "dhl":
    #     result = dhl.build_label(booking, file_path, lines)
    elif fp_name == "hunter":
        result = hunter.gen_barcode(booking, booking_lines)

    return result
