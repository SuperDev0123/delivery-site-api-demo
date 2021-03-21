import io
import time as t
import uuid
import json
import logging
import requests
import zipfile
from datetime import datetime, date
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
from api.serializers_client import *
from api.serializers import SimpleQuoteSerializer
from api.models import *
from api.common import (
    trace_error,
    constants as dme_constants,
    status_history,
    common_times as dme_time_lib,
)
from api.common.booking_quote import migrate_quote_info_to_booking
from api.fp_apis.utils import get_status_category_from_status, get_etd_in_hour
from api.clients.plum import index as plum
from api.clients.jason_l import index as jason_l
from api.clients.standard import index as standard
from api.clients.operations.index import get_client, get_warehouse


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


class BOK_1_ViewSet(viewsets.ModelViewSet):
    queryset = CostOption.objects.all()
    serializer_class = BOK_1_Serializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        bok_1_headers = BOK_1_headers.objects.all().order_by("-z_createdTimeStamp")[:50]
        serializer = BOK_1_Serializer(bok_1_headers, many=True)
        return Response(serializer.data)

    def create(self, request):
        """
        for BioPak
        """
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

    @action(detail=False, methods=["put"], permission_classes=[AllowAny])
    def update_freight_options(self, request, pk=None):
        """"""
        identifier = request.data.get("client_booking_id", None)
        logger.info(f"[UPDATE_FREIGHT_OPT]: {identifier}")

        if not identifier:
            return Response(
                {"message": "Wrong identifier."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bok_1 = BOK_1_headers.objects.get(client_booking_id=identifier)
            bok_1.b_027_b_pu_address_type = request.data.get("b_027_b_pu_address_type")
            bok_1.b_053_b_del_address_type = request.data.get(
                "b_053_b_del_address_type"
            )
            bok_1.b_019_b_pu_tail_lift = request.data.get("b_019_b_pu_tail_lift")
            bok_1.b_041_b_del_tail_lift = request.data.get("b_041_b_del_tail_lift")
            bok_1.b_072_b_pu_no_of_assists = request.data.get(
                "b_072_b_pu_no_of_assists", 0
            )
            bok_1.b_073_b_del_no_of_assists = request.data.get(
                "b_073_b_del_no_of_assists", 0
            )
            bok_1.b_078_b_pu_location = request.data.get("b_078_b_pu_location")
            bok_1.b_068_b_del_location = request.data.get("b_068_b_del_location")
            bok_1.b_074_b_pu_delivery_access = request.data.get(
                "b_074_b_pu_delivery_access"
            )
            bok_1.b_075_b_del_delivery_access = request.data.get(
                "b_075_b_del_delivery_access"
            )
            bok_1.b_079_b_pu_floor_number = request.data.get(
                "b_079_b_pu_floor_number", 0
            )
            bok_1.b_069_b_del_floor_number = request.data.get(
                "b_069_b_del_floor_number", 0
            )
            bok_1.b_080_b_pu_floor_access_by = request.data.get(
                "b_080_b_pu_floor_access_by"
            )
            bok_1.b_070_b_del_floor_access_by = request.data.get(
                "b_070_b_del_floor_access_by"
            )
            bok_1.b_076_b_pu_service = request.data.get("b_076_b_pu_service")
            bok_1.b_077_b_del_service = request.data.get("b_077_b_del_service")
            bok_1.save()
            res_json = {"success": True, "message": "Freigth options are updated."}

            return Response(res_json, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(
                f"[UPDATE_FREIGHT_OPT] BOK Failure with identifier: {identifier}, reason: {str(e)}"
            )
            return Response({"success": False}, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def get_boks_with_pricings(self, request):
        if settings.ENV == "local":
            t.sleep(2)

        client_booking_id = request.GET["identifier"]
        logger.info(
            f"#490 [get_boks_with_pricings] client_booking_id: {client_booking_id}"
        )

        if not client_booking_id:
            logger.info(f"#491 [get_boks_with_pricings] Error: Wrong identifier.")
            res_json = {"message": "Wrong identifier."}
            return Response(res_json, status=status.HTTP_400_BAD_REQUEST)

        try:
            bok_1 = BOK_1_headers.objects.get(client_booking_id=client_booking_id)
            bok_2s = BOK_2_lines.objects.filter(fk_header_id=bok_1.pk_header_id)
            quote_set = API_booking_quotes.objects.filter(
                fk_booking_id=bok_1.pk_header_id, is_used=False
            )
            client = DME_clients.objects.get(dme_account_num=bok_1.fk_client_id)

            result = BOK_1_Serializer(bok_1).data
            result["bok_2s"] = BOK_2_Serializer(bok_2s, many=True).data
            result["pricings"] = []
            best_quotes = quote_set

            if best_quotes:
                context = {"client_customer_mark_up": client.client_customer_mark_up}
                json_results = SimpleQuoteSerializer(
                    best_quotes, many=True, context=context
                ).data
                json_results = dme_time_lib.beautify_eta(
                    json_results, best_quotes, client
                )
                result["pricings"] = json_results

            res_json = {"message": "Succesfully get bok and pricings.", "data": result}
            logger.info(f"#495 [get_boks_with_pricings] Success!")
            return Response(res_json, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f"#499 [get_boks_with_pricings] Error: {e}")
            trace_error.print()
            return Response(
                {"message": "Couldn't find matching Booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["patch"], permission_classes=[AllowAny])
    def book(self, request):
        if settings.ENV == "local":
            t.sleep(2)

        identifier = request.GET["identifier"]

        if not identifier:
            return Response(
                {"message": "Wrong identifier."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bok_1 = BOK_1_headers.objects.select_related("quote").get(
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
                bok_1.vx_serviceType_XXX = bok_1.quote.service_code
                bok_1.save()

            logger.info(f"@843 [BOOK] BOK success with identifier: {identifier}")
            return Response({"success": True}, status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"@844 [BOOK] BOK Failure with identifier: {identifier}")
            logger.error(f"@845 [BOOK] BOK Failure: {str(e)}")
            return Response({"success": False}, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["delete"], permission_classes=[AllowAny])
    def cancel(self, request):
        if settings.ENV == "local":
            t.sleep(2)

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
        if settings.ENV == "local":
            t.sleep(2)

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


@api_view(["POST"])
def partial_pricing(request):
    LOG_ID = "[PARTIAL PRICING]"
    user = request.user
    logger.info(f"@810 {LOG_ID} Requester: {user.username}")
    logger.info(f"@811 {LOG_ID} Payload: {request.data}")

    try:
        client = get_client(user)
        warehouse = get_warehouse(client)
        dme_account_num = client.dme_account_num

        if dme_account_num == "461162D2-90C7-BF4E-A905-000000000004":  # Plum
            results = plum.partial_pricing(request.data, client, warehouse)
        elif dme_account_num == "1af6bcd2-6148-11eb-ae93-0242ac130002":  # Jason L
            results = jason_l.partial_pricing(request.data, client, warehouse)

        if results:
            logger.info(f"@819 {LOG_ID} Success!")
            return Response({"success": True, "results": results})
        else:
            message = "Pricing cannot be returned due to incorrect address information."
            logger.info(f"@827 {LOG_ID} {message}")
            res_json = {"success": False, "code": "invalid_request", "message": message}
            return Response(res_json, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.info(f"@829 {LOG_ID} Exception: {str(e)}")
        trace_error.print()
        res_json = {"success": False, "message": str(e)}
        return Response(res_json, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "PUT"])
def push_boks(request):
    """
    PUSH api (bok_1, bok_2, bok_3)
    """
    LOG_ID = "[PUSH BOKS]"
    user = request.user
    logger.info(f"@800 {LOG_ID} Requester: {user.username}")
    logger.info(f"@801 {LOG_ID} Payload: {request.data}")

    try:
        client = get_client(user)
        dme_account_num = client.dme_account_num

        if dme_account_num == "461162D2-90C7-BF4E-A905-000000000004":  # Plum
            result = plum.push_boks(
                payload=request.data,
                client=client,
                username=user.username,
                method=request.method,
            )
        elif dme_account_num == "1af6bcd2-6148-11eb-ae93-0242ac130002":  # Jason L
            result = jason_l.push_boks(
                payload=request.data,
                client=client,
                username=user.username,
                method=request.method,
            )
        else:  # Standard Client
            result = standard.push_boks(request.data, client)

        logger.info(f"@828 {LOG_ID} Push BOKS success!, 201_created")
        return JsonResponse(result, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.info(f"@829 {LOG_ID} Exception: {str(e)}")
        trace_error.print()
        res_json = {"success": False, "message": str(e)}
        return Response(res_json, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def scanned(request):
    """
    called as get_label

    request when item(s) is picked(scanned) at warehouse
    should response LABEL if payload is correct
    """
    LOG_ID = "[SCANNED]"
    user = request.user
    logger.info(f"@830 {LOG_ID} Requester: {user.username}")
    logger.info(f"@831 {LOG_ID} Payload: {request.data}")

    try:
        client = get_client(user)
        dme_account_num = client.dme_account_num

        if dme_account_num == "461162D2-90C7-BF4E-A905-000000000004":  # Plum
            result = plum.scanned(payload=request.data, client=client)
        elif dme_account_num == "1af6bcd2-6148-11eb-ae93-0242ac130002":  # Jason L
            result = jason_l.scanned(payload=request.data, client=client)

        message = f"Successfully scanned."
        logger.info(f"#838 {LOG_ID} {message}")
        return JsonResponse(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.info(f"@839 {LOG_ID} Exception: {str(e)}")
        trace_error.print()
        res_json = {"success": False, "message": str(e)}
        return Response(res_json, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def ready_boks(request):
    """
    When it is ready(picked all items) on Warehouse
    """
    LOG_ID = "[READY]"
    user = request.user
    logger.info(f"@840 {LOG_ID} Requester: {user.username}")
    logger.info(f"@841 {LOG_ID} Payload: {request.data}")

    try:
        client = get_client(user)
        dme_account_num = client.dme_account_num

        if dme_account_num == "461162D2-90C7-BF4E-A905-000000000004":  # Plum
            result = plum.ready_boks(payload=request.data, client=client)
        elif dme_account_num == "1af6bcd2-6148-11eb-ae93-0242ac130002":  # Jason L
            result = jason_l.ready_boks(payload=request.data, client=client)

        logger.info(f"#848 {LOG_ID} {result}")
        return Response({"success": True, "message": result})
    except Exception as e:
        logger.info(f"@849 {LOG_ID} Exception: {str(e)}")
        trace_error.print()
        res_json = {"success": False, "message": str(e)}
        return Response(res_json, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def reprint_label(request):
    """
    get label(already built)
    """
    LOG_ID = "[REPRINT]"
    user = request.user
    logger.info(f"@850 {LOG_ID} Requester: {user.username}")
    logger.info(f"@851 {LOG_ID} params: {request.GET}")

    try:
        client = get_client(user)
        dme_account_num = client.dme_account_num

        if dme_account_num == "461162D2-90C7-BF4E-A905-000000000004":  # Plum
            result = plum.reprint_label(params=request.GET, client=client)
        elif dme_account_num == "1af6bcd2-6148-11eb-ae93-0242ac130002":  # Jason L
            result = jason_l.reprint_label(params=request.GET, client=client)

        logger.info(f"#858 {LOG_ID} {result}")
        return Response(result)
    except Exception as e:
        logger.info(f"@859 {LOG_ID} Exception: {str(e)}")
        trace_error.print()
        res_json = {"success": False, "message": str(e)}
        return Response(res_json, status=status.HTTP_400_BAD_REQUEST)


@transaction.atomic
@api_view(["POST"])
def manifest_boks(request):
    """
    MANIFEST api
    """
    LOG_ID = "[MANIFEST]"
    user = request.user
    logger.info(f"@860 {LOG_ID} Requester: {user.username}")
    logger.info(f"@861 {LOG_ID} Payload: {request.data}")

    try:
        client = get_client(user)
        dme_account_num = client.dme_account_num

        if dme_account_num == "461162D2-90C7-BF4E-A905-000000000004":  # Plum
            result = plum.manifest(
                payload=request.data,
                client=client,
                username=user.username,
            )
        elif dme_account_num == "1af6bcd2-6148-11eb-ae93-0242ac130002":  # Jason L
            result = jason_l.manifest(
                payload=request.data,
                client=client,
                username=user.username,
            )

        logger.info(f"#858 {LOG_ID} {result}")
        return Response(result)
    except Exception as e:
        logger.info(f"@859 {LOG_ID} Exception: {str(e)}")
        trace_error.print()
        res_json = {"success": False, "message": str(e)}
        return Response(res_json, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_delivery_status(request):
    client_booking_id = request.GET.get("identifier")
    quote_data = {}

    # 1. Try to find from dme_bookings table
    booking = Bookings.objects.filter(
        b_client_booking_ref_num=client_booking_id
    ).first()
    client = DME_clients.objects.get(dme_account_num=booking.kf_client_id)

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
                    "message": "Please contact DME support center. <bookings@deliver-me.com.au>",
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
        json_quote = None

        if quote:
            context = {"client_customer_mark_up": client.client_customer_mark_up}
            quote_data = SimpleQuoteSerializer(quote, context=context).data
            json_quote = dme_time_lib.beautify_eta([quote_data], [quote], client)[0]

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
            b_status = "Processing"

        return Response(
            {
                "step": step,
                "status": b_status,
                "quote": json_quote,
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
    json_quote = None

    if quote:
        context = {"client_customer_mark_up": client.client_customer_mark_up}
        quote_data = SimpleQuoteSerializer(quote, context=context).data
        json_quote = dme_time_lib.beautify_eta([quote_data], [quote], client)[0]

    if bok_1:
        return Response(
            {"step": 1, "status": None, "quote": json_quote, "booking": booking}
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
