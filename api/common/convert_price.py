import collections
from api.models import DME_clients, Fp_freight_providers


def fp_price_2_dme_price(api_booking_quote):
    fp_name = api_booking_quote["fk_freight_provider_id"]
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name.lower())

    try:
        client = DME_clients.objects.get(
            company_name__iexact=api_booking_quote["fk_client_id"].lower()
        )
    except:
        client = DME_clients.objects.get(company_name="Pricing-Only")

    fp_markupfuel_levy_percent = fp.fp_markupfuel_levy_percent
    client_markup_percent = client.client_markup_percent
    client_min_markup_startingcostvalue = client.client_min_markup_startingcostvalue
    client_min_markup_value = client.client_min_markup_value

    cost_fl = float(booking["inv_cost_quoted"]) * (1 + fp_markupfuel_levy_percent)

    if cost_fl < float(client_min_markup_startingcostvalue):
        quoted_dollar = cost_fl * (1 + client_markup_percent)
    else:
        cost_mu = cost_fl * client_markup_percent

        if cost_mu > client_min_markup_value:
            quoted_dollar = cost_fl + cost_mu
        else:
            quoted_dollar = cost_fl + client_min_markup_value

    return quoted_dollar, fp.fp_markupfuel_levy_percent
