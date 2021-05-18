import logging
import xml.etree.ElementTree as ET

from django.conf import settings

from api.outputs.soap import send_soap_request
from api.outputs.email import send_email
from api.models import BOK_1_headers, BOK_2_lines, Log

logger = logging.getLogger(__name__)


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
    logger.info("@630 [PRONTO TOKEN] Start")
    url = f"{API_URL}/login"
    headers = {
        "X-Pronto-Username": USERNAME,
        "X-Pronto-Password": PASSWORD,
    }

    response = send_soap_request(url, "", headers)
    # logger.info(
    #     f"@631 [PRONTO TOKEN] response status_code: {response.status_code}, content: {response.content}"
    # )

    if response.status_code != 200:
        logger.error(f"@632 [PRONTO TOKEN] Failed")
        return False

    token = parse_token_xml(response)["token"]
    logger.info(f"@631 [PRONTO TOKEN] Finish - {token}")
    return token


def parse_order_xml(response):
    xml_str = response.content.decode("utf-8")
    # xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n<SalesOrderGetSalesOrdersResponse xmlns="http://www.pronto.net/so/1.0.0"><APIResponseStatus><Code>OK</Code></APIResponseStatus><SalesOrders><SalesOrder><Address1></Address1><Address2>690 Ann Street</Address2><Address3>Fortitude Valley</Address3><Address4>QLD</Address4><Address5></Address5><Address6></Address6><AddressName>Roman Shrestha</AddressName><AddressPostcode>4006</AddressPostcode><CustomerEmail>dark23shadow@gmail.com</CustomerEmail><DeliveryDate>2020-01-29</DeliveryDate><Packages>1</Packages><SOOrderNo>20176</SOOrderNo><SalesOrderLines><SalesOrderLine><ItemCode>HC028</ItemCode><OrderedQty>3.0000</OrderedQty></SalesOrderLine><SalesOrderLine><ItemCode>MY-M-06.LHS</ItemCode><OrderedQty>1.0000</OrderedQty></SalesOrderLine></SalesOrderLines><Warehouse>Botany</Warehouse></SalesOrder></SalesOrders></SalesOrderGetSalesOrdersResponse>\n'
    root = ET.fromstring(xml_str)
    SalesOrders = root.find("{http://www.pronto.net/so/1.0.0}SalesOrders")

    if not len(SalesOrders):
        return {}

    SalesOrder = SalesOrders[0]
    order_num = SalesOrder.find("{http://www.pronto.net/so/1.0.0}SOOrderNo").text
    b_021 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}DeliveryDate").text
    b_055 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}Address2").text
    b_056 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}Address3").text
    b_057 = ""  # SalesOrder.find("{http://www.pronto.net/so/1.0.0}Address4").text
    b_058 = ""  # Not provided
    b_059 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}AddressPostcode").text
    b_060 = "Australia"
    b_061 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}AddressName").text
    b_063 = SalesOrder.find("{http://www.pronto.net/so/1.0.0}CustomerEmail").text
    b_064 = "094857273"  # Not provided
    b_066 = "Email"  # Not provided
    b_067 = 0  # Not provided
    b_068 = "Drop at Door / Warehouse Dock"  # Not provided
    b_069 = 1  # Not provided
    b_070 = "Escalator"  # Not provided
    b_071 = 1  # Not provided

    order = {
        "b_client_order_num": order_num,
        "b_021_b_pu_avail_from_date": b_021,
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

    lines = []
    SalesOrderLines = SalesOrder.find("{http://www.pronto.net/so/1.0.0}SalesOrderLines")

    for SalesOrderLine in SalesOrderLines:
        ItemCode = SalesOrderLine.find("{http://www.pronto.net/so/1.0.0}ItemCode")
        OrderedQty = SalesOrderLine.find("{http://www.pronto.net/so/1.0.0}OrderedQty")
        SequenceNo = SalesOrderLine.find("{http://www.pronto.net/so/1.0.0}SequenceNo")
        UOMCode = SalesOrderLine.find("{http://www.pronto.net/so/1.0.0}UOMCode")
        line = {
            "model_number": ItemCode.text,
            "qty": int(float(OrderedQty.text)),
            "sequence": int(float(SequenceNo.text)),
            "UOMCode": UOMCode.text,
        }
        lines.append(line)

    return order, lines


def get_order(order_num):
    logger.info(f"@640 [PRONTO GET ORDER] Start! Order: {order_num}")

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
                                                <SequenceNo /> \
                                                <UOMCode /> \
                                                <TypeCode /> \
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
        f"@631 [PRONTO GET ORDER] response status_code: {response.status_code}, content: {response.content}"
    )

    if response.status_code != 200:
        logger.error(f"@632 [PRONTO GET ORDER] Failed")
        return False

    order, lines = parse_order_xml(response)
    logger.info(f"@649 [PRONTO GET ORDER] Finish \norder: {order}\nlines: {lines}")

    return order, lines


def send_info_back_to_pronto(booking, booking_lines):
    LOG_ID = "[PRONTO SEND ORDER BACK]"
    # logger.info(f"@640 {LOG_ID} Start! Order: {order_num}")

    # token = get_token()
    # url = f"{API_URL}/api/SalesOrderInsertSalesOrderLines"
    # headers = {
    #     "Content-Type": "application/x-www-form-urlencoded",
    #     "X-Pronto-Token": token,
    # }

    # body = f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\
    #             <SalesOrderInsertSalesOrderLinesRequest>\
    #                 <SalesOrderLines>\
    #                     <SalesOrderLine SOOrderNo="{booking.b_client_order_num}">\
    #                         <TypeCode>SN</TypeCode>\
    #                         <OrderedQty>{booking_line.e_qty}</OrderedQty>\
    #                         <PriceOverrideFlag>Y</PriceOverrideFlag>\
    #                         <ItemCode>{booking_line.e_item_type}</ItemCode>\
    #                         <LineDescription>{booking_line.e_item}</LineDescription>\
    #                         <ItemPrice></ItemPrice>\
    #                         <SolUserOnlyDate1>01/01/2021</SolUserOnlyDate1>\
    #                     </SalesOrderLine>\
    #                 </SalesOrderLines>\
    #             </SalesOrderInsertSalesOrderLinesRequest>'

    # # response = send_soap_request(url, body, headers)
    # logger.info(
    #     f"@631 {LOG_ID} response status_code: {response.status_code}, content: {response.content}"
    # )

    # if response.status_code != 200:
    #     logger.error(f"@632 {LOG_ID} Failed")
    #     return False
    # else:
    #     logger.error(f"@632 {LOG_ID} Success")
    #     return True
