import json


def parse_pricing_response(response, fp_name, booking):
    res_content = response.content.decode("utf8").replace("'", '"')
    json_data = json.loads(res_content)
    results = []

    try:
        if fp_name == "hunter" and json_data["price"]:
            for price in json_data["price"]:
                result = {}
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = booking.b_client_name
                result["fk_freight_provider_id"] = json_data["serviceProvider"].upper()
                result["etd"] = price["etd"]
                result["fee"] = price["netPrice"]
                result["service_name"] = price["serviceName"]
                result["service_code"] = price["serviceType"]
                result["tax_id_1"] = price["totalTaxes"]["id"]
                result["tax_value_1"] = price["totalTaxes"]["value"]
                results.append(result)
        elif fp_name == "tnt" and json_data["price"]:
            for price in json_data["price"]:
                result = {}
                result["api_results_id"] = json_data["requestId"]
                result["fk_booking_id"] = booking.pk_booking_id
                result["fk_client_id"] = booking.b_client_name
                result["fk_freight_provider_id"] = json_data["serviceProvider"].upper()
                result["fee"] = price["netPrice"]
                result["service_name"] = price["serviceType"]
                results.append(result)
        return results
    except Exception as e:
        error_msg = f"Error while parse Pricing response: {e}"
        print(error_msg)
        return {"error": error_msg}
