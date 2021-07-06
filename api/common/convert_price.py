import logging

from api.models import DME_clients, Fp_freight_providers
from api.fp_apis.constants import FP_CREDENTIALS


logger = logging.getLogger(__name__)


def _is_used_client_credential(fp_name, client_name, account_code):
    """
    Check if used client's credential
    """

    credentials = FP_CREDENTIALS.get(fp_name)

    if not credentials:
        return False

    for _client_name in credentials:
        client_credentials = credentials[_client_name]

        for client_key in client_credentials:
            if (
                client_credentials[client_key]["accountCode"] == account_code
                and _client_name == client_name.lower()
            ):
                return True

    return False


def _apply_mu(quote, fp, client):
    """
    Convert FP price to DME price

    params:
        * quote: api_booking_quote object
    """
    logger.info(f"[FP $ -> DME $] Start quote: {quote}")

    # Apply FP MU for Quotes with DME credentials
    # if client.gap_percent:
    if _is_used_client_credential(
        quote.freight_provider, quote.fk_client_id.lower(), quote.account_code
    ):
        fp_mu = 0
    else:  # FP MU(Fuel Levy)
        fp_mu = fp.fp_markupfuel_levy_percent

    # DME will consider tax on `invoicing` stage
    # tax = quote.tax_value_1 if quote.tax_value_1 else 0

    # Deactivated 2021-06-14: Need to be considered again
    # if quote.client_mu_1_minimum_values:
    #     fuel_levy_base = quote.client_mu_1_minimum_values * fp_mu
    # else:
    #     fuel_levy_base = quote.fee * fp_mu

    fuel_levy_base = quote.fee * fp_mu
    surcharge = quote.x_price_surcharge if quote.x_price_surcharge else 0
    cost = quote.fee + fuel_levy_base + surcharge

    # Client MU
    client_mu = client.client_mark_up_percent
    client_min_markup_startingcostvalue = client.client_min_markup_startingcostvalue
    client_min = client.client_min_markup_value

    if cost > float(client_min_markup_startingcostvalue):
        quoted_dollar = cost * (1 + client_mu)
    else:
        cost_mu = cost * client_mu

        if cost_mu > client_min:
            quoted_dollar = cost + cost_mu
        else:
            quoted_dollar = cost + client_min

    logger.info(f"[FP $ -> DME $] Finish quoted $: {quoted_dollar} FP_MU: {fp_mu}")
    return quoted_dollar, fuel_levy_base, fp_mu


def apply_markups(quotes):
    logger.info(f"[APPLY MU] Start")

    if not quotes:
        logger.info(f"[APPLY MU] No Quotes!")
        return quotes

    logger.info(f"[APPLY MU] Booking.fk_booking_id: {quotes[0].fk_booking_id}")

    try:
        client_name = quotes[0].fk_client_id.lower()
        client = DME_clients.objects.get(company_name__iexact=client_name)
    except:
        # Do not apply MU(s) when doing "Pricing-Only"
        logger.info(f"[APPLY MU] Pricing only!")
        return quotes

    for quote in quotes:
        fp_name = quote.freight_provider.lower()
        fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
        client_mu_1_minimum_values, fuel_levy_base, fp_mu = _apply_mu(quote, fp, client)
        quote.client_mu_1_minimum_values = client_mu_1_minimum_values
        quote.mu_percentage_fuel_levy = fp_mu
        quote.fuel_levy_base = fuel_levy_base
        quote.client_mark_up_percent = client.client_mark_up_percent
        quote.save()

    logger.info(f"[APPLY MU] Finished")
    return quotes


def _get_lowest_client_pricing(quotes):
    """
    Get lowest pricing which used client's credential
    """

    _lowest_pricing = None

    for quote in quotes:
        fp_name = quote.freight_provider.lower()
        client_name = quote.fk_client_id.lower()
        account_code = quote.account_code

        if _is_used_client_credential(fp_name, client_name, account_code):
            if not _lowest_pricing:
                _lowest_pricing = quote
            elif _lowest_pricing.fee > quote.fee:
                _lowest_pricing = quote

    return _lowest_pricing


def interpolate_gaps(quotes):
    """
    Interpolate DME pricings if has gap with lowest client pricing

    params:
        * quotes: api_booking_quote objects array
    """
    logger.info(f"[$ INTERPOLATE] Start")

    if not quotes.exists():
        logger.info(f"[$ INTERPOLATE] No Quotes!")
        return quotes

    logger.info(f"[$ INTERPOLATE] Booking.fk_booking_id: {quotes[0].fk_booking_id}")
    fp_name = quotes[0].freight_provider.lower()
    client_name = quotes[0].fk_client_id.lower()

    try:
        client = DME_clients.objects.get(company_name__iexact=client_name)
    except:
        # Do not interpolate gaps when doing "Pricing-Only"
        logger.info(f"[$ INTERPOLATE] Pricing only!")
        return quotes

    # Do not interpolate if gap_percent is not set
    # (gap_percent is set only clients which has its FP credentials)
    if not client.gap_percent:
        logger.info(f"[$ INTERPOLATE] No gap_percent! client: {client_name.upper()}")
        return quotes

    lowest_pricing = _get_lowest_client_pricing(quotes)

    if not lowest_pricing:
        return quotes

    logger.info(
        f"[$ INTERPOLATE] Lowest Clinet quote: {lowest_pricing.pk}({lowest_pricing.fee})"
    )
    for quote in quotes:
        fp_name = quote.freight_provider.lower()
        client_name = quote.fk_client_id.lower()
        account_code = quote.account_code

        # Interpolate gaps for DME pricings only
        gap = lowest_pricing.fee - quote.fee

        # DME will consider tax on `invoicing` stage
        # if lowest_pricing.tax_value_1:
        #     gap += float(lowest_pricing.tax_value_1)

        if (
            not _is_used_client_credential(fp_name, client_name, account_code)
            and gap > 0
        ):
            logger.info(
                f"[$ INTERPOLATE] process! Quote: {quote.pk}({quote.fee}), Gap: {gap}"
            )
            quote.fee += gap * client.gap_percent
            quote.save()

    logger.info(f"[$ INTERPOLATE] Finished")
    return quotes
