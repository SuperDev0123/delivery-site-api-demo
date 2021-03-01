import logging

from api.models import DME_clients, Fp_freight_providers
from api.fp_apis.constants import FP_CREDENTIALS


logger = logging.getLogger("dme_api")


def _is_used_client_credential(fp_name, client_name, account_code):
    """
    Check if used client's credential
    """

    credentials = FP_CREDENTIALS[fp_name]

    for _client_name in credentials:
        client_credentials = credentials[_client_name]

        for client_key in client_credentials:
            if (
                client_credentials[client_key]["accountCode"] == account_code
                and _client_name == client_name
            ):
                return True

    return False


def fp_price_2_dme_price(quote, fp, client):
    """
    Convert FP price to DME price

    params:
        * quote: api_booking_quote object
    """

    logger.info(f"[FP $ -> DME $] Start quote: {quote}")

    # # Apply FP MU only when used DME's credential
    # if _is_used_client_credential(fp_name, client_name, quote.account_code):

    # Apply FP MU when only Client doesn't have any FP credential
    if client.gap_percent:
        fp_mu = 0
    else:  # FP Markup(Fuel Levy)
        fp_mu = fp.fp_markupfuel_levy_percent

    cost = float(quote.client_mu_1_minimum_values) * (1 + fp_mu)

    # Client Markup
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
    return quoted_dollar, fp_mu


def apply_markups(quotes):
    logger.info(f"[APPLY MU] Start")

    if not quotes.exists():
        logger.info(f"[APPLY MU] No Quotes!")
        return quotes

    logger.info(f"[APPLY MU] Booking.fk_booking_id: {quotes[0].fk_booking_id}")
    fp_name = quotes[0].freight_provider.lower()
    client_name = quotes[0].fk_client_id.lower()
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)

    try:
        client = DME_clients.objects.get(company_name__iexact=client_name)
    except:
        # Do not apply MU(s) when doing "Pricing-Only"
        logger.info(f"[APPLY MU] Pricing only!")
        return quotes

    for quote in quotes:
        client_mu_1_minimum_values, mu_percentage_fuel_levy = fp_price_2_dme_price(
            quote, fp, client
        )
        quote.client_mu_1_minimum_values = client_mu_1_minimum_values
        quote.mu_percentage_fuel_levy = mu_percentage_fuel_levy
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

    for quote in quotes:
        fp_name = quote.freight_provider.lower()
        client_name = quote.fk_client_id.lower()
        account_code = quote.account_code

        # print(
        #     "@1  ",
        #     fp_name,
        #     client_name,
        #     account_code,
        #     _is_used_client_credential(fp_name, client_name, account_code),
        #     quote.client_mu_1_minimum_values,
        #     lowest_pricing.client_mu_1_minimum_values,
        # )
        # Interpolate gaps for DME pricings only
        if (
            not _is_used_client_credential(fp_name, client_name, account_code)
            and quote.client_mu_1_minimum_values
            < lowest_pricing.client_mu_1_minimum_values
        ):
            logger.info(f"[$ INTERPOLATE] process! Quote: {quote.pk}")
            quote.client_mu_1_minimum_values *= 1 + client.gap_percent
            quote.save()

    logger.info(f"[$ INTERPOLATE] Finished")
    return quotes
