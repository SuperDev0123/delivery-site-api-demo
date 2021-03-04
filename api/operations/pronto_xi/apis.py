import logging
import xml.etree.ElementTree as ET

from django.conf import settings

from api.outputs.soap import send_soap_request
from api.outputs.email import send_email
from api.models import BOK_1_headers, BOK_2_lines, Log

logger = logging.getLogger("dme_api")


# Constants
if settings.ENV in ["local", "dev"]:
    PORT = "8443"
    API_URL = f"https://jasonl-bi.prontohosted.com.au:{PORT}/pronto/rest/U01_avenue"
    USERNAME = "delme"
    PASSWORD = "Dme1234!$*"
    CUSTOMER_CODE = "3QD3D5X"


def parse_token_xml(response):
    xml_str = response.content.decode("utf-8")
    root = ET.fromstring(xml_str)
    token_ns = "token"

    return {"token": root.find(token_ns).text}


def get_token():
    logger.info("@630 [PRONTO_XI TOKEN] Start")
    url = f"{API_URL}/login"
    headers = {
        "X-Pronto-Username": USERNAME,
        "X-Pronto-Password": PASSWORD,
    }

    response = send_soap_request(url, "", headers)
    # logger.info(
    #     f"@631 - [PRONTO_XI TOKEN] response status_code: {response.status_code}, content: {response.content}"
    # )

    if response.status_code != 200:
        logger.error(f"@632 - [PRONTO_XI TOKEN] Failed")
        return False

    token = parse_token_xml(response)["token"]
    logger.info(f"@631 - [PRONTO_XI TOKEN] Finish - {token}")
    return token


def parse_order_xml(response):
    xml_str = response.content.decode("utf-8")
    root = ET.fromstring(xml_str)
    SalesOrders = root.find("{http://www.pronto.net/so/1.0.0}SalesOrders")

    if not len(SalesOrders):
        return {}

    SalesOrder = SalesOrders[0]
    order_num = SalesOrder.find("{http://www.pronto.net/so/1.0.0}SOOrderNo").text
    b_055 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}Address2").text
    b_056 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}Address3").text
    b_057 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}Address4").text
    b_058 = ""  # Not provided
    b_059 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}AddressPostcode").text
    b_060 = "Australia"
    b_061 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}AddressName").text
    b_063 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}CustomerEmail").text
    b_064 = ""  # Not provided
    b_066 = ""  # Not provided
    b_067 = ""  # Not provided
    b_068 = ""  # Not provided
    b_069 = ""  # Not provided
    b_070 = ""  # Not provided
    b_071 = ""  # Not provided

    order = {
        "b_client_order_num": order_num,
        "b_055_b_del_address_street_1": b_055,
        "b_056_b_del_address_street_2": b_056,
        "b_057_b_del_address_state": b_057,
        "b_058_b_del_address_suburb": b_058,
        "b_059_b_del_address_postalcode": b_059,
        "b_060_b_del_address_country": b_060,
        "b_061_b_del_contact_full_name": b_061,
        "b_063_b_del_email": b_063,
        "b_064_b_del_phone_main": b_064,
        "b_066_b_del_communicate_via": b_066,
        "b_067_assembly_required": b_067,
        "b_068_b_del_location": b_068,
        "b_069_b_del_floor_number": b_069,
        "b_070_b_del_floor_access_by": b_070,
        "b_071_b_del_sufficient_space": b_071,
    }

    return order


def get_order(order_num="20088"):
    logger.info("@640 [PRONTO_XI GET ORDER] Start")

    token = get_token()
    url = f"{API_URL}/api/SalesOrderGetSalesOrders"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Pronto-Token": token,
    }
    body = f'<?xml version="1.0" encoding="UTF-8" standalone="no"?> \
                <SalesOrderGetSalesOrdersRequest> \
                    <Parameters> \
                        <SOOrderNo>{order_num}</SOOrderNo> \
                    </Parameters> \
                    <RequestFields> \
                        <SalesOrders> \
                            <SalesOrder> \
                                <SOOrderNo/> \
                                <AddressName/> \
                                <DeliveryDate/> \
                                <Packages/> \
                                <Warehouse/> \
                                <CustomerEmail /> \
                                <Address1/> \
                                <Address2/> \
                                <Address3/> \
                                <Address4/> \
                                <Address5/> \
                                <Address6/> \
                                <AddressPostcode/> \
                                <SalesOrderLines> \
                                    <RequestFields> \
                                        <SalesOrderLines> \
                                            <SalesOrderLine> \
                                                <ItemCode /> \
                                                <OrderedQty /> \
                                            </SalesOrderLine> \
                                        </SalesOrderLines> \
                                    </RequestFields> \
                                </SalesOrderLines> \
                            </SalesOrder> \
                        </SalesOrders> \
                    </RequestFields> \
                </SalesOrderGetSalesOrdersRequest>'

    response = send_soap_request(url, body, headers)
    logger.info(
        f"@631 - [PRONTO_XI GET ORDER] response status_code: {response.status_code}, content: {response.content}"
    )

    if response.status_code != 200:
        logger.error(f"@632 - [PRONTO_XI GET ORDER] Failed")
        return False

    order = parse_order_xml(response)
    logger.info(f"@649 [PRONTO_XI GET ORDER] Finish order: {order}")

    return order
