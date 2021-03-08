import json
import logging
import xml.etree.ElementTree as ET

from django.conf import settings

from api.outputs.soap import send_soap_request
from api.outputs.email import send_email
from api.models import BOK_1_headers, BOK_2_lines, Log

logger = logging.getLogger("dme_api")


def build_xml_with_bok(bok_1, bok_2s):
    # Constants
    dme_account_num = "50365"
    customer_order_number = "y"
    order_type_code = "QI"
    customer_country = "AU"
    order_priority = "11"
    warehouse_code = "01"
    geographic_code = ""
    reference_number = ""
    send_status = "x"

    # Init result var
    _xml = ET.Element(
        "soapenv:Envelope",
        {
            "xmlns:soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
            "xmlns:sal": "http://www.paperless-warehousing.com/ACR/SalesOrderToWMS",
        },
    )

    # Add XML Header
    ET.SubElement(_xml, "soapenv:Header")

    # Build XML Body
    Body = ET.SubElement(_xml, "soapenv:Body")
    SalesOrderToWMS = ET.SubElement(Body, "sal:SalesOrderToWMS")

    # Build Header
    Header = ET.SubElement(SalesOrderToWMS, "Header")

    OrderNumber = ET.SubElement(Header, "OrderNumber")
    OrderNumber.text = f"{dme_account_num}{bok_1.b_client_order_num}"

    NumberOfDetails = ET.SubElement(Header, "NumberOfDetails")
    NumberOfDetails.text = str(bok_2s.count())

    HostOrderNumber = ET.SubElement(Header, "HostOrderNumber")
    HostOrderNumber.text = f"{dme_account_num}{bok_1.pk}"

    CustomerNumber = ET.SubElement(Header, "CustomerNumber")
    CustomerNumber.text = f"{dme_account_num}testcust123"

    CustomerName = ET.SubElement(Header, "CustomerName")
    CustomerName.text = "Plum Products Australia Ltd"  # hardcoded

    CustomerOrderNumber = ET.SubElement(Header, "CustomerOrderNumber")
    CustomerOrderNumber.text = customer_order_number

    OrderTypeCode = ET.SubElement(Header, "OrderTypeCode")
    OrderTypeCode.text = order_type_code

    CustomerStreet1 = ET.SubElement(Header, "CustomerStreet1")
    CustomerStreet1.text = bok_1.b_055_b_del_address_street_1

    CustomerStreet2 = ET.SubElement(Header, "CustomerStreet2")
    CustomerStreet2.text = bok_1.b_056_b_del_address_street_2

    CustomerStreet3 = ET.SubElement(Header, "CustomerStreet3")
    CustomerStreet3.text = ""

    CustomerSuburb = ET.SubElement(Header, "CustomerSuburb")
    CustomerSuburb.text = bok_1.b_058_b_del_address_suburb

    CustomerState = ET.SubElement(Header, "CustomerState")
    CustomerState.text = bok_1.b_057_b_del_address_state

    CustomerPostCode = ET.SubElement(Header, "CustomerPostCode")
    CustomerPostCode.text = bok_1.b_059_b_del_address_postalcode

    CustomerCountry = ET.SubElement(Header, "CustomerCountry")
    CustomerCountry.text = customer_country

    OrderPriority = ET.SubElement(Header, "OrderPriority")
    OrderPriority.text = order_priority

    DeliveryInstructions = ET.SubElement(Header, "DeliveryInstructions")
    DeliveryInstructions.text = f"{bok_1.b_043_b_del_instructions_contact} {bok_1.b_044_b_del_instructions_address}"

    # DeliveryDate = ET.SubElement(Header, "DeliveryDate")
    # DeliveryDate.text = str(bok_1.b_050_b_del_by_date)

    WarehouseCode = ET.SubElement(Header, "WarehouseCode")
    WarehouseCode.text = warehouse_code

    GeographicCode = ET.SubElement(Header, "GeographicCode")
    GeographicCode.text = geographic_code

    SpecialInstructions = ET.SubElement(Header, "SpecialInstructions")
    SpecialInstructions.text = ""

    Carrier = ET.SubElement(Header, "Carrier")
    _fp_name = bok_1.quote.freight_provider.lower()

    if not bok_1.quote:
        Carrier.text = ""
    elif _fp_name == "tnt":
        Carrier.text = "D_TNT"
    elif _fp_name == "hunter":
        Carrier.text = "D_HTX"
    elif _fp_name == "camerons":
        Carrier.text = "D_CAM"
    elif _fp_name == "hunter":
        Carrier.text = "D_HTX"
    elif _fp_name == "auspost" and bok_1.quote.account_code == "2006871123":
        Carrier.text = "D_EPI"

    ReferenceNumber = ET.SubElement(Header, "ReferenceNumber")
    ReferenceNumber.text = reference_number

    # DespatchDate = ET.SubElement(Header, "DespatchDate")
    # DespatchDate.text = ""

    SendStatus = ET.SubElement(Header, "SendStatus")
    SendStatus.text = send_status

    ContactPhoneNumber1 = ET.SubElement(Header, "ContactPhoneNumber1")
    ContactPhoneNumber1.text = bok_1.b_064_b_del_phone_main

    CustomerEmailAddress = ET.SubElement(Header, "CustomerEmailAddress")
    CustomerEmailAddress.text = bok_1.b_063_b_del_email

    # Build Detail(s)
    for index, bok_2 in enumerate(bok_2s):
        Detail = ET.SubElement(SalesOrderToWMS, "Detail")

        DetailSequenceNum = ET.SubElement(Detail, "DetailSequenceNum")
        DetailSequenceNum.text = str(index + 1)

        HostLineNumber = ET.SubElement(Detail, "HostLineNumber")
        HostLineNumber.text = str(bok_2.pk_lines_id)

        ProductCode = ET.SubElement(Detail, "ProductCode")
        ProductCode.text = f"{dme_account_num}{bok_2.e_item_type}"

        QuantityOrdered = ET.SubElement(Detail, "QuantityOrdered")
        QuantityOrdered.text = str(bok_2.l_002_qty)

    # ET.dump(_xml)  # Only used for debugging
    result = ET.tostring(_xml)
    return result


def parse_xml(response):
    xml_str = response.content.decode("utf-8")
    root = ET.fromstring(xml_str)
    Body_ns = "{http://schemas.xmlsoap.org/soap/envelope/}Body"
    Body = root.find(Body_ns)
    json_res = {}

    if response.status_code == 200:
        SalesOrderToWMSAck_ns = "{http://www.paperless-warehousing.com/TEST/SalesOrderToWMS}SalesOrderToWMSAck"
        SalesOrderToWMSAck = Body.find(SalesOrderToWMSAck_ns)

        if SalesOrderToWMSAck:
            json_res["DocNbr"] = SalesOrderToWMSAck.find("DocNbr").text
            json_res["WhsCode"] = SalesOrderToWMSAck.find("WhsCode").text
            json_res["Version"] = SalesOrderToWMSAck.find("Version").text
            json_res["DateRcvd"] = SalesOrderToWMSAck.find("DateRcvd").text
            json_res["TimeRcvd"] = SalesOrderToWMSAck.find("TimeRcvd").text
            json_res["MessageType"] = SalesOrderToWMSAck.find("MessageType").text
            json_res["MessageStatus"] = SalesOrderToWMSAck.find("MessageStatus").text

            if json_res["MessageStatus"] != "OK":
                ErrorDetails = SalesOrderToWMSAck.find("ErrorDetails")
                json_res["ErrorDetails"] = {
                    "Type": ErrorDetails.find("Type").text,
                    "Description": ErrorDetails.find("Description").text,
                    "Code": ErrorDetails.find("Code").text,
                    "Area": ErrorDetails.find("Area").text,
                    "Source": ErrorDetails.find("Source").text,
                    "User": ErrorDetails.find("User").text,
                }
    elif response.status_code == 500:
        Fault_ns = "{http://schemas.xmlsoap.org/soap/envelope/}Fault"
        Fault = Body.find(Fault_ns)
        json_res["faultcode"] = Fault.find("faultcode").text
        json_res["faultstring"] = Fault.find("faultcode").text
        json_res["detail"] = Fault.find("detail/WSDL_VALIDATION_FAILED").text

    return json_res


def send_order_info(bok_1):
    if settings.ENV == "local":
        return True

    if settings.ENV == "prod":
        return True

    try:
        headers = {
            "content-type": "text/xml",
            "soapaction": "http://www.paperless-warehousing.com/ACR/SalesOrderToWMS",
        }

        if settings.ENV == "prod":
            port = "32380"
        else:
            port = "33380"

        url = f"http://automation.acrsupplypartners.com.au:{port}/SalesOrderToWMS"
        bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)
        subject = "Error on Paperless workflow"
        to_emails = [settings.ADMIN_EMAIL_01, settings.ADMIN_EMAIL_02]
        log = Log(fk_booking_id=bok_1.pk_header_id, request_type="PAPERLESS_ORDER")
        log.save()

        if settings.ENV == "prod":
            to_emails.append(settings.SUPPORT_CENTER_EMAIL)

        try:
            body = build_xml_with_bok(bok_1, bok_2s)
            logger.info(f"@9000 Paperless payload body - {body}")
        except Exception as e:
            error = f"@901 Paperless error on payload builder.\n\nError: {str(e)}\nBok_1: {str(bok_1.pk)}"
            logger.error(error)
            raise Exception(error)

        log.request_payload = body.decode("utf-8")
        log.save()
        response = send_soap_request(url, body, headers)
        logger.error(
            f"@9001 - Paperless response status_code: {response.status_code}, content: {response.content}"
        )
        log.request_status = response.status_code
        log.response = response.content.decode("utf-8")
        log.save()

        try:
            json_res = parse_xml(response)
        except Exception as e:
            error = f"@902 Paperless error on parseing response.\n\nError: {str(e)}\nBok_1: {str(bok_1.pk)}\n\n"
            error += f"Request info:\n    url: {url}\n    headers: {json.dumps(headers, indent=4)}\n    body: {body}\n\n"
            error += f"Response info:\n    status_code: {response.status_code}\n    content: {response.content}"
            logger.error(error)
            raise Exception(error)

        if response.status_code > 400 or "ErrorDetails" in json_res:
            error = f"@903 Paperless response error.\n\nBok_1: {str(bok_1.pk)}\n\n"
            error += f"Request info:\n    url: {url}\n    headers: {json.dumps(headers, indent=4)}\n    body: {body}\n\n"
            error += f"Response info:\n    status_code: {response.status_code}\n    content: {response.content}\n\n"
            error += f"Parsed json: {json.dumps(json_res, indent=4)}"
            logger.error(error)
            raise Exception(error)

        log.response = json.dumps(json_res, indent=4)
        log.save()
        logger.error(
            f"@9009 - Paperless send_order_info() result: {json.dumps(json_res, indent=4)}"
        )
        return json_res
    except Exception as e:
        send_email(send_to=to_emails, send_cc=[], subject=subject, text=str(e))
        logger.error("@905 Sent email notification!")
        return None
