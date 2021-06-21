from api.models import Fp_freight_providers


def set_booking_quote(booking, quote=None):
    if not quote:
        booking.api_booking_quote = None
        booking.vx_freight_provider = None
        booking.vx_account_code = None
        booking.vx_serviceName = None
        booking.inv_cost_quoted = None
        booking.inv_sell_quoted = None
        booking.s_02_Booking_Cutoff_Time = None
    else:
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
