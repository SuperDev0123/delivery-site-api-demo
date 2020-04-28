import json
import logging

from django.conf import settings

from .payload_builder import get_service_provider
from api.common import convert_price

logger = logging.getLogger("dme_api")


def parse_pricing_response(response, fp_name, booking, is_from_self=False):
    try:
        if is_from_self:
            json_data = response
        else:
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)

        results = []
        if fp_name == "hunter" and "price" in json_data:  # Hunter
            for price in json_data["price"]:
                # Exclude "Air Freight" service on PROD
                if settings.ENV == "prod" and price["serviceName"] == "Air Freight":
                    continue

                result = {}
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = booking.b_client_name
                result["fk_freight_provider_id"] = get_service_provider(fp_name, False)
                result["etd"] = price["etd"] if "etd" in price else None
                result["fee"] = price["netPrice"]
                result["service_name"] = (
                    price["serviceName"] if "serviceName" in price else None
                )
                result["service_code"] = price["serviceType"]
                result["tax_id_1"] = price["totalTaxes"]["id"]
                result["tax_value_1"] = price["totalTaxes"]["value"]
                results.append(result)
        elif fp_name == "tnt" and "price" in json_data:  # TNT
            for price in json_data["price"]:
                result = {}
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = booking.b_client_name
                result["fk_freight_provider_id"] = get_service_provider(fp_name, False)
                result["etd"] = price["etd"] if "etd" in price else None
                result["fee"] = price["netPrice"]
                result["service_name"] = price["serviceType"]
                results.append(result)
        elif fp_name == "sendle" and "price" in json_data:  # Sendle
            for price in json_data["price"]:
                # Exclude "Premium" and "Easy" service on PROD
                if settings.ENV == "prod" and (
                    price["plan_name"] == "Premium" or price["plan_name"] == "Easy"
                ):
                    continue

                result = {}
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = booking.b_client_name
                result["fk_freight_provider_id"] = get_service_provider(fp_name, False)
                result["fee"] = price["quote"]["net"]["amount"]
                result["tax_value_1"] = price["quote"]["tax"]["amount"]
                result["service_name"] = price["plan_name"]
                result["etd"] = ", ".join(str(x) for x in price["eta"]["days_range"])
                results.append(result)
        elif fp_name == "capital" and "price" in json_data:  # Capital
            price = json_data["price"]
            result = {}
            result["api_results_id"] = json_data["requestId"]
            result["fk_booking_id"] = booking.pk_booking_id
            result["fk_client_id"] = booking.b_client_name
            result["fk_freight_provider_id"] = get_service_provider(fp_name, False)
            result["fee"] = price["netPrice"]
            result["tax_value_1"] = price["totalTaxes"]
            result["service_name"] = (
                price["serviceName"] if "serviceName" in price else None
            )
            results.append(result)
        elif fp_name == "startrack" and "price" in json_data:  # Startrack
            for price in json_data["price"]:
                result = {}
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = booking.b_client_name
                result["fk_freight_provider_id"] = get_service_provider(fp_name, False)
                result["fee"] = price["netPrice"]
                result["tax_value_1"] = price["totalTaxes"]
                result["service_name"] = (
                    price["serviceName"] if "serviceName" in price else None
                )
                results.append(result)
        elif fp_name == "fastway" and "price" in json_data:  # fastway
            price = json_data["price"]
            result = {}
            result["api_results_id"] = json_data["requestId"]
            result["fk_booking_id"] = booking.pk_booking_id
            result["fk_client_id"] = booking.b_client_name
            result["fk_freight_provider_id"] = get_service_provider(fp_name, False)
            result["etd"] = price["delivery_timeframe_days"]

            min_fee = 0
            min_tax_value_1 = 0
            min_serviceName = ""

            for service in price["services"]:
                fee = min(
                    float(service["totalprice_normal"]),
                    float(service["totalprice_frequent"]),
                    float(service["totalprice_normal_exgst"]),
                    float(service["totalprice_frequent_exgst"]),
                )
                tax_value_1 = min(
                    float(service["excess_label_price_normal"]),
                    float(service["excess_label_price_frequent"]),
                    float(service["excess_label_price_normal_exgst"]),
                    float(service["excess_label_price_frequent_exgst"]),
                )

                if min_fee == 0:
                    min_fee = fee
                    min_serviceName = service["name"]
                else:
                    if fee < min_fee:
                        min_serviceName = service["name"]
                        min_fee = fee

                if min_tax_value_1 == 0:
                    min_tax_value_1 = tax_value_1
                else:
                    min_tax_value_1 = min(tax_value_1, min_tax_value_1)

            result["fee"] = min_fee
            result["tax_value_1"] = min_tax_value_1
            result["service_name"] = min_serviceName

            results.append(result)
        # Built-in
        elif is_from_self and "price" in json_data:
            for price in json_data["price"]:
                result = {}
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = booking.b_client_name
                result["fk_freight_provider_id"] = get_service_provider(fp_name.lower())
                result["fee"] = price["netPrice"]
                result["etd"] = price["etd"]
                result["tax_value_1"] = price["totalTaxes"]
                result["service_name"] = (
                    price["serviceName"] if "serviceName" in price else None
                )
                result["account_code"] = "DME"
                results.append(result)

        for index, result in enumerate(results):
            (
                results[index]["client_mu_1_minimum_values"],
                results[index]["mu_percentage_fuel_levy"],
            ) = convert_price.fp_price_2_dme_price(result)
        return results
    except Exception as e:
        error_msg = f"Error while parse Pricing response: {e}"
        logger.info(error_msg)
        return None
