import time
import math
import uuid
import json
import logging
import requests
from datetime import datetime

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
from api.fp_apis.utils import (
    select_best_options,
    get_status_category_from_status,
    auto_select_pricing_4_bok,
)
from api.operations import push_operations, product_operations as product_oper


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
        identifier = request.GET["identifier"]

        if not identifier:
            return Response(
                {"message": "Wrong identifier."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bok_1 = BOK_1_headers.objects.get(client_booking_id=identifier)
            bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)
            quote_set = API_booking_quotes.objects.filter(
                fk_booking_id=bok_1.pk_header_id
            )
            client = DME_clients.objects.get(dme_account_num=bok_1.fk_client_id)

            result = BOK_1_Serializer(bok_1).data
            result["client_customer_mark_up"] = client.client_customer_mark_up
            result["bok_2s"] = BOK_2_Serializer(bok_2s, many=True).data

            # Select best quotes(fastest, lowest)
            if quote_set.exists() and quote_set.count() > 1:
                best_quotes = quote_set
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
            bok_1 = BOK_1_headers.objects.get(client_booking_id=identifier)
            bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)

            for bok_2 in bok_2s:
                bok_2.success = dme_constants.BOK_SUCCESS_4
                bok_2.save()

            bok_1.success = dme_constants.BOK_SUCCESS_4
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
            API_booking_quotes.objects.filter(fk_booking_id=bok_1.pk_header_id).delete()
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

            # TODO: update bok_2 and bok_3

            return Response({"success": True}, status.HTTP_200_OK)
        except:
            return Response({"success": False}, status.HTTP_400_BAD_REQUEST)


class BOK_2_ViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        bok_2_lines = BOK_2_lines.objects.all().order_by("-z_createdTimeStamp")[:50]
        serializer = BOK_2_Serializer(bok_2_lines, many=True)
        return Response(serializer.data)

    def create(self, request):
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
    bok_1.success = dme_constants.BOK_SUCCESS_4
    bok_1.save()

    bok_2s = BOK_2_lines.objects.filter(fk_header_id=pk_header_id)
    for bok_2 in bok_2s:
        bok_2.success = dme_constants.BOK_SUCCESS_4
        bok_2.save()

    bok_3s = BOK_3_lines_data.objects.filter(fk_header_id=pk_header_id)
    for bok_3 in bok_3s:
        bok_3.success = dme_constants.BOK_SUCCESS_4
        bok_3.save()

    # create status history
    status_history.create_4_bok(bok_1.pk_header_id, "Ordered", request.user.username)

    logger.info(f"#823 Order success")
    return Response(
        {"success": True},
        status=status.HTTP_200_OK,
    )


@transaction.atomic
@api_view(["POST", "PUT"])
def picked_boks(request):
    """
    request when item(s) is picked at warehouse
    """
    user = request.user
    logger.info(f"@890 Picked by: {user.username}")
    b_client_order_num = request.data.get("b_client_order_num")
    picked_items = request.data.get("picked_items")
    fk_client_id = request.data.get("fk_client_id")
    code = None
    message = None

    # Check required params are included
    if not b_client_order_num:
        code = "missing_param"
        message = "'b_client_order_num' is required."

    if not picked_items:
        code = "missing_param"
        message = "'picked_items' is required."

    if not fk_client_id:
        code = "missing_param"
        message = "'fk_client_id' is required."

    if message:
        raise ValidationError({"success": False, "code": code, "description": message})

    # Check if order does exist
    bok_1s = BOK_1_headers.objects.filter(
        fk_client_id=fk_client_id,
        b_client_order_num=b_client_order_num,
    )

    if not bok_1s.exists():
        code = "invalid_param"
        message = (
            "Order does not exist. 'fk_client_id' or 'b_client_order_num' is invalid."
        )
        raise ValidationError({"success": False, "code": code, "description": message})
    else:
        pk_header_id = bok_1s.first().pk_header_id
        bok_2s = BOK_2_lines.objects.filter(fk_header_id=pk_header_id)
        model_numbers = bok_2s.values_list("e_item_type", flat=True)

    # Check invalid model numbers
    invalid_model_numbers = []

    for item in picked_items:
        if "model_number" in item and not item["model_number"] in model_numbers:
            invalid_model_numbers.append(item["model_number"])
        elif "is_repacked" in item and "items" in item and item["items"]:
            for repacked_item in item["items"]:
                if (
                    "model_number" in repacked_item
                    and not repacked_item["model_number"] in model_numbers
                ):
                    invalid_model_numbers.append(repacked_item["model_number"])
                elif not "model_number" in repacked_item:
                    code = "invalid_repacked_item"
                    message = f"There is a repacked item which doesn`t have 'model_number' information. Invalid item: {json.dumps(item)}"
                    raise ValidationError(
                        {"success": False, "code": code, "description": message}
                    )
        elif not "model_number" in item:
            code = "invalid_item"
            message = f"There is an item which doesn`t have 'model_number' information. Invalid item: {json.dumps(item)}"
            raise ValidationError(
                {"success": False, "code": code, "description": message}
            )

    if invalid_model_numbers:
        code = "invalid_param"
        message = f"'{', '.join(invalid_model_numbers)}' are invalid model_numbers for this order."
        raise ValidationError({"success": False, "code": code, "description": message})

    # Check missing SSCC
    for item in picked_items:
        if not "sscc" in item:
            code = "missing_sscc"
            message = f"There is an item which doesn`t have 'sscc' information. Invalid item: {json.dumps(item)}"
            raise ValidationError(
                {"success": False, "code": code, "description": message}
            )

    for item in picked_items:
        if "model_number" in item:
            bok_2 = bok_2s.get(e_item_type=item["model_number"])
            bok_2.sscc = item["sscc"]
            bok_2.picked_up_timestamp = item["timestamp"]
            bok_2.save()
        else:
            new_bok_2 = BOK_2_lines()
            new_bok_2.fk_header_id = pk_header_id
            new_bok_2.pk_booking_lines_id = str(uuid.uuid4())
            new_bok_2.l_001_type_of_packaging = item["package_type"]
            new_bok_2.l_002_qty = 1
            new_bok_2.l_003_item = "Repacked Item"
            new_bok_2.l_004_dim_UOM = item["demensions"]["unit"]
            new_bok_2.l_005_dim_length = item["demensions"]["length"]
            new_bok_2.l_006_dim_width = item["demensions"]["width"]
            new_bok_2.l_007_dim_height = item["demensions"]["height"]
            new_bok_2.l_008_weight_UOM = item["weight"]["unit"]
            new_bok_2.l_009_weight_per_each = item["weight"]["weight"]
            new_bok_2.sscc = item["sscc"]
            new_bok_2.picked_up_timestamp = item["timestamp"]
            new_bok_2.success = 3
            new_bok_2.save()

            model_numbers = []
            for repacked_item in item["items"]:
                model_numbers.append(repacked_item["model_number"])
                bok_2 = bok_2s.get(e_item_type=repacked_item["model_number"])
                bok_2.is_deleted = True
                bok_2.save()

            new_bok_3 = BOK_3_lines_data()
            new_bok_3.fk_header_id = pk_header_id
            new_bok_3.fk_booking_lines_id = new_bok_2.pk_booking_lines_id
            new_bok_3.ld_002_model_number = ",".join(model_numbers)
            new_bok_3.ld_003_item_description = "Repacked"
            new_bok_3.ld_008_client_ref_number = ",".join(model_numbers)
            new_bok_3.success = 3
            new_bok_3.save()

    return Response({"success": True, "message": "Successfully picked at Warehouse"})


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
    best_quotes = None
    json_results = []
    logger.info(f"@880 Push request payload - {boks_json}")

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
        logger.info(f"@811 - client_employee does not exist, {str(e)}")
        message = "You are not allowed to use this api-endpoint."
        logger.info(message)
        return Response(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )

    # Check required fields
    if "Plum" in client_name and "_sapb1" in user.username:
        if not "b_client_order_num" in bok_1 or (
            "b_client_order_num" in bok_1 and not bok_1["b_client_order_num"]
        ):
            message = "'b_client_order_num' is required."
            logger.info(message)
            return Response(
                {"success": False, "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )
    elif "Plum" in client_name and "_magento" in user.username:
        if not "client_booking_id" in bok_1 or (
            "client_booking_id" in bok_1 and not bok_1["client_booking_id"]
        ):
            message = "'client_booking_id' is required."
            logger.info(message)
            return Response(
                {"success": False, "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Check if already pushed 'b_client_order_num', then return URL only
    if request.method == "POST" and "Plum" in client_name and "_sapb1" in user.username:
        if (
            bok_1["b_client_order_num"][0] != "Q"
            or bok_1["b_client_order_num"][1] != "_"
        ):
            old_bok_1s = BOK_1_headers.objects.filter(
                fk_client_id=client.dme_account_num,
                b_client_order_num=bok_1["b_client_order_num"],
            )

            if old_bok_1s.exists():
                if int(old_bok_1s[0].success) == int(dme_constants.BOK_SUCCESS_3):
                    return JsonResponse(
                        {
                            "success": True,
                            "results": [],
                            "pricePageUrl": f"http://{settings.WEB_SITE_IP}/price/{old_bok_1s[0].client_booking_id}/",
                        },
                        status=status.HTTP_201_CREATED,
                    )
                elif int(old_bok_1s[0].success) == int(dme_constants.BOK_SUCCESS_4):
                    return JsonResponse(
                        {
                            "success": True,
                            "results": [],
                            "pricePageUrl": f"http://{settings.WEB_SITE_IP}/status/{old_bok_1s[0].client_booking_id}/",
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
                API_booking_quotes.objects.filter(fk_booking_id=pk_header_id).delete()

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
                    if (
                        bok_1["b_client_order_num"][0] == "Q"
                        and bok_1["b_client_order_num"][1] == "_"
                    ):
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
                bok_1["b_038_b_pu_phone_main"] = "419294339"

            if not bok_1.get("b_029_b_pu_address_street_1"):
                bok_1["b_029_b_pu_address_street_1"] = warehouse.warehouse_address1

            if not bok_1.get("b_030_b_pu_address_street_2"):
                bok_1["b_030_b_pu_address_street_2"] = warehouse.warehouse_address2

            if not bok_1.get("b_034_b_pu_address_country"):
                bok_1["b_034_b_pu_address_country"] = "Australia"

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
                bok_1["b_064_b_del_phone_main"] = "419294339"

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
        else:
            bok_1["success"] = dme_constants.BOK_SUCCESS_2

        bok_1_serializer = BOK_1_Serializer(data=bok_1)
        if bok_1_serializer.is_valid():
            # Save bok_2s
            if "model_number" in bok_2s[0]:  # Product & Child items
                items = product_oper.get_product_items(bok_2s)
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

            if bok_1["success"] == dme_constants.BOK_SUCCESS_3:
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

                if json_results:
                    if "Plum" in client_name and "_sapb1" in user.username:
                        return JsonResponse(
                            {
                                "success": True,
                                "results": json_results,
                                "pricePageUrl": f"http://{settings.WEB_SITE_IP}/price/{bok_1['client_booking_id']}/",
                                "statusPageUrl": f"http://{settings.WEB_SITE_IP}/status/{bok_1['client_booking_id']}/",
                            },
                            status=status.HTTP_201_CREATED,
                        )
                    elif "Plum" in client_name and "_magento" in user.username:
                        return JsonResponse(
                            {
                                "success": True,
                                "results": json_results,
                            },
                            status=status.HTTP_201_CREATED,
                        )
                else:
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
@permission_classes((AllowAny,))
def get_delivery_status(request):
    client_booking_id = request.GET.get("identifier")

    # 1. Try to find from dme_bookings table
    bookings = Bookings.objects.filter(b_client_booking_ref_num=client_booking_id)

    if bookings.exists():
        b_status = bookings.first().b_status
        category = get_status_category_from_status(b_status)

        if category:
            if category == "Booked":
                return Response({"step": 2, "status": b_status})
            elif category == "Transit":
                return Response({"step": 3, "status": b_status})
            elif category == "Delivered":
                return Response({"step": 4, "status": b_status})
            elif category == "Futile":
                return Response({"step": 5, "status": b_status})

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

    # 2. Try to find from Bok tables
    bok_1s = BOK_1_headers.objects.filter(client_booking_id=client_booking_id)

    if bok_1s.exists():
        return Response({"step": 1, "status": None})

    return Response(
        {
            "code": "does_not_exist",
            "message": "Could not find Delivery!",
            "step": None,
            "status": None,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )
