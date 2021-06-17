import json
import logging

from django.conf import settings

from api.fp_apis.payload_builder import get_service_provider
from api.common import trace_error
from api.models import DME_clients, Fp_freight_providers, DME_Error

logger = logging.getLogger(__name__)


def parse_pricing_response(
    response,
    fp_name,
    booking,
    is_from_self=False,
    service_name=None,
    account_code="DME",
):
    try:
        if is_from_self:
            json_data = response
        else:
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)

        dme_client = DME_clients.objects.get(dme_account_num=booking.kf_client_id)

        results = []
        if fp_name == "hunter" and "price" in json_data:  # Hunter
            for price in json_data["price"]:
                # Exclude "Air Freight" service on PROD
                if (
                    settings.ENV in ["prod", "dev"]
                    and price["serviceName"] == "Air Freight"
                ):
                    continue

                result = {}
                result["account_code"] = account_code
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = dme_client.company_name
                result["freight_provider"] = get_service_provider(fp_name, False)
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
                result["account_code"] = account_code
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = dme_client.company_name
                result["freight_provider"] = get_service_provider(fp_name, False)
                result["etd"] = price["etd"] if "etd" in price else None
                result["fee"] = price["netPrice"]
                result["service_name"] = price["serviceType"]
                result["service_code"] = price["rateCode"]
                results.append(result)
        elif fp_name == "sendle" and "price" in json_data:  # Sendle
            for price in json_data["price"]:
                # Exclude "Premium" and "Easy" service on PROD
                if settings.ENV == "prod" and (
                    price["plan_name"] == "Premium" or price["plan_name"] == "Easy"
                ):
                    continue

                result = {}
                result["account_code"] = account_code
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = dme_client.company_name
                result["freight_provider"] = get_service_provider(fp_name, False)
                result["fee"] = price["quote"]["net"]["amount"]
                result["tax_value_1"] = price["quote"]["tax"]["amount"]
                result["service_name"] = price["plan_name"]
                result["etd"] = ", ".join(str(x) for x in price["eta"]["days_range"])
                results.append(result)
        elif fp_name == "capital" and "price" in json_data:  # Capital
            price = json_data["price"]
            result = {}
            result["account_code"] = account_code
            result["api_results_id"] = json_data["requestId"]
            result["fk_booking_id"] = booking.pk_booking_id
            result["fk_client_id"] = dme_client.company_name
            result["freight_provider"] = get_service_provider(fp_name, False)
            result["fee"] = price["netPrice"]
            result["tax_value_1"] = price["totalTaxes"]
            result["service_name"] = (
                price["serviceName"] if "serviceName" in price else None
            )
            results.append(result)
        # Startrack | AUSPost
        elif fp_name in ["startrack", "auspost"] and "price" in json_data:
            service_code = json_data["items"][0]["product_id"]

            for price in json_data["price"]:
                result = {}
                result["account_code"] = account_code
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = dme_client.company_name
                result["freight_provider"] = get_service_provider(fp_name, False)
                result["fee"] = price["netPrice"]
                result["tax_value_1"] = price["totalTaxes"]
                result["service_code"] = service_code
                result["service_name"] = service_name
                results.append(result)
        # Allied API
        elif fp_name == "allied" and "netPrice" in json_data:
            result = {}
            result["account_code"] = account_code
            result["api_results_id"] = json_data["requestId"]
            result["fk_booking_id"] = booking.pk_booking_id
            result["fk_client_id"] = dme_client.company_name
            result["freight_provider"] = get_service_provider(fp_name, False)
            result["fee"] = json_data["netPrice"]
            result["service_name"] = "Road Express"
            result["etd"] = 3  # TODO

            # We do not get surcharge from Allied api
            result["x_price_surcharge"] = 0
            # result["x_price_surcharge"] = float(json_data["totalPrice"]) - float(
            #     json_data["netPrice"]
            # )  # set surchargeTotal
            # Extra info - should be deleted before serialized
            # result["surcharges"] = json_data["surcharges"]
            results.append(result)
        elif fp_name == "fastway" and "price" in json_data:  # fastway
            price = json_data["price"]
            result = {}
            result["account_code"] = account_code
            result["api_results_id"] = json_data["requestId"]
            result["fk_booking_id"] = booking.pk_booking_id
            result["fk_client_id"] = dme_client.company_name
            result["freight_provider"] = get_service_provider(fp_name, False)
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

        if is_from_self and "price" in json_data:  # Built-in
            for price in json_data["price"]:
                result = {}
                result["account_code"] = account_code
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = dme_client.company_name
                result["freight_provider"] = get_service_provider(fp_name.lower())
                result["fee"] = price["netPrice"]
                result["etd"] = price["etd"]
                result["tax_value_1"] = price["totalTaxes"]
                result["service_name"] = (
                    price["serviceName"] if "serviceName" in price else None
                )
                results.append(result)

        return results
    except Exception as e:
        trace_error.print()
        error_msg = f"#580 Parse pricing res: FP - {fp_name}, {json_data}"
        logger.error(error_msg)
        error_msg = f"#581 Parse pricing error: {e}"
        logger.error(error_msg)
        return None


def capture_errors(response, booking, fp_name, accountCode, is_from_self=False):
    try:
        if is_from_self:
            json_data = response
        else:
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)

        fp = Fp_freight_providers.objects.filter(
            fp_company_name__iexact=fp_name
        ).first()

        if fp_name == "hunter" and "errorMessage" in json_data:  # Hunter
            DME_Error(
                error_code=json_data["errorCode"],
                error_description=json_data["errorMessage"],
                fk_booking_id=booking.pk_booking_id,
                accountCode=accountCode,
                freight_provider=fp,
            ).save()

        elif fp_name == "tnt" and "errors" in json_data:  # TNT
            errors = json_data["errors"]
            for error in errors:
                DME_Error(
                    error_code=error["errorCode"],
                    error_description=error["errorMsg"],
                    fk_booking_id=booking.pk_booking_id,
                    accountCode=accountCode,
                    freight_provider=fp,
                ).save()

        elif fp_name == "capital" and "status" in json_data:  # Capital
            if json_data["status"] == 3:

                DME_Error(
                    error_code=json_data["status"],
                    error_description=json_data["statusDescription"],
                    fk_booking_id=booking.pk_booking_id,
                    accountCode=accountCode,
                    freight_provider=fp,
                ).save()

        if fp_name == "fastway" and "error" in json_data:  # Fastway
            DME_Error(
                error_description=json_data["error"],
                fk_booking_id=booking.pk_booking_id,
                accountCode=accountCode,
                freight_provider=fp,
            ).save()

    except Exception as e:
        trace_error.print()
        error_msg = f"#581 Error while parse Pricing response: {e}"
        logger.info(error_msg)
        return None
