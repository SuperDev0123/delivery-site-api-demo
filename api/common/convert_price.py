import collections
from api.models import DME_clients, Fp_freight_providers


def fp_price_2_dme_price(api_booking_quote):
    fp_name = api_booking_quote["fk_freight_provider_id"]
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name.lower())
    client = DME_clients.objects.get(
        company_name__iexact=api_booking_quote["fk_client_id"].lower()
    )

    fp_mu_val = float(api_booking_quote["fee"]) * (1 + fp.fp_markupfuel_levy_percent)
    client_mu_val = fp_mu_val * (1 + client.client_mark_up_percent)
    client_mu_min_val = fp_mu_val + client.client_min_markup_value

    if float(api_booking_quote["fee"]) > client.client_min_markup_startingcostvalue:
        return client_mu_val, fp.fp_markupfuel_levy_percent

    greater = client_mu_val if client_mu_val > client_mu_min_val else client_mu_min_val

    if fp_mu_val < client.client_min_markup_startingcostvalue:
        return client_mu_val, fp.fp_markupfuel_levy_percent
    else:
        return greater, fp.fp_markupfuel_levy_percent
