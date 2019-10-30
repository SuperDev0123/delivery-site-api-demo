import collections
from api.models import DME_clients, Fp_freight_providers


def fp_price_2_dme_price(api_booking_quotes):
    new_booking_quotes = []
    for booking_quote in api_booking_quotes:
        json_booking_quote = dict(booking_quote)
        fp_name = json_booking_quote["fk_freight_provider_id"]
        fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name.lower())
        client = DME_clients.objects.get(
            company_name__iexact=json_booking_quote["fk_client_id"].lower()
        )

        dme_price = float(
            json_booking_quote["fee"]
        ) * fp.fp_markupfuel_levy_percent + float(json_booking_quote["fee"])
        mu_percentage_total = dme_price * client.client_mark_up_percent + dme_price
        min_mu_total = dme_price + client.client_min_markup_value

        greater = (
            mu_percentage_total if mu_percentage_total > min_mu_total else min_mu_total
        )
        dme_price = (
            mu_percentage_total
            if dme_price < client.client_min_markup_startingcostvalue
            else greater
        )

        json_booking_quote["fee"] = dme_price
        new_booking_quotes.append(collections.OrderedDict(json_booking_quote))

    return new_booking_quotes
