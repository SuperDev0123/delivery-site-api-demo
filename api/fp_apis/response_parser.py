import json
import logging

logger = logging.getLogger("dme_api")

from .payload_builder import get_service_provider
from api.common import convert_price


def parse_pricing_response(response, fp_name, booking, is_from_self=False):
    try:
        if is_from_self:
            json_data = response
        else:
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)

        results = []
        if fp_name == "hunter" and json_data["price"]:  # Hunter
            for price in json_data["price"]:
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
        elif fp_name == "tnt" and json_data["price"]:  # TNT
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
        elif fp_name == "sendle" and json_data["price"]:  # Sendle
            for price in json_data["price"]:
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
        elif fp_name == "capital" and json_data["price"]:  # Capital
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
        elif fp_name == "startrack" and json_data["price"]:  # Startrack
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
        # Built-in: Century, Camerons
        elif fp_name in ["century", "camerons", "toll"] and json_data["price"]:
            for price in json_data["price"]:
                result = {}
                print
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
        logger.error(error_msg)
        return None
