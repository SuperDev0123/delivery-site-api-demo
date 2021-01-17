import io
import time
import uuid
import json
import logging
import requests
import zipfile
from datetime import datetime
from base64 import b64decode, b64encode

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db import transaction
from rest_framework import views, serializers, status
from rest_framework.response import Response
from rest_framework import authentication, permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.decorators import (
    api_view,
    permission_classes,
    action,
)

from api.fp_apis.apis import get_pricing
from api.serializers_api import *
from api.serializers import SimpleQuoteSerializer
from api.models import *
from api.common import (
    trace_error,
    constants as dme_constants,
    status_history,
    common_times as dme_time_lib,
)
from api.common.booking_quote import migrate_quote_info_to_booking
from api.fp_apis.utils import (
    select_best_options,
    get_status_category_from_status,
    auto_select_pricing_4_bok,
    get_etd_in_hour,
    gen_consignment_num,
)
from api.operations import push_operations, product_operations as product_oper
from api.operations.labels.index import build_label, get_barcode
from api.operations.email_senders import send_email_to_admins
from api.operations.manifests.index import build_manifest
from api.convertors import pdf
from api.serializers import SimpleQuoteSerializer


logger = logging.getLogger("dme_api")


class BOK_0_ViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        bok_0_bookingkeys = BOK_0_BookingKeys.objects.all().order_by(
            "-z_createdTimeStamp"
        )[:50]
        serializer = BOK_0_Serializer(bok_0_bookingkeys, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = BOK_0_Serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BOK_1_ViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        bok_1_headers = BOK_1_headers.objects.all().order_by("-z_createdTimeStamp")[:50]
        serializer = BOK_1_Serializer(bok_1_headers, many=True)
        return Response(serializer.data)

    def create(self, request):
        logger.info(f"@871 User: {request.user.username}")
        logger.info(f"@872 request payload - {request.data}")
        bok_1_header = request.data
        b_client_warehouse_code = bok_1_header["b_client_warehouse_code"]
        warehouse = Client_warehouses.objects.get(
            client_warehouse_code=b_client_warehouse_code
        )
        bok_1_header["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
        bok_1_header["success"] = dme_constants.BOK_SUCCESS_2
        bok_1_header["client_booking_id"] = str(uuid.uuid4())
        serializer = BOK_1_Serializer(data=bok_1_header)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.info(f"@841 BOK_1 POST - {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def get_boks_with_pricings(self, request):
        client_booking_id = request.GET["identifier"]

        if not client_booking_id:
            return Response(
                {"message": "Wrong identifier."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bok_1 = BOK_1_headers.objects.get(client_booking_id=client_booking_id)
            bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)
            quote_set = API_booking_quotes.objects.filter(
                fk_booking_id=bok_1.pk_header_id
            )
            client = DME_clients.objects.get(dme_account_num=bok_1.fk_client_id)

            result = BOK_1_Serializer(bok_1).data
            result["client_customer_mark_up"] = client.client_customer_mark_up
            result["bok_2s"] = BOK_2_Serializer(bok_2s, many=True).data

            best_quotes = quote_set
            # Select best quotes(fastest, lowest)
            # if quote_set.exists() and quote_set.count() > 1:
            # best_quotes = select_best_options(pricings=quote_set)
            # logger.info(f"#520 - Selected Best Pricings: {best_quotes}")

            # Set Express or Standard
            if best_quotes:
                json_results = SimpleQuoteSerializer(best_quotes, many=True).data
                json_results = dme_time_lib.beautify_eta(json_results, best_quotes)

                # if len(json_results) == 1:
                #     json_results[0]["service_name"] = "Standard"
                # else:
                #     if float(json_results[0]["cost"]) > float(
                #         json_results[1]["cost"]
                #     ):
                #         json_results[0]["service_name"] = "Express"
                #         json_results[1]["service_name"] = "Standard"
                #         json_results = [json_results[1], json_results[0]]
                #     else:
                #         json_results[1]["service_name"] = "Express"
                #         json_results[0]["service_name"] = "Standard"

                result["pricings"] = json_results
            else:
                result["pricings"] = []

        except Exception as e:
            logger.info(f"#490 Error: {e}")
            trace_error.print()
            return Response(
                {"message": "Couldn't find matching Booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Succesfully get bok and pricings.", "data": result},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], permission_classes=[AllowAny])
    def book(self, request):
        identifier = request.GET["identifier"]

        if not identifier:
            return Response(
                {"message": "Wrong identifier."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bok_1 = BOK_1_headers.objects.prefetch_related("quote").get(
                client_booking_id=identifier
            )
            bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)
            bok_3s = BOK_3_lines_data.objects.filter(fk_header_id=bok_1.pk_header_id)

            for bok_2 in bok_2s:
                bok_2.success = dme_constants.BOK_SUCCESS_4
                bok_2.save()

            for bok_3 in bok_3s:
                bok_3.success = dme_constants.BOK_SUCCESS_4
                bok_3.save()

            bok_1.success = dme_constants.BOK_SUCCESS_4
            bok_1.save()

            if bok_1.quote:
                bok_1.b_001_b_freight_provider = bok_1.quote.freight_provider
                bok_1.b_003_b_service_name = bok_1.quote.service_name
                bok_1.save()

            logger.info(f"@843 [BOOK] BOK success with identifier: {identifier}")
            return Response({"success": True}, status.HTTP_200_OK)
        except:
            logger.info(f"@844 [BOOK] BOK Failure with identifier: {identifier}")
            return Response({"success": False}, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["delete"], permission_classes=[AllowAny])
    def cancel(self, request):
        identifier = request.GET["identifier"]

        if not identifier:
            return Response(
                {"message": "Wrong identifier."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bok_1 = BOK_1_headers.objects.get(client_booking_id=identifier)
            BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id).delete()
            BOK_3_lines_data.objects.filter(fk_header_id=bok_1.pk_header_id).delete()
            bok_1.delete()
            logger.info(f"@840 [CANCEL] BOK success with identifier: {identifier}")
            return Response({"success": True}, status.HTTP_200_OK)
        except Exception as e:
            logger.info(
                f"@841 [CANCEL] BOK Failure with identifier: {identifier}, reason: {str(e)}"
            )
            return Response({"success": False}, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def select_pricing(self, request):
        try:
            cost_id = request.data["costId"]
            identifier = request.data["identifier"]

            bok_1 = BOK_1_headers.objects.get(client_booking_id=identifier)
            bok_1.quote_id = cost_id
            bok_1.save()

            fc_log = (
                FC_Log.objects.filter(client_booking_id=bok_1.client_booking_id)
                .order_by("z_createdTimeStamp")
                .last()
            )
            fc_log.new_quote = bok_1.quote
            fc_log.save()

            return Response({"success": True}, status.HTTP_200_OK)
        except:
            trace_error.print()
            return Response({"success": False}, status.HTTP_400_BAD_REQUEST)


class BOK_2_ViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        bok_2_lines = BOK_2_lines.objects.all().order_by("-z_createdTimeStamp")[:50]
        serializer = BOK_2_Serializer(bok_2_lines, many=True)
        return Response(serializer.data)

    def create(self, request):
        logger.info(f"@873 User: {request.user.username}")
        logger.info(f"@874 request payload - {request.data}")
        bok_2_line = request.data
        bok_2_line["v_client_pk_consigment_num"] = bok_2_line["fk_header_id"]
        bok_2_line["success"] = dme_constants.BOK_SUCCESS_2
        serializer = BOK_2_Serializer(data=bok_2_line)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.info(f"@842 BOK_2 POST - {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BOK_3_ViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        bok_3_lines_data = BOK_3_lines_data.objects.all().order_by(
            "-z_createdTimeStamp"
        )
        serializer = BOK_3_Serializer(bok_3_lines_data, many=True)
        return Response(serializer.data)


@transaction.atomic
@api_view(["POST"])
def order_boks(request):
    user = request.user
    data_json = request.data
    logger.info(f"@879 Pusher: {user.username}")
    logger.info(f"@880 request payload - {data_json}")
    message = None

    # Find `Client`
    try:
        client_employee = Client_employees.objects.get(fk_id_user_id=user.pk)
        client = client_employee.fk_id_dme_client
        client_name = client.company_name
        logger.info(f"@810 - client: , {client_name}")
    except Exception as e:
        logger.info(f"@811 - client_employee does not exist, {str(e)}")
        message = "You are not allowed to use this api-endpoint."
        logger.info(message)
        return Response(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )

    # Check required fields
    if "Plum" in client_name:
        if not "cost_id" in data_json or (
            "cost_id" in data_json and not data_json["cost_id"]
        ):
            message = "'cost_id' is required."

        if not "b_client_sales_inv_num" in data_json or (
            "b_client_sales_inv_num" in data_json
            and not data_json["b_client_sales_inv_num"]
        ):
            message = "'b_client_sales_inv_num' is required."

        if "_sapb1" in user.username:
            if not "b_client_order_num" in data_json or (
                "b_client_order_num" in data_json
                and not data_json["b_client_order_num"]
            ):
                message = "'b_client_order_num' is required."
        if "_magento" in user.username:
            if not "client_booking_id" in data_json or (
                "client_booking_id" in data_json and not data_json["client_booking_id"]
            ):
                message = "'client_booking_id' is required."

        if message:
            logger.info(f"#821 {message}")
            return Response(
                {"success": False, "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Validate `client_booking_id` and `b_client_order_num`
    if "Plum" in client_name and "_sapb1" in user.username:
        b_client_order_num = data_json["b_client_order_num"]
        bok_1s = BOK_1_headers.objects.filter(b_client_order_num=b_client_order_num)

        if not bok_1s.exists():
            message = f"Object(b_client_order_num={b_client_order_num}) does not exist."
        else:
            bok_1 = bok_1s.first()
            pk_header_id = bok_1.pk_header_id
    if "Plum" in client_name and "_magento" in user.username:
        client_booking_id = data_json["client_booking_id"]
        bok_1s = BOK_1_headers.objects.filter(client_booking_id=client_booking_id)

        if not bok_1s.exists():
            message = f"Object(client_booking_id={client_booking_id}) does not exist."
        else:
            bok_1 = bok_1s.first()
            pk_header_id = bok_1.pk_header_id

    # Validate `cost_id`
    cost_id = data_json["cost_id"]
    quotes = API_booking_quotes.objects.filter(
        pk=cost_id, fk_booking_id=bok_1.pk_header_id
    )

    if not quotes.exists():
        message = f"Invalid cost_id: {cost_id}, Please get costs again."

    if message:
        logger.info(f"#822 {message}")
        return Response(
            {"success": False, "message": message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Update boks
    bok_1.b_client_sales_inv_num = data_json["b_client_sales_inv_num"]
    bok_1.save()

    # create status history
    status_history.create_4_bok(bok_1.pk_header_id, "Ordered", request.user.username)

    logger.info(f"#823 Order success")
    return Response(
        {"success": True},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def scanned(request):
    """
    request when item(s) is picked(scanned) at warehouse
    """
    user = request.user
    logger.info(f"@890 Picked by: {user.username}")
    logger.info(f"@891 Picked info: {request.data}")
    b_client_order_num = request.data.get("HostOrderNumber")
    picked_items = request.data.get("picked_items")
    b_client_name = request.data.get("CustomerName")
    code = None
    message = None
    labels = []

    # Check required params are included
    if not b_client_order_num:
        code = "missing_param"
        message = "'HostOrderNumber' is required."

    if not picked_items:
        code = "missing_param"
        message = "'picked_items' is required."

    if not b_client_name:
        code = "missing_param"
        message = "'CustomerName' is required."

    if message:
        raise ValidationError({"success": False, "code": code, "description": message})

    # Check if order exists
    booking = Bookings.objects.filter(
        b_client_name=b_client_name, b_client_order_num=b_client_order_num[5:]
    ).first()

    if not booking:
        code = "not_found"
        message = (
            "Order does not exist. 'CustomerName' or 'HostOrderNumber' is invalid."
        )
        raise ValidationError({"success": False, "code": code, "description": message})

    # Else
    pk_booking_id = booking.pk_booking_id
    lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
    line_datas = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)
    original_items = lines.filter(sscc__isnull=True)
    scanned_items = lines.filter(sscc__isnull=False, e_item="Picked Item")
    repacked_items_count = lines.filter(
        sscc__isnull=False, e_item="Repacked Item"
    ).count()
    model_number_qtys = original_items.values_list("e_item_type", "e_qty")
    sscc_list = scanned_items.values_list("sscc", flat=True)

    logger.info(f"@360 - Booking: {booking}")
    logger.info(f"@361 - Lines: {lines}")
    logger.info(f"@362 - original_items: {original_items}")
    logger.info(f"@363 - scanned_items: {scanned_items}")
    logger.info(f"@364 - model_number and qty(s): {model_number_qtys}")
    logger.info(f"@365 - sscc(s): {sscc_list}")

    # Validation
    missing_sscc_picked_items = []
    invalid_model_numbers = []
    invalid_sscc_list = []
    duplicated_sscc_list = []
    for picked_item in picked_items:
        # Check `sscc` is provided
        if not "sscc" in picked_item:
            code = "missing_param"
            message = f"There is an item which doesn`t have 'sscc' information. Invalid item: {json.dumps(picked_item)}"
            raise ValidationError(
                {"success": False, "code": code, "description": message}
            )

        # Check if sscc is invalid
        if Booking_lines.objects.filter(sscc=picked_item["sscc"]).exists():
            duplicated_sscc_list.append(picked_item["sscc"])

        # Validate repacked items
        if (
            "is_repacked" in picked_item
            and "items" in picked_item
            and picked_item["items"]
        ):
            repack_type = None

            for item in picked_item["items"]:
                # Get and check repack_type
                if "model_number" in item and not repack_type:
                    repack_type = "model_number"

                if "sscc" in item and not repack_type:
                    repack_type = "sscc"

                # Invalid sscc check
                if repack_type == "sscc" and not item["sscc"] in sscc_list:
                    invalid_sscc_list.append(item["sscc"])

                # Check qty
                if repack_type == "model_number":
                    if not "qty" in item:
                        code = "missing_param"
                        message = f"Qty is required. Invalid item: {json.dumps(item)}"
                        raise ValidationError(
                            {"success": False, "code": code, "description": message}
                        )
                    elif "qty" in item and not item["qty"]:
                        code = "invalid_param"
                        message = f"Qty should bigger than 0. Invalid item: {json.dumps(item)}"
                        raise ValidationError(
                            {"success": False, "code": code, "description": message}
                        )

                # Accumulate invalid_model_numbers
                if "model_number" in item:
                    is_valid = False

                    for model_number_qty in model_number_qtys:
                        if model_number_qty[0] == item["model_number"]:
                            is_valid = True

                    if not is_valid:
                        invalid_model_numbers.append(item["model_number"])

                # Invalid repack_type (which has both 'sscc' and 'model_number')
                if ("model_number" in item and repack_type == "sscc") or (
                    "sscc" in item and repack_type == "model_number"
                ):
                    code = "invalid_repacked_item"
                    message = f"Can not repack 'model_number' and 'sscc'."
                    raise ValidationError(
                        {"success": False, "code": code, "description": message}
                    )

                # Invalid repack_type (which doesn't have both 'sscc' and 'model_number')
                if not "model_number" in item and not "sscc" in item:
                    code = "invalid_repacked_item"
                    message = f"There is an item which does not have 'model_number' information. Invalid item: {json.dumps(item)}"
                    raise ValidationError(
                        {"success": False, "code": code, "description": message}
                    )
        else:
            code = "invalid_item"
            message = f"There is an invalid item: {json.dumps(picked_item)}"
            raise ValidationError(
                {"success": False, "code": code, "description": message}
            )

    if duplicated_sscc_list:
        code = "duplicated_sscc"
        message = f"There are duplicated sscc(s): {', '.join(duplicated_sscc_list)}"
        raise ValidationError({"success": False, "code": code, "description": message})

    if invalid_sscc_list:
        code = "invalid_sscc"
        message = (
            f"This order doesn't have given sscc(s): {', '.join(invalid_sscc_list)}"
        )
        raise ValidationError({"success": False, "code": code, "description": message})

    if invalid_model_numbers:
        code = "invalid_param"
        message = f"'{', '.join(invalid_model_numbers)}' are invalid model_numbers for this order."
        raise ValidationError({"success": False, "code": code, "description": message})

    # Check over picked items
    over_picked_items = []
    estimated_picked = {}
    is_picked_all = True
    scanned_items_count = 0

    for model_number_qty in model_number_qtys:
        estimated_picked[model_number_qty[0]] = 0

    for scanned_item in scanned_items:
        if scanned_item.e_item_type:
            estimated_picked[scanned_item.e_item_type] += scanned_item.e_qty
            scanned_items_count += scanned_item.e_qty

        for line_data in line_datas:
            if (
                line_data.fk_booking_lines_id == scanned_item.pk_booking_lines_id
                and line_data.itemDescription != "Repacked at warehouse"
            ):
                estimated_picked[line_data.modelNumber] += line_data.quantity

    if repack_type == "model_number":
        for picked_item in picked_items:
            for item in picked_item["items"]:
                estimated_picked[item["model_number"]] += item["qty"]

    logger.info(
        f"@366 - over picked - limit: {model_number_qtys}, estimated: {estimated_picked}"
    )

    for item in estimated_picked:
        for model_number_qty in model_number_qtys:
            if (
                item == model_number_qty[0]
                and estimated_picked[item] > model_number_qty[1]
            ):
                over_picked_items.append(model_number_qty[0])

            if (
                item == model_number_qty[0]
                and estimated_picked[item] != model_number_qty[1]
            ):
                is_picked_all = False

    if over_picked_items:
        logger.error(
            f"@367 - over picked - limit: {model_number_qtys}, estimated: {estimated_picked}"
        )
        code = "over_picked"
        message = f"There are over picked items: {', '.join(over_picked_items)}"
        raise ValidationError({"success": False, "code": code, "description": message})

    # Save
    try:
        with transaction.atomic():
            for picked_item in picked_items:
                # Create new Lines
                new_line = Booking_lines()
                new_line.fk_booking_id = pk_booking_id
                new_line.pk_booking_lines_id = str(uuid.uuid4())
                new_line.e_type_of_packaging = picked_item["package_type"]
                new_line.e_qty = 1

                if repack_type == "model_number":
                    new_line.e_item = "Picked Item"
                else:
                    new_line.e_item = "Repacked Item"

                new_line.e_dimUOM = picked_item["dimensions"]["unit"]
                new_line.e_dimLength = picked_item["dimensions"]["length"]
                new_line.e_dimWidth = picked_item["dimensions"]["width"]
                new_line.e_dimHeight = picked_item["dimensions"]["height"]
                new_line.e_weightUOM = picked_item["weight"]["unit"]
                new_line.e_weightPerEach = picked_item["weight"]["weight"]
                new_line.sscc = picked_item["sscc"]
                new_line.picked_up_timestamp = picked_item["timestamp"]
                new_line.save()

                for item in picked_item["items"]:
                    # Soft delete original line
                    if repack_type == "model_number":
                        line = lines.get(e_item_type=item["model_number"])
                    elif repack_type == "sscc":
                        line = lines.get(sscc=item["sscc"])

                    line.is_deleted = True
                    line.save()

                    # Create new Line_Data
                    line_data = Booking_lines_data()
                    line_data.fk_booking_id = pk_booking_id
                    line_data.fk_booking_lines_id = new_line.pk_booking_lines_id

                    if repack_type == "model_number":
                        line_data.modelNumber = item["model_number"]
                        line_data.itemDescription = "Picked at warehouse"
                        line_data.quantity = item["qty"]
                        line_data.clientRefNumber = picked_item["sscc"]
                    else:
                        line_data.modelNumber = item["sscc"]
                        line_data.itemDescription = "Repacked at warehouse"
                        line_data.clientRefNumber = picked_item["sscc"]

                    line_data.save()

                # Build label with Line
                if not booking.api_booking_quote:
                    raise Exception("Booking doens't have quote.")

                if not booking.vx_freight_provider and booking.api_booking_quote:
                    _booking = migrate_quote_info_to_booking(
                        booking, booking.api_booking_quote
                    )

                if settings.ENV == "prod":
                    file_path = (
                        f"/opt/s3_public/pdfs/{booking.vx_freight_provider.lower()}_au/"
                    )
                else:
                    file_path = f"./static/pdfs/"

                logger.info(f"@368 - building label...")
                label_index = scanned_items_count + repacked_items_count
                file_path, file_name = build_label(
                    booking, file_path, [new_line], label_index
                )

                # Convert label into ZPL format
                logger.info(
                    f"@369 - converting LABEL({file_path}/{file_name}) into ZPL format..."
                )
                label_url = f"{file_path}/{file_name}"
                result = pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

                if not result:
                    code = "unknown_status"
                    description = "Please contact DME support center. <bookings@deliver-me.com.au>"
                    raise Exception(
                        {"success": False, "code": code, "description": description}
                    )

                with open(label_url[:-4] + ".zpl", "rb") as zpl:
                    zpl_data = str(b64encode(zpl.read()))[2:-1]
                    labels.append(
                        {
                            "sscc": picked_item["sscc"],
                            "label": zpl_data,
                            "barcode": get_barcode(booking, [new_line]),
                        }
                    )

        if is_picked_all:
            new_fc_log = FC_Log.objects.create(
                client_booking_id=booking.b_client_booking_ref_num,
                old_quote=booking.api_booking_quote,
            )
            new_fc_log.save()
            logger.info(
                f"#371 - Picked all items: {booking.b_bookingID_Visual}, now getting Quotes again..."
            )
            _, success, message, quotes = get_pricing(body=None, booking_id=booking.pk)
            logger.info(
                f"#372 - Pricing result: success: {success}, message: {message}, results cnt: {quotes.count()}"
            )

            # Select best quotes(fastest, lowest)
            if quotes.exists() and quotes.count() > 1:
                quotes = quotes.filter(
                    freight_provider__iexact=booking.vx_freight_provider,
                    service_name=booking.vx_serviceName,
                )
                best_quotes = select_best_options(pricings=quotes)
                logger.info(f"#373 - Selected Best Pricings: {best_quotes}")

                if best_quotes:
                    booking.api_booking_quote = best_quotes[0]
                    booking.save()
                    new_fc_log.new_quote = booking.api_booking_quote
                    new_fc_log.save()
                else:
                    booking.api_booking_quote = None
                    booking.save()

        return Response(
            {
                "success": True,
                "message": "Successfully updated picked info.",
                "consignment_number": gen_consignment_num(
                    booking.vx_freight_provider, booking.b_bookingID_Visual
                ),
                "labels": labels,
            }
        )
    except Exception as e:
        trace_error.print()
        error_msg = f"@370 Error on PICKED api: {str(e)}"
        logger.error(error_msg)
        send_email_to_admins(
            "Scanned api-endpoint error",
            f"{error_msg}",
        )
        raise ValidationError(
            {
                "success": False,
                "message": "Please contact DME support center. <bookings@deliver-me.com.au>",
            }
        )


@transaction.atomic
@api_view(["POST"])
def ready_boks(request):
    """
    When it is ready(picked all items) on Warehouse
    """
    user = request.user
    logger.info(f"@840 Ready api-endpoint: {user.username}")
    logger.info(f"@841 payload: {request.data}")
    b_client_order_num = request.data.get("HostOrderNumber")
    is_ready = request.data.get("is_ready")
    b_client_name = request.data.get("CustomerName")
    code = None
    message = None

    # Check required params are included
    if not b_client_order_num:
        code = "missing_param"
        message = "'HostOrderNumber' is required."

    if is_ready is None:
        code = "missing_param"
        message = "'is_ready' is required."

    if not b_client_name:
        code = "missing_param"
        message = "'CustomerName' is required."

    if message:
        raise ValidationError({"success": False, "code": code, "description": message})

    # Check if order exists
    booking = Bookings.objects.filter(
        b_client_name=b_client_name, b_client_order_num=b_client_order_num[5:]
    ).first()

    if not booking:
        code = "not_found"
        message = (
            "Order does not exist. 'CustomerName' or 'HostOrderNumber' is invalid."
        )
        raise ValidationError({"success": False, "code": code, "description": message})

    if not is_ready:
        return Response(
            {
                "success": False,
                "message": f"`is_ready` is false.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    pk_booking_id = booking.pk_booking_id
    lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
    line_datas = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)

    # Check if Order items are all picked
    original_items = lines.filter(sscc__isnull=True)
    scanned_items = lines.filter(sscc__isnull=False, e_item="Picked Item")
    repacked_items_count = lines.filter(
        sscc__isnull=False, e_item="Repacked Item"
    ).count()
    model_number_qtys = original_items.values_list("e_item_type", "e_qty")
    estimated_picked = {}
    is_picked_all = True
    not_picked_items = []

    for model_number_qty in model_number_qtys:
        estimated_picked[model_number_qty[0]] = 0

    for scanned_item in scanned_items:
        if scanned_item.e_item_type:
            estimated_picked[scanned_item.e_item_type] += scanned_item.e_qty

        for line_data in line_datas:
            if (
                line_data.fk_booking_lines_id == scanned_item.pk_booking_lines_id
                and line_data.itemDescription != "Repacked at warehouse"
            ):
                estimated_picked[line_data.modelNumber] += line_data.quantity

    logger.info(f"@843 - limit: {model_number_qtys}, picked: {estimated_picked}")

    for item in estimated_picked:
        for model_number_qty in model_number_qtys:
            if (
                item == model_number_qty[0]
                and estimated_picked[item] != model_number_qty[1]
            ):
                not_picked_items.append(
                    {
                        "all_items_count": model_number_qty[1],
                        "picked_items_count": estimated_picked[item],
                    }
                )
                is_picked_all = False

    if not is_picked_all:
        return Response(
            {
                "success": False,
                "message": f"There are some items are not picked yet - {json.dumps(not_picked_items)}",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Update DB so that Booking can be BOOKED
    if booking.api_booking_quote:
        booking.b_status = "Ready for Booking"
    else:
        booking.b_status = "On Hold"
        send_email_to_admins(
            f"Quote issue on Booking(#{booking.b_bookingID_Visual})",
            f"Original FP was {booking.vx_freight_provider}({booking.vx_serviceName})."
            + f" After labels were made {booking.vx_freight_provider}({booking.vx_serviceName}) was not an option for shipment."
            + f" Please do FC manually again on DME portal.",
        )

    booking.save()

    return Response(
        {
            "success": True,
            "message": "Order will be BOOKED soon.",
        }
    )


@transaction.atomic
@api_view(["POST", "PUT"])
def push_boks(request):
    """
    PUSH api (bok_1, bok_2, bok_3)
    """
    user = request.user
    logger.info(f"@879 Pusher: {user.username}")
    boks_json = request.data
    bok_1 = boks_json["booking"]
    bok_2s = boks_json["booking_lines"]
    client_name = None
    message = None
    old_quote = None
    best_quotes = None
    json_results = []
    logger.info(f"@880 Push request - [{request.method}] {boks_json}")

    # Check missing model numbers
    if bok_2s and "model_number" in bok_2s[0]:
        missing_model_numbers = product_oper.find_missing_model_numbers(bok_2s)

        if missing_model_numbers:
            return Response(
                {
                    "success": False,
                    "results": [],
                    "message": f"Missing model numbers - {', '.join(missing_model_numbers)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Required fields
    if not bok_1.get("b_059_b_del_address_postalcode"):
        message = "'b_059_b_del_address_postalcode' is required."
        raise ValidationError(
            {"success": False, "code": "missing_param", "description": message}
        )

    # Find `Client`
    try:
        client_employee = Client_employees.objects.get(fk_id_user_id=user.pk)
        client = client_employee.fk_id_dme_client
        client_name = client.company_name
        logger.info(f"@810 - client: , {client_name}")
    except Exception as e:
        trace_error()
        logger.info(f"@811 - client_employee does not exist, {str(e)}")
        message = "You are not allowed to use this api-endpoint."
        logger.info(message)
        return Response(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )

    # Check required fields
    if "Plum" in client_name and "_sapb1" in user.username:
        if not bok_1.get("shipping_type"):
            message = "'shipping_type' is required."
            raise ValidationError(
                {"success": False, "code": "missing_param", "description": message}
            )
        elif len(bok_1.get("shipping_type")) != 4:
            message = "'shipping_type' is not valid."
            raise ValidationError(
                {"success": False, "code": "invalid_param", "description": message}
            )

        if not bok_1.get("b_client_order_num"):
            message = "'b_client_order_num' is required."
            logger.info(message)
            return Response(
                {"success": False, "code": "missing_param", "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )
    elif "Plum" in client_name and "_magento" in user.username:
        if not bok_1.get("client_booking_id"):
            message = "'client_booking_id' is required."
            logger.info(message)
            return Response(
                {"success": False, "code": "missing_param", "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Check if already pushed 'b_client_order_num', then return URL only
    if request.method == "POST" and "Plum" in client_name and "_sapb1" in user.username:
        if bok_1["b_client_order_num"][:2] != "Q_":
            bok_1_obj = (
                BOK_1_headers.objects.prefetch_related("quote")
                .filter(
                    fk_client_id=client.dme_account_num,
                    # b_client_order_num=bok_1["b_client_order_num"],
                    b_client_sales_inv_num=bok_1["b_client_sales_inv_num"],
                )
                .first()
            )

            if bok_1_obj:
                if not bok_1_obj.b_client_order_num:
                    bok_1_obj.b_client_order_num = bok_1["b_client_order_num"]
                    bok_1_obj.save()

                    if bok_1.get("shipping_type") == "DMEA":
                        bok_2_objs = BOK_2_lines.objects.filter(
                            fk_header_id=bok_1_obj.pk_header_id
                        )
                        bok_3_objs = BOK_3_lines_data.objects.filter(
                            fk_header_id=bok_1_obj.pk_header_id
                        )

                        for bok_2_obj in bok_2_objs:
                            bok_2_obj.success = dme_constants.BOK_SUCCESS_4
                            bok_2_obj.save()

                        for bok_3_obj in bok_3_objs:
                            bok_3_obj.success = dme_constants.BOK_SUCCESS_4
                            bok_3_obj.save()

                        bok_1_obj.success = dme_constants.BOK_SUCCESS_4
                        bok_1_obj.save()

                        if bok_1_obj.quote:
                            bok_1_obj.b_001_b_freight_provider = (
                                bok_1_obj.quote.freight_provider
                            )
                            bok_1_obj.b_003_b_service_name = (
                                bok_1_obj.quote.service_name
                            )
                            bok_1_obj.save()

                if int(bok_1_obj.success) == int(dme_constants.BOK_SUCCESS_3):
                    return JsonResponse(
                        {
                            "success": True,
                            "results": [],
                            "pricePageUrl": f"http://{settings.WEB_SITE_IP}/price/{bok_1_obj.client_booking_id}/",
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    return JsonResponse(
                        {
                            "success": True,
                            "results": [],
                            "pricePageUrl": f"http://{settings.WEB_SITE_IP}/status/{bok_1_obj.client_booking_id}/",
                        },
                        status=status.HTTP_201_CREATED,
                    )

    # Find `Warehouse`
    if "Plum" in client_name:
        try:
            warehouse = Client_warehouses.objects.get(fk_id_dme_client=client)
        except Exception as e:
            message = f"@821 Client doesn't have Warehouse(s): {str(e)}"
            logger.info(message)
            return JsonResponse(
                {"success": False, "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # "Detect modified data" and "delete existing boks" if request method is PUT
    if request.method == "PUT":
        if "Plum" in client_name:
            pk_header_id = None

            # if not bok_1.get("b_058_b_del_address_suburb"):
            #     message = "'b_058_b_del_address_suburb' is required."
            #     raise ValidationError({"code": "missing_param", "description": message})

            # if not bok_1.get("b_057_b_del_address_state"):
            #     message = "'b_057_b_del_address_state' is required."
            #     raise ValidationError({"code": "missing_param", "description": message})

            if "_sapb1" in user.username:
                old_bok_1s = BOK_1_headers.objects.filter(
                    fk_client_id=client.dme_account_num,
                    b_client_order_num=bok_1["b_client_order_num"],
                )

                if not old_bok_1s.exists():
                    if (
                        "b_client_sales_inv_num" in bok_1
                        and bok_1["b_client_sales_inv_num"]
                    ):
                        old_bok_1s = BOK_1_headers.objects.filter(
                            fk_client_id=client.dme_account_num,
                            b_client_sales_inv_num=bok_1["b_client_sales_inv_num"],
                        )

                        if not old_bok_1s.exists():
                            message = f"BOKS API Error - Object(b_client_order_num={bok_1['b_client_order_num']}) does not exist."
                            logger.info(f"@870 {message}")
                            return JsonResponse(
                                {"success": False, "message": message},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                else:
                    pk_header_id = old_bok_1s.first().pk_header_id
            elif "_magento" in user.username:
                old_bok_1s = BOK_1_headers.objects.filter(
                    client_booking_id=bok_1["client_booking_id"],
                )
                if not old_bok_1s.exists():
                    message = f"BOKS API Error - Object(client_booking_id={bok_1['client_booking_id']}) does not exist."
                    logger.info(f"@884 {message}")
                    return JsonResponse(
                        {"success": False, "message": message},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    pk_header_id = old_bok_1s.first().pk_header_id

            if pk_header_id:
                old_bok_1 = old_bok_1s.first()
                old_bok_2s = BOK_2_lines.objects.filter(fk_header_id=pk_header_id)
                old_bok_3s = BOK_3_lines_data.objects.filter(fk_header_id=pk_header_id)
                push_operations.detect_modified_data(
                    client_name, old_bok_1, old_bok_2s, old_bok_3s, boks_json
                )

                old_bok_1.delete()
                old_bok_2s.delete()
                old_bok_3s.delete()

    bok_1["pk_header_id"] = str(uuid.uuid4())
    # Check duplicated push with `b_client_order_num`
    if request.method == "POST":
        if "Plum" in client_name:
            if "_sapb1" in user.username:
                bok_1s = BOK_1_headers.objects.filter(
                    fk_client_id=client.dme_account_num,
                    b_client_order_num=bok_1["b_client_order_num"],
                )
                if bok_1s.exists():
                    # If "sales quote" request, then clear all existing information
                    if bok_1["b_client_order_num"][:2] == "Q_":
                        pk_header_id = bok_1s.first().pk_header_id
                        old_bok_1 = bok_1s.first()
                        old_bok_2s = BOK_2_lines.objects.filter(
                            fk_header_id=pk_header_id
                        )
                        old_bok_3s = BOK_3_lines_data.objects.filter(
                            fk_header_id=pk_header_id
                        )
                        old_bok_1.delete()
                        old_bok_2s.delete()
                        old_bok_3s.delete()
                        old_quote = old_bok_1.quote
                    else:
                        message = f"BOKS API Error - Object(b_client_order_num={bok_1['b_client_order_num']}) does already exist."

            elif "_magento" in user.username:
                bok_1s = BOK_1_headers.objects.filter(
                    client_booking_id=bok_1["client_booking_id"],
                )
                if bok_1s.exists():
                    message = f"BOKS API Error - Object(client_booking_id={bok_1['client_booking_id']}) does already exist."

        if message:
            logger.info(f"@884 {message}")
            return JsonResponse(
                {"success": False, "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Generate `client_booking_id` for SAPB1
    if "Plum" in client_name and "_sapb1" in user.username:
        client_booking_id = f"{bok_1['b_client_order_num']}_{bok_1['pk_header_id']}_{datetime.strftime(datetime.utcnow(), '%s')}"
        bok_1["client_booking_id"] = client_booking_id

    # Save
    try:
        # Save bok_1
        bok_1["fk_client_id"] = client.dme_account_num
        bok_1["x_booking_Created_With"] = "DME PUSH API"

        if client_name == "Seaway-Tempo-Aldi":  # Seaway-Tempo-Aldi
            bok_1["b_001_b_freight_provider"] = "DHL"

        if "Plum" in client_name:  # Plum
            if bok_1.get("shipping_type") == "DMEA":
                bok_1["success"] = dme_constants.BOK_SUCCESS_4
            else:
                bok_1["success"] = dme_constants.BOK_SUCCESS_3

            bok_1["b_client_name"] = client_name
            bok_1["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
            bok_1["b_clientPU_Warehouse"] = warehouse.warehousename
            bok_1["b_client_warehouse_code"] = warehouse.client_warehouse_code

            if not bok_1.get("b_000_1_b_clientreference_ra_numbers"):
                bok_1["b_000_1_b_clientreference_ra_numbers"] = ""

            if not bok_1.get("b_003_b_service_name"):
                bok_1["b_003_b_service_name"] = "RF"

            if not bok_1.get("b_028_b_pu_company"):
                bok_1["b_028_b_pu_company"] = "PU_PLUM_company"

            if not bok_1.get("b_035_b_pu_contact_full_name"):
                bok_1["b_035_b_pu_contact_full_name"] = "PU_PLUM"

            if not bok_1.get("b_037_b_pu_email"):
                bok_1["b_037_b_pu_email"] = "pu_plum@email.com"

            if not bok_1.get("b_038_b_pu_phone_main"):
                bok_1["b_038_b_pu_phone_main"] = "0419294339"

            if not bok_1.get("b_029_b_pu_address_street_1"):
                bok_1["b_029_b_pu_address_street_1"] = warehouse.warehouse_address1

            if not bok_1.get("b_030_b_pu_address_street_2"):
                bok_1["b_030_b_pu_address_street_2"] = warehouse.warehouse_address2

            if not bok_1.get("b_034_b_pu_address_country"):
                bok_1["b_034_b_pu_address_country"] = "AU"

            if not bok_1.get("b_033_b_pu_address_postalcode"):
                bok_1["b_033_b_pu_address_postalcode"] = warehouse.warehouse_postal_code

            if not bok_1.get("b_031_b_pu_address_state"):
                bok_1["b_031_b_pu_address_state"] = warehouse.warehouse_state

            if not bok_1.get("b_032_b_pu_address_suburb"):
                bok_1["b_032_b_pu_address_suburb"] = warehouse.warehouse_suburb

            if not bok_1.get("b_054_b_del_company"):
                bok_1["b_054_b_del_company"] = "DE_PLUM_company"

            if not bok_1.get("b_061_b_del_contact_full_name"):
                bok_1["b_061_b_del_contact_full_name"] = "DE_PLUM"

            if not bok_1.get("b_063_b_del_email"):
                bok_1["b_063_b_del_email"] = "de_plum@email.com"

            if not bok_1.get("b_064_b_del_phone_main"):
                bok_1["b_064_b_del_phone_main"] = "0419294339"

            if not bok_1.get("b_021_b_pu_avail_from_date"):
                bok_1["b_021_b_pu_avail_from_date"] = str(
                    datetime.now() + timedelta(days=7)
                )[:10]

            # Find `Suburb` and `State`
            if not bok_1.get("b_057_b_del_address_state") or not bok_1.get(
                "b_058_b_del_address_suburb"
            ):
                logger.info(f"@870 PUSH API - auto populating state and subrub...")
                de_postal_code = bok_1["b_059_b_del_address_postalcode"]
                addresses = Utl_suburbs.objects.filter(postal_code=de_postal_code)

                if not addresses.exists():
                    message = "Delivery PostalCode is not valid."
                    return Response(
                        {"success": False, "message": message},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    de_suburb = addresses[0].suburb
                    de_state = addresses[0].state

                if not bok_1.get("b_057_b_del_address_state"):
                    bok_1["b_057_b_del_address_state"] = de_state

                if not bok_1.get("b_058_b_del_address_suburb"):
                    bok_1["b_058_b_del_address_suburb"] = de_suburb

            bok_1["b_057_b_del_address_state"] = bok_1[
                "b_057_b_del_address_state"
            ].upper()
            bok_1["b_031_b_pu_address_state"] = bok_1[
                "b_031_b_pu_address_state"
            ].upper()
        else:  # If not from Plum, then set success to be ready for mapping
            bok_1["success"] = dme_constants.BOK_SUCCESS_2

        bok_1_serializer = BOK_1_Serializer(data=bok_1)
        if bok_1_serializer.is_valid():
            # Save bok_2s
            if "model_number" in bok_2s[0]:  # Product & Child items
                ignore_product = False

                if "Plum" in client_name and "_sapb1" in user.username:
                    ignore_product = True

                items = product_oper.get_product_items(bok_2s, ignore_product)
                new_bok_2s = []

                for index, item in enumerate(items):
                    line = {}
                    line["fk_header_id"] = bok_1["pk_header_id"]
                    line["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
                    line["pk_booking_lines_id"] = str(uuid.uuid1())
                    line["success"] = bok_1["success"]
                    line["l_001_type_of_packaging"] = "Carton"
                    line["l_002_qty"] = item["qty"]
                    line["l_003_item"] = item["description"]
                    line["l_004_dim_UOM"] = item["e_dimUOM"]
                    line["l_005_dim_length"] = item["e_dimLength"]
                    line["l_006_dim_width"] = item["e_dimWidth"]
                    line["l_007_dim_height"] = item["e_dimHeight"]
                    line["l_009_weight_per_each"] = item["e_weightPerEach"]
                    line["l_008_weight_UOM"] = item["e_weightUOM"]
                    line["e_item_type"] = item["e_item_type"]
                    new_bok_2s.append({"booking_line": line})

                    bok_2_serializer = BOK_2_Serializer(data=line)
                    if bok_2_serializer.is_valid():
                        bok_2_serializer.save()
                    else:
                        logger.info(f"@8822 BOKS API Error - {bok_2_serializer.errors}")
                        return Response(
                            {"success": False, "message": bok_2_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                bok_2s = new_bok_2s
            else:
                for index, bok_2 in enumerate(bok_2s):
                    bok_3s = bok_2["booking_lines_data"]
                    bok_2["booking_line"]["fk_header_id"] = bok_1["pk_header_id"]
                    bok_2["booking_line"]["v_client_pk_consigment_num"] = bok_1[
                        "pk_header_id"
                    ]
                    bok_2["booking_line"]["pk_booking_lines_id"] = str(uuid.uuid1())
                    bok_2["booking_line"]["success"] = bok_1["success"]
                    bok_2["booking_line"]["l_001_type_of_packaging"] = (
                        "Carton"
                        if not bok_2["booking_line"].get("l_001_type_of_packaging")
                        else bok_2["booking_line"]["l_001_type_of_packaging"]
                    )

                    bok_2_serializer = BOK_2_Serializer(data=bok_2["booking_line"])
                    if bok_2_serializer.is_valid():
                        bok_2_serializer.save()
                    else:
                        logger.info(f"@8822 BOKS API Error - {bok_2_serializer.errors}")
                        return Response(
                            {"success": False, "message": bok_2_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Save bok_3s
                    for bok_3 in bok_3s:
                        bok_3["fk_header_id"] = bok_1["pk_header_id"]
                        bok_3["fk_booking_lines_id"] = bok_2["booking_line"][
                            "pk_booking_lines_id"
                        ]
                        bok_3["v_client_pk_consigment_num"] = bok_1["pk_header_id"]
                        bok_3["success"] = bok_1["success"]

                        bok_3_serializer = BOK_3_Serializer(data=bok_3)
                        if bok_3_serializer.is_valid():
                            bok_3_serializer.save()
                        else:
                            logger.info(
                                f"@8823 BOKS API Error - {bok_3_serializer.errors}"
                            )
                            return Response(
                                {"success": False, "message": bok_3_serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

            bok_1_obj = bok_1_serializer.save()

            # create status history
            status_history.create_4_bok(
                bok_1["pk_header_id"], "Pushed", request.user.username
            )

            if bok_1["success"] in [
                dme_constants.BOK_SUCCESS_3,
                dme_constants.BOK_SUCCESS_4,
            ]:
                booking = {}
                booking_lines = []

                booking = {
                    "pk_booking_id": bok_1["pk_header_id"],
                    "puPickUpAvailFrom_Date": bok_1["b_021_b_pu_avail_from_date"],
                    "b_clientReference_RA_Numbers": bok_1[
                        "b_000_1_b_clientreference_ra_numbers"
                    ],
                    "puCompany": bok_1["b_028_b_pu_company"],
                    "pu_Contact_F_L_Name": bok_1["b_035_b_pu_contact_full_name"],
                    "pu_Email": bok_1["b_037_b_pu_email"],
                    "pu_Phone_Main": bok_1["b_038_b_pu_phone_main"],
                    "pu_Address_Street_1": bok_1["b_029_b_pu_address_street_1"],
                    "pu_Address_street_2": bok_1["b_030_b_pu_address_street_2"],
                    "pu_Address_Country": bok_1["b_034_b_pu_address_country"],
                    "pu_Address_PostalCode": bok_1["b_033_b_pu_address_postalcode"],
                    "pu_Address_State": bok_1["b_031_b_pu_address_state"],
                    "pu_Address_Suburb": bok_1["b_032_b_pu_address_suburb"],
                    "deToCompanyName": bok_1["b_054_b_del_company"],
                    "de_to_Contact_F_LName": bok_1["b_061_b_del_contact_full_name"],
                    "de_Email": bok_1["b_063_b_del_email"],
                    "de_to_Phone_Main": bok_1["b_064_b_del_phone_main"],
                    "de_To_Address_Street_1": bok_1["b_055_b_del_address_street_1"],
                    "de_To_Address_Street_2": bok_1["b_056_b_del_address_street_2"],
                    "de_To_Address_Country": bok_1["b_060_b_del_address_country"],
                    "de_To_Address_PostalCode": bok_1["b_059_b_del_address_postalcode"],
                    "de_To_Address_State": bok_1["b_057_b_del_address_state"],
                    "de_To_Address_Suburb": bok_1["b_058_b_del_address_suburb"],
                    "client_warehouse_code": bok_1["b_client_warehouse_code"],
                    "vx_serviceName": bok_1["b_003_b_service_name"],
                    "kf_client_id": bok_1["fk_client_id"],
                    "b_client_name": bok_1["b_client_name"],
                }

                for bok_2 in bok_2s:
                    bok_2_line = {
                        "fk_booking_id": bok_2["booking_line"]["fk_header_id"],
                        "packagingType": bok_2["booking_line"][
                            "l_001_type_of_packaging"
                        ],
                        "e_qty": bok_2["booking_line"]["l_002_qty"],
                        "e_item": bok_2["booking_line"]["l_003_item"],
                        "e_dimUOM": bok_2["booking_line"]["l_004_dim_UOM"],
                        "e_dimLength": bok_2["booking_line"]["l_005_dim_length"],
                        "e_dimWidth": bok_2["booking_line"]["l_006_dim_width"],
                        "e_dimHeight": bok_2["booking_line"]["l_007_dim_height"],
                        "e_weightUOM": bok_2["booking_line"]["l_008_weight_UOM"],
                        "e_weightPerEach": bok_2["booking_line"][
                            "l_009_weight_per_each"
                        ],
                    }
                    booking_lines.append(bok_2_line)

                fc_log, _ = FC_Log.objects.get_or_create(
                    client_booking_id=bok_1["client_booking_id"],
                    old_quote__isnull=True,
                    new_quote__isnull=True,
                )
                fc_log.old_quote = old_quote
                body = {"booking": booking, "booking_lines": booking_lines}
                _, success, message, quote_set = get_pricing(
                    body=body,
                    booking_id=None,
                    is_pricing_only=True,
                )
                logger.info(
                    f"#519 - Pricing result: success: {success}, message: {message}, results cnt: {quote_set.count()}"
                )

                # Select best quotes(fastest, lowest)
                if quote_set.exists() and quote_set.count() > 1:
                    auto_select_pricing_4_bok(bok_1_obj, quote_set)
                    best_quotes = select_best_options(pricings=quote_set)
                    logger.info(f"#520 - Selected Best Pricings: {best_quotes}")

                # Set Express or Standard
                if best_quotes:
                    json_results = SimpleQuoteSerializer(best_quotes, many=True).data
                    json_results = dme_time_lib.beautify_eta(json_results, best_quotes)

                    if bok_1["success"] == dme_constants.BOK_SUCCESS_4:
                        best_quote = best_quotes[0]
                        bok_1_obj.b_003_b_service_name = best_quote.service_name
                        bok_1_obj.b_001_b_freight_provider = best_quote.freight_provider
                        bok_1_obj.save()
                        fc_log.new_quote = best_quotes[0]
                        fc_log.save()

                    if len(json_results) == 1:
                        json_results[0]["service_name"] = "Standard"
                    else:
                        if float(json_results[0]["cost"]) > float(
                            json_results[1]["cost"]
                        ):
                            json_results[0]["service_name"] = "Express"
                            json_results[1]["service_name"] = "Standard"
                            json_results = [json_results[1], json_results[0]]
                        else:
                            json_results[1]["service_name"] = "Express"
                            json_results[0]["service_name"] = "Standard"
                else:
                    message = f"#521 No Pricing results to select - BOK_1 pk_header_id: {bok_1['pk_header_id']}"
                    logger.error(message)
                    send_email_to_admins("No FC result", message)

                if json_results:
                    if "Plum" in client_name and "_sapb1" in user.username:
                        result = {
                            "success": True,
                            "results": json_results,
                        }

                        if bok_1["success"] == dme_constants.BOK_SUCCESS_3:
                            result[
                                "pricePageUrl"
                            ] = f"http://{settings.WEB_SITE_IP}/price/{bok_1['client_booking_id']}/"
                        elif bok_1["success"] == dme_constants.BOK_SUCCESS_4:
                            result[
                                "pricePageUrl"
                            ] = f"http://{settings.WEB_SITE_IP}/status/{bok_1['client_booking_id']}/"

                        logger.info(f"@8837 - success: True, 201_created")
                        return JsonResponse(
                            result,
                            status=status.HTTP_201_CREATED,
                        )
                    elif "Plum" in client_name and "_magento" in user.username:
                        logger.info(f"@8838 - success: True, 201_created")
                        return JsonResponse(
                            {
                                "success": True,
                                "results": json_results,
                            },
                            status=status.HTTP_201_CREATED,
                        )
                else:
                    logger.info(
                        f"@8839 - success: False, message: Didn't get pricings due to wrong suburb and state"
                    )
                    return JsonResponse(
                        {
                            "success": False,
                            "results": json_results,
                            "message": "Didn't get pricings due to wrong suburb and state",
                        },
                        status=status.HTTP_201_CREATED,
                    )
            else:
                return JsonResponse({"success": True}, status=status.HTTP_201_CREATED)
        else:
            logger.info(f"@8821 BOKS API Error - {bok_1_serializer.errors}")
            return Response(
                {"success": False, "message": bok_1_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except Exception as e:
        logger.info(f"@889 BOKS API Error - {e}")
        trace_error.print()
        return JsonResponse(
            {"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
        )


@transaction.atomic
@api_view(["POST"])
def partial_pricing(request):
    logger.info(f"@810 - pricing request payload: {request.data}")
    user = request.user
    boks_json = request.data
    bok_1 = boks_json["booking"]
    bok_1["pk_header_id"] = str(uuid.uuid4())
    bok_2s = boks_json["booking_lines"]
    json_results = []

    # Find `Client`
    try:
        client_employee = Client_employees.objects.get(fk_id_user_id=user.pk)
        client = client_employee.fk_id_dme_client
    except Exception as e:
        logger.info(f"@811 - client_employee does not exist, {str(e)}")
        message = "You are not allowed to use this api-endpoint."
        return Response(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )

    # Find `Warehouse`
    try:
        warehouse = Client_warehouses.objects.get(fk_id_dme_client=client)
    except Exception as e:
        logger.info(f"@812 Client doesn't have Warehouse(s): {str(e)}")
        return JsonResponse(
            {"success": False, "message": "Client doesn't have Warehouse(s)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find `Suburb` and `State`
    de_postal_code = bok_1.get("b_059_b_del_address_postalcode")

    if not de_postal_code:
        message = "'b_059_b_del_address_postalcode' is required."
        logger.info(f"@813 {message}")
        raise ValidationError(
            {"success": False, "code": "missing_param", "description": message}
        )

    addresses = Utl_suburbs.objects.filter(postal_code=de_postal_code)

    if not addresses.exists():
        message = "Delivery PostalCode is not valid"
        logger.info(f"@814 {message}")
        return Response(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )
    else:
        de_suburb = addresses[0].suburb
        de_state = addresses[0].state

    # Check if has lines
    if len(bok_2s) == 0:
        message = "No lines are provided"
        logger.info(f"@815 {message}")
        return Response(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )

    booking = {
        "pk_booking_id": bok_1["pk_header_id"],
        "puPickUpAvailFrom_Date": str(datetime.now() + timedelta(days=7))[:10],
        "b_clientReference_RA_Numbers": "initial_RA_num",
        "puCompany": warehouse.warehousename,
        "pu_Contact_F_L_Name": "initial_PU_contact",
        "pu_Email": "pu@email.com",
        "pu_Phone_Main": "419294339",
        "pu_Address_Street_1": warehouse.warehouse_address1,
        "pu_Address_street_2": warehouse.warehouse_address2,
        "pu_Address_Country": "Australia",
        "pu_Address_PostalCode": warehouse.warehouse_postal_code,
        "pu_Address_State": warehouse.warehouse_state,
        "pu_Address_Suburb": warehouse.warehouse_suburb,
        "deToCompanyName": "initial_DE_company",
        "de_to_Contact_F_LName": "initial_DE_contact",
        "de_Email": "de@email.com",
        "de_to_Phone_Main": "419294339",
        "de_To_Address_Street_1": "initial_DE_street_1",
        "de_To_Address_Street_2": "",
        "de_To_Address_Country": "Australia",
        "de_To_Address_PostalCode": de_postal_code.upper(),
        "de_To_Address_State": de_state,
        "de_To_Address_Suburb": de_suburb,
        "client_warehouse_code": warehouse.client_warehouse_code,
        "vx_serviceName": "exp",
        "kf_client_id": warehouse.fk_id_dme_client.dme_account_num,
        "b_client_name": client.company_name,
    }

    booking_lines = []

    if "model_number" in bok_2s[0]:  # Product & Child items
        missing_model_numbers = product_oper.find_missing_model_numbers(bok_2s)

        if missing_model_numbers:
            message = f"Missing model numbers - {', '.join(missing_model_numbers)}"
            logger.info(f"@816 {message}")
            return Response(
                {
                    "success": False,
                    "results": [],
                    "message": message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = product_oper.get_product_items(bok_2s)

        for item in items:
            booking_line = {
                "e_type_of_packaging": "Carton"
                if not item.get("e_type_of_packaging")
                else item["e_type_of_packaging"],
                "fk_booking_id": bok_1["pk_header_id"],
                "e_qty": item["qty"],
                "e_item": item["description"],
                "e_dimUOM": item["e_dimUOM"],
                "e_dimLength": item["e_dimLength"],
                "e_dimWidth": item["e_dimWidth"],
                "e_dimHeight": item["e_dimHeight"],
                "e_weightUOM": item["e_weightUOM"],
                "e_weightPerEach": item["e_weightPerEach"],
            }
            booking_lines.append(booking_line)
    else:  # If lines have dimentions
        for bok_2 in bok_2s:
            e_type_of_packaging = (
                "Carton"
                if not bok_2["booking_line"].get("l_001_type_of_packaging")
                else bok_2["booking_line"]["l_001_type_of_packaging"]
            )
            booking_line = {
                "e_type_of_packaging": e_type_of_packaging,
                "fk_booking_id": bok_1["pk_header_id"],
                "e_qty": bok_2["booking_line"]["l_002_qty"],
                "e_item": "initial_item",
                "e_dimUOM": bok_2["booking_line"]["l_004_dim_UOM"],
                "e_dimLength": bok_2["booking_line"]["l_005_dim_length"],
                "e_dimWidth": bok_2["booking_line"]["l_006_dim_width"],
                "e_dimHeight": bok_2["booking_line"]["l_007_dim_height"],
                "e_weightUOM": bok_2["booking_line"]["l_008_weight_UOM"],
                "e_weightPerEach": bok_2["booking_line"]["l_009_weight_per_each"],
            }
            booking_lines.append(booking_line)

    body = {"booking": booking, "booking_lines": booking_lines}
    _, success, message, quote_set = get_pricing(
        body=body, booking_id=None, is_pricing_only=True
    )
    logger.info(
        f"#519 - Pricing result: success: {success}, message: {message}, results cnt: {quote_set}"
    )

    # Select best quotes(fastest, lowest)
    if quote_set.exists() and quote_set.count() > 1:
        best_quotes = select_best_options(pricings=quote_set)
        logger.info(f"#520 - Selected Best Pricings: {best_quotes}")

    # Set Express or Standard
    if quote_set:
        json_results = SimpleQuoteSerializer(best_quotes, many=True).data
        json_results = dme_time_lib.beautify_eta(json_results, best_quotes)

        # delete quote quotes
        quote_set.delete()

        if len(json_results) == 1:
            json_results[0]["service_name"] = "Standard"
        else:
            if float(json_results[0]["cost"]) > float(json_results[1]["cost"]):
                json_results[0]["service_name"] = "Express"
                json_results[1]["service_name"] = "Standard"
                json_results = [json_results[1], json_results[0]]
            else:
                json_results[1]["service_name"] = "Express"
                json_results[0]["service_name"] = "Standard"

    if json_results:
        return Response({"success": True, "results": json_results})
    else:
        message = "Didn't get pricings due to wrong suburb and state"
        logger.info(f"@818 {message}")
        return Response(
            {
                "success": False,
                "results": json_results,
                "message": message,
            }
        )


@api_view(["GET"])
def reprint_label(request):
    """
    get label(already built)
    """
    logger.info(f"@871 User: {request.user.username}")
    logger.info(f"@872 request payload - {request.data}")
    b_client_order_num = request.GET.get("HostOrderNumber")
    b_client_name = request.GET.get("CustomerName")
    sscc = request.GET.get("sscc")

    if not b_client_order_num:
        code = "missing_param"
        description = "'HostOrderNumber' is required."
        raise ValidationError(
            {"success": False, "code": code, "description": description}
        )

    if not b_client_name:
        code = "missing_param"
        description = "'CustomerName' is required."
        raise ValidationError(
            {"success": False, "code": code, "description": description}
        )

    try:
        booking = Bookings.objects.get(
            b_client_order_num=b_client_order_num[5:], b_client_name=b_client_name
        )
    except:
        code = "not_found"
        description = "Order is not found."
        raise ValidationError(
            {"success": False, "code": code, "description": description}
        )

    if sscc:
        is_exist = False
        sscc_line = None
        lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

        for line in lines:
            if line.sscc == sscc:
                is_exist = True
                sscc_line = line

        if not is_exist:
            code = "not_found"
            description = "SSCC is not found."
            raise ValidationError(
                {"success": False, "code": code, "description": description}
            )

    if not sscc and not booking.z_label_url:
        code = "not_ready"
        description = "Label is not ready."
        raise ValidationError(
            {"success": False, "code": code, "description": description}
        )

    if sscc:
        filename = (
            booking.pu_Address_State
            + "_"
            + str(booking.b_bookingID_Visual)
            + "_"
            + str(sscc_line.pk)
            + ".pdf"
        )

        # Build label with Line
        if settings.ENV == "prod":
            label_url = f"/opt/s3_public/pdfs/{filename}"
        else:
            label_url = f"./static/pdfs/{filename}"

        # Convert label into ZPL format
        logger.info(f"@369 - converting LABEL({label_url}) into ZPL format...")
        result = pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

        if not result:
            code = "unknown_status"
            description = (
                "Please contact DME support center. <bookings@deliver-me.com.au>"
            )
            raise Exception(
                {"success": False, "code": code, "description": description}
            )
    else:
        if settings.ENV == "prod":
            label_url = f"/opt/s3_public/pdfs/{booking.z_label_url}"
        else:
            label_url = f"./static/pdfs/{booking.z_label_url}"

        result = pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

        if not result:
            code = "unknown_status"
            description = (
                "Please contact DME support center. <bookings@deliver-me.com.au>"
            )
            raise Exception(
                {"success": False, "code": code, "description": description}
            )

    with open(label_url[:-4] + ".zpl", "rb") as zpl:
        zpl_data = str(b64encode(zpl.read()))[2:-1]

    return Response(
        {
            "success": True,
            "zpl": zpl_data,
        }
    )


@transaction.atomic
@api_view(["POST"])
def manifest_boks(request):
    """
    MANIFEST api
    """
    user = request.user
    request_json = request.data
    logger.info(f"@879 Pusher: {user.username}")
    logger.info(f"@880 Push request - [{request.method}] {request_json}")

    # Required fields
    if not request_json.get("OrderNumbers"):
        message = "'OrderNumbers' is required."
        raise ValidationError(
            {"success": False, "code": "missing_param", "description": message}
        )

    booking_ids = request_json.get("OrderNumbers")
    manifest_url = build_manifest(booking_ids, user.username)

    with open(manifest_url, "rb") as manifest:
        manifest_data = str(b64encode(manifest.read()))

    return Response(
        {
            "success": True,
            "manifest": manifest_data,
        }
    )


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_delivery_status(request):
    client_booking_id = request.GET.get("identifier")
    quote_data = {}

    # 1. Try to find from dme_bookings table
    booking = Bookings.objects.filter(
        b_client_booking_ref_num=client_booking_id
    ).first()

    if booking:
        b_status = booking.b_status
        quote = booking.api_booking_quote
        category = get_status_category_from_status(b_status)

        if not category:
            logger.info(
                f"#301 - unknown_status - client_booking_id={client_booking_id}, status={b_status}"
            )
            return Response(
                {
                    "code": "unknown_status",
                    "message": "Please contact support center!",
                    "step": None,
                    "status": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = {
            "b_bookingID_Visual": booking.b_bookingID_Visual,
            "b_client_order_num": booking.b_client_order_num,
            "b_client_sales_inv_num": booking.b_client_sales_inv_num,
        }

        if quote:
            quote_data = SimpleQuoteSerializer(quote).data
            quote_data["eta_readable"] = get_etd_in_hour(quote) / 24

        if category == "Booked":
            step = 2
        elif category == "Transit":
            step = 3
        elif category == "Complete":
            step = 4
        elif category == "Hold":
            step = 5
        else:
            step = 1

        return Response(
            {
                "step": step,
                "status": b_status,
                "quote": quote_data,
                "booking": booking,
            }
        )

    # 2. Try to find from Bok tables
    bok_1 = BOK_1_headers.objects.filter(client_booking_id=client_booking_id).first()
    booking = {
        "b_client_order_num": bok_1.b_client_order_num,
        "b_client_sales_inv_num": bok_1.b_client_sales_inv_num,
    }
    quote = bok_1.quote

    if quote:
        quote_data = SimpleQuoteSerializer(quote).data
        quote_data["eta_readable"] = get_etd_in_hour(quote) / 24

    if bok_1:
        return Response(
            {"step": 1, "status": None, "quote": quote_data, "booking": booking}
        )

    return Response(
        {
            "code": "does_not_exist",
            "message": "Could not find Delivery!",
            "step": None,
            "status": None,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )
