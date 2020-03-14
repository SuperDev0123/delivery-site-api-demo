import uuid
import json
import logging

from django.http import JsonResponse
from rest_framework import views, serializers, status
from rest_framework.response import Response
from rest_framework import authentication, permissions, viewsets
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from .serializers_api import *
from .models import *

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
        serializer = BOK_1_Serializer(data=bok_1_header)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"@841 BOK_1 POST - {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BOK_2_ViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        bok_2_lines = BOK_2_lines.objects.all().order_by("-z_createdTimeStamp")[:50]
        serializer = BOK_2_Serializer(bok_2_lines, many=True)
        return Response(serializer.data)

    def create(self, request):
        bok_2_line = request.data
        bok_2_line["v_client_pk_consigment_num"] = bok_2_line["fk_header_id"]
        serializer = BOK_2_Serializer(data=bok_2_line)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"@842 BOK_2 POST - {serializer.errors}")
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
def boks(request):
    boks_json = request.data
    bok_1 = boks_json["booking"]
    bok_2s = boks_json["booking_lines"]

    try:
        # Save bok_1
        try:
            warehouse = Client_warehouses.objects.get(
                client_warehouse_code=bok_1["b_client_warehouse_code"]
            )
        except Client_warehouses.DoesNotExist:
            logger.error(
                f"@881 BOKS API Error - : Warehouse code is not valid({bok_1['b_client_warehouse_code']}"
            )
            return JsonResponse(
                {"success": False, "message": "Warehouse code is not valid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"@882 BOKS API Error - {e}")
            return JsonResponse(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bok_1["fk_client_warehouse"] = warehouse.pk_id_client_warehouses
        bok_1["success"] = 2

        if bok_1["fk_client_id"] == "461162D2-90C7-BF4E-A905-000000000002":
            bok_1["b_001_b_freight_provider"] = "DHL"

        if BOK_1_headers.objects.filter(pk_header_id=bok_1["pk_header_id"]).count() > 0:
            logger.error(f"@883 BOKS API Error - Same object is already exist.")
            return JsonResponse(
                {"success": False, "message": "Same object is already exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bok_1_serializer = BOK_1_Serializer(data=bok_1)
        if bok_1_serializer.is_valid():
            bok_1_serializer.save()

            # Save bok_2
            for bok_2 in bok_2s:
                bok_3s = bok_2["booking_lines_data"]
                bok_2["booking_line"]["success"] = 2
                bok_2["booking_line"]["fk_header_id"] = bok_1["pk_header_id"]
                bok_2["booking_line"]["v_client_pk_consigment_num"] = bok_1[
                    "pk_header_id"
                ]
                bok_2["booking_line"]["pk_booking_lines_id"] = str(uuid.uuid1())

                bok_2_serializer = BOK_2_Serializer(data=bok_2["booking_line"])
                if bok_2_serializer.is_valid():
                    bok_2_serializer.save()
                else:
                    logger.error(f"@8822 BOKS API Error - {bok_2_serializer.errors}")
                    return Response(
                        bok_2_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                # Save bok_3
                for bok_3 in bok_3s:
                    bok_3["success"] = 2
                    bok_3["fk_header_id"] = bok_1["pk_header_id"]
                    bok_3["fk_booking_lines_id"] = bok_2["booking_line"][
                        "pk_booking_lines_id"
                    ]
                    bok_3["v_client_pk_consigment_num"] = bok_1["pk_header_id"]

                    bok_3_serializer = BOK_3_Serializer(data=bok_3)
                    if bok_3_serializer.is_valid():
                        bok_3_serializer.save()
                    else:
                        logger.error(
                            f"@8823 BOKS API Error - {bok_3_serializer.errors}"
                        )
                        return Response(
                            bok_3_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                        )
            return JsonResponse({"success": True}, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"@8821 BOKS API Error - {bok_1_serializer.errors}")
            return Response(bok_1_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"@883 BOKS API Error - {e}")
        return JsonResponse(
            {"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
        )
