import re
import os
import io
from collections import OrderedDict
import pytz
import json
import uuid
import time
import math
import logging
import operator
import requests
import tempfile
import zipfile
from base64 import b64encode
from wsgiref.util import FileWrapper
from datetime import datetime, date, timedelta
from time import gmtime, strftime
from ast import literal_eval
from functools import reduce
from pydash import _
from django_rest_passwordreset.signals import (
    reset_password_token_created,
    post_password_reset,
    pre_password_reset,
)

from django.shortcuts import render
from django.core import serializers, files
from django.http import HttpResponse, JsonResponse, QueryDict
from django.db.models import Q, Case, When, Count, F, Sum
from django.db import connection
from django.utils import timezone
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, views, status, authentication, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    action,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.exceptions import ValidationError

from api.serializers import *
from api.models import *
from api.base.viewsets import *
from api.utils import (
    build_xml,
    build_pdf,
    build_xls_and_send,
    make_3digit,
    get_sydney_now_time,
    get_client_name,
    calc_collect_after_status_change,
    tables_in_query,
    get_clientname,
)
from api.operations.manifests.index import build_manifest
from api.operations.csv.index import build_csv
from api.operations.email_senders import send_booking_status_email
from api.operations.labels.index import build_label as build_label_oper
from api.operations.booking.auto_augment import auto_augment as auto_augment_oper
from api.operations.booking.cancel import cancel_book as cancel_book_oper
from api.fp_apis.utils import (
    get_dme_status_from_fp_status,
    get_status_category_from_status,
    gen_consignment_num,
)
from api.fp_apis.constants import SPECIAL_FPS
from api.fp_apis.operations.tracking import create_fp_status_history
from api.outputs import tempo
from api.outputs.email import send_email
from api.common import status_history
from api.common.common_times import convert_to_UTC_tz, TIME_DIFFERENCE
from api.common.postal_code import get_postal_codes
from api.common.booking_quote import set_booking_quote
from api.common.constants import BOOKING_FIELDS_4_ALLBOOKING_TABLE
from api.stats.pricing import analyse_booking_quotes_table
from api.file_operations import (
    uploads as upload_lib,
    delete as delete_lib,
    downloads as download_libs,
)
from api.file_operations.operations import doesFileExist
from api.helpers.cubic import get_cubic_meter
from api.helpers.filter import filter_bookings_by_columns
from api.convertors.pdf import pdf_merge, rotate_pdf, pdf_to_zpl
from api.operations.packing.booking import (
    reset_repack as booking_reset_repack,
    auto_repack as booking_auto_repack,
    manual_repack as booking_manual_repack,
)
from api.operations.booking.parent_child import get_run_out_bookings
from api.operations.booking.line_refs import (
    get_gapRas,
    get_clientRefNumbers,
    get_lines_in_bulk,
)

if settings.ENV == "local":
    S3_URL = "./static"
elif settings.ENV == "dev":
    S3_URL = "/opt/s3_public"
elif settings.ENV == "prod":
    S3_URL = "/opt/s3_public"

logger = logging.getLogger(__name__)


@receiver(reset_password_token_created)
def password_reset_token_created(
    sender, instance, reset_password_token, *args, **kwargs
):
    context = {
        "current_user": reset_password_token.user,
        "username": reset_password_token.user.username,
        "email": reset_password_token.user.email,
        "reset_password_url": f"{settings.WEB_SITE_URL}/reset-password?token="
        + reset_password_token.key,
    }

    try:
        filepath = settings.EMAIL_ROOT + "/user_reset_password.html"
    except MultiValueDictKeyError:
        logger.info("Error #101: Either the file is missing or not readable")

    email_html_message = render_to_string(
        settings.EMAIL_ROOT + "/user_reset_password.html", context
    )

    subject = f"Reset Your Password"
    mime_type = "html"

    try:
        send_email([context["email"]], [], subject, email_html_message, None, mime_type)
    except Exception as e:
        logger.info(f"Error #102: {e}")


class UserViewSet(viewsets.ViewSet):
    @action(detail=True, methods=["get"])
    def get(self, request, pk, format=None):
        return_data = []
        try:
            resultObjects = []
            resultObject = User.objects.get(pk=pk)

            return_data.append(
                {
                    "id": resultObject.id,
                    "first_name": resultObject.first_name,
                    "last_name": resultObject.last_name,
                    "username": resultObject.username,
                    "email": resultObject.email,
                    "last_login": resultObject.last_login,
                    "is_staff": resultObject.is_staff,
                    "is_active": resultObject.is_active,
                }
            )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print("@Exception", e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = User.objects.create(
                fk_idEmailParent=request.data["fk_idEmailParent"],
                emailName=request.data["emailName"],
                emailBody=request.data["emailBody"],
                sectionName=request.data["sectionName"],
                emailBodyRepeatEven=request.data["emailBodyRepeatEven"],
                emailBodyRepeatOdd=request.data["emailBodyRepeatOdd"],
                whenAttachmentUnavailable=request.data["whenAttachmentUnavailable"],
            )

            return JsonResponse({"results": resultObjects})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=True, methods=["put"])
    def edit(self, request, pk, format=None):
        user = User.objects.get(pk=pk)

        try:
            User.objects.filter(pk=pk).update(is_active=request.data["is_active"])
            dme_employee = DME_employees.objects.filter(fk_id_user=user.id).first()
            client_employee = Client_employees.objects.filter(
                fk_id_user=user.id
            ).first()

            if dme_employee is not None:
                dme_employee.status_time = str(datetime.now())
                dme_employee.save()

            if client_employee is not None:
                client_employee.status_time = str(datetime.now())
                client_employee.save()

            return JsonResponse({"results": request.data})
            # if serializer.is_valid():
            # try:
            # serializer.save()
            # return Response(serializer.data)
            # except Exception as e:
            # print('%s (%s)' % (e.message, type(e)))
            # return Response({"results": e.message})
            # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({"results": str(e)})
            # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete(self, request, pk, format=None):
        user = User.objects.get(pk=pk)

        try:
            # user.delete()
            return JsonResponse({"results": fp_freight_providers})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def username(self, request, format=None):
        user_id = self.request.user.id
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()
        if dme_employee is not None:
            return JsonResponse(
                {
                    "username": request.user.username,
                    "clientname": "dme",
                }
            )
        else:
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client = DME_clients.objects.get(
                pk_id_dme_client=client_employee.fk_id_dme_client_id
            )
            return JsonResponse(
                {
                    "username": request.user.username,
                    "clientname": client.company_name,
                    "clientId": client.dme_account_num,
                    "clientPK": client.pk_id_dme_client,
                }
            )

    @action(detail=False, methods=["get"])
    def get_clients(self, request, format=None):
        user_id = self.request.user.id
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            user_type = "DME"
            dme_clients = DME_clients.objects.all()
        else:
            user_type = "CLIENT"
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client_employee_role = client_employee.get_role()
            dme_clients = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            )

        if not dme_clients.exists():
            return JsonResponse({"dme_clients": []})
        else:
            return_data = []
            if user_type == "DME":

                return_data = [
                    {
                        "pk_id_dme_client": 0,
                        "company_name": "dme",
                        "dme_account_num": "dme_account_num",
                        "current_freight_provider": "*",
                        "client_filter_date_field": "0",
                        "client_mark_up_percent": "0",
                        "client_min_markup_startingcostvalue": "0",
                        "client_min_markup_value": "0",
                        "augment_pu_by_time": "0",
                        "augment_pu_available_time": "0",
                        "num_client_products": 0,
                    }
                ]

            for client in dme_clients:
                num_client_products = len(
                    Client_Products.objects.filter(
                        fk_id_dme_client=client.pk_id_dme_client
                    )
                )
                return_data.append(
                    {
                        "pk_id_dme_client": client.pk_id_dme_client,
                        "company_name": client.company_name,
                        "dme_account_num": client.dme_account_num,
                        "current_freight_provider": client.current_freight_provider,
                        "client_filter_date_field": client.client_filter_date_field,
                        "client_mark_up_percent": client.client_mark_up_percent,
                        "client_min_markup_startingcostvalue": client.client_min_markup_startingcostvalue,
                        "client_min_markup_value": client.client_min_markup_value,
                        "augment_pu_by_time": client.augment_pu_by_time,
                        "augment_pu_available_time": client.augment_pu_available_time,
                        "num_client_products": num_client_products,
                    }
                )

            return JsonResponse({"dme_clients": return_data})

    @action(detail=False, methods=["get"])
    def get_user_date_filter_field(self, request, pk=None):
        user_id = self.request.user.id
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            return JsonResponse({"user_date_filter_field": "z_CreatedTimestamp"})
        else:
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client = DME_clients.objects.get(
                pk_id_dme_client=client_employee.fk_id_dme_client_id
            )
            return JsonResponse(
                {"user_date_filter_field": client.client_filter_date_field}
            )

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []
        client_pk = self.request.query_params.get("clientPK", None)

        if client_pk is not None:
            filter_data = Client_employees.objects.filter(
                fk_id_dme_client_id=int(client_pk)
            )

            filter_arr = []
            for data in filter_data:
                filter_arr.append(data.fk_id_user_id)

        try:
            resultObjects = []
            if len(filter_arr) == 0:
                resultObjects = User.objects.all().order_by("username")
            else:
                resultObjects = User.objects.filter(pk__in=filter_arr).order_by(
                    "username"
                )
            for resultObject in resultObjects:
                dme_employee = DME_employees.objects.filter(
                    fk_id_user=resultObject.id
                ).first()
                client_employee = Client_employees.objects.filter(
                    fk_id_user=resultObject.id
                ).first()

                if dme_employee is not None:
                    status_time = dme_employee.status_time

                if client_employee is not None:
                    status_time = client_employee.status_time

                return_data.append(
                    {
                        "id": resultObject.id,
                        "first_name": resultObject.first_name,
                        "last_name": resultObject.last_name,
                        "username": resultObject.username,
                        "email": resultObject.email,
                        "last_login": resultObject.last_login,
                        "is_staff": resultObject.is_staff,
                        "is_active": resultObject.is_active,
                        "status_time": status_time,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            logger.info(f"Error #502: {e}")
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["get"])
    def get_created_for_infos(self, request, pk=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id)

        if dme_employee:
            client_employees = Client_employees.objects.filter(
                email__isnull=False
            ).order_by("name_first")
            company_name = "dme"
        else:
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()
            client_employees = (
                Client_employees.objects.filter(
                    fk_id_dme_client_id=client.pk_id_dme_client, email__isnull=False
                )
                .prefetch_related("fk_id_dme_client")
                .order_by("name_first")
            )
            company_name = client_employee.fk_id_dme_client.company_name

        results = []
        for client_employee in client_employees:
            result = {
                "id": client_employee.pk_id_client_emp,
                "name_first": client_employee.name_first,
                "name_last": client_employee.name_last,
                "email": client_employee.email,
                "company_name": client_employee.fk_id_dme_client.company_name,
            }
            results.append(result)

        return JsonResponse({"success": True, "results": results})


class BookingsViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer

    @action(detail=False, methods=["get"])
    def get_bookings(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id)

        # Initialize values:
        errors_to_correct = 0
        missing_labels = 0
        to_manifest = 0
        to_process = 0
        closed = 0
        unprinted_labels = 0
        client = None
        client_employee_role = None

        if dme_employee.exists():
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client_employee_role = client_employee.get_role()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()

        start_date = self.request.query_params.get("startDate", None)

        if start_date == "*":
            search_type = "ALL"
        else:
            search_type = "FILTER"
            end_date = self.request.query_params.get("endDate", None)

        if search_type == "FILTER":
            first_date = datetime.strptime(start_date, "%Y-%m-%d")
            last_date = datetime.strptime(end_date, "%Y-%m-%d")
            last_date = last_date.replace(hour=23, minute=59, second=59)

        warehouse_id = self.request.query_params.get("warehouseId", None)
        fp_id = self.request.query_params.get("fpId", None)
        sort_field = self.request.query_params.get("sortField", None)
        column_filters = self.request.query_params.get("columnFilters", None)
        column_filters = json.loads(column_filters or "{}")
        active_tab_index = self.request.query_params.get("activeTabInd", None)
        active_tab_index = json.loads(active_tab_index or "{}")
        simple_search_keyword = self.request.query_params.get(
            "simpleSearchKeyword", None
        )
        download_option = self.request.query_params.get("downloadOption", None)
        client_pk = self.request.query_params.get("clientPK", None)
        page_item_cnt = self.request.query_params.get("pageItemCnt", 10)
        page_ind = self.request.query_params.get("pageInd", 0)
        dme_status = self.request.query_params.get("dmeStatus", None)
        multi_find_field = self.request.query_params.get("multiFindField", None)
        multi_find_values = self.request.query_params.get("multiFindValues", "")
        project_name = self.request.query_params.get("projectName", None)
        booking_ids = self.request.query_params.get("bookingIds", None)

        if multi_find_values:
            multi_find_values = multi_find_values.split(", ")

        if booking_ids:
            booking_ids = booking_ids.split(", ")

        # item_count_per_page = self.request.query_params.get('itemCountPerPage', 10)

        # if user_type == 'CLIENT':
        #     print('@01 - Client filter: ', client.dme_account_num)
        # else:
        #     print('@01 - DME user')

        # if start_date == '*':
        #     print('@02 - Date filter: ', start_date)
        # else:
        #     print('@02 - Date filter: ', start_date, end_date, first_date, last_date)

        # print('@03 - Warehouse ID filter: ', warehouse_id)
        # print('@04 - Sort field: ', sort_field)

        # if user_type == 'CLIENT':
        #     print('@05 - Company name: ', client.company_name)
        # else:
        #     print('@05 - Company name: DME')

        # print('@06 - active_tab_index: ', active_tab_index)
        # print('@07 - Simple search keyword: ', simple_search_keyword)
        # print('@08 - Download Option: ', download_option)
        # print('@09 - Client PK: ', client_pk)
        # print("@010 - MultiFind Field: ", multi_find_field)
        # print("@011 - MultiFind Values: ", multi_find_values)

        # DME & Client filter
        if user_type == "DME":
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == "company":
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == "warehouse":
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(
                    kf_client_id=client.dme_account_num,
                    fk_client_warehouse_id=employee_warehouse_id,
                )

        # active_tab_index filter: 0 -> all
        if active_tab_index == 1:  # Erros to Correct
            queryset = queryset.exclude(b_error_Capture__isnull=True).exclude(
                b_error_Capture__exact=""
            )
        if active_tab_index == 2:  # Missing labels
            queryset = queryset.filter(Q(z_label_url__isnull=True) | Q(z_label_url=""))
        elif active_tab_index == 3:  # To manifest
            # BioPak
            if (
                client
                and client.dme_account_num == "7EAA4B16-484B-3944-902E-BC936BFEF535"
            ):
                queryset = queryset.filter(b_status="Booked").filter(
                    Q(z_manifest_url__isnull=True) | Q(z_manifest_url="")
                )
            else:
                queryset = queryset.filter(
                    b_status__in=["Picked", "Ready for Despatch", "Ready for Booking"]
                )
        elif active_tab_index == 40:  # Booked
            queryset = queryset.filter(
                b_status__in=["Booked", "Futile Pickup", "Pickup Rebooked"]
            )
        elif active_tab_index == 41:  # Cancel Requested
            queryset = queryset.filter(b_status="Cancel Requested")
        elif active_tab_index == 42:  # In Progress
            queryset = queryset.filter(
                b_status__in=[
                    "In Transit",
                    "Partially In Transit",
                    "On-Forwarded",
                    "On Board for delivery",
                    "Futile Delivery",
                    "Partially Delivered",
                    "Delivery Delayed",
                    "Delivery Rebooked",
                ]
            )
        elif active_tab_index == 43:  # On Hold
            queryset = queryset.filter(b_status="On Hold")
        elif active_tab_index == 5:  # Closed
            queryset = queryset.filter(b_status__in=["Closed", "Cancelled"])
        elif active_tab_index == 51:  # Closed with issue
            queryset = queryset.filter(b_status__in=["Lost in Transit", "Damaged"])
        elif active_tab_index == 6:  # 'Delivery Management' - exclude BioPak
            queryset = queryset.exclude(b_client_name="BioPak")
        elif active_tab_index == 8:  # 'Pre-Processing'
            queryset = queryset.filter(
                b_status__in=[
                    "To Quote",
                    "Quoted",
                    "Entered",
                    "Imported / Integrated",
                ]
            )
        elif active_tab_index == 81:  # 'Processing'
            queryset = queryset.filter(b_status="Picking")
        elif active_tab_index == 9:  # 'Unprinted Labels'
            queryset = queryset.filter(
                z_label_url__isnull=False,
                z_downloaded_shipping_label_timestamp__isnull=True,
            )
        elif active_tab_index == 90:  # 'Returning'
            queryset = queryset.filter(b_status="Returning")
        elif active_tab_index == 91:  # 'Returned'
            queryset = queryset.filter(b_status="Returned")
        elif active_tab_index == 10:  # More tab
            queryset = queryset.filter(b_status=dme_status)
        elif active_tab_index == 11:
            queryset = queryset.filter(b_status="Parent Booking")
            run_out_bookings = get_run_out_bookings(queryset)
            queryset = queryset.exclude(pk__in=run_out_bookings)
        elif active_tab_index == 12:  # Delivered
            queryset = queryset.filter(
                b_status__in=["Delivered", "Collected by Customer"]
            )

        queryset = queryset.select_related("api_booking_quote")
        # If booking_ids is not None
        if booking_ids:
            queryset = queryset.filter(pk__in=booking_ids)

            # Column fitler
            queryset = filter_bookings_by_columns(
                queryset, column_filters, active_tab_index
            )
        else:
            # Client filter
            if client_pk is not "0":
                client = DME_clients.objects.get(pk_id_dme_client=int(client_pk))
                queryset = queryset.filter(kf_client_id=client.dme_account_num)

            if (
                "new" in download_option
                or "check_pod" in download_option
                or "flagged" in download_option
            ):
                # New POD filter
                if download_option == "new_pod":
                    queryset = queryset.filter(
                        z_downloaded_pod_timestamp__isnull=True
                    ).exclude(Q(z_pod_url__isnull=True) | Q(z_pod_url__exact=""))

                # New POD_SOG filter
                if download_option == "new_pod_sog":
                    queryset = queryset.filter(
                        z_downloaded_pod_sog_timestamp__isnull=True
                    ).exclude(
                        Q(z_pod_signed_url__isnull=True) | Q(z_pod_signed_url__exact="")
                    )

                # New Lable filter
                if download_option == "new_label":
                    queryset = queryset.filter(
                        z_downloaded_shipping_label_timestamp__isnull=True
                    ).exclude(Q(z_label_url__isnull=True) | Q(z_label_url__exact=""))

                # New Connote filter
                if download_option == "new_connote":
                    queryset = queryset.filter(
                        z_downloaded_connote_timestamp__isnull=True
                    ).exclude(
                        Q(z_connote_url__isnull=True) | Q(z_connote_url__exact="")
                    )

                # Check POD
                if download_option == "check_pod":
                    queryset = (
                        queryset.exclude(b_status__icontains="delivered")
                        .exclude(
                            (Q(z_pod_url__isnull=True) | Q(z_pod_url__exact="")),
                            (
                                Q(z_pod_signed_url__isnull=True)
                                | Q(z_pod_signed_url__exact="")
                            ),
                        )
                        .order_by("-check_pod")
                    )

                # Flagged
                if download_option == "flagged":
                    queryset = queryset.filter(b_is_flagged_add_on_services=True)

                if column_filters:
                    queryset = filter_bookings_by_columns(
                        queryset, column_filters, active_tab_index
                    )

            else:
                if search_type == "FILTER":
                    # Date filter
                    if user_type == "DME":
                        queryset = queryset.filter(
                            z_CreatedTimestamp__range=(
                                convert_to_UTC_tz(first_date),
                                convert_to_UTC_tz(last_date),
                            )
                        )
                    else:
                        if client.company_name == "BioPak":
                            queryset = queryset.filter(
                                puPickUpAvailFrom_Date__range=(first_date, last_date)
                            )
                        else:
                            queryset = queryset.filter(
                                z_CreatedTimestamp__range=(
                                    convert_to_UTC_tz(first_date),
                                    convert_to_UTC_tz(last_date),
                                )
                            )

                # Warehouse filter
                if int(warehouse_id) is not 0:
                    queryset = queryset.filter(fk_client_warehouse=int(warehouse_id))

                # Warehouse filter
                if int(fp_id) is not 0:
                    fp = Fp_freight_providers.objects.get(pk=fp_id)
                    queryset = queryset.filter(
                        vx_freight_provider__iexact=fp.fp_company_name
                    )

                # Mulitple search | Simple search | Project Name Search
                if project_name:
                    queryset = queryset.filter(b_booking_project=project_name)
                elif (
                    multi_find_field
                    and multi_find_values
                    and len(multi_find_values) > 0
                ):
                    if multi_find_field == "postal_code_pair":
                        queryset = queryset.filter(
                            de_To_Address_PostalCode__gte=multi_find_values[0],
                            de_To_Address_PostalCode__lte=multi_find_values[1],
                        )
                    elif multi_find_field == "postal_code_type":
                        postal_code_ranges = get_postal_codes(name=multi_find_values[0])
                        or_filters = Q()
                        or_filters.connector = Q.OR

                        for one_or_range in postal_code_ranges:
                            if "-" in one_or_range:
                                _from = one_or_range.split("-")[0]
                                _to = one_or_range.split("-")[1]
                                or_filters.add(
                                    Q(de_To_Address_PostalCode__gte=_from)
                                    & Q(de_To_Address_PostalCode__lte=_to),
                                    Q.OR,
                                )
                            else:
                                _one = one_or_range
                                or_filters.add(Q(de_To_Address_PostalCode=_one), Q.OR)

                        queryset = queryset.filter(or_filters)
                    else:
                        preserved = Case(
                            *[
                                When(
                                    **{
                                        f"{multi_find_field}": multi_find_value,
                                        "then": pos,
                                    }
                                )
                                for pos, multi_find_value in enumerate(
                                    multi_find_values
                                )
                            ]
                        )
                        filter_kwargs = {f"{multi_find_field}__in": multi_find_values}

                        if not multi_find_field in ["gap_ra", "clientRefNumber"]:
                            queryset = queryset.filter(**filter_kwargs).order_by(
                                preserved
                            )
                        else:
                            line_datas = Booking_lines_data.objects.filter(
                                **filter_kwargs
                            ).order_by(preserved)

                            booking_ids = []
                            for line_data in line_datas:
                                if line_data.booking():
                                    booking_ids.append(line_data.booking().id)

                            preserved = Case(
                                *[
                                    When(pk=pk, then=pos)
                                    for pos, pk in enumerate(booking_ids)
                                ]
                            )
                            queryset = queryset.filter(pk__in=booking_ids).order_by(
                                preserved
                            )
                elif simple_search_keyword and len(simple_search_keyword) > 0:
                    if (
                        not "&" in simple_search_keyword
                        and not "|" in simple_search_keyword
                    ):
                        queryset = queryset.filter(
                            Q(b_bookingID_Visual__icontains=simple_search_keyword)
                            | Q(puPickUpAvailFrom_Date__icontains=simple_search_keyword)
                            | Q(puCompany__icontains=simple_search_keyword)
                            | Q(pu_Address_Suburb__icontains=simple_search_keyword)
                            | Q(pu_Address_State__icontains=simple_search_keyword)
                            | Q(pu_Address_PostalCode__icontains=simple_search_keyword)
                            | Q(
                                pu_Comm_Booking_Communicate_Via__icontains=simple_search_keyword
                            )
                            | Q(deToCompanyName__icontains=simple_search_keyword)
                            | Q(de_To_Address_Suburb__icontains=simple_search_keyword)
                            | Q(de_To_Address_State__icontains=simple_search_keyword)
                            | Q(
                                de_To_Address_PostalCode__icontains=simple_search_keyword
                            )
                            | Q(
                                de_To_Comm_Delivery_Communicate_Via=simple_search_keyword
                            )
                            | Q(
                                b_clientReference_RA_Numbers__icontains=simple_search_keyword
                            )
                            | Q(vx_freight_provider__icontains=simple_search_keyword)
                            | Q(vx_serviceName__icontains=simple_search_keyword)
                            | Q(v_FPBookingNumber__icontains=simple_search_keyword)
                            | Q(b_status__icontains=simple_search_keyword)
                            | Q(b_status_API__icontains=simple_search_keyword)
                            | Q(b_booking_Category__icontains=simple_search_keyword)
                            | Q(b_status_category__icontains=simple_search_keyword)
                            | Q(
                                s_05_Latest_Pick_Up_Date_TimeSet__icontains=simple_search_keyword
                            )
                            | Q(
                                s_06_Latest_Delivery_Date_TimeSet__icontains=simple_search_keyword
                            )
                            | Q(
                                s_20_Actual_Pickup_TimeStamp__icontains=simple_search_keyword
                            )
                            | Q(
                                s_21_Actual_Delivery_TimeStamp__icontains=simple_search_keyword
                            )
                            | Q(b_client_sales_inv_num__icontains=simple_search_keyword)
                            | Q(pu_Contact_F_L_Name__icontains=simple_search_keyword)
                            | Q(
                                de_to_PickUp_Instructions_Address__icontains=simple_search_keyword
                            )
                            | Q(b_client_name__icontains=simple_search_keyword)
                            | Q(b_client_name_sub__icontains=simple_search_keyword)
                            | Q(b_client_order_num__icontains=simple_search_keyword)
                        )
                    else:
                        if "&" in simple_search_keyword:
                            search_keywords = simple_search_keyword.split("&")

                            for search_keyword in search_keywords:
                                search_keyword = search_keyword.replace(" ", "").lower()

                                if len(search_keyword) > 0:
                                    queryset = queryset.filter(
                                        de_to_PickUp_Instructions_Address__icontains=search_keyword
                                    )
                        elif "|" in simple_search_keyword:
                            search_keywords = simple_search_keyword.split("|")

                            for index, search_keyword in enumerate(search_keywords):
                                search_keywords[index] = search_keyword.replace(
                                    " ", ""
                                ).lower()

                            list_of_Q = [
                                Q(
                                    **{
                                        "de_to_PickUp_Instructions_Address__icontains": val
                                    }
                                )
                                for val in search_keywords
                            ]
                            queryset = queryset.filter(reduce(operator.or_, list_of_Q))
                # Column fitler
                queryset = filter_bookings_by_columns(
                    queryset, column_filters, active_tab_index
                )

        # Sort
        if download_option != "check_pod" and (
            len(multi_find_values) == 0
            or (len(multi_find_values) > 0 and sort_field not in ["id", "-id"])
        ):
            if sort_field is None:
                queryset = queryset.order_by("id")
            else:
                if sort_field == "z_pod_url":
                    queryset = queryset.order_by(sort_field, "z_pod_signed_url")
                else:
                    queryset = queryset.order_by(sort_field)

        # Assign to bookings value!
        bookings = queryset.only(*BOOKING_FIELDS_4_ALLBOOKING_TABLE)

        filtered_booking_ids = []
        for booking in queryset:
            filtered_booking_ids.append(booking.id)

        # Count
        bookings_cnt = len(filtered_booking_ids)

        # Pagination
        page_cnt = (
            int(bookings_cnt / int(page_item_cnt))
            if bookings_cnt % int(page_item_cnt) == 0
            else int(bookings_cnt / int(page_item_cnt)) + 1
        )
        queryset = queryset[
            int(page_item_cnt)
            * int(page_ind) : int(page_item_cnt)
            * (int(page_ind) + 1)
        ]

        if active_tab_index == 8:
            picked_booking_pk_booking_ids = []

            for booking in queryset:
                if booking.b_status == "Picked" or booking.b_dateBookedDate:
                    picked_booking_pk_booking_ids.append(booking.pk_booking_id)

            scanned_quotes_4_picked_bookings = API_booking_quotes.objects.filter(
                fk_booking_id__in=picked_booking_pk_booking_ids,
                packed_status=Booking_lines.SCANNED_PACK,
                is_used=False,
            ).only(
                "id",
                "fk_booking_id",
                "freight_provider",
                "account_code",
                "client_mu_1_minimum_values",
            )

            context = {
                "scanned_quotes_4_picked_bookings": scanned_quotes_4_picked_bookings
            }
            bookings = SimpleBookingSerializer(
                queryset, many=True, context=context
            ).data
        else:
            bookings = SimpleBookingSerializer(queryset, many=True).data

        # Sort on `remaining time` on 'Delivery Management' tab
        if active_tab_index == 6:
            bookings = sorted(bookings, key=lambda k: k["remaining_time_in_seconds"])

        # clientRefNumber & gapRa
        results = []
        if multi_find_field == "gap_ra":
            line_datas = get_gapRas(bookings)
            for booking in bookings:
                booking_gap_ras = []
                for line_data in line_datas:
                    if booking["pk_booking_id"] == line_data.fk_booking_id:
                        booking_gap_ras.append(line_data.gap_ra)

                gapRas = ("gapRas", ", ".join(booking_gap_ras))
                items = list(booking.items())
                items.append(gapRas)
                booking = OrderedDict(items)
                results.append(booking)
        elif multi_find_field == "clientRefNumber":
            line_datas = get_clientRefNumbers(bookings)
            for booking in bookings:
                booking_clientRefNumbers = []
                for line_data in line_datas:
                    if booking["pk_booking_id"] == line_data.fk_booking_id:
                        booking_clientRefNumbers.append(line_data.clientRefNumber)

                clientRefNumbers = (
                    "clientRefNumbers",
                    ", ".join(booking_clientRefNumbers),
                )
                items = list(booking.items())
                items.append(clientRefNumbers)
                booking = OrderedDict(items)
                results.append(booking)
        else:
            results = bookings

        # lines info
        _results = []
        lines = get_lines_in_bulk(bookings)
        for result in results:
            # if has 'scanned' then extract lines info from `scanned`
            # else extract from `original`
            original_lines_count = 0
            original_total_kgs = 0
            original_total_cbm = 0  # Cubic Meter

            scanned_lines_count = 0
            scanned_total_kgs = 0
            scanned_total_cbm = 0  # Cubic Meter

            for line in lines:
                if result["pk_booking_id"] == line.fk_booking_id:
                    if line.packed_status == "scanned":
                        scanned_lines_count += line.e_qty or 0
                        scanned_total_kgs += line.e_Total_KG_weight or 0
                        scanned_total_cbm += line.e_1_Total_dimCubicMeter or 0
                    else:
                        original_lines_count += line.e_qty or 0
                        original_total_kgs += line.e_Total_KG_weight or 0
                        original_total_cbm += line.e_1_Total_dimCubicMeter or 0

            original_total_kgs = round(original_total_kgs, 3)
            original_total_cbm = round(original_total_cbm, 3)
            scanned_total_kgs = round(scanned_total_kgs, 3)
            scanned_total_cbm = round(scanned_total_cbm, 3)
            _lines_count = ("lines_count", scanned_lines_count or original_lines_count)
            _total_kgs = ("total_kgs", scanned_total_kgs or original_total_kgs)
            _total_cbm = ("total_cbm", scanned_total_cbm or original_total_cbm)
            items = list(result.items())
            items.append(_lines_count)
            items.append(_total_kgs)
            items.append(_total_cbm)
            result = OrderedDict(items)
            _results.append(result)

        return JsonResponse(
            {
                "bookings": _results,
                "filtered_booking_ids": filtered_booking_ids,
                "count": bookings_cnt,
                "page_cnt": page_cnt,
                "page_ind": page_ind,
                "page_item_cnt": page_item_cnt,
            }
        )

    @action(detail=True, methods=["put"])
    def update_booking(self, request, pk, format=None):
        booking = Bookings.objects.get(pk=pk)
        lowest_pricing = None

        # Check if `booking_type` changes
        if (
            booking.b_client_name == "Jason L"
            and booking.booking_type != request.data.get("booking_type")
        ):
            if request.data.get("booking_type") == Bookings.DMEP:
                request.data["inv_cost_quoted"] = 0
                request.data["inv_sell_quoted"] = 0
            elif (
                request.data.get("booking_type") == Bookings.DMEA
                and booking.api_booking_quote
            ):
                lowest_pricing = (
                    API_booking_quotes.objects.filter(
                        fk_booking_id=booking.pk_booking_id,
                        packed_status=booking.api_booking_quote.packed_status,
                    )
                    .order_by("client_mu_1_minimum_values")
                    .first()
                )

        serializer = BookingSerializer(booking, data=request.data)
        try:
            if serializer.is_valid():
                serializer.save()

                if lowest_pricing:
                    set_booking_quote(booking, lowest_pricing)

                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"update_booking Error: {str(e)}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["put"])
    def change_bookings_status(self, request, format=None):
        LOG_ID = "[CHANGE STATUS IN BULK]"
        status = request.data["status"]
        optional_value = request.data["optionalValue"]
        booking_ids = request.data["bookingIds"]

        try:
            if "flag_add_on_services" in status:
                for booking_id in booking_ids:
                    booking = Bookings.objects.get(pk=booking_id)
                    booking.b_is_flagged_add_on_services = (
                        1 if status == "flag_add_on_services" else 0
                    )
                    booking.save()
                return JsonResponse({"status": "success"})
            else:
                for booking_id in booking_ids:
                    booking = Bookings.objects.get(pk=booking_id)
                    delivery_kpi_days = int(booking.delivery_kpi_days or 14)

                    if status == "In Transit":
                        booking.z_calculated_ETA = (
                            datetime.strptime(optional_value[:19], "%Y-%m-%d %H:%M:%S")
                            + timedelta(days=delivery_kpi_days)
                        ).date()
                        booking.b_given_to_transport_date_time = datetime.strptime(
                            optional_value[:19], "%Y-%m-%d %H:%M:%S"
                        )

                    status_history.create(
                        booking, status, request.user.username, optional_value[:19]
                    )
                    calc_collect_after_status_change(booking.pk_booking_id, status)
                    booking.save()
                return JsonResponse({"status": "success"})
        except Exception as e:
            logger.error(f"{LOG_ID} Error: {str(e)}")
            return Response({"status": "error"})

    @action(detail=False, methods=["post"])
    def get_xls(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client_employee_role = client_employee.get_role()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()

        vx_freight_provider = request.data["vx_freight_provider"]
        pk_id_dme_client = request.data["pk_id_dme_client"]
        report_type = request.data["report_type"]
        email_addr = request.data["emailAddr"]
        show_field_name = request.data["showFieldName"]
        use_selected = request.data["useSelected"]
        first_date = None
        last_date = None

        if use_selected:
            booking_ids = request.data["selectedBookingIds"]
        else:
            start_date = request.data["startDate"]
            end_date = request.data["endDate"]
            first_date = datetime.strptime(start_date, "%Y-%m-%d")
            last_date = datetime.strptime(end_date, "%Y-%m-%d")
            last_date = last_date.replace(hour=23, minute=59, second=59)

        # DME & Client filter
        if user_type == "DME":
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == "company":
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == "warehouse":
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(
                    kf_client_id=client.dme_account_num,
                    fk_client_warehouse_id=employee_warehouse_id,
                )

        if use_selected:
            queryset = queryset.filter(pk__in=booking_ids)
        else:
            if report_type == "pending_bookings":
                queryset = queryset.filter(
                    z_CreatedTimestamp__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    ),
                    b_status__iexact="ready for booking",
                )
            elif report_type == "booked_bookings":
                queryset = queryset.filter(
                    b_dateBookedDate__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    )
                )
            elif report_type == "picked_up_bookings":
                queryset = queryset.filter(
                    s_20_Actual_Pickup_TimeStamp__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    )
                )
            elif report_type == "box":
                queryset = queryset.filter(
                    b_dateBookedDate__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    ),
                    puCompany__icontains="Tempo Aus Whs",
                    pu_Address_Suburb__iexact="FRENCHS FOREST",
                )
            elif report_type == "futile":
                queryset = queryset.filter(
                    b_dateBookedDate__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    )
                )
            elif report_type == "goods_delivered":
                queryset = queryset.filter(
                    s_21_Actual_Delivery_TimeStamp__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    ),
                    b_status__iexact="delivered",
                )
            elif report_type == "goods_sent":
                queryset = queryset.filter(
                    b_dateBookedDate__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    ),
                    b_dateBookedDate__isnull=False,
                )
            else:
                # Date filter
                if user_type == "DME":
                    queryset = queryset.filter(
                        z_CreatedTimestamp__range=(
                            convert_to_UTC_tz(first_date),
                            convert_to_UTC_tz(last_date),
                        )
                    )
                else:
                    if client.company_name == "BioPak":
                        queryset = queryset.filter(
                            puPickUpAvailFrom_Date__range=(first_date, last_date)
                        )
                    else:
                        queryset = queryset.filter(
                            z_CreatedTimestamp__range=(
                                convert_to_UTC_tz(first_date),
                                convert_to_UTC_tz(last_date),
                            )
                        )

            # Freight Provider filter
            if vx_freight_provider != "All":
                queryset = queryset.filter(vx_freight_provider=vx_freight_provider)

            # Client filter
            if pk_id_dme_client != "All" and pk_id_dme_client != 0:
                client = DME_clients.objects.get(pk_id_dme_client=pk_id_dme_client)
                queryset = queryset.filter(kf_client_id=client.dme_account_num)

        # Optimized to speed up building XLS
        queryset.only(
            "id",
            "pk_booking_id",
            "b_dateBookedDate",
            "pu_Address_State",
            "puCompany",
            "deToCompanyName",
            "de_To_Address_Suburb",
            "de_To_Address_State",
            "de_To_Address_PostalCode",
            "b_client_sales_inv_num",
            "b_client_order_num",
            "v_FPBookingNumber",
            "b_status",
            "b_status_category",
            "dme_status_detail",
            "dme_status_action",
            "s_05_LatestPickUpDateTimeFinal",
            "s_06_Latest_Delivery_Date_TimeSet",
            "s_20_Actual_Pickup_TimeStamp",
            "s_21_ActualDeliveryTimeStamp",
            "z_pod_url",
            "z_pod_signed_url",
            "delivery_kpi_days",
            "de_Deliver_By_Date",
            "vx_freight_provider",
            "pu_Address_Suburb",
            "b_bookingID_Visual",
            "b_client_name",
            "b_client_name_sub",
            "fp_invoice_no",
            "inv_cost_quoted",
            "inv_cost_actual",
            "inv_sell_quoted",
            "inv_sell_actual",
            "dme_status_linked_reference_from_fp",
            "inv_billing_status",
            "inv_billing_status_note",
            "b_booking_Category",
            # "clientRefNumbers",
            # "gap_ras",
            "s_05_LatestPickUpDateTimeFinal",
            "b_booking_Notes",
            "z_CreatedTimestamp",
            "de_to_Pick_Up_Instructions_Contact",
            "de_to_PickUp_Instructions_Address",
            "de_To_AddressType",
            "b_client_warehouse_code",
        )

        build_xls_and_send(
            queryset,
            email_addr,
            report_type,
            str(self.request.user),
            first_date,
            last_date,
            show_field_name,
            get_clientname(request),
        )
        return JsonResponse({"status": "started generate xml"})

    @action(detail=False, methods=["post"])
    def calc_collected(self, request, format=None):
        booking_ids = request.data["bookingIds"]
        type = request.data["type"]

        try:
            for id in booking_ids:
                booking = Bookings.objects.get(id=int(id))
                booking_lines = Booking_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                )

                for booking_line in booking_lines:
                    if type == "Calc":
                        if not booking_line.e_qty:
                            booking_line.e_qty = 0
                        if not booking_line.e_qty_awaiting_inventory:
                            booking_line.e_qty_awaiting_inventory = 0

                        booking_line.e_qty_collected = int(booking_line.e_qty) - int(
                            booking_line.e_qty_awaiting_inventory
                        )
                        booking_line.save()
                    elif type == "Clear":
                        booking_line.e_qty_collected = 0
                        booking_line.save()
            return JsonResponse(
                {"success": "All bookings e_qty_collected has been calculated"}
            )
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({"error": "Got error, please contact support center"})

    @action(detail=False, methods=["get"])
    def get_bookings_4_manifest(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client_employee_role = client_employee.get_role()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()

        puPickUpAvailFrom_Date = request.GET["puPickUpAvailFrom_Date"]
        vx_freight_provider = request.GET["vx_freight_provider"]
        if vx_freight_provider == "Tas":
            vx_freight_provider = "TASFR"

        # DME & Client filter
        if user_type == "DME":
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == "company":
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == "warehouse":
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(
                    kf_client_id=client.dme_account_num,
                    fk_client_warehouse_id=employee_warehouse_id,
                )

        queryset = queryset.filter(puPickUpAvailFrom_Date=puPickUpAvailFrom_Date)
        queryset = queryset.filter(vx_freight_provider=vx_freight_provider)
        queryset = queryset.filter(b_status__icontains="Ready for XML")

        # Active Tab content count
        errors_to_correct = 0
        missing_labels = 0
        to_manifest = 0
        to_process = 0
        closed = 0

        for booking in queryset:
            if booking.b_error_Capture is not None and len(booking.b_error_Capture) > 0:
                errors_to_correct += 1
            if booking.z_label_url is None or len(booking.z_label_url) == 0:
                missing_labels += 1
            if booking.b_status == "Booked":
                to_manifest += 1
            if booking.b_status == "Ready to booking":
                to_process += 1
            if booking.b_status == "Closed":
                closed += 1

        # Sort
        queryset = queryset.order_by("-id")

        # Count
        bookings_cnt = queryset.count()
        bookings = queryset

        return JsonResponse(
            {
                "bookings": BookingSerializer(bookings, many=True).data,
                "count": bookings_cnt,
                "errors_to_correct": errors_to_correct,
                "to_manifest": to_manifest,
                "missing_labels": missing_labels,
                "to_process": to_process,
                "closed": closed,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_booking_update(self, request, format=None):
        booking_ids = request.data["bookingIds"]
        field_name = request.data["fieldName"]
        field_content = request.data["fieldContent"]

        if field_content == "":
            field_content = None

        try:
            for booking_id in booking_ids:
                if field_name == "fp_scan":
                    field_content["booking"] = booking_id
                    fp_status_history = FPStatusHistorySerializer(data=field_content)

                    if fp_status_history.is_valid():
                        fp_status_history.save()
                    else:
                        return JsonResponse(
                            {
                                "message": f"Error: {fp_status_history.errors}, Please contact support center!"
                            },
                            status=400,
                        )
                elif field_name == "additional_surcharge":
                    field_content["booking"] = booking_id
                    surcharge = SurchargeSerializer(data=field_content)

                    if surcharge.is_valid():
                        surcharge.save()
                    else:
                        return JsonResponse(
                            {
                                "message": f"Error: {surcharge.errors}, Please contact support center!"
                            },
                            status=400,
                        )
                else:
                    booking = Bookings.objects.get(id=booking_id)
                    setattr(booking, field_name, field_content)

                    if not booking.delivery_kpi_days:
                        delivery_kpi_days = 14
                    else:
                        delivery_kpi_days = int(booking.delivery_kpi_days)

                    if field_name == "b_project_due_date" and field_content:
                        if not booking.delivery_booking:
                            booking.de_Deliver_From_Date = field_content
                            booking.de_Deliver_By_Date = field_content
                    elif field_name == "delivery_booking" and field_content:
                        booking.de_Deliver_From_Date = field_content
                        booking.de_Deliver_By_Date = field_content
                    elif (
                        field_name == "fp_received_date_time"
                        and field_content
                        and not booking.b_given_to_transport_date_time
                    ):
                        booking.z_calculated_ETA = datetime.strptime(
                            field_content, "%Y-%m-%d"
                        ) + timedelta(days=delivery_kpi_days)
                    elif (
                        field_name == "b_given_to_transport_date_time" and field_content
                    ):
                        booking.z_calculated_ETA = datetime.strptime(
                            field_content, "%Y-%m-%d %H:%M:%S"
                        ) + timedelta(days=delivery_kpi_days)
                    elif field_name == "vx_freight_provider" and field_content:
                        logger.info(f"Rebuild label required")
                        booking.z_downloaded_shipping_label_timestamp = None

                        if booking.z_label_url:
                            booking.z_label_url = (
                                "[REBUILD_REQUIRED]" + booking.z_label_url
                            )
                        else:
                            booking.z_label_url = "[REBUILD_REQUIRED]"

                        # JasonL and 3 special FP
                        if booking.b_client_name == "Jason L":
                            if field_content in SPECIAL_FPS:
                                booking.booking_type = "DMEM"

                    booking.save()
            return JsonResponse(
                {"message": "Bookings are updated successfully"}, status=200
            )
        except Exception as e:
            # print("Exception: ", e)
            return JsonResponse(
                {"message": f"Error: {e}, Please contact support center!"}, status=400
            )

    @action(detail=False, methods=["get"])
    def get_status_info(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client_employee_role = client_employee.get_role()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()

        start_date = self.request.query_params.get("startDate", None)
        end_date = self.request.query_params.get("endDate", None)
        first_date = datetime.strptime(start_date, "%Y-%m-%d")
        last_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        client_pk = self.request.query_params.get("clientPK", None)

        # DME & Client filter
        if user_type == "DME":
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == "company":
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == "warehouse":
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(
                    kf_client_id=client.dme_account_num,
                    fk_client_warehouse_id=employee_warehouse_id,
                )

        # Client filter
        if client_pk is not "0":
            client = DME_clients.objects.get(pk_id_dme_client=int(client_pk))
            queryset = queryset.filter(kf_client_id=client.dme_account_num)

        # Date filter
        if user_type == "DME":
            queryset = queryset.filter(
                z_CreatedTimestamp__range=(
                    convert_to_UTC_tz(first_date),
                    convert_to_UTC_tz(last_date),
                )
            )
        else:
            if client.company_name == "BioPak":
                queryset = queryset.filter(
                    puPickUpAvailFrom_Date__range=(first_date, last_date)
                )
            else:
                queryset = queryset.filter(
                    z_CreatedTimestamp__range=(
                        convert_to_UTC_tz(first_date),
                        convert_to_UTC_tz(last_date),
                    )
                )

        # Get all statuses
        dme_statuses = Utl_dme_status.objects.all().order_by("dme_delivery_status")

        ret_data = []
        for dme_status in dme_statuses:
            ret_data.append(
                {
                    "dme_delivery_status": dme_status.dme_delivery_status,
                    "dme_status_label": dme_status.dme_status_label
                    if dme_status.dme_status_label is not None
                    else dme_status.dme_delivery_status,
                    "count": queryset.filter(
                        b_status=dme_status.dme_delivery_status
                    ).count(),
                }
            )

        return JsonResponse({"results": ret_data})

    @action(detail=False, methods=["get"])
    def get_manifest_report(self, request, format=None):
        clientname = get_client_name(self.request)
        page_index = int(request.GET["index"])

        if not clientname in ["Jason L", "Bathroom Sales Direct", "BioPak", "dme"]:
            return JsonResponse(
                {"message": "You have no permission to see this information"},
                status=400,
            )

        if clientname in ["BioPak"]:
            sydney_now = get_sydney_now_time("datetime")
            last_date = datetime.now() - timedelta(days=20 * page_index)
            first_date = (sydney_now - timedelta(days=20 * (page_index + 1))).date()
            bookings_with_manifest = (
                Bookings.objects.prefetch_related("fk_client_warehouse")
                .exclude(manifest_timestamp__isnull=True)
                .filter(manifest_timestamp__range=(first_date, last_date))
                .order_by("-manifest_timestamp")
                .only(
                    "b_bookingID_Visual",
                    "z_manifest_url",
                    "manifest_timestamp",
                    "vx_freight_provider",
                    "kf_client_id",
                    "b_booking_project",
                )
            )

            if clientname != "dme":
                bookings_with_manifest = bookings_with_manifest.filter(
                    b_client_name=clientname
                )

            manifest_dates = []
            for booking in bookings_with_manifest:
                if not booking.manifest_timestamp in manifest_dates:
                    manifest_dates.append(booking.manifest_timestamp)

            results = []
            for manifest_date in manifest_dates:
                result = {"freight_providers": [], "vehicles": [], "cnt_4_each_fp": {}}
                daily_count = 0
                first_booking = None
                b_bookingID_Visuals = []

                for booking in bookings_with_manifest:
                    if booking.manifest_timestamp == manifest_date:
                        first_booking = booking
                        daily_count += 1
                        b_bookingID_Visuals.append(booking.b_bookingID_Visual)

                        if not booking.vx_freight_provider in result["cnt_4_each_fp"]:
                            result["cnt_4_each_fp"][booking.vx_freight_provider] = 1
                        else:
                            result["cnt_4_each_fp"][booking.vx_freight_provider] += 1

                        if (
                            not booking.vx_freight_provider
                            in result["freight_providers"]
                        ):
                            result["freight_providers"].append(
                                booking.vx_freight_provider
                            )
                            result["vehicles"].append(
                                booking.b_booking_project
                                if booking.vx_freight_provider == "Deliver-ME"
                                else f"{booking.vx_freight_provider} Vehicle"
                            )

                result["count"] = daily_count
                result["z_manifest_url"] = first_booking.z_manifest_url
                result["warehouse_name"] = first_booking.fk_client_warehouse.name
                result["manifest_date"] = manifest_date
                result["b_bookingID_Visuals"] = b_bookingID_Visuals
                result["kf_client_id"] = first_booking.kf_client_id
                results.append(result)

            return JsonResponse({"results": results})

        sydney_now = get_sydney_now_time("datetime")
        last_date = datetime.now() - timedelta(days=20 * page_index)
        first_date = (sydney_now - timedelta(days=20 * (page_index + 1))).date()
        manifest_logs = (
            Dme_manifest_log.objects.filter(
                z_createdTimeStamp__range=(first_date, last_date)
            )
            .order_by("-z_createdTimeStamp")
            .only("id", "manifest_url")
        )

        manifest_urls = []
        manifest_ids = []
        for manifest_log in manifest_logs:
            manifest_ids.append(manifest_log.id)
            manifest_urls.append("startrack_au/" + manifest_log.manifest_url)

        bookings_with_manifest = (
            Bookings.objects.prefetch_related("fk_client_warehouse")
            .exclude(manifest_timestamp__isnull=True)
            .filter(z_manifest_url__in=manifest_urls)
            .order_by("-manifest_timestamp")
            .only(
                "b_bookingID_Visual",
                "z_manifest_url",
                "manifest_timestamp",
                "vx_freight_provider",
                "kf_client_id",
                "b_booking_project",
            )
        )

        if clientname != "dme":
            bookings_with_manifest = bookings_with_manifest.filter(
                b_client_name=clientname
            )

        manifest_dates = []
        for booking in bookings_with_manifest:
            if not booking.manifest_timestamp in manifest_dates:
                manifest_dates.append(booking.manifest_timestamp)

        results = []
        report_fps = []
        client_ids = []
        index = 0
        for manifest_date in manifest_dates:
            result = {"freight_providers": [], "vehicles": [], "cnt_4_each_fp": {}}
            daily_count = 0
            first_booking = None
            b_bookingID_Visuals = []

            for booking in bookings_with_manifest:
                if booking.manifest_timestamp == manifest_date:
                    first_booking = booking
                    daily_count += 1
                    b_bookingID_Visuals.append(booking.b_bookingID_Visual)

                    if not booking.vx_freight_provider in result["cnt_4_each_fp"]:
                        result["cnt_4_each_fp"][booking.vx_freight_provider] = 1
                    else:
                        result["cnt_4_each_fp"][booking.vx_freight_provider] += 1

                    if not booking.vx_freight_provider in result["freight_providers"]:
                        result["freight_providers"].append(booking.vx_freight_provider)
                        result["vehicles"].append(
                            booking.b_booking_project
                            if booking.vx_freight_provider == "Deliver-ME"
                            else f"{booking.vx_freight_provider} Vehicle"
                        )

            result["manifest_id"] = manifest_ids[index]
            result["count"] = daily_count
            result["z_manifest_url"] = first_booking.z_manifest_url
            result["warehouse_name"] = first_booking.fk_client_warehouse.name
            result["manifest_date"] = manifest_date
            result["b_bookingID_Visuals"] = b_bookingID_Visuals
            result["kf_client_id"] = first_booking.kf_client_id

            results.append(result)

            if first_booking.vx_freight_provider not in report_fps:
                report_fps.append(first_booking.vx_freight_provider)
            if first_booking.kf_client_id not in client_ids:
                client_ids.append(first_booking.kf_client_id)
            index += 1

        clients = DME_clients.objects.filter(dme_account_num__in=client_ids).only(
            "company_name", "dme_account_num"
        )
        report_clients = []
        for client in clients:
            report_client = {}
            report_client["company_name"] = client.company_name
            report_client["dme_account_num"] = client.dme_account_num
            report_clients.append(report_client)
        return JsonResponse(
            {
                "results": results,
                "report_fps": report_fps,
                "report_clients": report_clients,
            }
        )

    @action(detail=False, methods=["get"])
    def get_project_names(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client_employee_role = client_employee.get_role()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()

        # DME & Client filter
        if user_type == "DME":
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == "company":
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == "warehouse":
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(
                    kf_client_id=client.dme_account_num,
                    fk_client_warehouse_id=employee_warehouse_id,
                )

        results = (
            queryset.exclude(
                Q(b_booking_project__isnull=True) | Q(b_booking_project__exact="")
            )
            .values_list("b_booking_project", flat=True)
            .distinct()
        )

        return JsonResponse({"results": list(results)})

    @action(detail=False, methods=["get"])
    def send_email(self, request, format=None):
        user_id = int(self.request.user.id)
        template_name = self.request.query_params.get("templateName", None)
        booking_id = self.request.query_params.get("bookingId", None)
        send_booking_status_email(booking_id, template_name, self.request.user.username)
        return JsonResponse({"message": "success"}, status=200)

    @action(detail=False, methods=["post"])
    def pricing_analysis(self, request, format=None):
        bookingIds = request.data["bookingIds"]
        results = analyse_booking_quotes_table(bookingIds)
        return JsonResponse({"message": "success", "results": results}, status=200)

    @action(detail=False, methods=["post"])
    def get_bookings_summary(self, request, format=None):
        bookingIds = request.data["bookingIds"]
        bookings = Bookings.objects.filter(pk__in=bookingIds).only(
            "pk_booking_id", "vx_freight_provider"
        )
        pk_booking_ids = []

        for booking in bookings:
            pk_booking_ids.append(booking.pk_booking_id)

        booking_lines = Booking_lines.objects.filter(
            fk_booking_id__in=pk_booking_ids,
            packed_status__in=[Booking_lines.ORIGINAL, Booking_lines.SCANNED_PACK],
        ).only(
            "fk_booking_id",
            "e_qty",
            "e_dimUOM",
            "e_dimLength",
            "e_dimHeight",
            "e_dimWidth",
            "e_Total_KG_weight",
            "e_weightPerEach",
            "packed_status",
        )

        total_qty, total_kgs, total_cbm = 0, 0, 0
        fps = {}

        for booking in bookings:
            if not booking.vx_freight_provider in fps:
                fps[booking.vx_freight_provider] = {
                    "orderCnt": 0,
                    "totalQty": 0,
                    "totalKgs": 0,
                    "totalCubicMeter": 0,
                }

            fps[booking.vx_freight_provider]["orderCnt"] += 1

            original_lines = []
            scanned_lines = []
            for line in booking_lines:
                if booking.pk_booking_id == line.fk_booking_id:
                    if line.packed_status == Booking_lines.ORIGINAL:
                        original_lines.append(line)
                    else:
                        scanned_lines.append(line)

            for line in scanned_lines or original_lines or []:
                total_qty += line.e_qty
                total_kgs += line.e_Total_KG_weight or 0
                total_cbm += line.e_1_Total_dimCubicMeter or 0

                fps[booking.vx_freight_provider]["totalQty"] += line.e_qty
                fps[booking.vx_freight_provider]["totalKgs"] += line.e_qty * (
                    line.e_weightPerEach or 0
                )
                fps[booking.vx_freight_provider]["totalCubicMeter"] += (
                    line.e_1_Total_dimCubicMeter or 0
                )

        result = {}
        result["fps"] = fps
        result["total_qty"] = total_qty
        result["total_kgs"] = total_kgs
        result["total_cbm"] = total_cbm
        return JsonResponse(result, status=200)


class BookingViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer

    @action(detail=False, methods=["get"])
    def get_booking(self, request, format=None):
        uid = request.GET["id"]
        filterName = request.GET["filter"]
        user_id = request.user.id

        try:
            dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()
            client_customer_mark_up = None

            if dme_employee is not None:
                user_type = "DME"
            else:
                user_type = "CLIENT"

            if user_type == "DME":
                queryset = Bookings.objects.all()
            else:
                client_employee = Client_employees.objects.filter(
                    fk_id_user=user_id
                ).first()

                if client_employee is None:
                    return JsonResponse({"booking": {}, "nextid": 0, "previd": 0})

                client_employee_role = client_employee.get_role()
                client = DME_clients.objects.get(
                    pk_id_dme_client=client_employee.fk_id_dme_client_id
                )

                if client is None:
                    return JsonResponse({"booking": {}, "nextid": 0, "previd": 0})

                client_customer_mark_up = client.client_customer_mark_up

                if client_employee_role == "company":
                    queryset = Bookings.objects.filter(
                        kf_client_id=client.dme_account_num
                    )
                elif client_employee_role == "warehouse":
                    employee_warehouse_id = client_employee.warehouse_id
                    queryset = Bookings.objects.filter(
                        kf_client_id=client.dme_account_num,
                        fk_client_warehouse_id=employee_warehouse_id,
                    )

            if filterName == "null":
                booking = queryset.last()
            elif filterName == "dme":
                booking = queryset.get(b_bookingID_Visual=uid)
            elif filterName == "con":
                booking = queryset.filter(v_FPBookingNumber=uid).first()
            elif filterName == "id" and uid and uid != "null":
                booking = queryset.get(id=uid)
            else:
                return JsonResponse({"booking": {}, "nextid": 0, "previd": 0})

            if booking is not None:
                nextBooking = queryset.filter(id__gt=booking.id).order_by("id").first()
                prevBooking = queryset.filter(id__lt=booking.id).order_by("-id").first()
                nextBookingId = 0
                prevBookingId = 0

                if nextBooking is not None:
                    nextBookingId = nextBooking.id
                if prevBooking is not None:
                    prevBookingId = prevBooking.id

                # Get count for `Shipment Packages / Goods`
                booking_lines = Booking_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                )

                e_qty_total = 0
                for booking_line in booking_lines:
                    e_qty_total += booking_line.e_qty or 0

                client_customer_mark_up = 0
                if not client_customer_mark_up and booking.kf_client_id:
                    try:
                        client = DME_clients.objects.get(
                            dme_account_num=booking.kf_client_id
                        )
                        client_customer_mark_up = client.client_customer_mark_up
                    except:
                        pass

                # Get count for 'Attachments'
                cnt_attachments = Dme_attachments.objects.filter(
                    fk_id_dme_booking=booking.pk_booking_id
                ).count()

                # Get count for `additional surcharges`
                cnt_additional_surcharges = Surcharge.objects.filter(
                    booking=booking, is_manually_entered=True
                ).count()

                context = {"client_customer_mark_up": client_customer_mark_up}

                return JsonResponse(
                    {
                        "booking": BookingSerializer(booking, context=context).data,
                        "nextid": nextBookingId,
                        "previd": prevBookingId,
                        "e_qty_total": e_qty_total,
                        "cnt_attachments": cnt_attachments,
                        "cnt_additional_surcharges": cnt_additional_surcharges,
                    }
                )
            return JsonResponse(
                {
                    "booking": {},
                    "nextid": 0,
                    "previd": 0,
                    "e_qty_total": 0,
                    "cnt_attachments": 0,
                    "cnt_additional_surcharges": 0,
                }
            )
        except Exception as e:
            trace_error.print()
            logger.info(f"#104 - Get booking exception: {str(e)}")
            return JsonResponse(
                {
                    "booking": {},
                    "nextid": 0,
                    "previd": 0,
                    "e_qty_total": 0,
                    "cnt_attachments": 0,
                    "cnt_additional_surcharges": 0,
                }
            )

    @action(detail=False, methods=["get"])
    def get_status(self, request, format=None):
        pk_booking_id = request.GET["pk_header_id"]
        user_id = request.user.id

        try:
            dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

            if dme_employee is not None:
                user_type = "DME"
            else:
                user_type = "CLIENT"

            if user_type == "CLIENT":
                client_employee = Client_employees.objects.filter(
                    fk_id_user=user_id
                ).first()
                client = DME_clients.objects.get(
                    pk_id_dme_client=client_employee.fk_id_dme_client_id
                )

                if client is None:
                    return JsonResponse({"booking": {}, "nextid": 0, "previd": 0})

            try:
                booking = Bookings.objects.filter(pk_booking_id=pk_booking_id).values(
                    "b_status",
                    "v_FPBookingNumber",
                    "vx_account_code",
                    "kf_client_id",
                )

                if (
                    user_type == "CLIENT"
                    and booking.kf_client_id != client.dme_account_num
                ):
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "You don't have permission to get status of this booking.",
                            "pk_header_id": pk_booking_id,
                        }
                    )

                if booking.vx_account_code:
                    quote = booking.api_booking_quote

                if booking.vx_account_code and booking.b_status == "Ready for Booking":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Pricing is selected but not booked yet",
                            "pk_header_id": pk_booking_id,
                            "status": booking.b_status,
                            "price": {
                                "fee": quote.client_mu_1_minimum_values,
                                "tax": qutoe.mu_percentage_fuel_levy,
                            },
                        }
                    )
                elif (
                    not booking.vx_account_code
                    and booking.b_status == "Ready for Booking"
                ):
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Pricing is not selected.",
                            "pk_header_id": pk_booking_id,
                            "status": booking.b_status,
                            "price": None,
                        }
                    )
                elif booking.vx_account_code and booking.b_status == "Booked":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Booking is booked.",
                            "pk_header_id": pk_booking_id,
                            "status": booking.b_status,
                            "price": {
                                "fee": quote.client_mu_1_minimum_values,
                                "tax": qutoe.mu_percentage_fuel_levy,
                            },
                            "connote": booking.v_FPBookingNumber,
                        }
                    )
                elif booking.vx_account_code and booking.b_status == "Closed":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Booking is cancelled.",
                            "pk_header_id": pk_booking_id,
                            "status": booking.b_status,
                            "price": {
                                "fee": quote.client_mu_1_minimum_values,
                                "tax": qutoe.mu_percentage_fuel_levy,
                            },
                            "connote": booking.v_FPBookingNumber,
                        }
                    )
            except Bookings.DoesNotExist:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Booking is not exist with provided pk_header_id.",
                        "pk_header_id": pk_booking_id,
                    }
                )
        except Exception as e:
            return JsonResponse(
                {"success": False, "message": str(e), "pk_header_id": pk_booking_id}
            )

    @action(detail=False, methods=["post"])
    def create_booking(self, request, format=None):
        bookingData = request.data
        bookingData["b_bookingID_Visual"] = Bookings.get_max_b_bookingID_Visual() + 1
        bookingData["pk_booking_id"] = str(uuid.uuid1())
        bookingData["b_client_booking_ref_num"] = bookingData["pk_booking_id"]
        serializer = BookingSerializer(data=request.data)

        if serializer.is_valid():
            booking = serializer.save()
            serializer.data["id"] = booking.pk
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def duplicate_booking(self, request, pk=None, format=None):
        LOG_ID = "[DUP BOOKING]"
        user_id = request.user.id
        booking = Bookings.objects.get(pk=pk)
        payload = request.data
        logger.info(
            f"{LOG_ID} Booking: {pk}({booking.b_bookingID_Visual}), Payload: {payload}"
        )
        dup_line_and_linedetail = payload.get("dupLineAndLineDetail")
        switch_info = payload.get("switchInfo")
        is_4_child = payload.get("is4Child")
        qtys_4_children = payload.get("qtys4Children")

        if switch_info:
            newBooking = {
                "puCompany": booking.deToCompanyName,
                "pu_Address_Street_1": booking.de_To_Address_Street_1,
                "pu_Address_street_2": booking.de_To_Address_Street_2,
                "pu_Address_PostalCode": booking.de_To_Address_PostalCode,
                "pu_Address_Suburb": booking.de_To_Address_Suburb,
                "pu_Address_Country": booking.de_To_Address_Country,
                "pu_Contact_F_L_Name": booking.de_to_Contact_F_LName,
                "pu_Phone_Main": booking.de_to_Phone_Main,
                "pu_Email": booking.de_Email,
                "pu_Address_State": booking.de_To_Address_State,
                "deToCompanyName": booking.puCompany,
                "de_To_Address_Street_1": booking.pu_Address_Street_1,
                "de_To_Address_Street_2": booking.pu_Address_street_2,
                "de_To_Address_PostalCode": booking.pu_Address_PostalCode,
                "de_To_Address_Suburb": booking.pu_Address_Suburb,
                "de_To_Address_Country": booking.pu_Address_Country,
                "de_to_Contact_F_LName": booking.pu_Contact_F_L_Name,
                "de_to_Phone_Main": booking.pu_Phone_Main,
                "de_Email": booking.pu_Email,
                "de_To_Address_State": booking.pu_Address_State,
                "pu_email_Group_Name": booking.de_Email_Group_Name,
                "pu_email_Group": booking.de_Email_Group_Emails,
                "de_Email_Group_Name": booking.pu_email_Group_Name,
                "de_Email_Group_Emails": booking.pu_email_Group,
                "pu_Address_Type": booking.de_To_AddressType,
                "de_To_AddressType": booking.pu_Address_Type,
                "pu_no_of_assists": booking.pu_no_of_assists,
                "de_no_of_assists": booking.de_no_of_assists,
                "pu_location": booking.pu_location,
                "de_to_location": booking.de_to_location,
                "pu_access": booking.pu_access,
                "de_access": booking.de_access,
                "pu_floor_number": booking.pu_floor_number,
                "de_floor_number": booking.de_floor_number,
                "pu_floor_access_by": booking.pu_floor_access_by,
                "de_to_floor_access_by": booking.de_to_floor_access_by,
                "pu_service": booking.pu_service,
                "de_service": booking.de_service,
            }
        else:
            newBooking = {
                "puCompany": booking.puCompany,
                "pu_Address_Street_1": booking.pu_Address_Street_1,
                "pu_Address_street_2": booking.pu_Address_street_2,
                "pu_Address_PostalCode": booking.pu_Address_PostalCode,
                "pu_Address_Suburb": booking.pu_Address_Suburb,
                "pu_Address_Country": booking.pu_Address_Country,
                "pu_Contact_F_L_Name": booking.pu_Contact_F_L_Name,
                "pu_Phone_Main": booking.pu_Phone_Main,
                "pu_Email": booking.pu_Email,
                "pu_Address_State": booking.pu_Address_State,
                "deToCompanyName": booking.deToCompanyName,
                "de_To_Address_Street_1": booking.de_To_Address_Street_1,
                "de_To_Address_Street_2": booking.de_To_Address_Street_2,
                "de_To_Address_PostalCode": booking.de_To_Address_PostalCode,
                "de_To_Address_Suburb": booking.de_To_Address_Suburb,
                "de_To_Address_Country": booking.de_To_Address_Country,
                "de_to_Contact_F_LName": booking.de_to_Contact_F_LName,
                "de_to_Phone_Main": booking.de_to_Phone_Main,
                "de_Email": booking.de_Email,
                "de_To_Address_State": booking.de_To_Address_State,
                "pu_email_Group_Name": booking.pu_email_Group_Name,
                "pu_email_Group": booking.pu_email_Group,
                "de_Email_Group_Name": booking.de_Email_Group_Name,
                "de_Email_Group_Emails": booking.de_Email_Group_Emails,
                "pu_Address_Type": booking.pu_Address_Type,
                "de_To_AddressType": booking.de_To_AddressType,
                "pu_no_of_assists": booking.de_no_of_assists,
                "de_no_of_assists": booking.pu_no_of_assists,
                "pu_location": booking.de_to_location,
                "de_to_location": booking.pu_location,
                "pu_access": booking.de_access,
                "de_access": booking.pu_access,
                "pu_floor_number": booking.de_floor_number,
                "de_floor_number": booking.pu_floor_number,
                "pu_floor_access_by": booking.de_to_floor_access_by,
                "de_to_floor_access_by": booking.pu_floor_access_by,
                "pu_service": booking.de_service,
                "de_service": booking.pu_service,
            }

        newBooking["b_bookingID_Visual"] = Bookings.get_max_b_bookingID_Visual() + 1
        newBooking["fk_client_warehouse"] = booking.fk_client_warehouse_id
        newBooking["b_client_warehouse_code"] = booking.b_client_warehouse_code
        newBooking["b_clientPU_Warehouse"] = booking.b_clientPU_Warehouse
        newBooking["b_client_name"] = booking.b_client_name
        newBooking["pk_booking_id"] = str(uuid.uuid1())
        newBooking["z_lock_status"] = booking.z_lock_status
        newBooking["b_status"] = "Ready for booking"
        newBooking["vx_freight_provider"] = booking.vx_freight_provider
        newBooking["kf_client_id"] = booking.kf_client_id
        newBooking[
            "b_clientReference_RA_Numbers"
        ] = booking.b_clientReference_RA_Numbers
        newBooking["vx_serviceName"] = booking.vx_serviceName
        newBooking["z_CreatedByAccount"] = request.user.username
        newBooking["booking_type"] = booking.booking_type
        newBooking["b_client_booking_ref_num"] = newBooking["pk_booking_id"]

        if is_4_child:
            newBooking[
                "x_booking_Created_With"
            ] = f"Child of #{booking.b_bookingID_Visual}"
        else:
            newBooking[
                "x_booking_Created_With"
            ] = f"Duped from #{booking.b_bookingID_Visual}"

        if dup_line_and_linedetail or is_4_child:
            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )

            for booking_line in booking_lines:
                if qtys_4_children:
                    if (
                        str(booking_line.pk) in qtys_4_children
                        and qtys_4_children[str(booking_line.pk)]
                        and qtys_4_children[str(booking_line.pk)] > 0
                    ):
                        booking_line.e_qty = qtys_4_children[str(booking_line.pk)]
                    else:
                        continue

                booking_line.pk_lines_id = None
                booking_line.fk_booking_id = newBooking["pk_booking_id"]
                booking_line.e_qty_delivered = 0
                booking_line.e_qty_adjusted_delivered = 0
                booking_line.z_createdTimeStamp = datetime.now()
                booking_line.z_modifiedTimeStamp = None
                booking_line.picked_up_timestamp = None
                booking_line.sscc = None
                new_pk_booking_lines_id = str(uuid.uuid1())

                if booking_line.pk_booking_lines_id:
                    booking_line_details = Booking_lines_data.objects.filter(
                        fk_booking_lines_id=booking_line.pk_booking_lines_id
                    )

                    for booking_line_detail in booking_line_details:
                        booking_line_detail.pk_id_lines_data = None
                        booking_line_detail.fk_booking_id = newBooking["pk_booking_id"]
                        booking_line_detail.fk_booking_lines_id = (
                            new_pk_booking_lines_id
                        )
                        booking_line_detail.z_createdTimeStamp = datetime.now()
                        booking_line_detail.z_modifiedTimeStamp = None
                        booking_line_detail.save()

                booking_line.pk_booking_lines_id = new_pk_booking_lines_id
                booking_line.save()

        serializer = BookingSerializer(data=newBooking)
        if serializer.is_valid():
            serializer.save()

            if is_4_child:
                status_history.create(
                    booking, "Parent Booking", request.user.username, datetime.now()
                )

            logger.info(
                f"{LOG_ID} Successfully duplicated! Original: {pk}({booking.b_bookingID_Visual}) -> New: {serializer.data['id']}({serializer.data['b_bookingID_Visual']})"
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def tick_manual_book(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        id = body["id"]
        user_id = request.user.id
        dme_employees = DME_employees.objects.filter(fk_id_user=user_id)

        if not dme_employees.exists():
            user_type = "CLIENT"
            return Response(status=status.HTTP_403_FORBIDDEN)

        booking = Bookings.objects.get(id=id)

        if booking.b_dateBookedDate:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            booking.x_manual_booked_flag = not booking.x_manual_booked_flag
            booking.api_booking_quote_id = None  # clear relation with Quote
            booking.save()
            serializer = BookingSerializer(booking)

            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def manual_book(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        id = body["id"]
        user_id = request.user.id
        dme_employees = DME_employees.objects.filter(fk_id_user=user_id)

        if not dme_employees.exists():
            user_type = "CLIENT"
            return Response(status=status.HTTP_403_FORBIDDEN)

        booking = Bookings.objects.get(id=id)

        if not booking.x_manual_booked_flag:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            status_history.create(booking, "Booked", request.user.username)
            booking.b_dateBookedDate = datetime.now()
            booking.save()
            serializer = BookingSerializer(booking)

            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel_book(self, request, pk, format=None):
        LOG_ID = "[CANCEL BOOK]"
        try:
            booking = Bookings.objects.get(pk=pk)
            cancel_book_oper(booking, request.user)
            return Response(
                {"success": True, "message": "Successfully Cancelled"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            trace_error.print()
            logger.info(f"{LOG_ID} Error: {str(e)}")
            return Response({"success": False}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def update_augment(self, request, format=None):
        Client_Process_Mgr.objects.filter(id=request.data["id"]).update(
            origin_puCompany=request.data["origin_puCompany"],
            origin_pu_Address_Street_1=request.data["origin_pu_Address_Street_1"],
            origin_pu_Address_Street_2=request.data["origin_pu_Address_Street_2"],
            origin_deToCompanyName=request.data["origin_deToCompanyName"],
            origin_pu_pickup_instructions_address=request.data[
                "origin_pu_pickup_instructions_address"
            ],
            origin_de_Email_Group_Emails=request.data["origin_de_Email_Group_Emails"],
        )
        return JsonResponse({"message": "Updated client successfully."})

    @action(detail=False, methods=["post"])
    def auto_augment(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        bookingId = body["bookingId"]
        booking = Bookings.objects.get(pk=bookingId)

        # Do now allow create new client_progress_mgr when already exist for this Booking.
        client_process = Client_Process_Mgr.objects.filter(
            fk_booking_id=bookingId
        ).first()

        if client_process:
            return JsonResponse(
                {"message": "Already Augmented!", "success": False},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply only "Salvage Expense" category
        if booking.b_booking_Category != "Salvage Expense":
            return JsonResponse(
                {
                    "message": "Booking Category is not Salvage Expense",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get client_auto_augment
        dme_client = DME_clients.objects.filter(
            dme_account_num=booking.kf_client_id
        ).first()
        client_auto_augment = Client_Auto_Augment.objects.filter(
            fk_id_dme_client_id=dme_client.pk_id_dme_client,
            de_to_companyName__iexact=booking.deToCompanyName.strip(),
        ).first()

        if not client_auto_augment:
            return JsonResponse(
                {
                    "message": "This Client is not set up for auto augment",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            auto_augment_oper(booking, client_auto_augment)
            return Response({"success": True})
        except Exception as e:
            logger.error(f"@207 Auto Augment - {str(e)}")
            return JsonResponse(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def set_pu_date_augment(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        bookingId = body["bookingId"]
        booking = Bookings.objects.get(pk=bookingId)

        try:
            tempo_client = DME_clients.objects.get(company_name="Tempo Pty Ltd")
            sydney_now = get_sydney_now_time("datetime")

            if booking.x_ReadyStatus == "Available From":
                weekno = sydney_now.weekday()

                if weekno > 4:
                    booking.puPickUpAvailFrom_Date = (
                        sydney_now + timedelta(days=6 - weekno)
                    ).date()
                    booking.pu_PickUp_By_Date = (
                        sydney_now + timedelta(days=6 - weekno)
                    ).date()
                else:
                    booking.puPickUpAvailFrom_Date = (
                        sydney_now + timedelta(days=1)
                    ).date()
                    booking.pu_PickUp_By_Date = (sydney_now + timedelta(days=1)).date()

                booking.pu_PickUp_Avail_Time_Hours = (
                    tempo_client.augment_pu_available_time.strftime("%H")
                )
                booking.pu_PickUp_Avail_Time_Minutes = (
                    tempo_client.augment_pu_available_time.strftime("%M")
                )

                booking.pu_PickUp_By_Time_Hours = (
                    tempo_client.augment_pu_by_time.strftime("%H")
                )
                booking.pu_PickUp_By_Time_Minutes = (
                    tempo_client.augment_pu_by_time.strftime("%M")
                )
            elif booking.x_ReadyStatus == "Available Now":
                booking.puPickUpAvailFrom_Date = sydney_now.date()
                booking.pu_PickUp_By_Date = sydney_now.date()

                booking.pu_PickUp_Avail_Time_Hours = sydney_now.strftime("%H")
                booking.pu_PickUp_Avail_Time_Minutes = 0
                booking.pu_PickUp_By_Time_Hours = (
                    tempo_client.augment_pu_by_time.strftime("%H")
                )
                booking.pu_PickUp_By_Time_Minutes = (
                    tempo_client.augment_pu_by_time.strftime("%M")
                )
            else:
                booking.puPickUpAvailFrom_Date = sydney_now.date()
                booking.pu_PickUp_By_Date = sydney_now.date()

                booking.pu_PickUp_Avail_Time_Hours = (
                    tempo_client.augment_pu_available_time.strftime("%H")
                )
                booking.pu_PickUp_Avail_Time_Minutes = (
                    tempo_client.augment_pu_available_time.strftime("%M")
                )
                booking.pu_PickUp_By_Time_Hours = (
                    tempo_client.augment_pu_by_time.strftime("%H")
                )
                booking.pu_PickUp_By_Time_Minutes = (
                    tempo_client.augment_pu_by_time.strftime("%M")
                )

            booking.save()
            serializer = BookingSerializer(booking)
            return Response(serializer.data)

        except Exception as e:
            # print(str(e))
            return JsonResponse(
                {"type": "Failure", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def revert_augment(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        bookingId = body["bookingId"]
        booking = Bookings.objects.get(pk=bookingId)

        try:
            client_process = Client_Process_Mgr.objects.filter(
                fk_booking_id=bookingId
            ).first()
            if client_process is not None:
                booking.puCompany = client_process.origin_puCompany
                booking.pu_Address_Street_1 = client_process.origin_pu_Address_Street_1
                booking.pu_Address_street_2 = client_process.origin_pu_Address_Street_2
                booking.pu_pickup_instructions_address = (
                    client_process.origin_pu_pickup_instructions_address
                )
                booking.deToCompanyName = client_process.origin_deToCompanyName
                booking.de_Email = client_process.origin_de_Email
                booking.de_Email_Group_Emails = (
                    client_process.origin_de_Email_Group_Emails
                )
                booking.de_To_Address_Street_1 = (
                    client_process.origin_de_To_Address_Street_1
                )
                booking.de_To_Address_Street_2 = (
                    client_process.origin_de_To_Address_Street_2
                )

                client_process.delete()
                booking.save()
                serializer = BookingSerializer(booking)
                return Response(serializer.data)
            else:
                return JsonResponse(
                    {"message": "This booking is not Augmented", "type": "Failure"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"type": "Failure", "message": "Exception occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def get_email_logs(self, request, format=None):
        booking_id = request.GET["bookingId"]

        if not booking_id:
            return JsonResponse(
                {"success": False, "message": "Booking id is required."}
            )

        email_logs = EmailLogs.objects.filter(booking_id=int(booking_id)).order_by(
            "-z_createdTimeStamp"
        )
        return JsonResponse(
            {
                "success": True,
                "results": EmailLogsSerializer(email_logs, many=True).data,
            }
        )

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def get_labels(self, request):
        LOG_ID = "[LABELS]"
        b_client_booking_ref_num = request.GET.get("b_client_booking_ref_num", None)
        message = f"#100 {LOG_ID}: b_client_booking_ref_num: {b_client_booking_ref_num}"
        logger.info(message)

        if not b_client_booking_ref_num:
            message = "Wrong identifier."
            logger.info(f"#101 {LOG_ID} {message}")
            raise ValidationError({"message": message})

        booking = (
            Bookings.objects.filter(b_client_booking_ref_num=b_client_booking_ref_num)
            .only(
                "id",
                "pk_booking_id",
                "b_bookingID_Visual",
                "b_client_name",
                "b_client_order_num",
                "b_client_sales_inv_num",
                "v_FPBookingNumber",
                "vx_freight_provider",
                "z_label_url",
                "pu_Address_State",
                "x_manual_booked_flag",
                "api_booking_quote",
                "b_dateBookedDate",
            )
            .order_by("id")
            .last()
        )

        if not booking:
            message = "Order does not exist!"
            logger.info(f"#102 {LOG_ID} {message}")
            raise ValidationError({"message": message})

        quotes = API_booking_quotes.objects.filter(
            fk_booking_id=booking.pk_booking_id, is_used=False
        ).only("id", "freight_provider", "account_code", "client_mu_1_minimum_values")
        logger.info(f"#103 {LOG_ID} BookingId: {booking.b_bookingID_Visual}")
        file_path = (
            f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au"
        )

        lines = booking.lines().only(
            "pk_lines_id",
            "pk_booking_lines_id",
            "sscc",
            "e_item",
            "e_item_type",
            "e_qty",
            "e_type_of_packaging",
        )
        line_datas = booking.line_datas().only(
            "pk_id_lines_data", "quantity", "itemDescription", "clientRefNumber"
        )

        sscc_arr = []
        result_with_sscc = {}

        for line in lines:
            if line.sscc and not line.sscc in sscc_arr:
                sscc_arr.append(line.sscc)

        for sscc in sscc_arr:
            result_with_sscc[str(sscc)] = []
            original_line = None
            selected_line_data = None
            label_url = None
            is_available = False

            # Auto populated lines
            for line_data in line_datas:
                if line_data.clientRefNumber != sscc:
                    continue

                for line in lines:
                    if (
                        not line.sscc
                        and line.e_item_type == line_data.modelNumber
                        and line.zbl_131_decimal_1 == line_data.itemSerialNumbers
                    ):
                        original_line = line
                        selected_line_data = line_data
                        break

                if original_line:
                    # For TNT orders, DME builds label for each SSCC
                    file_name = (
                        booking.pu_Address_State
                        + "_"
                        + str(booking.b_bookingID_Visual)
                        + "_"
                        + str(sscc)
                        + ".pdf"
                    )
                    is_available = doesFileExist(file_path, file_name)
                    label_url = f"{booking.vx_freight_provider.lower()}_au/{file_name}"

                    with open(f"{file_path}/{file_name}", "rb") as file:
                        pdf_data = str(b64encode(file.read()))[2:-1]

                    result_with_sscc[str(sscc)].append(
                        {
                            "pk_lines_id": original_line.pk_lines_id,
                            "sscc": sscc,
                            "e_item": original_line.e_item,
                            "e_item_type": original_line.e_item_type,
                            "e_qty": selected_line_data.quantity
                            if selected_line_data
                            else original_line.e_qty,
                            "e_type_of_packaging": original_line.e_type_of_packaging,
                            "is_available": is_available,
                            "url": label_url,
                            "pdf": pdf_data,
                        }
                    )

            # Manually populated lines
            if not original_line:
                for line in lines:
                    if line.sscc == sscc:
                        original_line = line
                        break

                # For TNT orders, DME builds label for each SSCC
                file_name = (
                    booking.pu_Address_State
                    + "_"
                    + str(booking.b_bookingID_Visual)
                    + "_"
                    + str(sscc)
                    + ".pdf"
                )
                is_available = doesFileExist(file_path, file_name)
                label_url = f"{booking.vx_freight_provider.lower()}_au/{file_name}"

                with open(f"{file_path}/{file_name}", "rb") as file:
                    pdf_data = str(b64encode(file.read()))[2:-1]

                result_with_sscc[str(sscc)].append(
                    {
                        "pk_lines_id": original_line.pk_lines_id,
                        "sscc": sscc,
                        "e_item": original_line.e_item,
                        "e_item_type": original_line.e_item_type,
                        "e_qty": selected_line_data.quantity
                        if selected_line_data
                        else original_line.e_qty,
                        "e_type_of_packaging": original_line.e_type_of_packaging,
                        "is_available": is_available,
                        "url": label_url,
                        "pdf": pdf_data,
                    }
                )

        # Full PDF
        full_label_name = ""
        try:
            pdf_data = None
            file_name = f"DME{booking.b_bookingID_Visual}.pdf"

            with open(f"{file_path}/{file_name}", "rb") as file:
                pdf_data = str(b64encode(file.read()))[2:-1]

            full_label_name = f"{booking.vx_freight_provider.lower()}_au/{file_name}"
        except:
            full_label_name = ""
            pass

        # Cheapest quote
        quote_json = {}
        scanned_quotes = []
        cheapest_quote = None

        for quote in quotes:
            if quote.packed_status == Booking_lines.SCANNED_PACK:
                scanned_quotes.append(quote)

        if scanned_quotes:
            cheapest_quote = booking.api_booking_quote or scanned_quotes[0]
            original_quote = None
            scanned_quote = None

            for quote in quotes:
                if (
                    quote.packed_status == Booking_lines.ORIGINAL
                    and quote.client_mu_1_minimum_values == booking.inv_sell_quoted
                ):
                    original_quote = quote

                if (
                    quote.packed_status == Booking_lines.SCANNED_PACK
                    and quote.client_mu_1_minimum_values == booking.inv_booked_quoted
                ):
                    scanned_quote = quote

            for quote in scanned_quotes:
                if (
                    quote.client_mu_1_minimum_values
                    < cheapest_quote.client_mu_1_minimum_values
                ):
                    cheapest_quote = quote

            if (
                booking.api_booking_quote
                and cheapest_quote != booking.api_booking_quote
            ):
                quote_json = {
                    "cheapest": {
                        "id": cheapest_quote.pk,
                        "fp": cheapest_quote.freight_provider,
                        "cost_dollar": cheapest_quote.client_mu_1_minimum_values,
                        "savings": booking.api_booking_quote.client_mu_1_minimum_values
                        - cheapest_quote.client_mu_1_minimum_values,
                    }
                }

                if original_quote:
                    quote_json["original"] = {
                        "fp": original_quote.freight_provider,
                        "cost_dollar": original_quote.client_mu_1_minimum_values,
                    }

                if scanned_quote:
                    quote_json["scanned"] = {
                        "fp": scanned_quote.freight_provider,
                        "cost_dollar": scanned_quote.client_mu_1_minimum_values,
                    }

        result = {
            "id": booking.pk,
            "pk_booking_id": booking.pk_booking_id,
            "b_bookingID_Visual": booking.b_bookingID_Visual,
            "b_client_name": booking.b_client_name,
            "b_client_order_num": booking.b_client_order_num,
            "b_client_sales_inv_num": booking.b_client_sales_inv_num,
            "v_FPBookingNumber": booking.v_FPBookingNumber,
            "vx_freight_provider": booking.vx_freight_provider,
            "x_manual_booked_flag": booking.x_manual_booked_flag,
            "api_booking_quote_id": booking.api_booking_quote_id,
            "b_dateBookedDate": booking.b_dateBookedDate,
            "no_of_sscc": len(result_with_sscc),
            "url": booking.z_label_url,
            "pdf": pdf_data,
            "full_label_name": full_label_name,
            "sscc_obj": result_with_sscc,
            "quotes_cnt": quotes.count(),
            "quote": quote_json,
        }

        return JsonResponse({"success": True, "result": result})

    @action(detail=True, methods=["post"])
    def repack(self, request, pk, format=None):
        LOG_ID = "[REPACK LINES]"
        body = literal_eval(request.body.decode("utf8"))
        repack_status = body["repackStatus"]
        # logger.info(f"@200 {LOG_ID}, BookingPk: {pk}, Repack Status: {repack_status}")

        try:
            booking = Bookings.objects.get(pk=pk)

            if repack_status and repack_status[0] == "-":
                booking_reset_repack(booking, repack_status[1:])
            elif repack_status == "auto":
                booking_auto_repack(booking, repack_status)
            else:
                booking_manual_repack(booking, repack_status)

            return JsonResponse({"success": True})
        except Exception as e:
            trace_error.print()
            logger.error(f"@204 {LOG_ID} Error: {str(e)}")
            return JsonResponse({"success": False}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def get_status_page_url(self, request):
        LOG_ID = "[get_status_page_url]"
        v_FPBookingNumber = request.GET.get("v_FPBookingNumber", None)
        logger.info(f"{LOG_ID} v_FPBookingNumber: {v_FPBookingNumber}")

        if v_FPBookingNumber:
            bookings = Bookings.objects.filter(
                v_FPBookingNumber__iexact=v_FPBookingNumber
            )

            if bookings:
                booking = bookings.first()

                if not booking.b_client_booking_ref_num:
                    booking.b_client_booking_ref_num = (
                        f"{booking.b_bookingID_Visual}_{booking.pk_booking_id}"
                    )
                    booking.save()

                status_page_url = f"{settings.WEB_SITE_URL}/status/{booking.b_client_booking_ref_num}/"
                return JsonResponse({"success": True, "statusPageUrl": status_page_url})

        logger.error(f"{LOG_ID} Failed to find status page url")
        return JsonResponse({"success": False}, status=status.HTTP_400_BAD_REQUEST)


class BookingLinesViewSet(viewsets.ViewSet):
    serializer_class = BookingLineSerializer

    @action(detail=False, methods=["get"])
    def get_booking_lines(self, request, format=None):
        pk_booking_id = request.GET["pk_booking_id"]
        booking_lines = Booking_lines.objects.filter(is_deleted=False)

        if pk_booking_id != "undefined":
            booking_lines = booking_lines.filter(fk_booking_id=pk_booking_id)

        return JsonResponse(
            {"booking_lines": BookingLineSerializer(booking_lines, many=True).data}
        )

    @action(detail=False, methods=["get"])
    def get_count(self, request, format=None):
        booking_ids = request.GET["bookingIds"].split(",")
        bookings = Bookings.objects.filter(id__in=booking_ids)

        count = 0
        for booking in bookings:
            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )

            for booking_line in booking_lines:
                count = count + booking_line.e_qty

        return JsonResponse({"count": count})

    @action(detail=False, methods=["post"])
    def create_booking_line(self, request, format=None):
        request.data["pk_booking_lines_id"] = str(uuid.uuid1())
        serializer = BookingLineSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def duplicate_booking_line(self, request, format=None):
        booking_line = Booking_lines.objects.get(pk=request.data["pk_lines_id"])
        newbooking_line = {
            "fk_booking_id": booking_line.fk_booking_id,
            "pk_booking_lines_id": str(uuid.uuid1()),
            "e_type_of_packaging": booking_line.e_type_of_packaging,
            "e_item": booking_line.e_item,
            "e_qty": booking_line.e_qty,
            "e_weightUOM": booking_line.e_weightUOM,
            "e_weightPerEach": booking_line.e_weightPerEach,
            "e_dimUOM": booking_line.e_dimUOM,
            "e_dimLength": booking_line.e_dimLength,
            "e_dimWidth": booking_line.e_dimWidth,
            "e_dimHeight": booking_line.e_dimHeight,
            "e_Total_KG_weight": booking_line.e_Total_KG_weight,
            "e_1_Total_dimCubicMeter": booking_line.e_1_Total_dimCubicMeter,
            "total_2_cubic_mass_factor_calc": booking_line.total_2_cubic_mass_factor_calc,
            "z_createdTimeStamp": datetime.now(),
            "z_modifiedTimeStamp": None,
            "packed_status": booking_line.packed_status,
        }
        serializer = BookingLineSerializer(data=newbooking_line)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["put"])
    def update_booking_line(self, request, pk, format=None):
        booking_line = Booking_lines.objects.get(pk=pk)
        serializer = BookingLineSerializer(booking_line, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            trace_error.print()
            logger.error("Exception: ", e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete_booking_line(self, request, pk, format=None):
        booking_line = Booking_lines.objects.get(pk=pk)

        try:
            # Delete related line_data
            line_datas = Booking_lines_data.objects.filter(
                fk_booking_lines_id=booking_line.pk_booking_lines_id
            )

            if line_datas.exists():
                line_datas.delete()

            booking_line.delete()
            return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            trace_error.print()
            logger.error(f"#330 - booking line delete: {str(e)}")
            return JsonResponse({"error": "Can not delete BookingLine"})

    @action(detail=False, methods=["post"])
    def calc_collected(self, request, format=None):
        ids = request.data["ids"]
        type = request.data["type"]

        try:
            for id in ids:
                booking_line = Booking_lines.objects.get(pk_lines_id=id)

                if type == "Calc":
                    if not booking_line.e_qty:
                        booking_line.e_qty = 0
                    if not booking_line.e_qty_awaiting_inventory:
                        booking_line.e_qty_awaiting_inventory = 0

                    booking_line.e_qty_collected = int(booking_line.e_qty) - int(
                        booking_line.e_qty_awaiting_inventory
                    )
                    booking_line.save()
                elif type == "Clear":
                    booking_line.e_qty_collected = 0
                    booking_line.save()
            return JsonResponse(
                {"success": "All bookings e_qty_collected has been calculated"}
            )
        except Exception as e:
            # print("Exception: ", e)
            return JsonResponse({"error": "Got error, please contact support center"})


class BookingLineDetailsViewSet(viewsets.ViewSet):
    serializer_class = BookingLineDetailSerializer

    @action(detail=False, methods=["get"])
    def get_booking_line_details(self, request, format=None):
        pk_booking_id = request.GET["pk_booking_id"]
        booking_line_details = Booking_lines_data.objects.all()

        if pk_booking_id != "undefined":
            booking_line_details = Booking_lines_data.objects.filter(
                fk_booking_id=pk_booking_id
            )

        return JsonResponse(
            {
                "booking_line_details": BookingLineDetailSerializer(
                    booking_line_details, many=True
                ).data
            }
        )

    @action(detail=False, methods=["post"])
    def create_booking_line_detail(self, request, format=None):
        serializer = BookingLineDetailSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def duplicate_booking_line_detail(self, request, format=None):
        booking_line_detail = Booking_lines_data.objects.get(
            pk=request.data["pk_id_lines_data"]
        )
        newbooking_line_detail = {
            "fk_booking_id": booking_line_detail.fk_booking_id,
            "modelNumber": booking_line_detail.modelNumber,
            "itemDescription": booking_line_detail.itemDescription,
            "quantity": booking_line_detail.quantity,
            "itemFaultDescription": booking_line_detail.itemFaultDescription,
            "insuranceValueEach": booking_line_detail.insuranceValueEach,
            "gap_ra": booking_line_detail.gap_ra,
            "clientRefNumber": booking_line_detail.clientRefNumber,
            "fk_booking_lines_id": booking_line_detail.fk_booking_lines_id,
            "z_createdTimeStamp": datetime.now(),
            "z_modifiedTimeStamp": None,
        }
        serializer = BookingLineDetailSerializer(data=newbooking_line_detail)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["put"])
    def update_booking_line_detail(self, request, pk, format=None):
        booking_line_detail = Booking_lines_data.objects.get(pk=pk)
        serializer = BookingLineDetailSerializer(booking_line_detail, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete_booking_line_detail(self, request, pk, format=None):
        booking_line_detail = Booking_lines_data.objects.get(pk=pk)
        serializer = BookingLineDetailSerializer(booking_line_detail)

        try:
            booking_line_detail.delete()
            return JsonResponse({"Deleted BookingLineDetail ": serializer.data})
        except Exception as e:
            trace_error.print()
            logger.error(f"#331 - booking lines data delete: {str(e)}")
            return JsonResponse({"error": "Can not delete BookingLineDetail"})

    @action(detail=False, methods=["post"])
    def bulk_move(self, request):
        """
        bulk move LineData(s) to other Line
        """

        LOG_ID = "[BULK MOVE LINE DATA]"
        line_id = request.data["lineId"]
        line_detail_ids = request.data["lineDetailIds"]
        moved_line_detail_ids = []
        logger.info(f"{LOG_ID} Request payload: {request.data}")

        try:
            line = Booking_lines.objects.get(pk=line_id)
            line_details = Booking_lines_data.objects.filter(
                pk__in=line_detail_ids
            ).only("pk", "fk_booking_lines_id")

            for line_detail in line_details:
                line_detail.fk_booking_lines_id = line.pk_booking_lines_id
                line_detail.save()
                moved_line_detail_ids.append(line_detail.pk)

            logger.info(f"{LOG_ID} Success. Moved Id(s):{moved_line_detail_ids}")
            return JsonResponse(
                {
                    "message": "LineDetails are successfully moved",
                    "result": moved_line_detail_ids,
                }
            )
        except Exception as e:
            trace_error.print()
            logger.error(f"{LOG_ID} Error: str{e}")
            return JsonResponse(
                {"error": "Can not move BookingLineDetails"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"

        if user_type == "DME":
            clientWarehouseObject_list = Client_warehouses.objects.all().order_by(
                "client_warehouse_code"
            )
            queryset = clientWarehouseObject_list
            return queryset
        else:
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client_employee_role = client_employee.get_role()

            if client_employee_role == "company":
                clientWarehouseObject_list = Client_warehouses.objects.filter(
                    fk_id_dme_client_id=int(client_employee.fk_id_dme_client_id)
                ).order_by("client_warehouse_code")
                queryset = clientWarehouseObject_list
                return queryset
            elif client_employee_role == "warehouse":
                employee_warehouse_id = client_employee.warehouse_id
                employee_warehouse = Client_warehouses.objects.get(
                    pk_id_client_warehouses=employee_warehouse_id
                )
                queryset = [employee_warehouse]
                return queryset


class PackageTypesViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def get_packagetypes(self, request, pk=None):
        packageTypes = Dme_package_types.objects.all().order_by("id")

        return_datas = []
        for packageType in packageTypes:
            return_data = {
                "id": packageType.id,
                "dmePackageTypeCode": packageType.dmePackageTypeCode,
                "dmePackageCategory": packageType.dmePackageCategory,
                "dmePackageTypeDesc": packageType.dmePackageTypeDesc,
            }
            return_datas.append(return_data)
        return JsonResponse({"packageTypes": return_datas})


class BookingStatusViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_all_booking_status(self, request, pk=None):
        user_id = request.user.id
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"

        if user_type == "DME":
            all_booking_status = Utl_dme_status.objects.all().order_by("sort_order")
        else:
            all_booking_status = Utl_dme_status.objects.filter(
                z_show_client_option=1
            ).order_by("sort_order")

        return_datas = []
        if not all_booking_status.exists():
            return JsonResponse({"all_booking_status": []})
        else:
            for booking_status in all_booking_status:
                return_data = {
                    "id": booking_status.id,
                    "dme_delivery_status": booking_status.dme_delivery_status,
                    "sort_order": booking_status.sort_order,
                }
                return_datas.append(return_data)
            return JsonResponse({"all_booking_status": return_datas})


class StatusHistoryViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        pk_booking_id = self.request.GET.get("pk_booking_id")
        queryset = Dme_status_history.objects.filter(
            fk_booking_id=pk_booking_id
        ).order_by("-id")

        return JsonResponse(
            {"results": StatusHistorySerializer(queryset, many=True).data}
        )

    @action(detail=False, methods=["post"])
    def save_status_history(self, request, pk=None):
        LOG_ID = "STATUS_HISTORY_CREATE"
        try:
            logger.info(f"{LOG_ID} Payload: {request.data}")
            booking = Bookings.objects.get(pk_booking_id=request.data["fk_booking_id"])
            status_last = request.data.get("status_last")
            event_time_stamp = request.data.get("event_time_stamp")
            dme_notes = request.data.get("dme_notes")
            is_from_script = request.data.get("is_from_script")

            if is_from_script:
                fp = booking.get_fp()
                b_status_API = request.data.get("fp_status")
                data = {
                    "b_status_API": b_status_API,
                    "status_desc": request.data.get("fp_status_description"),
                    "event_time": event_time_stamp,
                }
                create_fp_status_history(booking, fp, data)
                status_last = get_dme_status_from_fp_status(
                    fp.fp_company_name, b_status_API, booking
                )

                if not status_last:
                    logger.info(
                        f"{LOG_ID} Booking: {booking}, FP: {fp}, b_status_API: {b_status_API}"
                    )
                    return Response(
                        {"success": False}, status=status.HTTP_400_BAD_REQUEST
                    )

            status_history.create(
                booking,
                status_last,
                request.user.username,
                event_time_stamp,
                dme_notes,
            )

            # ######################################## #
            #    Disabled because it was for `Cope`    #
            # ######################################## #
            # if request.data["status_last"] == "In Transit":
            #     calc_collect_after_status_change(
            #         request.data["fk_booking_id"], request.data["status_last"]
            #     )
            # elif request.data["status_last"] == "Delivered":
            #     booking.z_api_issue_update_flag_500 = 0
            #     booking.delivery_booking = str(datetime.now())
            #     booking.save()

            # status_category = get_status_category_from_status(
            #     request.data["status_last"]
            # )

            # if status_category == "Transit":
            #     booking.s_20_Actual_Pickup_TimeStamp = request.data[
            #         "event_time_stamp"
            #     ]

            #     if booking.s_20_Actual_Pickup_TimeStamp:
            #         z_calculated_ETA = datetime.strptime(
            #             booking.s_20_Actual_Pickup_TimeStamp[:10], "%Y-%m-%d"
            #         ) + timedelta(days=booking.delivery_kpi_days)
            #     else:
            #         z_calculated_ETA = datetime.now() + timedelta(
            #             days=booking.delivery_kpi_days
            #         )

            #     if not booking.b_given_to_transport_date_time:
            #         booking.b_given_to_transport_date_time = datetime.now()

            #     booking.z_calculated_ETA = datetime.strftime(
            #         z_calculated_ETA, "%Y-%m-%d"
            #     )
            # elif status_category == "Complete":
            #     booking.s_21_Actual_Delivery_TimeStamp = request.data[
            #         "event_time_stamp"
            #     ]
            #     booking.delivery_booking = request.data["event_time_stamp"][:10]
            #     booking.z_api_issue_update_flag_500 = 0

            # booking.b_status = request.data["status_last"]
            # booking.save()
            # serializer.save()

            return Response({"success": True})
        except Exception as e:
            trace_error.print()
            logger.error(f"@902 - save_status_history Error: {str(e)}")
            return Response({"success": False}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["put"])
    def update_status_history(self, request, pk, format=None):
        status_history = Dme_status_history.objects.get(pk=pk)
        booking = Bookings.objects.get(pk_booking_id=request.data["fk_booking_id"])
        serializer = StatusHistorySerializer(status_history, data=request.data)

        try:
            if serializer.is_valid():
                status_category = get_status_category_from_status(
                    request.data["status_last"]
                )

                if status_category == "Transit":
                    calc_collect_after_status_change(
                        request.data["fk_booking_id"], request.data["status_last"]
                    )

                    booking.s_20_Actual_Pickup_TimeStamp = request.data[
                        "event_time_stamp"
                    ]

                    if booking.s_20_Actual_Pickup_TimeStamp:
                        z_calculated_ETA = datetime.strptime(
                            booking.s_20_Actual_Pickup_TimeStamp[:10], "%Y-%m-%d"
                        ) + timedelta(days=booking.delivery_kpi_days)
                    else:
                        z_calculated_ETA = datetime.now() + timedelta(
                            days=booking.delivery_kpi_days
                        )

                    if not booking.b_given_to_transport_date_time:
                        booking.b_given_to_transport_date_time = (
                            booking.s_20_Actual_Pickup_TimeStamp
                        )

                    booking.z_calculated_ETA = datetime.strftime(
                        z_calculated_ETA, "%Y-%m-%d"
                    )
                elif status_category == "Complete":
                    booking.s_21_Actual_Delivery_TimeStamp = request.data[
                        "event_time_stamp"
                    ]
                    booking.delivery_booking = request.data["event_time_stamp"][:10]

                # When update last statusHistory of a booking
                if (
                    status_history.is_last_status_of_booking(booking)
                    and status_history.status_last != request.data["status_last"]
                ):
                    booking.b_status = request.data["status_last"]

                booking.save()
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print("Exception: ", e)
            logger.info(f"Exception: {e}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Code for only [TNT REBOOK]
    @action(detail=False, methods=["post"])
    def create_with_pu_dates(self, request, pk=None):
        booking_id = request.data["bookingId"]
        booking = Bookings.objects.get(id=int(booking_id))

        if booking and booking.fk_fp_pickup_id:
            dme_status_history = Dme_status_history.objects.create(
                fk_booking_id=booking.pk_booking_id
            )

            pu_avail_date_str = booking.puPickUpAvailFrom_Date.strftime("%Y-%m-%d")
            pu_avail_time_str = f"{str(booking.pu_PickUp_Avail_Time_Hours).zfill(2)}-{str(booking.pu_PickUp_Avail_Time_Minutes).zfill(2)}-00"

            pu_by_date_str = booking.pu_PickUp_By_Date.strftime("%Y-%m-%d")
            pu_by_time_str = f"{str(booking.pu_PickUp_By_Time_Hours).zfill(2)}-{str(booking.pu_PickUp_By_Time_Minutes).zfill(2)}-00"

            dme_status_history.notes = (
                f"Rebooked PU Info - Current PU ID: {booking.fk_fp_pickup_id} "
                + f"Pickup From: ({pu_avail_date_str} {pu_avail_time_str}) "
                + f"Pickup By: ({pu_by_date_str} {pu_by_time_str})"
            )
            dme_status_history.save()

            status_histories = Dme_status_history.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )

            return JsonResponse(
                {
                    "success": True,
                    "result": StatusHistorySerializer(dme_status_history).data,
                }
            )

        return JsonResponse({"success": False})


class FPViewSet(viewsets.ViewSet):
    serializer_class = FpSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        resultObjects = Fp_freight_providers.objects.all().order_by("fp_company_name")

        return JsonResponse(
            {"success": True, "results": FpSerializer(resultObjects, many=True).data}
        )

    @action(detail=True, methods=["get"])
    def get(self, request, pk, format=None):
        return_data = []
        try:
            resultObjects = []
            resultObjects = Fp_freight_providers.objects.get(pk=pk)
            if not resultObjects.fp_inactive_date:
                return_data.append(
                    {
                        "id": resultObjects.id,
                        "fp_company_name": resultObjects.fp_company_name,
                        "fp_address_country": resultObjects.fp_address_country,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        try:
            resultObject = Fp_freight_providers.objects.get_or_create(
                fp_company_name=request.data["fp_company_name"],
                fp_address_country=request.data["fp_address_country"],
            )

            return JsonResponse(
                {
                    "result": FpSerializer(resultObject[0]).data,
                    "isCreated": resultObject[1],
                }
            )
        except Exception as e:
            # print("@Exception", e)
            return JsonResponse({"results": None})

    @action(detail=True, methods=["put"])
    def edit(self, request, pk, format=None):
        fp_freight_providers = Fp_freight_providers.objects.get(pk=pk)
        serializer = FpSerializer(fp_freight_providers, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete(self, request, pk, format=None):
        fp_freight_providers = Fp_freight_providers.objects.get(pk=pk)

        try:
            fp_freight_providers.delete()
            return JsonResponse({"results": fp_freight_providers})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["get"])
    def get_carriers(self, request, pk=None):
        fp_id = request.GET["fp_id"]
        return_data = []
        try:
            resultObjects = []
            resultObjects = FP_carriers.objects.filter(fk_fp=fp_id)

            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "fk_fp": resultObject.fk_fp,
                        "carrier": resultObject.carrier,
                        "connote_start_value": resultObject.connote_start_value,
                        "connote_end_value": resultObject.connote_end_value,
                        "current_value": resultObject.current_value,
                        "label_end_value": resultObject.label_end_value,
                        "label_start_value": resultObject.label_start_value,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def add_carrier(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = FP_carriers.objects.create(
                fk_fp=request.data["fk_fp"],
                carrier=request.data["carrier"],
                connote_start_value=request.data["connote_start_value"],
                connote_end_value=request.data["connote_end_value"],
                current_value=request.data["current_value"],
                label_start_value=request.data["label_start_value"],
                label_end_value=request.data["label_end_value"],
            )

            return JsonResponse({"results": resultObjects})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=True, methods=["put"])
    def edit_carrier(self, request, pk, format=None):
        fp_carrier = FP_carriers.objects.get(pk=pk)
        serializer = CarrierSerializer(fp_carrier, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete_carrier(self, request, pk, format=None):
        fp_carrier = FP_carriers.objects.get(id=pk)

        try:
            fp_carrier.delete()
            return JsonResponse({"results": fp_carrier})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["get"])
    def get_zones(self, request, pk=None):
        fp_id = self.request.GET["fp_id"]
        page_item_cnt = self.request.query_params.get("pageItemCnt", 10)
        page_ind = self.request.query_params.get("pageInd", 0)
        return_data = []
        try:
            resultObjects = []
            resultObjects = FP_zones.objects.filter(fk_fp=fp_id)
            # Count
            zones_cnt = resultObjects.count()

            # Pagination
            page_cnt = (
                int(zones_cnt / int(page_item_cnt))
                if zones_cnt % int(page_item_cnt) == 0
                else int(zones_cnt / int(page_item_cnt)) + 1
            )
            resultObjects = resultObjects[
                int(page_item_cnt)
                * int(page_ind) : int(page_item_cnt)
                * (int(page_ind) + 1)
            ]
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "fk_fp": resultObject.fk_fp,
                        "suburb": resultObject.suburb,
                        "state": resultObject.state,
                        "postal_code": resultObject.postal_code,
                        "zone": resultObject.zone,
                        "carrier": resultObject.carrier,
                        "service": resultObject.service,
                        "sender_code": resultObject.sender_code,
                    }
                )
            return JsonResponse(
                {
                    "results": return_data,
                    "page_cnt": page_cnt,
                    "page_ind": page_ind,
                    "page_item_cnt": page_item_cnt,
                }
            )
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def add_zone(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = FP_zones.objects.create(
                fk_fp=request.data["fk_fp"],
                suburb=request.data["suburb"],
                state=request.data["state"],
                postal_code=request.data["postal_code"],
                zone=request.data["zone"],
                carrier=request.data["carrier"],
                service=request.data["service"],
                sender_code=request.data["sender_code"],
            )

            return JsonResponse({"results": resultObjects})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=True, methods=["put"])
    def edit_zone(self, request, pk, format=None):
        fp_zone = FP_zones.objects.get(pk=pk)
        serializer = ZoneSerializer(fp_zone, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete_zone(self, request, pk, format=None):
        fp_zone = FP_zones.objects.get(pk=pk)

        try:
            fp_zone.delete()
            return JsonResponse({"results": fp_zone})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})


class EmailTemplatesViewSet(viewsets.ViewSet):
    serializer_class = EmailTemplatesSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = DME_Email_Templates.objects.all()
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "fk_idEmailParent": resultObject.fk_idEmailParent,
                        "emailName": resultObject.emailName,
                        "emailBody": resultObject.emailBody,
                        "sectionName": resultObject.sectionName,
                        "emailBodyRepeatEven": resultObject.emailBodyRepeatEven,
                        "emailBodyRepeatOdd": resultObject.emailBodyRepeatOdd,
                        "whenAttachmentUnavailable": resultObject.whenAttachmentUnavailable,
                        "z_createdByAccount": resultObject.z_createdByAccount,
                        "z_createdTimeStamp": resultObject.z_createdTimeStamp,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=True, methods=["get"])
    def get(self, request, pk, format=None):
        return_data = []
        try:
            resultObjects = []
            resultObject = DME_Email_Templates.objects.get(pk=pk)

            return_data.append(
                {
                    "id": resultObject.id,
                    "fk_idEmailParent": resultObject.fk_idEmailParent,
                    "emailName": resultObject.emailName,
                    "emailBody": resultObject.emailBody,
                    "sectionName": resultObject.sectionName,
                    "emailBodyRepeatEven": resultObject.emailBodyRepeatEven,
                    "emailBodyRepeatOdd": resultObject.emailBodyRepeatOdd,
                    "whenAttachmentUnavailable": resultObject.whenAttachmentUnavailable,
                    "z_createdByAccount": resultObject.z_createdByAccount,
                    "z_createdTimeStamp": resultObject.z_createdTimeStamp,
                }
            )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print("@Exception", e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = DME_Email_Templates.objects.create(
                fk_idEmailParent=request.data["fk_idEmailParent"],
                emailName=request.data["emailName"],
                emailBody=request.data["emailBody"],
                sectionName=request.data["sectionName"],
                emailBodyRepeatEven=request.data["emailBodyRepeatEven"],
                emailBodyRepeatOdd=request.data["emailBodyRepeatOdd"],
                whenAttachmentUnavailable=request.data["whenAttachmentUnavailable"],
            )

            return JsonResponse({"results": resultObjects})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=True, methods=["put"])
    def edit(self, request, pk, format=None):
        email_template = DME_Email_Templates.objects.get(pk=pk)
        # return JsonResponse({"results": (email_template.emailBody)})
        # serializer = EmailTemplatesSerializer(email_template, data=request.data)

        try:
            DME_Email_Templates.objects.filter(pk=pk).update(
                emailBody=request.data["emailBody"]
            )
            return JsonResponse({"results": request.data})
            # if serializer.is_valid():
            # try:
            # serializer.save()
            # return Response(serializer.data)
            # except Exception as e:
            # print('%s (%s)' % (e.message, type(e)))
            # return Response({"results": e.message})
            # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({"results": str(e)})
            # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete(self, request, pk, format=None):
        email_template = DME_Email_Templates.objects.get(pk=pk)

        try:
            email_template.delete()
            return JsonResponse({"results": fp_freight_providers})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})


class OptionsViewSet(viewsets.ViewSet):
    serializer_class = OptionsSerializer

    def list(self, request, pk=None):
        try:
            queryset = DME_Options.objects.filter(show_in_admin=True)
            serializer = OptionsSerializer(queryset, many=True)
            return JsonResponse({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse({"error": str(e)})

    def partial_update(self, request, pk, format=None):
        dme_options = DME_Options.objects.get(pk=pk)
        serializer = OptionsSerializer(dme_options, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StatusViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_status_actions(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Utl_dme_status_actions.objects.all()
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "dme_status_action": resultObject.dme_status_action,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def create_status_action(self, request, pk=None):
        try:
            utl_dme_status_action = Utl_dme_status_actions(
                dme_status_action=request.data["newStatusAction"]
            )
            utl_dme_status_action.save()
            return JsonResponse({"success": "Created new status action"})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"error": "Can not create new status action"})

    @action(detail=False, methods=["get"])
    def get_status_details(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Utl_dme_status_details.objects.all()
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "dme_status_detail": resultObject.dme_status_detail,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def create_status_detail(self, request, pk=None):
        try:
            utl_dme_status_action = Utl_dme_status_details(
                dme_status_detail=request.data["newStatusDetail"]
            )
            utl_dme_status_action.save()
            return JsonResponse({"success": "Created new status detail"})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"error": "Can not create new status action"})


class ApiBCLViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_api_bcls(self, request, pk=None):
        booking_id = request.GET["bookingId"]
        booking = Bookings.objects.get(id=int(booking_id))
        return_data = []

        try:
            resultObjects = []
            resultObjects = Api_booking_confirmation_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "fk_booking_id": resultObject.fk_booking_id,
                        "fk_booking_line_id": resultObject.fk_booking_line_id,
                        "label_code": resultObject.label_code,
                        "client_item_reference": resultObject.client_item_reference,
                        "fp_event_date": resultObject.fp_event_date,
                        "fp_event_time": resultObject.fp_event_time,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})


class DmeReportsViewSet(viewsets.ViewSet):
    def list(self, request):
        queryset = DME_reports.objects.all()
        serializer = DmeReportsSerializer(queryset, many=True)
        return Response(serializer.data)


class FPStoreBookingLog(viewsets.ViewSet):
    # def list(self, request):
    #     queryset = FP_Store_Booking_Log.objects.all()
    #     serializer = FPStoreBookingLogSerializer(queryset, many=True)
    #     return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def get_store_booking_logs(self, request, pk=None):
        v_FPBookingNumber = request.GET["v_FPBookingNumber"]
        queryset = FP_Store_Booking_Log.objects.filter(
            v_FPBookingNumber=v_FPBookingNumber
        ).order_by("-id")
        serializer = FPStoreBookingLogSerializer(queryset, many=True)
        return Response(serializer.data)


class ApiBookingQuotesViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_pricings(self, request):
        dme_employee = DME_employees.objects.filter(fk_id_user=request.user.id)

        if dme_employee:
            user_type = "DME"
            fields_to_exclude = []
        else:
            user_type = "CLIENT"
            fields_to_exclude = ["fee", "client_mark_up_percent", "fuel_levy_base"]

        fk_booking_id = request.GET["fk_booking_id"]
        booking = Bookings.objects.get(pk_booking_id=fk_booking_id)
        queryset = (
            API_booking_quotes.objects.prefetch_related("vehicle")
            .filter(fk_booking_id=fk_booking_id, is_used=False)
            .exclude(service_name="Air Freight")
            .order_by("client_mu_1_minimum_values")
        )

        # When DmeInvoice is set
        if booking.inv_dme_invoice_no and booking.api_booking_quote:
            queryset = queryset.filter(pk=booking.api_booking_quote.pk)

        client = booking.get_client()
        context = {
            "booking": booking,
            "client_customer_mark_up": client.client_customer_mark_up if client else 0,
        }

        serializer = ApiBookingQuotesSerializer(
            queryset,
            many=True,
            fields_to_exclude=fields_to_exclude,
            context=context,
        )

        # When DmeInvoice and Quote $* is set
        res = list(serializer.data)
        if (
            res
            and booking.inv_dme_invoice_no
            and (booking.inv_sell_quoted_override or booking.inv_sell_quoted)
        ):
            res = list(serializer.data)[0]
            res["freight_provider"] = booking.vx_freight_provider
            quoted_amount = (
                booking.inv_sell_quoted_override
                if booking.inv_sell_quoted_override
                else booking.inv_sell_quoted
            )
            res["client_mu_1_minimum_values"] = quoted_amount
            quote = booking.api_booking_quote
            surcharge_total = quote.x_price_surcharge if quote.x_price_surcharge else 0
            without_surcharge = res["client_mu_1_minimum_values"] - surcharge_total
            fp = Fp_freight_providers.objects.get(
                fp_company_name__iexact=booking.vx_freight_provider
            )
            res["fuel_levy_base_cl"] = without_surcharge * fp.fp_markupfuel_levy_percent
            res["cost_dollar"] = without_surcharge - res["fuel_levy_base_cl"]
            res = [res]

        return Response(res)


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
def download(request):
    LOG_ID = "[DOWNLOAD]"
    body = literal_eval(request.body.decode("utf8"))
    download_option = body["downloadOption"]
    file_paths = []
    logger.info(f"{LOG_ID} Option: {download_option}")

    if download_option != "logs":
        if download_option in ["pricing-only", "pricing-rule", "xls import"]:
            file_name = body["fileName"]
        elif download_option == "manifest":
            z_manifest_url = body["z_manifest_url"]
        elif download_option == "zpl":
            pass
        else:
            bookingIds = body["ids"]
            bookings = Bookings.objects.filter(id__in=bookingIds)

    if download_option == "pricing-only":
        src_file_path = f"./static/uploaded/pricing_only/achieve/{file_name}"
        file_paths.append(src_file_path)
        file_name_without_ext = file_name.split(".")[0]
        result_file_record = DME_Files.objects.filter(
            file_name__icontains=file_name_without_ext, file_type="pricing-result"
        )

        if result_file_record:
            file_paths.append(result_file_record.first().file_path)
    elif download_option == "pricing-rule":
        src_file_path = f"./static/uploaded/pricing_rule/achieve/{file_name}"
        file_paths.append(src_file_path)
    elif download_option == "xls import":
        file_name_without_ext = file_name.split(".")[0]
        result_file_record = DME_Files.objects.filter(
            file_name__icontains=file_name_without_ext, file_type="xls import"
        )

        if result_file_record:
            file_paths.append(result_file_record.first().file_path)
    elif download_option == "manifest":
        file_paths.append(f"{settings.STATIC_PUBLIC}/pdfs/{z_manifest_url}")
    elif download_option == "label":
        for booking in bookings:
            if booking.z_label_url and len(booking.z_label_url) > 0:
                file_paths.append(
                    f"{settings.STATIC_PUBLIC}/pdfs/{booking.z_label_url}"
                )
                booking.z_downloaded_shipping_label_timestamp = str(datetime.now())
                booking.save()
    elif download_option == "pod":
        for booking in bookings:
            if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
                file_paths.append(f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_url}")
                booking.z_downloaded_pod_timestamp = timezone.now()
                booking.save()
    elif download_option == "pod_sog":
        for booking in bookings:
            if booking.z_pod_signed_url and len(booking.z_pod_signed_url) > 0:
                file_paths.append(
                    f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_signed_url}"
                )
                booking.z_downloaded_pod_sog_timestamp = timezone.now()
                booking.save()
    elif download_option == "new_pod":
        for booking in bookings:
            if booking.z_downloaded_pod_timestamp is None:
                if booking.z_pod_url and len(booking.z_pod_url) > 0:
                    file_paths.append(
                        f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_url}"
                    )
                    booking.z_downloaded_pod_timestamp = timezone.now()
                    booking.save()
    elif download_option == "new_pod_sog":
        for booking in bookings:
            if booking.z_downloaded_pod_sog_timestamp is None:
                if booking.z_pod_signed_url and len(booking.z_pod_signed_url) > 0:
                    file_paths.append(
                        f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_signed_url}"
                    )
                    booking.z_downloaded_pod_sog_timestamp = timezone.now()
                    booking.save()
    elif download_option == "connote":
        for booking in bookings:
            if booking.z_connote_url and len(booking.z_connote_url) is not 0:
                file_paths.append(
                    f"{settings.STATIC_PRIVATE}/connotes/" + booking.z_connote_url
                )
                booking.z_downloaded_connote_timestamp = timezone.now()
                booking.save()
    elif download_option == "new_connote":
        for booking in bookings:
            if booking.z_downloaded_pod_timestamp is None:
                if booking.z_connote_url and len(booking.z_connote_url) > 0:
                    file_paths.append(
                        f"{settings.STATIC_PRIVATE}/connotes/" + booking.z_connote_url
                    )
                    booking.z_downloaded_connote_timestamp = timezone.now()
                    booking.save()
    elif download_option == "label_and_connote":
        for booking in bookings:
            if booking.z_connote_url and len(booking.z_connote_url) > 0:
                file_paths.append(
                    f"{settings.STATIC_PRIVATE}/connotes/" + booking.z_connote_url
                )
                booking.z_downloaded_connote_timestamp = timezone.now()
                booking.save()
            if booking.z_label_url and len(booking.z_label_url) > 0:
                file_paths.append(
                    f"{settings.STATIC_PUBLIC}/pdfs/{booking.z_label_url}"
                )
                booking.z_downloaded_shipping_label_timestamp = timezone.now()
                booking.save()
    elif download_option == "zpl":
        pdf_url = body.get("url")
        booking_id = body.get("id")
        booking = Bookings.objects.get(pk=booking_id)
        label_url = f"{settings.STATIC_PUBLIC}/pdfs/{pdf_url}"

        # Plum ZPL printer requries portrait label
        if booking.vx_freight_provider.lower() in ["hunter", "tnt"]:
            label_url = rotate_pdf(label_url)

        # Convert label into ZPL format
        logger.info(f"{LOG_ID} - converting LABEL({label_url}) into ZPL format...")
        result = pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

        zpl_url = label_url[:-4] + ".zpl"
        file_paths.append(zpl_url)
    elif download_option == "logs":
        mode = body["mode"]

        if mode == 0:
            file_paths.append(os.path.join(f"{settings.BASE_DIR}/logs", "debug.log"))
        else:
            count = 10 if mode == 1 else 50

            for i in range(count):
                if i == 0:
                    path = f"{settings.BASE_DIR}/logs/debug.log"
                else:
                    path = f"{settings.BASE_DIR}/logs/debug.log.{i}"

                if os.path.exists(path):
                    file_paths.append(path)

    response = download_libs.download_from_disk(download_option, file_paths)
    return response


@api_view(["DELETE"])
@permission_classes((IsAuthenticated,))
def delete_file(request):
    body = literal_eval(request.body.decode("utf8"))
    file_option = body["deleteFileOption"]

    if file_option in ["label", "pod"]:
        try:
            booking_id = body["bookingId"]
            booking = Bookings.objects.get(id=booking_id)
        except Bookings.DoesNotExist as e:
            return JsonResponse(
                {"message": "Booking does not exist", "status": "failure"}, status=400
            )

        if file_option == "label":
            file_name = f"{booking.z_label_url}"
            file_path = f"{settings.STATIC_PUBLIC}/pdfs/{file_name}"
            booking.z_label_url = None
            booking.z_downloaded_shipping_label_timestamp = None
        elif file_option == "pod":
            file_name = f"{booking.z_pod_url}"
            file_path = f"{settings.STATIC_PUBLIC}/imgs/"
            booking.z_pod_url = None
            booking.z_downloaded_pod_timestamp = None

        booking.save()
        delete_lib.delete(file_path)
    elif file_option == "pricing-only":
        file_name = body["fileName"]
        delete_lib.delete(f"./static/uploaded/pricing_only/indata/{file_name}")
        delete_lib.delete(f"./static/uploaded/pricing_only/inprogress/{file_name}")
        delete_lib.delete(f"./static/uploaded/pricing_only/achieve/{file_name}")
        file_name_without_ext = file_name.split(".")[0]
        result_file_record = DME_Files.objects.filter(
            file_name__icontains=file_name_without_ext, file_type="pricing-result"
        )

        if result_file_record:
            delete_lib.delete(result_file_record.first().file_path)

        DME_Files.objects.filter(file_name__icontains=file_name_without_ext).delete()
    elif file_option == "pricing-rule":
        file_name = body["fileName"]
        delete_lib.delete(f"./static/uploaded/pricing_rule/indata/{file_name}")
        delete_lib.delete(f"./static/uploaded/pricing_rule/inprogress/{file_name}")
        delete_lib.delete(f"./static/uploaded/pricing_rule/achieve/{file_name}")
        file_name_without_ext = file_name.split(".")[0]
        DME_Files.objects.filter(file_name__icontains=file_name_without_ext).delete()

    return JsonResponse(
        {
            "filename": file_name,
            "status": "success",
            "message": "Deleted successfully!",
        },
        status=200,
    )


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
@authentication_classes([JSONWebTokenAuthentication])
def get_csv(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body.get("vx_freight_provider", None)
    file_paths = []
    label_names = []

    if not booking_ids:
        return JsonResponse(
            {"success": False, "filename": "", "status": "No bookings to build CSV."},
            status=400,
        )

    bookings = Bookings.objects.filter(pk__in=booking_ids)

    if bookings and not vx_freight_provider:
        vx_freight_provider = bookings.first().vx_freight_provider.lower()

    has_error = build_csv(booking_ids)

    if has_error:
        return JsonResponse(
            {"status": False, "message": "Failed to create CSV"}, status=400
        )
    else:
        for booking in bookings:
            if vx_freight_provider == "cope":
                ############################################################################################
                # This is a comment this is what I did and why to make this happen 05/09/2019 pete walbolt #
                ############################################################################################
                booking.b_dateBookedDate = get_sydney_now_time()
                status_history.create(booking, "Booked", request.user.username)
                booking.v_FPBookingNumber = "DME" + str(booking.b_bookingID_Visual)
                booking.save()

                booking_lines = Booking_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                )
                index = 1

                for booking_line in booking_lines:
                    for i in range(int(booking_line.e_qty)):
                        api_booking_confirmation_line = Api_booking_confirmation_lines(
                            fk_booking_id=booking.pk_booking_id,
                            fk_booking_line_id=booking_line.pk_lines_id,
                            api_item_id=str("COPDME")
                            + str(booking.b_bookingID_Visual)
                            + make_3digit(index),
                            service_provider=booking.vx_freight_provider,
                            label_code=str("COPDME")
                            + str(booking.b_bookingID_Visual)
                            + make_3digit(index),
                            client_item_reference=booking_line.client_item_reference,
                        )
                        api_booking_confirmation_line.save()
                        index = index + 1
            else:  # vx_freight_provider in ["dhl", "state transport", "century"]:
                booking.b_dateBookedDate = get_sydney_now_time(return_type="datetime")
                booking.v_FPBookingNumber = "DME" + str(booking.b_bookingID_Visual)
                status_history.create(booking, "Booked", request.user.username)
                booking.save()

                if vx_freight_provider == "state transport":
                    file_path = f"{S3_URL}/pdfs/{vx_freight_provider}_au/"
                    file_path, file_name = build_label_oper(booking, file_path)
                    booking.z_label_url = f"{vx_freight_provider}_au/{file_name}"
                    booking.save()

                    # Send email when GET_LABEL
                    email_template_name = "General Booking"

                    # if booking.b_booking_Category == "Salvage Expense":
                    #     email_template_name = "Return Booking"

                    send_booking_status_email(
                        booking.pk, email_template_name, request.user.username
                    )

        return JsonResponse(
            {"success": True, "message": "Created CSV successfully"}, status=200
        )


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
@authentication_classes([JSONWebTokenAuthentication])
def get_xml(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body["vx_freight_provider"]

    if len(booking_ids) == 0:
        return JsonResponse({"success": True, "status": "No bookings to build XML"})

    try:
        booked_list = build_xml(booking_ids, vx_freight_provider, 1)

        if len(booked_list) == 0:
            return JsonResponse({"success": "success"})
        else:
            return JsonResponse(
                {"error": "Found set has booked bookings", "booked_list": booked_list}
            )
    except Exception as e:
        return JsonResponse({"error": str(e)})


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
@authentication_classes([JSONWebTokenAuthentication])
def get_manifest(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body["vx_freight_provider"]
    username = body["username"]
    clientname = get_client_name(request)
    need_truck = body.get("needTruck") or False
    is_from_fm = body.get("isFromFM") or False
    timestamp = body.get("timestamp") or None

    bookings = (
        Bookings.objects.filter(pk__in=booking_ids)
        .filter(Q(z_manifest_url__isnull=True) | Q(z_manifest_url__exact=""))
        .only("id", "vx_freight_provider")
    )
    fps = {}

    for booking in bookings:
        if not booking.vx_freight_provider in fps:
            fps[booking.vx_freight_provider] = []

        fps[booking.vx_freight_provider].append(booking.id)

    try:
        file_paths = []

        for fp in fps:
            bookings, filename = build_manifest(
                fps[fp], username, need_truck, timestamp
            )

            if vx_freight_provider.upper() == "TASFR":
                file_path = f"{settings.STATIC_PUBLIC}/pdfs/tas_au/{filename}"
            elif vx_freight_provider.upper() == "DHL":
                file_path = f"{settings.STATIC_PUBLIC}/pdfs/dhl_au/{filename}"
            else:
                file_path = f"{settings.STATIC_PUBLIC}/pdfs/startrack_au/{filename}"

            file_paths.append(file_path)
            for booking in bookings:
                booking.z_manifest_url = f"startrack_au/{filename}"
                booking.manifest_timestamp = timestamp or datetime.now()

                # Jason L & BSD: Create new statusHistory
                if (
                    "bsd" in request.user.username
                    or "jason" in request.user.username
                    or clientname == "dme"
                ) and not booking.b_dateBookedDate:
                    if booking.vx_freight_provider in SPECIAL_FPS:
                        status_history.create(booking, "Booked", username)
                        booking.b_dateBookedDate = timestamp or datetime.now()
                        booking.v_FPBookingNumber = gen_consignment_num(
                            booking.vx_freight_provider, booking.b_bookingID_Visual
                        )

                        # Update status to `In Transit` for DME linehaul
                        if booking.vx_freight_provider == "Deliver-ME":
                            status_history.create(booking, "In Transit", username)
                    else:
                        status_history.create(booking, "Ready for Despatch", username)

                booking.save()

        if is_from_fm:
            return JsonResponse(
                {
                    "success": True,
                    "message": "Manifest is built successfully.",
                    "manifest_url": file_paths[0].replace(
                        settings.STATIC_PUBLIC, settings.S3_URL
                    ),
                }
            )
        else:
            zip_subdir = "manifest_files"
            zip_filename = "%s.zip" % zip_subdir

            s = io.BytesIO()
            zf = zipfile.ZipFile(s, "w")
            for index, file_path in enumerate(file_paths):
                if os.path.isfile(file_path):
                    file_name = file_path.split("/")[-1]
                    file_name = file_name.split("\\")[-1]
                    zf.write(file_path, f"manifest_files/{file_name}")
            zf.close()

            response = HttpResponse(s.getvalue(), "application/x-zip-compressed")
            response["Content-Disposition"] = "attachment; filename=%s" % zip_filename
            return response
    except Exception as e:
        trace_error.print()
        logger.error(f"get_mainifest error: {str(e)}")
        return JsonResponse(
            {"success": False, "message": "Please contact support center."}
        )


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
@authentication_classes([JSONWebTokenAuthentication])
def get_pdf(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body["vx_freight_provider"]

    try:
        results_cnt = build_pdf(booking_ids, vx_freight_provider)

        if results_cnt > 0:
            return JsonResponse({"success": "success"})
        else:
            return JsonResponse({"error": "No one has been generated"})
    except Exception as e:
        # print('get_pdf error: ', e)
        return JsonResponse({"error": "error"})


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
@authentication_classes([JSONWebTokenAuthentication])
def build_label(request):
    LOG_ID = "[DME LABEL BUILD]"

    body = literal_eval(request.body.decode("utf8"))
    booking_id = body["booking_id"]
    logger.info(f"{LOG_ID} Booking pk: {booking_id}")
    booking = Bookings.objects.get(pk=booking_id)
    lines = booking.lines().filter(is_deleted=False)

    # Reset all Api_booking_confirmation_lines
    Api_booking_confirmation_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id
    ).delete()

    for line in lines:
        if line.sscc and "NOSSCC_" in line.sscc:
            line.sscc = None
            line.save()

    scanned_lines = []
    for line in lines:
        if line.packed_status == "scanned":
            scanned_lines.append(line)

    original_lines = []
    for line in lines:
        if line.packed_status == "original":
            original_lines.append(line)

    if booking.api_booking_quote:
        selected_lines = []

        for line in lines:
            if line.packed_status == booking.api_booking_quote.packed_status:
                selected_lines.append(line)

        lines = selected_lines
    else:
        if scanned_lines:
            lines = scanned_lines
        else:
            lines = original_lines

    # Populate SSCC if doesn't exist
    for line in lines:
        if not line.sscc:
            line.sscc = f"NOSSCC_{booking.b_bookingID_Visual}_{line.pk}"
            line.save()

    label_urls = []
    sscc_list = []
    sscc_lines = {}
    total_qty = 0
    for line in lines:
        if line.sscc not in sscc_list:
            sscc_list.append(line.sscc)
            total_qty += line.e_qty
            _lines = []

            for line1 in lines:
                if line1.sscc == line.sscc:
                    _lines.append(line1)

            sscc_lines[line.sscc] = _lines
    logger.info(f"{LOG_ID} \nsscc_list:{sscc_list}\nsscc_lines: {sscc_lines}")

    try:
        # Build label with SSCC - one sscc should have one page label
        file_path = (
            f"{settings.STATIC_PUBLIC}/pdfs/{booking.vx_freight_provider.lower()}_au"
        )

        label_index = 0
        for sscc in sscc_list:
            logger.info(f"@368 - building label with SSCC...")
            file_path, file_name = build_label_oper(
                booking=booking,
                file_path=file_path,
                lines=sscc_lines[sscc],
                label_index=label_index,
                sscc=sscc,
                sscc_cnt=total_qty,
                one_page_label=False,
            )
            label_urls.append(f"{file_path}/{file_name}")

            for _line in sscc_lines[sscc]:
                label_index += _line.e_qty

        if label_urls:
            entire_label_url = f"{file_path}/DME{booking.b_bookingID_Visual}.pdf"
            pdf_merge(label_urls, entire_label_url)

        message = f"#379 {LOG_ID} - Successfully build label. Booking Id: {booking.b_bookingID_Visual}"
        logger.info(message)

        if not booking.b_client_booking_ref_num:
            booking.b_client_booking_ref_num = (
                f"{booking.b_bookingID_Visual}_{str(uuid.uuid4())}"
            )

        booking.z_label_url = (
            f"{settings.WEB_SITE_URL}/label/{booking.b_client_booking_ref_num}/"
        )
        booking.z_downloaded_shipping_label_timestamp = datetime.utcnow()

        # Jason L
        if not booking.b_dateBookedDate and booking.b_status != "Picked":
            status_history.create(booking, "Picked", request.user.username)

        booking.save()
    except Exception as e:
        trace_error.print()
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"success": "failure", "message": "Label operation get failed!"}
        )

    return JsonResponse(
        {"success": "success", "message": "Label is successfully built!"}
    )


@api_view(["GET"])
@permission_classes((IsAuthenticated,))
@authentication_classes([JSONWebTokenAuthentication])
def getAttachmentsHistory(request):
    fk_booking_id = request.GET.get("fk_booking_id")
    return_data = []

    try:
        resultObjects = []
        resultObjects = Dme_attachments.objects.filter(fk_id_dme_booking=fk_booking_id)
        for resultObject in resultObjects:
            # print('@bookingID', resultObject.fk_id_dme_booking.id)
            return_data.append(
                {
                    "pk_id_attachment": resultObject.pk_id_attachment,
                    "fk_id_dme_client": resultObject.fk_id_dme_client.pk_id_dme_client,
                    "fk_id_dme_booking": resultObject.fk_id_dme_booking,
                    "fileName": resultObject.fileName,
                    "linkurl": resultObject.linkurl,
                    "upload_Date": resultObject.upload_Date,
                }
            )
        return JsonResponse({"history": return_data})
    except Exception as e:
        # print('@Exception', e)
        return JsonResponse({"history": ""})


@api_view(["GET"])
@authentication_classes([JSONWebTokenAuthentication])
@permission_classes([IsAuthenticated])
def getSuburbs(request):
    requestType = request.GET.get("type")
    return_data = []

    try:
        resultObjects = []
        if requestType == "state":
            resultObjects = Utl_suburbs.objects.all()
            for resultObject in resultObjects:
                if len(return_data) > 0:
                    temp = {
                        "value": resultObject.state.lower(),
                        "label": resultObject.state,
                    }
                    try:
                        if return_data.index(temp) is None:
                            return_data.append(
                                {
                                    "value": resultObject.state.lower(),
                                    "label": resultObject.state,
                                }
                            )
                    except:
                        return_data.append(
                            {
                                "value": resultObject.state.lower(),
                                "label": resultObject.state,
                            }
                        )
                else:
                    return_data.append(
                        {
                            "value": resultObject.state.lower(),
                            "label": resultObject.state,
                        }
                    )
        elif requestType == "postalcode":
            stateName = request.GET.get("name")
            resultObjects = Utl_suburbs.objects.filter(state=stateName)

            for resultObject in resultObjects:
                if len(return_data) > 0:
                    temp = {
                        "value": resultObject.postal_code,
                        "label": resultObject.postal_code,
                    }
                    try:
                        if return_data.index(temp) is None:
                            return_data.append(
                                {
                                    "value": resultObject.postal_code,
                                    "label": resultObject.postal_code,
                                }
                            )
                    except:
                        return_data.append(
                            {
                                "value": resultObject.postal_code,
                                "label": resultObject.postal_code,
                            }
                        )
                else:
                    return_data.append(
                        {
                            "value": resultObject.postal_code,
                            "label": resultObject.postal_code,
                        }
                    )
        elif requestType == "suburb":
            postalCode = request.GET.get("name")
            resultObjects = Utl_suburbs.objects.filter(postal_code=postalCode)

            for resultObject in resultObjects:
                if len(return_data) > 0:
                    temp = {"value": resultObject.suburb, "label": resultObject.suburb}
                    try:
                        if return_data.index(temp) is None:
                            return_data.append(
                                {
                                    "value": resultObject.suburb,
                                    "label": resultObject.suburb,
                                }
                            )
                    except:
                        return_data.append(
                            {"value": resultObject.suburb, "label": resultObject.suburb}
                        )
                else:
                    return_data.append(
                        {"value": resultObject.suburb, "label": resultObject.suburb}
                    )
        return JsonResponse({"type": requestType, "suburbs": return_data})
    except Exception as e:
        return JsonResponse({"type": requestType, "suburbs": ""})


class SqlQueriesViewSet(viewsets.ViewSet):
    serializer_class = SqlQueriesSerializer
    queryset = Utl_sql_queries.objects.all()

    def list(self, request, pk=None):
        queryset = Utl_sql_queries.objects.all()
        serializer = SqlQueriesSerializer(queryset, many=True)
        return JsonResponse(
            {
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def get(self, request, pk, format=None):
        return_data = []
        try:
            resultObject = Utl_sql_queries.objects.get(id=pk)
            return JsonResponse({"result": SqlQueriesSerializer(resultObject).data})
        except Exception as e:
            # print("@Exception", e)
            return JsonResponse({"message": e}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        serializer = SqlQueriesSerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print("Exception: ", e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["put"])
    def edit(self, request, pk, format=None):
        data = Utl_sql_queries.objects.get(pk=pk)
        serializer = SqlQueriesSerializer(data, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print("Exception: ", e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete(self, request, pk=None):
        result = Utl_sql_queries.objects.get(pk=pk)
        result.delete()
        return Response(SqlQueriesSerializer(result).data)

    @action(detail=False, methods=["post"])
    def execute(self, request, pk=None):
        return_data = []
        query_tables = tables_in_query(request.data["sql_query"])
        serializer = SqlQueriesSerializer(data=request.data)

        if serializer.is_valid():
            with connection.cursor() as cursor:
                try:
                    cursor.execute(request.data["sql_query"])
                    columns = cursor.description
                    row = cursor.fetchall()
                    cursor.execute(
                        "SHOW KEYS FROM "
                        + query_tables[0]
                        + " WHERE Key_name = 'PRIMARY'"
                    )
                    row1 = cursor.fetchone()
                    result = []

                    for value in row:
                        tmp = {}

                        for (index, column) in enumerate(value):
                            tmp[columns[index][0]] = column
                        result.append(tmp)

                    return JsonResponse({"results": result, "tables": row1})
                except Exception as e:
                    # print("@Exception", e)
                    return JsonResponse({"message": str(e)}, status=400)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def update_query(self, request, pk=None):
        return_data = []
        if re.search("update", request.data["sql_query"], flags=re.IGNORECASE):
            with connection.cursor() as cursor:
                try:
                    cursor.execute(request.data["sql_query"])
                    columns = cursor.description
                    row = cursor.fetchall()
                    result = []
                    for value in row:
                        tmp = {}
                        for (index, column) in enumerate(value):
                            tmp[columns[index][0]] = column
                        result.append(tmp)
                    return JsonResponse({"results": result})
                except Exception as e:
                    # print('@Exception', e)
                    return JsonResponse({"error": str(e)})
        else:
            return JsonResponse({"error": "Sorry only UPDATE statement allowed"})


class FileUploadView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, format=None):
        user_id = request.user.id
        username = request.user.username
        file = request.FILES["file"]
        upload_option = request.POST.get("uploadOption", None)
        client_id = request.POST.get("clientId", None)
        result = None

        if upload_option == "import":
            uploader = request.POST["uploader"]
            file_name = upload_lib.upload_import_file(user_id, file, uploader)
            result = file_name
        elif upload_option in ["pod", "label", "attachment"]:
            booking_id = request.POST.get("bookingId", None)
            file_name = upload_lib.upload_attachment_file(
                user_id, file, booking_id, upload_option
            )
            result = file_name
        elif upload_option == "pricing-only":
            file_name = upload_lib.upload_pricing_only_file(
                user_id, username, file, upload_option
            )
            result = file_name
        elif upload_option == "pricing-rule":
            rule_type = request.POST.get("ruleType", None)
            file_name = upload_lib.upload_pricing_rule_file(
                user_id, username, file, upload_option, rule_type
            )
            result = file_name
        elif upload_option == "client-products":
            import_results = upload_lib.upload_client_products_file(
                user_id, username, client_id, file
            )
            result = import_results

        return Response(result)


@permission_classes((IsAuthenticated,))
class FilesViewSet(viewsets.ViewSet):
    def list(self, request):
        file_type = request.GET["fileType"]
        dme_files = DME_Files.objects.filter(file_type=file_type)
        dme_files = dme_files.order_by("-z_createdTimeStamp")[:50]
        json_results = FilesSerializer(dme_files, many=True).data
        pk_booking_ids = []

        for json_data in json_results:
            pk_booking_ids += json_data["note"].split(", ")

        bookings = Bookings.objects.filter(pk_booking_id__in=pk_booking_ids)

        for index, json_data in enumerate(json_results):
            b_bookingID_Visuals = []
            booking_ids = []

            for booking in bookings:
                if booking.pk_booking_id in json_data["note"]:
                    b_bookingID_Visuals.append(str(booking.b_bookingID_Visual))
                    booking_ids.append(str(booking.pk))

            json_results[index]["b_bookingID_Visual"] = ", ".join(b_bookingID_Visuals)
            json_results[index]["booking_id"] = ", ".join(booking_ids)

        return Response(json_results)

    def create(self, request):
        serializer = FilesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VehiclesViewSet(viewsets.ViewSet):
    serializer_class = VehiclesSerializer

    def list(self, request, pk=None):
        queryset = FP_vehicles.objects.all()
        serializer = VehiclesSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        try:
            request.data.pop("id", None)
            resultObject = FP_vehicles.objects.get_or_create(**request.data)

            return JsonResponse(
                {
                    "result": VehiclesSerializer(resultObject[0]).data,
                    "isCreated": resultObject[1],
                },
                status=200,
            )
        except Exception as e:
            trace_error.print()
            logger.error(f"Vehicle Add error: {str(e)}")
            return JsonResponse({"result": None}, status=400)


class AvailabilitiesViewSet(viewsets.ViewSet):
    serializer_class = AvailabilitiesSerializer

    def list(self, request, pk=None):
        queryset = FP_availabilities.objects.all()
        serializer = AvailabilitiesSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        try:
            request.data.pop("id", None)
            logger.info(f"Availability Create payload: {request.data}")
            resultObject = FP_availabilities.objects.get_or_create(**request.data)

            return JsonResponse(
                {
                    "result": AvailabilitiesSerializer(resultObject[0]).data,
                    "isCreated": resultObject[1],
                },
                status=200,
            )
        except Exception as e:
            logger.error(f"Availabilities Add error: {str(e)}")
            return JsonResponse({"result": None}, status=400)


class FPCostsViewSet(viewsets.ModelViewSet):
    queryset = FP_costs.objects.all()
    serializer_class = FPCostsSerializer

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        try:
            request.data.pop("id", None)
            resultObject = FP_costs.objects.get_or_create(**request.data)

            return JsonResponse(
                {
                    "result": FPCostsSerializer(resultObject[0]).data,
                    "isCreated": resultObject[1],
                },
                status=200,
            )
        except Exception as e:
            logger.error(f"[FP_COST ADD] {str(e)}")
            return JsonResponse({"result": None}, status=400)


class PricingRulesViewSet(viewsets.ViewSet):
    serializer_class = PricingRulesSerializer

    def list(self, request, pk=None):
        queryset = FP_pricing_rules.objects.all()
        serializer = PricingRulesSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        try:
            request.data.pop("id", None)
            resultObject = FP_pricing_rules.objects.get_or_create(**request.data)

            return JsonResponse(
                {
                    "result": PricingRulesSerializer(resultObject[0]).data,
                    "isCreated": resultObject[1],
                },
                status=200,
            )
        except Exception as e:
            logger.error(f"[FP_RULE ADD] {str(e)}, payload: {request.data}")
            return JsonResponse({"result": None}, status=400)


class BookingSetsViewSet(viewsets.ModelViewSet):
    queryset = BookingSets.objects.all()
    serializer_class = BookingSetsSerializer

    def list(self, request, pk=None):
        # TODO: should implement pagination here as well
        MAX_SETS_COUNT = 25
        queryset = BookingSets.objects.all()

        if get_clientname(request) != "dme":
            queryset = queryset.filter(z_createdByAccount=get_clientname(request))

        queryset = queryset.order_by("-id")[:MAX_SETS_COUNT]
        serializer = BookingSetsSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, pk=None):
        bookingIds = []

        for bookingId in request.data["bookingIds"]:
            bookingIds.append(str(bookingId))

        request.data["booking_ids"] = ", ".join(bookingIds)
        request.data["status"] = "Created"
        request.data["z_createdByAccount"] = get_clientname(request)
        request.data["z_createdTimeStamp"] = str(datetime.now())

        # prevent empty string
        if not request.data["line_haul_date"]:
            request.data["line_haul_date"] = None

        serializer = BookingSetsSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientEmployeesViewSet(viewsets.ModelViewSet):
    serializer_class = ClientEmployeesSerializer

    def get_queryset(self):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee:
            client_employees = Client_employees.objects.filter(email__isnull=False)
        else:
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()
            client_employees = Client_employees.objects.filter(
                fk_id_dme_client_id=client.pk_id_dme_client, email__isnull=False
            )

        return client_employees.order_by("name_first")


class ClientProductsViewSet(viewsets.ModelViewSet):
    serializer_class = ClientProductsSerializer
    queryset = Client_Products.objects.all()

    def get_client_id(self):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()

        if dme_employee:
            client = self.request.query_params.get("clientId")
        else:
            client_employee = Client_employees.objects.filter(
                fk_id_user=user_id
            ).first()
            client = DME_clients.objects.filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            ).first()

        return client

    def list(self, request, *args, **kwargs):
        client = self.get_client_id()
        client_products = Client_Products.objects.filter(
            fk_id_dme_client=client
        ).order_by("id")
        serializer = ClientProductsSerializer(client_products, many=True)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        id = self.kwargs["pk"]
        try:
            Client_Products.objects.filter(id=id).delete()
        except Exception as e:
            return Response({"msg": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({id})


class ClientRasViewSet(viewsets.ModelViewSet):
    serializer_class = ClientRasSerializer
    queryset = Client_Ras.objects.all()


class ErrorViewSet(viewsets.ModelViewSet):
    serializer_class = ErrorSerializer
    queryset = DME_Error.objects.all()

    def list(self, request, pk=None):
        pk_booking_id = request.GET["pk_booking_id"]

        if pk_booking_id:
            queryset = DME_Error.objects.filter(fk_booking_id=pk_booking_id)
        else:
            queryset = DME_Error.objects.all()

        serializer = ErrorSerializer(queryset, many=True)
        return Response(serializer.data)


class ClientProcessViewSet(viewsets.ModelViewSet):
    serializer_class = ClientProcessSerializer

    def get_queryset(self):
        booking_id = self.request.GET["bookingId"]

        if booking_id:
            queryset = Client_Process_Mgr.objects.filter(fk_booking_id=booking_id)
        else:
            queryset = Client_Process_Mgr.objects.all()

        return queryset.order_by("id")


class AugmentAddressViewSet(viewsets.ModelViewSet):
    serializer_class = AugmentAddressSerializer
    queryset = DME_Augment_Address.objects.all()


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    queryset = DME_clients.objects.all()


class RoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    queryset = DME_Roles.objects.all()


@permission_classes((IsAuthenticated,))
class SurchargeViewSet(viewsets.ModelViewSet):
    serializer_class = SurchargeSerializer

    def get_queryset(self):
        booking_id = self.request.GET.get("bookingId")
        queryset = Surcharge.objects.all()

        if booking_id:
            queryset = queryset.filter(booking_id=booking_id)

        return queryset.order_by("id")


@permission_classes((IsAuthenticated,))
class ChartsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_num_bookings_per_fp(self, request):
        try:
            startDate = request.GET.get("startDate")
            endDate = request.GET.get("endDate")

            result = (
                Bookings.objects.filter(
                    Q(b_status="Delivered")
                    & Q(b_dateBookedDate__range=[startDate, endDate])
                )
                .extra(select={"freight_provider": "vx_freight_provider"})
                .values("freight_provider")
                .annotate(deliveries=Count("vx_freight_provider"))
                .order_by("deliveries")
            )

            late_result = (
                Bookings.objects.filter(
                    Q(b_status="Delivered")
                    & Q(b_dateBookedDate__range=[startDate, endDate])
                    & Q(
                        s_21_Actual_Delivery_TimeStamp__gt=F(
                            "s_06_Latest_Delivery_Date_TimeSet"
                        )
                    )
                )
                .extra(select={"freight_provider": "vx_freight_provider"})
                .values("freight_provider")
                .annotate(late_deliveries=Count("vx_freight_provider"))
                .order_by("late_deliveries")
            )

            ontime_result = (
                Bookings.objects.filter(
                    Q(b_status="Delivered")
                    & Q(b_dateBookedDate__range=[startDate, endDate])
                    & Q(
                        s_21_Actual_Delivery_TimeStamp__lte=F(
                            "s_06_Latest_Delivery_Date_TimeSet"
                        )
                    )
                )
                .extra(select={"freight_provider": "vx_freight_provider"})
                .values("freight_provider")
                .annotate(ontime_deliveries=Count("vx_freight_provider"))
                .order_by("ontime_deliveries")
            )

            num_reports = list(result)
            num_late_reports = list(late_result)
            num_ontime_reports = list(ontime_result)

            for report in num_reports:
                for late_report in num_late_reports:
                    if report["freight_provider"] == late_report["freight_provider"]:
                        report["late_deliveries"] = late_report["late_deliveries"]
                        report["late_deliveries_percentage"] = math.ceil(
                            late_report["late_deliveries"] / report["deliveries"] * 100
                        )

                for ontime_report in num_ontime_reports:
                    if report["freight_provider"] == ontime_report["freight_provider"]:
                        report["ontime_deliveries"] = ontime_report["ontime_deliveries"]
                        report["ontime_deliveries_percentage"] = math.ceil(
                            ontime_report["ontime_deliveries"]
                            / report["deliveries"]
                            * 100
                        )

            return JsonResponse({"results": num_reports})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_bookings_per_status(self, request):
        try:
            startDate = request.GET.get("startDate")
            endDate = request.GET.get("endDate")
            category_result = (
                Bookings.objects.filter(Q(b_dateBookedDate__range=[startDate, endDate]))
                .extra(select={"status": "b_status"})
                .values("status")
                .annotate(value=Count("b_status"))
                .order_by("value")
            )

            categories = []
            category_reports = list(category_result)

            for category_report in category_reports:
                if (
                    category_report["status"] is not None
                    and category_report["status"] != ""
                ):
                    utl_dme_status = Utl_dme_status.objects.filter(
                        dme_delivery_status=category_report["status"]
                    ).first()

                    if utl_dme_status:
                        category_report["status"] = (
                            utl_dme_status.dme_delivery_status_category
                            + "("
                            + category_report["status"]
                            + ")"
                        )
                        categories.append(category_report)

            return JsonResponse({"results": categories})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_bookings_per_client(self, request):
        try:
            startDate = request.GET.get("startDate")
            endDate = request.GET.get("endDate")

            result = (
                Bookings.objects.filter(Q(b_dateBookedDate__range=[startDate, endDate]))
                .extra(select={"client_name": "b_client_name"})
                .values("client_name")
                .annotate(deliveries=Count("b_client_name"))
                .order_by("deliveries")
            )

            late_result = (
                Bookings.objects.filter(
                    Q(b_dateBookedDate__range=[startDate, endDate])
                    & Q(
                        s_21_Actual_Delivery_TimeStamp__gt=F(
                            "s_06_Latest_Delivery_Date_TimeSet"
                        )
                    )
                )
                .extra(select={"client_name": "b_client_name"})
                .values("client_name")
                .annotate(late_deliveries=Count("b_client_name"))
                .order_by("late_deliveries")
            )

            ontime_result = (
                Bookings.objects.filter(
                    Q(b_dateBookedDate__range=[startDate, endDate])
                    & Q(
                        s_21_Actual_Delivery_TimeStamp__lte=F(
                            "s_06_Latest_Delivery_Date_TimeSet"
                        )
                    )
                )
                .extra(select={"client_name": "b_client_name"})
                .values("client_name")
                .annotate(ontime_deliveries=Count("b_client_name"))
                .order_by("ontime_deliveries")
            )

            inv_sell_quoted_result = (
                Bookings.objects.filter(Q(b_dateBookedDate__range=[startDate, endDate]))
                .extra(select={"client_name": "b_client_name"})
                .values("client_name")
                .annotate(inv_sell_quoted=Sum("inv_sell_quoted"))
                .order_by("inv_sell_quoted")
            )

            inv_sell_quoted_override_result = (
                Bookings.objects.filter(Q(b_dateBookedDate__range=[startDate, endDate]))
                .extra(select={"client_name": "b_client_name"})
                .values("client_name")
                .annotate(inv_sell_quoted_override=Sum("inv_sell_quoted_override"))
                .order_by("inv_sell_quoted_override")
            )

            inv_cost_quoted_result = (
                Bookings.objects.filter(Q(b_dateBookedDate__range=[startDate, endDate]))
                .extra(select={"client_name": "b_client_name"})
                .values("client_name")
                .annotate(inv_cost_quoted=Sum("inv_cost_quoted"))
                .order_by("inv_cost_quoted")
            )

            deliveries_reports = list(result)
            inv_sell_quoted_reports = list(inv_sell_quoted_result)
            inv_sell_quoted_override_reports = list(inv_sell_quoted_override_result)
            inv_cost_quoted_reports = list(inv_cost_quoted_result)
            late_reports = list(late_result)
            ontime_reports = list(ontime_result)

            for report in deliveries_reports:
                for late_report in late_reports:
                    if report["client_name"] == late_report["client_name"]:
                        report["late_deliveries"] = late_report["late_deliveries"]

                for ontime_report in ontime_reports:
                    if report["client_name"] == ontime_report["client_name"]:
                        report["ontime_deliveries"] = ontime_report["ontime_deliveries"]

                for inv_sell_quoted_report in inv_sell_quoted_reports:
                    if report["client_name"] == inv_sell_quoted_report["client_name"]:
                        report["inv_sell_quoted"] = (
                            0
                            if not inv_sell_quoted_report["inv_sell_quoted"]
                            else round(
                                float(inv_sell_quoted_report["inv_sell_quoted"]), 2
                            )
                        )

                for inv_sell_quoted_override_report in inv_sell_quoted_override_reports:
                    if (
                        report["client_name"]
                        == inv_sell_quoted_override_report["client_name"]
                    ):
                        report["inv_sell_quoted_override"] = (
                            0
                            if not inv_sell_quoted_override_report[
                                "inv_sell_quoted_override"
                            ]
                            else round(
                                float(
                                    inv_sell_quoted_override_report[
                                        "inv_sell_quoted_override"
                                    ]
                                ),
                                2,
                            )
                        )

                for inv_cost_quoted_report in inv_cost_quoted_reports:
                    if report["client_name"] == inv_cost_quoted_report["client_name"]:
                        report["inv_cost_quoted"] = (
                            0
                            if not inv_cost_quoted_report["inv_cost_quoted"]
                            else round(
                                float(inv_cost_quoted_report["inv_cost_quoted"]), 2
                            )
                        )

            return JsonResponse({"results": deliveries_reports})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_ready_bookings_per_fp(self, request):
        try:
            result = (
                Bookings.objects.filter(b_status="Ready for booking")
                .values("vx_freight_provider")
                .annotate(vx_freight_provider_count=Count("vx_freight_provider"))
                .order_by("vx_freight_provider_count")
            )
            return JsonResponse({"results": list(result)})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_booked_bookings_per_fp(self, request):
        try:
            result = (
                Bookings.objects.filter(b_status="Booked")
                .values("vx_freight_provider")
                .annotate(vx_freight_provider_count=Count("vx_freight_provider"))
                .order_by("vx_freight_provider_count")
            )
            return JsonResponse({"results": list(result)})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_rebooked_bookings_per_fp(self, request):
        try:
            result = (
                Bookings.objects.filter(b_status="Pickup Rebooked")
                .values("vx_freight_provider")
                .annotate(vx_freight_provider_count=Count("vx_freight_provider"))
                .order_by("vx_freight_provider_count")
            )
            return JsonResponse({"results": list(result)})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_closed_bookings_per_fp(self, request):
        try:
            result = (
                Bookings.objects.filter(b_status="Closed")
                .values("vx_freight_provider")
                .annotate(vx_freight_provider_count=Count("vx_freight_provider"))
                .order_by("vx_freight_provider_count")
            )
            return JsonResponse({"results": list(result)})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_month_bookings(self, request):
        try:
            result = (
                Bookings.objects.filter(b_status="Delivered")
                .extra(select={"month": "EXTRACT(month FROM b_dateBookedDate)"})
                .values("month")
                .annotate(count_items=Count("b_dateBookedDate"))
            )

            return JsonResponse({"results": list(result)})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_year_bookings(self, request):
        try:
            result = (
                Bookings.objects.filter(b_status="Delivered")
                .extra(select={"year": "EXTRACT(year FROM b_dateBookedDate)"})
                .values("year")
                .annotate(count_items=Count("b_dateBookedDate"))
            )

            return JsonResponse({"results": list(result)})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})

    @action(detail=False, methods=["get"])
    def get_num_active_bookings_per_client(self, request):
        try:
            result = (
                Bookings.objects.filter(
                    b_client_name__in=[
                        "Tempo Pty Ltd",
                        "Reworx",
                        "Plum Products Australia Ltd",
                        "Cinnamon Creations",
                        "Jason L",
                        "Bathroom Sales Direct",
                    ],
                    b_dateBookedDate__isnull=False,
                )
                .exclude(
                    b_status__in=[
                        "Closed",
                        "Cancelled",
                        "Ready for booking",
                        "Delivered",
                        "To Quote",
                        "Picking",
                        "Picked",
                        "On Hold",
                    ]
                )
                .extra(select={"b_client": "b_client_name"})
                .values("b_client")
                .annotate(inprogress=Count("b_client_name"))
                .order_by("inprogress")
            )
            num_reports = list(result)
            return JsonResponse({"results": num_reports})
        except Exception as e:
            # print(f"Error #102: {e}")
            return JsonResponse({"results": [], "success": False, "message": str(e)})


class PalletViewSet(NoUpdateMixin, NoDestroyMixin, viewsets.ModelViewSet):
    queryset = Pallet.objects.all()
    serializer_class = PalletSerializer
    permission_classes = (AllowAny,)


class FpStatusesViewSet(viewsets.ViewSet):
    serializer_class = FpStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    @authentication_classes([JSONWebTokenAuthentication])
    def get_fp_statuses(self, request, pk=None):
        try:
            fp_name = request.GET.get("fp_name")
            queryset = Dme_utl_fp_statuses.objects.filter(fp_name=fp_name)
            serializer = FpStatusSerializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.info(f"Get Fp Statuses Error: {str(e)}")

    def create(self, request):
        serializer = FpStatusSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.info(f"Create Fp Status Error: {str(e)}")
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        fp_status = Dme_utl_fp_statuses.objects.get(pk=pk)
        serializer = FpStatusSerializer(fp_status, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            logger.info(f"Create Fp Status Error: {str(e)}")
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        fp_status = Dme_utl_fp_statuses.objects.get(pk=pk)
        try:
            fp_status.delete()
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f"Delete Fp Status Error: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)


class DMEBookingCSNoteViewSet(viewsets.ModelViewSet):
    queryset = DMEBookingCSNote.objects.all().order_by("z_createdTimeStamp")
    serializer_class = DMEBookingCSNoteSerializer

    def list(self, request):
        booking_id = request.GET.get("bookingId")

        if booking_id:
            queryset = DMEBookingCSNote.objects.filter(booking_id=booking_id)
        else:
            queryset = DMEBookingCSNote.objects.all()

        serializer = DMEBookingCSNoteSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        dme_employee = DME_employees.objects.get(fk_id_user_id=request.user.pk)
        request.data[
            "z_createdByAccount"
        ] = f"{dme_employee.name_first} {dme_employee.name_last}"
        serializer = DMEBookingCSNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.info(f"Create CS Note Error: {str(serializer.errors)}")
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            cs_note = DMEBookingCSNote.objects.get(pk=pk)
            serializer = DMEBookingCSNoteSerializer(cs_note)
            res_json = serializer.data
            cs_note.delete()
            return Response(res_json, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f"Delete Fp Status Error: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
