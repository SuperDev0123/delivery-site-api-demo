import pytz
import os
import json
import uuid
import time
import logging
import operator
import requests
import tempfile
import re
from wsgiref.util import FileWrapper
from datetime import datetime, date, timedelta
from time import gmtime, strftime
from ast import literal_eval
from functools import reduce
from pydash import _

from django.shortcuts import render
from django.core import serializers, files
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, views, status, authentication, permissions
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    action,
)
from rest_framework.parsers import MultiPartParser
from django.http import HttpResponse, JsonResponse, QueryDict
from django.db.models import Q, Case, When
from django.db import connection
from django.utils import timezone
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse

from django_rest_passwordreset.signals import (
    reset_password_token_created,
    post_password_reset,
    pre_password_reset,
)

from .serializers import *
from .models import *
from .utils import (
    _generate_csv,
    build_xml,
    build_pdf,
    build_xls_and_send,
    make_3digit,
    build_manifest,
    get_sydney_now_time,
    get_client_name,
    calc_collect_after_status_change,
    send_email,
    tables_in_query,
)
from api.outputs import tempo, emails as email_module
from api.common import status_history
from api.file_operations import (
    uploads as upload_lib,
    delete as delete_lib,
    downloads as download_libs,
)

logger = logging.getLogger("dme_api")


@receiver(reset_password_token_created)
def password_reset_token_created(
    sender, instance, reset_password_token, *args, **kwargs
):
    url = f"http://{settings.WEB_SITE_IP}"
    context = {
        "current_user": reset_password_token.user,
        "username": reset_password_token.user.username,
        "email": reset_password_token.user.email,
        "reset_password_url": f"{url}/reset-password?token=" + reset_password_token.key,
    }

    try:
        filepath = settings.EMAIL_ROOT + "/user_reset_password.html"
    except MultiValueDictKeyError:
        logger.error("Error #101: Either the file is missing or not readable")

    email_html_message = render_to_string(
        settings.EMAIL_ROOT + "/user_reset_password.html", context
    )

    subject = f"Reset Your Password"
    mime_type = "html"
    try:
        send_email([context["email"]], subject, email_html_message, None, mime_type)
    except Exception as e:
        logger.error(f"Error #102: {e}")


class UserViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def username(self, request, format=None):
        user_id = self.request.user.id
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )
        if dme_employee is not None:
            return JsonResponse(
                {"username": request.user.username, "clientname": "dme"}
            )
        else:
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client = DME_clients.objects.get(
                pk_id_dme_client=client_employee.fk_id_dme_client_id
            )
            return JsonResponse(
                {
                    "username": request.user.username,
                    "clientname": client.company_name,
                    "clientId": client.dme_account_num,
                }
            )

    @action(detail=False, methods=["get"])
    def get_clients(self, request, format=None):
        user_id = self.request.user.id
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is not None:
            user_type = "DME"
            dme_clients = DME_clients.objects.all()
        else:
            user_type = "CLIENT"
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client_employee_role = client_employee.get_role()
            dme_clients = DME_clients.objects.select_related().filter(
                pk_id_dme_client=int(client_employee.fk_id_dme_client_id)
            )

        if len(dme_clients) is 0:
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
                    }
                ]

            for client in dme_clients:
                return_data.append(
                    {
                        "pk_id_dme_client": client.pk_id_dme_client,
                        "company_name": client.company_name,
                        "dme_account_num": client.dme_account_num,
                        "current_freight_provider": client.current_freight_provider,
                    }
                )

            return JsonResponse({"dme_clients": return_data})

    @action(detail=False, methods=["get"])
    def get_user_date_filter_field(self, request, pk=None):
        user_id = self.request.user.id
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is not None:
            return JsonResponse({"user_date_filter_field": "z_CreatedTimestamp"})
        else:
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
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
            # print('@Exception', e)
            return JsonResponse({"results": ""})

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
            print("@Exception", e)
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


class BookingsViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer

    def _column_filter_4_get_bookings(self, queryset, column_filters):
        # Column filter
        try:
            column_filter = column_filters["b_bookingID_Visual"]
            queryset = queryset.filter(b_bookingID_Visual__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["b_dateBookedDate"]
            queryset = queryset.filter(b_dateBookedDate__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["puPickUpAvailFrom_Date"]
            queryset = queryset.filter(puPickUpAvailFrom_Date__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["puCompany"]
            queryset = queryset.filter(puCompany__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["pu_Address_Suburb"]
            queryset = queryset.filter(pu_Address_Suburb__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["pu_Address_State"]
            queryset = queryset.filter(pu_Address_State__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["pu_Address_PostalCode"]
            queryset = queryset.filter(pu_Address_PostalCode__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["deToCompanyName"]
            queryset = queryset.filter(deToCompanyName__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["de_To_Address_Suburb"]
            queryset = queryset.filter(de_To_Address_Suburb__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["de_To_Address_State"]
            queryset = queryset.filter(de_To_Address_State__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["de_To_Address_PostalCode"]
            queryset = queryset.filter(
                de_To_Address_PostalCode__icontains=column_filter
            )
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["b_clientReference_RA_Numbers"]
            queryset = queryset.filter(
                b_clientReference_RA_Numbers__icontains=column_filter
            )
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["vx_freight_provider"]
            queryset = queryset.filter(vx_freight_provider__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["vx_serviceName"]
            queryset = queryset.filter(vx_serviceName__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["v_FPBookingNumber"]
            queryset = queryset.filter(v_FPBookingNumber__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["b_status"]
            queryset = queryset.filter(b_status__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["b_status_API"]
            queryset = queryset.filter(b_status_API__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["s_05_LatestPickUpDateTimeFinal"]
            queryset = queryset.filter(
                s_05_LatestPickUpDateTimeFinal__icontains=column_filter
            )
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["s_06_LatestDeliveryDateTimeFinal"]
            queryset = queryset.filter(
                s_06_LatestDeliveryDateTimeFinal__icontains=column_filter
            )
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["s_20_Actual_Pickup_TimeStamp"]
            queryset = queryset.filter(
                s_20_Actual_Pickup_TimeStamp__icontains=column_filter
            )
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["s_21_Actual_Delivery_TimeStamp"]
            queryset = queryset.filter(
                s_21_Actual_Delivery_TimeStamp__icontains=column_filter
            )
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["b_client_sales_inv_num"]
            queryset = queryset.filter(b_client_sales_inv_num__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["dme_status_detail"]
            queryset = queryset.filter(dme_status_detail__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["dme_status_action"]
            queryset = queryset.filter(dme_status_action__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["z_calculated_ETA"]
            queryset = queryset.filter(z_calculated_ETA__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["de_to_PickUp_Instructions_Address"]
            queryset = queryset.filter(
                de_to_PickUp_Instructions_Address__icontains=column_filter
            )
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["b_booking_project"]
            queryset = queryset.filter(b_booking_project__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["de_Deliver_By_Date"]
            queryset = queryset.filter(de_Deliver_By_Date__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["b_project_due_date"]
            queryset = queryset.filter(b_project_due_date__icontains=column_filter)
        except KeyError:
            column_filter = ""

        try:
            column_filter = column_filters["delivery_booking"]
            queryset = queryset.filter(delivery_booking__icontains=column_filter)
        except KeyError:
            column_filter = ""

        return queryset

    @action(detail=False, methods=["get"])
    def get_bookings(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client_employee_role = client_employee.get_role()
            client = (
                DME_clients.objects.select_related()
                .filter(pk_id_dme_client=int(client_employee.fk_id_dme_client_id))
                .first()
            )

        start_date = self.request.query_params.get("startDate", None)

        if start_date == "*":
            search_type = "ALL"
        else:
            search_type = "FILTER"
            end_date = self.request.query_params.get("endDate", None)

        if search_type == "FILTER":
            first_date = datetime.strptime(start_date, "%Y-%m-%d")
            last_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

        warehouse_id = self.request.query_params.get("warehouseId", None)
        sort_field = self.request.query_params.get("sortField", None)
        column_filters = json.loads(
            self.request.query_params.get("columnFilters", None)
        )
        active_tab_index = json.loads(
            self.request.query_params.get("activeTabInd", None)
        )
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

        if multi_find_values:
            multi_find_values = multi_find_values.split(", ")
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
                ).exclude(Q(z_connote_url__isnull=True) | Q(z_connote_url__exact=""))

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
                queryset = self._column_filter_4_get_bookings(queryset, column_filters)

        else:
            if search_type == "FILTER":
                # Date filter
                if user_type == "DME":
                    queryset = queryset.filter(
                        z_CreatedTimestamp__range=(first_date, last_date)
                    )
                else:
                    if client.company_name == "BioPak":
                        queryset = queryset.filter(
                            puPickUpAvailFrom_Date__range=(first_date, last_date)
                        )
                    else:
                        queryset = queryset.filter(
                            z_CreatedTimestamp__range=(first_date, last_date)
                        )

            # Warehouse filter
            if int(warehouse_id) is not 0:
                queryset = queryset.filter(fk_client_warehouse=int(warehouse_id))

            # Mulitple search | Simple search | Project Name Search
            if project_name and len(project_name) > 0:
                queryset = queryset.filter(b_booking_project=project_name)
            elif multi_find_values and len(multi_find_values) > 0:
                preserved = Case(
                    *[
                        When(**{f"{multi_find_field}": multi_find_value, "then": pos})
                        for pos, multi_find_value in enumerate(multi_find_values)
                    ]
                )
                filter_kwargs = {f"{multi_find_field}__in": multi_find_values}
                queryset = queryset.filter(**filter_kwargs).order_by(preserved)
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
                        | Q(deToCompanyName__icontains=simple_search_keyword)
                        | Q(de_To_Address_Suburb__icontains=simple_search_keyword)
                        | Q(de_To_Address_State__icontains=simple_search_keyword)
                        | Q(de_To_Address_PostalCode__icontains=simple_search_keyword)
                        | Q(
                            b_clientReference_RA_Numbers__icontains=simple_search_keyword
                        )
                        | Q(vx_freight_provider__icontains=simple_search_keyword)
                        | Q(vx_serviceName__icontains=simple_search_keyword)
                        | Q(v_FPBookingNumber__icontains=simple_search_keyword)
                        | Q(b_status__icontains=simple_search_keyword)
                        | Q(b_status_API__icontains=simple_search_keyword)
                        | Q(
                            s_05_LatestPickUpDateTimeFinal__icontains=simple_search_keyword
                        )
                        | Q(
                            s_06_LatestDeliveryDateTimeFinal__icontains=simple_search_keyword
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
                            Q(**{"de_to_PickUp_Instructions_Address__icontains": val})
                            for val in search_keywords
                        ]
                        queryset = queryset.filter(reduce(operator.or_, list_of_Q))
            # Column fitler
            queryset = self._column_filter_4_get_bookings(queryset, column_filters)

        # active_tab_index count
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
            if booking.b_status == "Booked" and not booking.z_manifest_url:
                to_manifest += 1
            if booking.b_status == "Ready to booking":
                to_process += 1
            if booking.b_status == "Closed":
                closed += 1

        # active_tab_index 0 -> all, 1 -> errors_to_correct
        if active_tab_index == 1:
            queryset = queryset.exclude(b_error_Capture__isnull=True).exclude(
                b_error_Capture__exact=""
            )
        if active_tab_index == 2:
            queryset = queryset.filter(
                Q(z_label_url__isnull=True) | Q(z_label_url__exact="")
            )
        elif active_tab_index == 3:
            queryset = queryset.filter(b_status__icontains="Booked")
        elif active_tab_index == 4:
            queryset = queryset.filter(b_status__icontains="Ready to booking")
        elif active_tab_index == 5:
            queryset = queryset.filter(b_status__icontains="Closed")
        elif active_tab_index == 6:
            queryset = queryset.filter(b_status=dme_status)

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

        # Count
        bookings_cnt = queryset.count()

        filtered_booking_ids = []
        for booking in queryset:
            filtered_booking_ids.append(booking.id)

        bookings = queryset
        ret_data = []

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

        ret_data = []
        for booking in queryset:
            ret_data.append(
                {
                    "id": booking.id,
                    "b_bookingID_Visual": booking.b_bookingID_Visual,
                    "b_dateBookedDate": booking.b_dateBookedDate,
                    "puPickUpAvailFrom_Date": booking.puPickUpAvailFrom_Date,
                    "b_clientReference_RA_Numbers": booking.b_clientReference_RA_Numbers,
                    "b_status": booking.b_status,
                    "vx_freight_provider": booking.vx_freight_provider,
                    "v_FPBookingNumber": booking.v_FPBookingNumber,
                    "vx_serviceName": booking.vx_serviceName,
                    "s_05_LatestPickUpDateTimeFinal": booking.s_05_LatestPickUpDateTimeFinal,
                    "s_06_LatestDeliveryDateTimeFinal": booking.s_06_LatestDeliveryDateTimeFinal,
                    "puCompany": booking.puCompany,
                    "deToCompanyName": booking.deToCompanyName,
                    "z_label_url": booking.z_label_url,
                    "b_error_Capture": booking.b_error_Capture,
                    "z_downloaded_shipping_label_timestamp": booking.z_downloaded_shipping_label_timestamp,
                    "pk_booking_id": booking.pk_booking_id,
                    "pu_Address_street_1": booking.pu_Address_Street_1,
                    "pu_Address_street_2": booking.pu_Address_street_2,
                    "pu_Address_Suburb": booking.pu_Address_Suburb,
                    "pu_Address_City": booking.pu_Address_City,
                    "pu_Address_State": booking.pu_Address_State,
                    "pu_Address_PostalCode": booking.pu_Address_PostalCode,
                    "pu_Address_Country": booking.pu_Address_Country,
                    "de_To_Address_street_1": booking.de_To_Address_Street_1,
                    "de_To_Address_street_2": booking.de_To_Address_Street_2,
                    "de_To_Address_Suburb": booking.de_To_Address_Suburb,
                    "de_To_Address_City": booking.de_To_Address_City,
                    "de_To_Address_State": booking.de_To_Address_State,
                    "de_To_Address_PostalCode": booking.de_To_Address_PostalCode,
                    "de_To_Address_Country": booking.de_To_Address_Country,
                    "s_20_Actual_Pickup_TimeStamp": booking.s_20_Actual_Pickup_TimeStamp,
                    "s_21_Actual_Delivery_TimeStamp": booking.s_21_Actual_Delivery_TimeStamp,
                    "b_status_API": booking.b_status_API,
                    "z_pod_url": booking.z_pod_url,
                    "z_pod_signed_url": booking.z_pod_signed_url,
                    "z_connote_url": booking.z_connote_url,
                    "z_downloaded_pod_timestamp": booking.z_downloaded_pod_timestamp,
                    "z_downloaded_pod_sog_timestamp": booking.z_downloaded_pod_sog_timestamp,
                    "z_downloaded_connote_timestamp": booking.z_downloaded_connote_timestamp,
                    "has_comms": booking.has_comms(),
                    "b_client_sales_inv_num": booking.b_client_sales_inv_num,
                    "z_lock_status": booking.z_lock_status,
                    "business_group": booking.get_group_name(),
                    "pu_PickUp_By_Date_DME": booking.pu_PickUp_By_Date_DME,
                    "de_Deliver_By_Date": booking.de_Deliver_By_Date,
                    "de_Deliver_From_Date": booking.de_Deliver_From_Date,
                    "dme_delivery_status_category": booking.get_dme_delivery_status_category(),
                    "dme_status_detail": booking.dme_status_detail,
                    "dme_status_action": booking.dme_status_action,
                    "vx_fp_del_eta_time": booking.vx_fp_del_eta_time,
                    "b_client_name": booking.b_client_name,
                    "check_pod": booking.check_pod,
                    "fk_manifest_id": booking.fk_manifest_id,
                    "b_is_flagged_add_on_services": booking.b_is_flagged_add_on_services,
                    "de_to_PickUp_Instructions_Address": booking.de_to_PickUp_Instructions_Address,
                    "warehouse_code": booking.fk_client_warehouse.client_warehouse_code,
                    "b_fp_qty_delivered": booking.b_fp_qty_delivered,
                    "manifest_timestamp": booking.manifest_timestamp,
                    "b_booking_project": booking.b_booking_project,
                    "b_project_opened": booking.b_project_opened,
                    "b_project_inventory_due": booking.b_project_inventory_due,
                    "b_project_wh_unpack": booking.b_project_wh_unpack,
                    "b_project_dd_receive_date": booking.b_project_dd_receive_date,
                    "z_calculated_ETA": booking.z_calculated_ETA,
                    "b_project_due_date": booking.b_project_due_date,
                    "delivery_booking": booking.delivery_booking,
                    "fp_store_event_date": booking.fp_store_event_date,
                    "fp_store_event_time": booking.fp_store_event_time,
                    "fp_store_event_desc": booking.fp_store_event_desc,
                    "fp_received_date_time": booking.fp_received_date_time,
                    "b_given_to_transport_date_time": booking.b_given_to_transport_date_time,
                }
            )

        return JsonResponse(
            {
                "bookings": ret_data,
                "filtered_booking_ids": filtered_booking_ids,
                "count": bookings_cnt,
                "page_cnt": page_cnt,
                "page_ind": page_ind,
                "page_item_cnt": page_item_cnt,
                "errors_to_correct": errors_to_correct,
                "to_manifest": to_manifest,
                "missing_labels": missing_labels,
                "to_process": to_process,
                "closed": closed,
            }
        )

    @action(detail=True, methods=["put"])
    def update_booking(self, request, pk, format=None):
        booking = Bookings.objects.get(pk=pk)
        serializer = BookingSerializer(booking, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["put"])
    def change_bookings_status(self, request, format=None):
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

                    if not booking.delivery_kpi_days:
                        delivery_kpi_days = 14
                    else:
                        delivery_kpi_days = int(booking.delivery_kpi_days)

                    if status == "In Transit":
                        booking.z_calculated_ETA = (
                            datetime.strptime(optional_value, "%Y-%m-%d %H:%M:%S")
                            + timedelta(days=delivery_kpi_days)
                        ).date()
                        booking.b_given_to_transport_date_time = datetime.strptime(
                            optional_value, "%Y-%m-%d %H:%M:%S"
                        )

                    status_history.create(booking, status, request.user.username)
                    booking.b_status = status
                    calc_collect_after_status_change(booking.pk_booking_id, status)
                    booking.save()
                return JsonResponse({"status": "success"})
        except Exception as e:
            if settings.env == "local":
                print("Exception: ", e)
            return Response({"status": "error"})

    @action(detail=False, methods=["post"])
    def generate_xls(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client_employee_role = client_employee.get_role()
            client = (
                DME_clients.objects.select_related()
                .filter(pk_id_dme_client=int(client_employee.fk_id_dme_client_id))
                .first()
            )

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
            last_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

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

        # Optimize to speed up building XLS
        queryset.only(
            "pk_booking_id",
            "b_dateBookedDate",
            "pu_Address_State",
            "deToCompanyName",
            "de_To_Address_Suburb",
            "de_To_Address_State",
            "de_To_Address_PostalCode",
            "b_client_sales_inv_num",
            "b_client_order_num",
            "v_FPBookingNumber",
            "b_status",
            "dme_status_detail",
            "dme_status_action",
            "dme_status_history_notes",
            "s_21_ActualDeliveryTimeStamp",
            "z_pod_url",
            "z_pod_signed_url",
            "delivery_kpi_days",
            "de_Deliver_By_Date",
            "vx_freight_provider",
            "puCompany",
            "pu_Address_Suburb",
            "b_bookingID_Visual",
        )

        if use_selected:
            queryset = queryset.filter(pk__in=booking_ids)
        else:
            # Date filter
            if user_type == "DME":
                queryset = queryset.filter(
                    z_CreatedTimestamp__range=(first_date, last_date)
                )
            else:
                if client.company_name == "BioPak":
                    queryset = queryset.filter(
                        puPickUpAvailFrom_Date__range=(first_date, last_date)
                    )
                else:
                    queryset = queryset.filter(
                        z_CreatedTimestamp__range=(first_date, last_date)
                    )

        # Freight Provider filter
        if vx_freight_provider != "All":
            queryset = queryset.filter(vx_freight_provider=vx_freight_provider)

        # Client filter
        if pk_id_dme_client != "All" and pk_id_dme_client != 0:
            client = DME_clients.objects.get(pk_id_dme_client=pk_id_dme_client)
            queryset = queryset.filter(kf_client_id=client.dme_account_num)

        build_xls_and_send(
            queryset,
            email_addr,
            report_type,
            str(self.request.user),
            first_date,
            last_date,
            show_field_name,
        )
        return JsonResponse({"status": "started generate xml"})

    @action(detail=False, methods=["post"])
    def calc_collected(self, request, format=None):
        booking_ids = request.data["bookignIds"]
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
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client_employee_role = client_employee.get_role()
            client = (
                DME_clients.objects.select_related()
                .filter(pk_id_dme_client=int(client_employee.fk_id_dme_client_id))
                .first()
            )

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
        ret_data = []

        for booking in bookings:
            ret_data.append(
                {
                    "id": booking.id,
                    "b_bookingID_Visual": booking.b_bookingID_Visual,
                    "b_dateBookedDate": booking.b_dateBookedDate,
                    "puPickUpAvailFrom_Date": booking.puPickUpAvailFrom_Date,
                    "b_clientReference_RA_Numbers": booking.b_clientReference_RA_Numbers,
                    "b_status": booking.b_status,
                    "vx_freight_provider": booking.vx_freight_provider,
                    "v_FPBookingNumber": booking.v_FPBookingNumber,
                    "vx_serviceName": booking.vx_serviceName,
                    "s_05_LatestPickUpDateTimeFinal": booking.s_05_LatestPickUpDateTimeFinal,
                    "s_06_LatestDeliveryDateTimeFinal": booking.s_06_LatestDeliveryDateTimeFinal,
                    "puCompany": booking.puCompany,
                    "deToCompanyName": booking.deToCompanyName,
                    "z_label_url": booking.z_label_url,
                    "b_error_Capture": booking.b_error_Capture,
                    "z_downloaded_shipping_label_timestamp": booking.z_downloaded_shipping_label_timestamp,
                    "pk_booking_id": booking.pk_booking_id,
                    "pu_Address_street_1": booking.pu_Address_Street_1,
                    "pu_Address_street_2": booking.pu_Address_street_2,
                    "pu_Address_Suburb": booking.pu_Address_Suburb,
                    "pu_Address_City": booking.pu_Address_City,
                    "pu_Address_State": booking.pu_Address_State,
                    "pu_Address_PostalCode": booking.pu_Address_PostalCode,
                    "pu_Address_Country": booking.pu_Address_Country,
                    "de_To_Address_street_1": booking.de_To_Address_Street_1,
                    "de_To_Address_street_2": booking.de_To_Address_Street_2,
                    "de_To_Address_Suburb": booking.de_To_Address_Suburb,
                    "de_To_Address_City": booking.de_To_Address_City,
                    "de_To_Address_State": booking.de_To_Address_State,
                    "de_To_Address_PostalCode": booking.de_To_Address_PostalCode,
                    "de_To_Address_Country": booking.de_To_Address_Country,
                    "s_20_Actual_Pickup_TimeStamp": booking.s_20_Actual_Pickup_TimeStamp,
                    "s_21_Actual_Delivery_TimeStamp": booking.s_21_Actual_Delivery_TimeStamp,
                    "b_status_API": booking.b_status_API,
                    "z_downloaded_pod_timestamp": booking.z_downloaded_pod_timestamp,
                    "z_pod_url": booking.z_pod_url,
                    "z_pod_signed_url": booking.z_pod_signed_url,
                    "has_comms": booking.has_comms(),
                    "b_client_sales_inv_num": booking.b_client_sales_inv_num,
                    "z_lock_status": booking.z_lock_status,
                    "business_group": booking.get_group_name(),
                    "de_Deliver_By_Date": booking.de_Deliver_By_Date,
                    "de_Deliver_From_Date": booking.de_Deliver_From_Date,
                    "dme_delivery_status_category": booking.get_dme_delivery_status_category(),
                    "dme_status_detail": booking.dme_status_detail,
                    "dme_status_action": booking.dme_status_action,
                    "vx_fp_del_eta_time": booking.vx_fp_del_eta_time,
                    "z_manifest_url": booking.z_manifest_url,
                    "z_calculated_ETA": booking.z_calculated_ETA,
                }
            )

        return JsonResponse(
            {
                "bookings": ret_data,
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
                elif field_name == "b_given_to_transport_date_time" and field_content:
                    booking.z_calculated_ETA = datetime.strptime(
                        field_content, "%Y-%m-%d %H:%M:%S"
                    ) + timedelta(days=delivery_kpi_days)

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
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client_employee_role = client_employee.get_role()
            client = (
                DME_clients.objects.select_related()
                .filter(pk_id_dme_client=int(client_employee.fk_id_dme_client_id))
                .first()
            )

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
                z_CreatedTimestamp__range=(first_date, last_date)
            )
        else:
            if client.company_name == "BioPak":
                queryset = queryset.filter(
                    puPickUpAvailFrom_Date__range=(first_date, last_date)
                )
            else:
                queryset = queryset.filter(
                    z_CreatedTimestamp__range=(first_date, last_date)
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

        if clientname in ["BioPak", "dme"]:
            st_bookings_has_manifest = (
                Bookings.objects.exclude(manifest_timestamp__isnull=True)
                .filter(vx_freight_provider__iexact="startrack")
                .order_by("-manifest_timestamp")
            )
            manifest_dates = st_bookings_has_manifest.values_list(
                "manifest_timestamp", flat=True
            ).distinct()

            results = []
            for manifest_date in manifest_dates:
                result = {}

                each_day_manifest_bookings = st_bookings_has_manifest.filter(
                    manifest_timestamp=manifest_date
                )
                first_booking = each_day_manifest_bookings.first()
                result["count"] = each_day_manifest_bookings.count()
                result["z_manifest_url"] = first_booking.z_manifest_url
                result[
                    "warehouse_name"
                ] = first_booking.fk_client_warehouse.warehousename
                result["manifest_date"] = manifest_date
                results.append(result)
        else:
            return JsonResponse(
                {"message": "You have no permission to see this information"},
                status=400,
            )

        return JsonResponse({"results": results})

    @action(detail=False, methods=["get"])
    def get_project_names(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is not None:
            user_type = "DME"
        else:
            user_type = "CLIENT"
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client_employee_role = client_employee.get_role()
            client = (
                DME_clients.objects.select_related()
                .filter(pk_id_dme_client=int(client_employee.fk_id_dme_client_id))
                .first()
            )

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
        email_module.send_booking_email_using_template(booking_id, template_name)
        return JsonResponse({"message": "success"}, status=200)


class BookingViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer

    @action(detail=False, methods=["get"])
    def get_booking(self, request, format=None):
        idBookingNumber = request.GET["id"]
        filterName = request.GET["filter"]
        user_id = request.user.id

        try:
            dme_employee = (
                DME_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )

            if dme_employee is not None:
                user_type = "DME"
            else:
                user_type = "CLIENT"

            if user_type == "DME":
                queryset = Bookings.objects.all()
            else:
                client_employee = (
                    Client_employees.objects.select_related()
                    .filter(fk_id_user=user_id)
                    .first()
                )

                if client_employee is None:
                    return JsonResponse({"booking": {}, "nextid": 0, "previd": 0})

                client_employee_role = client_employee.get_role()
                client = DME_clients.objects.get(
                    pk_id_dme_client=client_employee.fk_id_dme_client_id
                )

                if client is None:
                    return JsonResponse({"booking": {}, "nextid": 0, "previd": 0})

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

            if filterName == "dme":
                booking = queryset.get(b_bookingID_Visual=idBookingNumber)
            elif filterName == "con":
                booking = queryset.filter(v_FPBookingNumber=idBookingNumber).first()
            elif filterName == "id":
                booking = queryset.get(id=idBookingNumber)
            elif filterName == "null":
                booking = queryset.last()
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
                    e_qty_total += (
                        booking_line.e_qty if booking_line.e_qty is not None else 0
                    )

                # Get count for `Communication Log`
                comms = Dme_comm_and_task.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                )

                # Get count for 'Attachments'
                attachments = Dme_attachments.objects.filter(
                    fk_id_dme_booking=booking.pk_booking_id
                )

                return_data = []
                if booking is not None:
                    return_data = {
                        "id": booking.id,
                        "puCompany": booking.puCompany,
                        "pu_Address_Street_1": booking.pu_Address_Street_1,
                        "pu_Address_street_2": booking.pu_Address_street_2,
                        "pu_Address_PostalCode": booking.pu_Address_PostalCode,
                        "pu_Address_Suburb": booking.pu_Address_Suburb,
                        "pu_Address_Country": booking.pu_Address_Country,
                        "pu_Contact_F_L_Name": booking.pu_Contact_F_L_Name,
                        "pu_Phone_Main": booking.pu_Phone_Main,
                        "pu_Email": booking.pu_Email,
                        "de_To_Address_Street_1": booking.de_To_Address_Street_1,
                        "de_To_Address_Street_2": booking.de_To_Address_Street_2,
                        "de_To_Address_PostalCode": booking.de_To_Address_PostalCode,
                        "de_To_Address_Suburb": booking.de_To_Address_Suburb,
                        "de_To_Address_Country": booking.de_To_Address_Country,
                        "de_to_Contact_F_LName": booking.de_to_Contact_F_LName,
                        "de_to_Phone_Main": booking.de_to_Phone_Main,
                        "de_Email": booking.de_Email,
                        "deToCompanyName": booking.deToCompanyName,
                        "b_bookingID_Visual": booking.b_bookingID_Visual,
                        "v_FPBookingNumber": booking.v_FPBookingNumber,
                        "pk_booking_id": booking.pk_booking_id,
                        "vx_freight_provider": booking.vx_freight_provider,
                        "z_label_url": booking.z_label_url,
                        "z_pod_url": booking.z_pod_url,
                        "z_pod_signed_url": booking.z_pod_signed_url,
                        "pu_Address_State": booking.pu_Address_State,
                        "de_To_Address_State": booking.de_To_Address_State,
                        "b_status": booking.b_status,
                        "b_dateBookedDate": booking.b_dateBookedDate,
                        "s_20_Actual_Pickup_TimeStamp": booking.s_20_Actual_Pickup_TimeStamp,
                        "s_21_Actual_Delivery_TimeStamp": booking.s_21_Actual_Delivery_TimeStamp,
                        "b_client_name": booking.b_client_name,
                        "b_client_warehouse_code": booking.b_client_warehouse_code,
                        "b_clientPU_Warehouse": booking.b_clientPU_Warehouse,
                        "booking_Created_For": booking.booking_Created_For,
                        "booking_Created_For_Email": booking.booking_Created_For_Email,
                        "vx_fp_pu_eta_time": booking.vx_fp_pu_eta_time,
                        "vx_fp_del_eta_time": booking.vx_fp_del_eta_time,
                        "b_clientReference_RA_Numbers": booking.b_clientReference_RA_Numbers,
                        "de_to_Pick_Up_Instructions_Contact": booking.de_to_Pick_Up_Instructions_Contact,
                        "de_to_PickUp_Instructions_Address": booking.de_to_PickUp_Instructions_Address,
                        "pu_pickup_instructions_address": booking.pu_pickup_instructions_address,
                        "pu_PickUp_Instructions_Contact": booking.pu_PickUp_Instructions_Contact,
                        "vx_serviceName": booking.vx_serviceName,
                        "consignment_label_link": booking.consignment_label_link,
                        "s_02_Booking_Cutoff_Time": booking.s_02_Booking_Cutoff_Time,
                        "puPickUpAvailFrom_Date": booking.puPickUpAvailFrom_Date,
                        "z_CreatedTimestamp": booking.z_CreatedTimestamp,
                        "b_dateBookedDate": booking.b_dateBookedDate,
                        "total_lines_qty_override": booking.total_lines_qty_override,
                        "total_1_KG_weight_override": booking.total_1_KG_weight_override,
                        "total_Cubic_Meter_override": booking.total_Cubic_Meter_override,
                        "b_status_API": booking.b_status_API,
                        "z_lock_status": booking.z_lock_status,
                        "tally_delivered": booking.tally_delivered,
                        "dme_status_history_notes": booking.dme_status_history_notes,
                        "dme_status_detail": booking.dme_status_detail,
                        "dme_status_action": booking.dme_status_action,
                        "dme_status_linked_reference_from_fp": booking.dme_status_linked_reference_from_fp,
                        "pu_PickUp_Avail_From_Date_DME": booking.pu_PickUp_Avail_From_Date_DME,
                        "pu_PickUp_Avail_Time_Hours": booking.pu_PickUp_Avail_Time_Hours,
                        "pu_PickUp_Avail_Time_Minutes": booking.pu_PickUp_Avail_Time_Minutes,
                        "pu_PickUp_By_Date_DME": booking.pu_PickUp_By_Date_DME,
                        "pu_PickUp_By_Time_Hours_DME": booking.pu_PickUp_By_Time_Hours_DME,
                        "pu_PickUp_By_Time_Minutes_DME": booking.pu_PickUp_By_Time_Minutes_DME,
                        "de_Deliver_From_Date": booking.de_Deliver_From_Date,
                        "de_Deliver_From_Hours": booking.de_Deliver_From_Hours,
                        "de_Deliver_From_Minutes": booking.de_Deliver_From_Minutes,
                        "de_Deliver_By_Date": booking.de_Deliver_By_Date,
                        "de_Deliver_By_Hours": booking.de_Deliver_By_Hours,
                        "de_Deliver_By_Minutes": booking.de_Deliver_By_Minutes,
                        "client_item_references": booking.get_client_item_references(),
                        "v_service_Type_2": booking.v_service_Type_2,
                        "fk_fp_pickup_id": booking.fk_fp_pickup_id,
                        "v_vehicle_Type": booking.v_vehicle_Type,
                        "inv_billing_status": booking.inv_billing_status,
                        "inv_billing_status_note": booking.inv_billing_status_note,
                        "b_client_sales_inv_num": booking.b_client_sales_inv_num,
                        "b_client_order_num": booking.b_client_order_num,
                        "b_client_name_sub": booking.b_client_name_sub,
                        "inv_dme_invoice_no": booking.inv_dme_invoice_no,
                        "fp_invoice_no": booking.fp_invoice_no,
                        "inv_cost_quoted": booking.inv_cost_quoted,
                        "inv_cost_actual": booking.inv_cost_actual,
                        "inv_sell_quoted": booking.inv_sell_quoted,
                        "inv_sell_actual": booking.inv_sell_actual,
                        "x_manual_booked_flag": booking.x_manual_booked_flag,
                        "b_fp_qty_delivered": booking.b_fp_qty_delivered,
                        "manifest_timestamp": booking.manifest_timestamp,
                        "b_booking_project": booking.b_booking_project,
                        "b_project_opened": booking.b_project_opened,
                        "b_project_inventory_due": booking.b_project_inventory_due,
                        "b_project_wh_unpack": booking.b_project_wh_unpack,
                        "b_project_dd_receive_date": booking.b_project_dd_receive_date,
                        "z_calculated_ETA": booking.z_calculated_ETA,
                        "b_project_due_date": booking.b_project_due_date,
                        "delivery_booking": booking.delivery_booking,
                        "fp_store_event_date": booking.fp_store_event_date,
                        "fp_store_event_time": booking.fp_store_event_time,
                        "fp_store_event_desc": booking.fp_store_event_desc,
                        "fp_received_date_time": booking.fp_received_date_time,
                        "b_given_to_transport_date_time": booking.b_given_to_transport_date_time,
                        "delivery_kpi_days": 14
                        if not booking.delivery_kpi_days
                        else booking.delivery_kpi_days,
                        "api_booking_quote": booking.api_booking_quote.id
                        if booking.api_booking_quote
                        else None,
                    }
                    return JsonResponse(
                        {
                            "booking": return_data,
                            "nextid": nextBookingId,
                            "previd": prevBookingId,
                            "e_qty_total": e_qty_total,
                            "cnt_comms": len(comms),
                            "cnt_attachments": len(attachments),
                        }
                    )
            else:
                return JsonResponse(
                    {
                        "booking": {},
                        "nextid": 0,
                        "previd": 0,
                        "e_qty_total": 0,
                        "cnt_comms": 0,
                        "cnt_attachments": 0,
                    }
                )
        except Bookings.DoesNotExist:
            return JsonResponse(
                {
                    "booking": {},
                    "nextid": 0,
                    "previd": 0,
                    "e_qty_total": 0,
                    "cnt_comms": 0,
                    "cnt_attachments": 0,
                }
            )

    @action(detail=False, methods=["get"])
    def get_status(self, request, format=None):
        pk_booking_id = request.GET["pk_header_id"]
        user_id = request.user.id

        try:
            dme_employee = (
                DME_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )

            if dme_employee is not None:
                user_type = "DME"
            else:
                user_type = "CLIENT"

            if user_type == "CLIENT":
                client_employee = (
                    Client_employees.objects.select_related()
                    .filter(fk_id_user=user_id)
                    .first()
                )
                client = DME_clients.objects.get(
                    pk_id_dme_client=client_employee.fk_id_dme_client_id
                )

                if client is None:
                    return JsonResponse({"booking": {}, "nextid": 0, "previd": 0})

            try:
                booking = (
                    Bookings.objects.select_related()
                    .filter(pk_booking_id=pk_booking_id)
                    .values(
                        "b_status",
                        "v_FPBookingNumber",
                        "vx_account_code",
                        "kf_client_id",
                    )
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
        bookingData["pk_booking_id"] = str(uuid.uuid1()) + "_" + str(time.time())

        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def duplicate_booking(self, request, format=None):
        switch_info = request.GET["switchInfo"]
        dup_line_and_linedetail = request.GET["dupLineAndLineDetail"]
        booking_id = request.GET["bookingId"]
        user_id = request.user.id
        booking = Bookings.objects.get(id=booking_id)

        if switch_info == "true":
            newBooking = {
                "b_bookingID_Visual": Bookings.get_max_b_bookingID_Visual() + 1,
                "fk_client_warehouse": booking.fk_client_warehouse_id,
                "b_client_warehouse_code": booking.b_client_warehouse_code,
                "b_clientPU_Warehouse": booking.b_clientPU_Warehouse,
                "b_client_name": booking.b_client_name,
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
                "pk_booking_id": str(uuid.uuid1()),
                "z_lock_status": booking.z_lock_status,
                "b_status": "Ready for booking",
                "vx_freight_provider": booking.vx_freight_provider,
                "kf_client_id": booking.kf_client_id,
                "b_clientReference_RA_Numbers": booking.b_clientReference_RA_Numbers,
                "vx_serviceName": booking.vx_serviceName,
                "z_CreatedTimestamp": datetime.now(),
            }
        else:
            newBooking = {
                "b_bookingID_Visual": Bookings.get_max_b_bookingID_Visual() + 1,
                "fk_client_warehouse": booking.fk_client_warehouse_id,
                "b_client_warehouse_code": booking.b_client_warehouse_code,
                "b_clientPU_Warehouse": booking.b_clientPU_Warehouse,
                "b_client_name": booking.b_client_name,
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
                "pk_booking_id": str(uuid.uuid1()),
                "z_lock_status": booking.z_lock_status,
                "b_status": "Ready for booking",
                "vx_freight_provider": booking.vx_freight_provider,
                "kf_client_id": booking.kf_client_id,
                "b_clientReference_RA_Numbers": booking.b_clientReference_RA_Numbers,
                "vx_serviceName": booking.vx_serviceName,
                "z_CreatedTimestamp": datetime.now(),
            }

        if dup_line_and_linedetail == "true":
            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )
            booking_line_details = Booking_lines_data.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )
            for booking_line in booking_lines:
                booking_line.pk_lines_id = None
                booking_line.fk_booking_id = newBooking["pk_booking_id"]
                booking_line.e_qty_delivered = 0
                booking_line.e_qty_adjusted_delivered = 0
                booking_line.save()
            for booking_line_detail in booking_line_details:
                booking_line_detail.pk_id_lines_data = None
                booking_line_detail.fk_booking_id = newBooking["pk_booking_id"]
                booking_line_detail.z_createdTimeStamp = datetime.now()
                booking_line_detail.z_modifiedTimeStamp = datetime.now()
                booking_line_detail.save()

        serializer = BookingSerializer(data=newBooking)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def tick_manual_book(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        id = body["id"]
        user_id = request.user.id

        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is None:
            user_type = "CLIENT"
            return Response(status=status.HTTP_400_BAD_REQUEST)

        booking = Bookings.objects.get(id=id)

        if booking.b_dateBookedDate:
            return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            booking.x_manual_booked_flag = not booking.x_manual_booked_flag
            booking.save()
            serializer = BookingSerializer(booking)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def manual_book(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        id = body["id"]
        user_id = request.user.id

        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

        if dme_employee is None:
            user_type = "CLIENT"
            return Response(status=status.HTTP_400_BAD_REQUEST)

        booking = Bookings.objects.get(id=id)

        if not booking.x_manual_booked_flag:
            return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            booking.b_status = "Booked"
            booking.b_dateBookedDate = datetime.now()
            booking.x_booking_Created_With = "Manual"
            booking.save()
            serializer = BookingSerializer(booking)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def auto_augment(self, request, format=None):
        body = literal_eval(request.body.decode("utf8"))
        bookingId = body["bookingId"]
        booking = Bookings.objects.get(pk=bookingId)

        try:
            client_process = (
                Client_Process_Mgr.objects.select_related()
                .filter(fk_booking_id=bookingId)
                .first()
            )
            if client_process is None:
                client_process = Client_Process_Mgr(fk_booking_id=bookingId)
                client_process.process_name = "Auto Augment " + str(bookingId)
                client_process.origin_puCompany = booking.puCompany
                client_process.origin_pu_Address_Street_1 = booking.pu_Address_Street_1
                client_process.origin_pu_Address_Street_2 = booking.pu_Address_street_2
                client_process.origin_pu_pickup_instructions_address = (
                    booking.pu_pickup_instructions_address
                )
                client_process.origin_deToCompanyName = booking.deToCompanyName
                client_process.origin_de_Email = booking.de_Email
                client_process.origin_de_Email_Group_Emails = (
                    booking.de_Email_Group_Emails
                )
                client_process.origin_de_To_Address_Street_1 = (
                    booking.de_To_Address_Street_1
                )
                client_process.origin_de_To_Address_Street_2 = (
                    booking.de_To_Address_Street_2
                )
                client_process.origin_pu_PickUp_By_Date = booking.pu_PickUp_By_Date
                client_process.origin_pu_PickUp_Avail_Time_Hours = (
                    booking.pu_PickUp_Avail_Time_Hours
                )

                client_auto_augment = Client_Auto_Augment.objects.first()

                if (
                    "Tempo" in booking.b_client_name
                    and booking.b_booking_Category == "Salvage Expense"
                ):
                    pu_Contact_F_L_Name = booking.pu_Contact_F_L_Name
                    puCompany = booking.puCompany
                    deToCompanyName = booking.deToCompanyName
                    booking.puCompany = (
                        puCompany + " (Ctct: " + pu_Contact_F_L_Name + ")"
                    )

                    if (
                        booking.pu_Address_street_2 == ""
                        or booking.pu_Address_street_2 == None
                    ):
                        booking.pu_Address_street_2 = booking.pu_Address_Street_1
                        custRefNumVerbage = (
                            "Ref: "
                            + str(booking.b_clientReference_RA_Numbers or "")
                            + " Returns 4 "
                            + booking.b_client_name
                            + ". Fragile"
                        )
                        booking.pu_Address_Street_1 = custRefNumVerbage
                        booking.de_Email = str(booking.de_Email or "").replace(";", ",")
                        booking.de_Email_Group_Emails = str(
                            booking.de_Email_Group_Emails or ""
                        ).replace(";", ",")
                        booking.pu_pickup_instructions_address = (
                            str(booking.pu_pickup_instructions_address or "")
                            + " "
                            + custRefNumVerbage
                        )

                    if "TIC" in booking.deToCompanyName:
                        booking.deToCompanyName = (
                            deToCompanyName + " (Open 7am-3pm, 1pm Fri)"
                        )
                        booking.de_Email = client_auto_augment.tic_de_Email
                        booking.de_Email_Group_Emails = (
                            client_auto_augment.tic_de_Email_Group_Emails
                        )
                        booking.de_To_Address_Street_1 = (
                            client_auto_augment.tic_de_To_Address_Street_1
                        )
                        booking.de_To_Address_Street_2 = (
                            client_auto_augment.tic_de_To_Address_Street_2
                        )

                    if "Sales Club" in booking.deToCompanyName:
                        booking.de_Email = client_auto_augment.sales_club_de_Email
                        booking.de_Email_Group_Emails = (
                            client_auto_augment.sales_club_de_Email_Group_Emails
                        )

                    if (
                        booking.x_ReadyStatus == "Available Now"
                        and booking.pu_PickUp_By_Date == None
                        and booking.pu_PickUp_By_Time_Hours == None
                    ):
                        booking.pu_PickUp_By_Date = datetime.now

                    if (
                        booking.x_ReadyStatus == "Available From"
                        and booking.puPickUpAvailFrom_Date == None
                        and booking.pu_PickUp_Avail_Time_Hours == None
                    ):
                        booking.pu_PickUp_Avail_Time_Hours = datetime.now

                    if (
                        booking.x_ReadyStatus == "Available From"
                        and booking.pu_PickUp_By_Date == None
                        and booking.pu_PickUp_Avail_Time_Hours == None
                    ):
                        booking.pu_PickUp_By_Date = datetime.now

                    client_process.save()
                    booking.save()
                    serializer = BookingSerializer(booking)
                    return Response(serializer.data)
                else:
                    if not "Tempo" in booking.b_client_name:
                        return JsonResponse(
                            {"message": "Client is not Tempo", "type": "Failure"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    elif booking.b_booking_Category != "Salvage Expense":
                        return JsonResponse(
                            {
                                "message": "Booking Category is not  Salvage Expense",
                                "type": "Failure",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            else:
                return JsonResponse(
                    {"message": "Already Augmented", "type": "Failure"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            print(str(e))
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
            client_process = (
                Client_Process_Mgr.objects.select_related()
                .filter(fk_booking_id=bookingId)
                .first()
            )
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
                booking.pu_PickUp_By_Date = client_process.origin_pu_PickUp_By_Date
                booking.pu_PickUp_Avail_Time_Hours = (
                    client_process.origin_pu_PickUp_Avail_Time_Hours
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
            print(str(e))
            return Response(
                {"type": "Failure", "message": "Exception occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def check_augmented(self, request, format=None):
        bookingId = request.GET.get("bookingId")

        client_process = (
            Client_Process_Mgr.objects.select_related()
            .filter(fk_booking_id=bookingId)
            .first()
        )

        if client_process is not None:
            return JsonResponse({"isAutoAugmented": True})
        else:
            return JsonResponse({"isAutoAugmented": False})


class BookingLinesViewSet(viewsets.ViewSet):
    serializer_class = BookingLineSerializer

    @action(detail=False, methods=["get"])
    def get_booking_lines(self, request, format=None):
        pk_booking_id = request.GET["pk_booking_id"]
        return_data = []

        if pk_booking_id == "undefined":
            booking_lines = Booking_lines.objects.all()
        else:
            booking_lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)

        for booking_line in booking_lines:
            return_data.append(
                {
                    "pk_lines_id": booking_line.pk_lines_id,
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
                    "e_qty_awaiting_inventory": booking_line.e_qty_awaiting_inventory,
                    "e_qty_collected": booking_line.e_qty_collected,
                    "e_qty_scanned_depot": booking_line.e_qty_scanned_depot,
                    "e_qty_delivered": booking_line.e_qty_delivered,
                    "e_qty_adjusted_delivered": booking_line.e_qty_adjusted_delivered,
                    "e_qty_damaged": booking_line.e_qty_damaged,
                    "e_qty_returned": booking_line.e_qty_returned,
                    "e_qty_shortages": booking_line.e_qty_shortages,
                    "e_qty_scanned_fp": booking_line.e_qty_scanned_fp,
                    "is_scanned": booking_line.get_is_scanned(),
                }
            )

        return JsonResponse({"booking_lines": return_data})

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
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete_booking_line(self, request, pk, format=None):
        booking_line = Booking_lines.objects.get(pk=pk)

        try:
            booking_line.delete()
            return JsonResponse({"Deleted BookingLine": booking_line})
        except Exception as e:
            # print('Exception: ', e)
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
        return_data = []

        if pk_booking_id == "undefined":
            booking_line_details = Booking_lines_data.objects.all()
        else:
            booking_line_details = Booking_lines_data.objects.filter(
                fk_booking_id=pk_booking_id
            )

        for booking_line_detail in booking_line_details:
            return_data.append(
                {
                    "pk_id_lines_data": booking_line_detail.pk_id_lines_data,
                    "modelNumber": booking_line_detail.modelNumber,
                    "itemDescription": booking_line_detail.itemDescription,
                    "quantity": booking_line_detail.quantity,
                    "itemFaultDescription": booking_line_detail.itemFaultDescription,
                    "insuranceValueEach": booking_line_detail.insuranceValueEach,
                    "gap_ra": booking_line_detail.gap_ra,
                    "clientRefNumber": booking_line_detail.clientRefNumber,
                    "fk_booking_lines_id": booking_line_detail.fk_booking_lines_id,
                }
            )

        return JsonResponse({"booking_line_details": return_data})

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

        try:
            booking_line_detail.delete()
            return JsonResponse({"Deleted BookingLineDetail ": booking_line_detail})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({"error": "Can not delete BookingLineDetail"})


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        user_id = int(self.request.user.id)
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

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
            client_employee = (
                Client_employees.objects.select_related()
                .filter(fk_id_user=user_id)
                .first()
            )
            client_employee_role = client_employee.get_role()

            if client_employee_role == "company":
                clientWarehouseObject_list = (
                    Client_warehouses.objects.select_related()
                    .filter(
                        fk_id_dme_client_id=int(client_employee.fk_id_dme_client_id)
                    )
                    .order_by("client_warehouse_code")
                )
                queryset = clientWarehouseObject_list
                return queryset
            elif client_employee_role == "warehouse":
                employee_warehouse_id = client_employee.warehouse_id
                employee_warehouse = Client_warehouses.objects.get(
                    pk_id_client_warehouses=employee_warehouse_id
                )
                queryset = [employee_warehouse]
                return queryset


class CommsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_comms(self, request, pk=None):
        def convert_date(date):
            if not date:
                date = datetime(2100, 1, 1).date()

            return date

        def reverse_date(object):
            if object["due_by_date"] == datetime(2100, 1, 1).date():
                object["due_by_date"] = None

            return object

        user_id = self.request.user.id
        booking_id = self.request.GET["bookingId"]
        sort_field = self.request.query_params.get("sortField", None)
        sort_type = self.request.query_params.get("sortType", None)
        column_filters = json.loads(
            self.request.query_params.get("columnFilters", None)
        )
        simple_search_keyword = self.request.query_params.get(
            "simpleSearchKeyword", None
        )
        sort_by_date = self.request.query_params.get("sortByDate", None)
        active_tab_ind = int(self.request.query_params.get("activeTabInd", None))

        if not sort_field:
            sort_by_date = "true"

        if booking_id == "":
            comms = Dme_comm_and_task.objects.all()
            bookings = Bookings.objects.all()
            return_datas = []
            closed_comms_cnt = 0
            opened_comms_cnt = 0
            all_cnt = 0

            # Simple search & Column fitler
            is_booking_filtered = True
            if len(simple_search_keyword) > 0:
                filtered_bookings = bookings.filter(
                    Q(b_bookingID_Visual__icontains=simple_search_keyword)
                    | Q(b_status__icontains=simple_search_keyword)
                    | Q(vx_freight_provider__icontains=simple_search_keyword)
                    | Q(puCompany__icontains=simple_search_keyword)
                    | Q(deToCompanyName__icontains=simple_search_keyword)
                    | Q(v_FPBookingNumber__icontains=simple_search_keyword)
                )

                if len(filtered_bookings) == 0:
                    is_booking_filtered = False
                else:
                    is_booking_filtered = True
                    bookings = filtered_bookings
            else:
                # Column Bookings filter
                try:
                    column_filter = column_filters["b_bookingID_Visual"]
                    bookings = bookings.filter(
                        b_bookingID_Visual__icontains=column_filter
                    )
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["b_status"]
                    bookings = bookings.filter(b_status__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["vx_freight_provider"]
                    bookings = bookings.filter(
                        vx_freight_provider__icontains=column_filter
                    )
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["puCompany"]
                    bookings = bookings.filter(puCompany__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["deToCompanyName"]
                    bookings = bookings.filter(deToCompanyName__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["v_FPBookingNumber"]
                    bookings = bookings.filter(
                        v_FPBookingNumber__icontains=column_filter
                    )
                except KeyError:
                    column_filter = ""

            # Filter on comms
            if sort_type == "comms":
                if sort_field is None:
                    comms = comms.order_by("-id")
                else:
                    comms = comms.order_by(sort_field)

            # Simple search & Column fitler
            if len(simple_search_keyword) > 0:
                new_comms = comms.filter(
                    Q(id__icontains=simple_search_keyword)
                    | Q(priority_of_log__icontains=simple_search_keyword)
                    | Q(assigned_to__icontains=simple_search_keyword)
                    | Q(dme_notes_type__icontains=simple_search_keyword)
                    | Q(query__icontains=simple_search_keyword)
                    | Q(dme_action__icontains=simple_search_keyword)
                    | Q(status_log_closed_time__icontains=simple_search_keyword)
                    | Q(dme_detail__icontains=simple_search_keyword)
                    | Q(dme_notes_external__icontains=simple_search_keyword)
                    | Q(due_by_date__icontains=simple_search_keyword)
                    | Q(due_by_time__icontains=simple_search_keyword)
                )

                if len(new_comms) == 0 and is_booking_filtered == False:
                    comms = []
                elif len(new_comms) > 0:
                    comms = new_comms
            else:
                # Column Comms filter
                try:
                    column_filter = column_filters["id"]
                    comms = comms.filter(id__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["priority_of_log"]
                    comms = comms.filter(priority_of_log__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["assigned_to"]
                    comms = comms.filter(assigned_to__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_notes_type"]
                    comms = comms.filter(dme_notes_type__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["query"]
                    comms = comms.filter(query__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_action"]
                    comms = comms.filter(dme_action__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["status_log_closed_time"]
                    comms = comms.filter(
                        status_log_closed_time__icontains=column_filter
                    )
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_detail"]
                    comms = comms.filter(dme_detail__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_notes_external"]
                    comms = comms.filter(dme_notes_external__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["due_by_date"]
                    comms = comms.filter(due_by_date__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["due_by_time"]
                    comms = comms.filter(due_by_time__icontains=column_filter)
                except KeyError:
                    column_filter = ""

            for comm in comms:
                for booking in bookings:
                    if comm.fk_booking_id == booking.pk_booking_id:
                        all_cnt += 1

                        if active_tab_ind == 1:
                            if comm.closed:
                                closed_comms_cnt += 1
                            else:
                                opened_comms_cnt += 1

                                return_data = {
                                    "b_bookingID_Visual": booking.b_bookingID_Visual,
                                    "b_status": booking.b_status,
                                    "vx_freight_provider": booking.vx_freight_provider,
                                    "puCompany": booking.puCompany,
                                    "deToCompanyName": booking.deToCompanyName,
                                    "v_FPBookingNumber": booking.v_FPBookingNumber,
                                    "id": comm.id,
                                    "fk_booking_id": comm.fk_booking_id,
                                    "priority_of_log": comm.priority_of_log,
                                    "assigned_to": comm.assigned_to,
                                    "query": comm.query,
                                    "dme_com_title": comm.dme_com_title,
                                    "closed": comm.closed,
                                    "status_log_closed_time": comm.status_log_closed_time,
                                    "dme_detail": comm.dme_detail,
                                    "dme_notes_type": comm.dme_notes_type,
                                    "dme_notes_external": comm.dme_notes_external,
                                    "due_by_datetime": str(comm.due_by_date)
                                    + " "
                                    + str(comm.due_by_time),
                                    "due_by_date": convert_date(comm.due_by_date),
                                    "due_by_time": comm.due_by_time,
                                    "dme_action": comm.dme_action,
                                    "z_createdTimeStamp": comm.z_createdTimeStamp,
                                }
                                return_datas.append(return_data)
                        elif active_tab_ind == 2:
                            if comm.closed:
                                closed_comms_cnt += 1

                                return_data = {
                                    "b_bookingID_Visual": booking.b_bookingID_Visual,
                                    "b_status": booking.b_status,
                                    "vx_freight_provider": booking.vx_freight_provider,
                                    "puCompany": booking.puCompany,
                                    "deToCompanyName": booking.deToCompanyName,
                                    "v_FPBookingNumber": booking.v_FPBookingNumber,
                                    "id": comm.id,
                                    "fk_booking_id": comm.fk_booking_id,
                                    "priority_of_log": comm.priority_of_log,
                                    "assigned_to": comm.assigned_to,
                                    "query": comm.query,
                                    "dme_com_title": comm.dme_com_title,
                                    "closed": comm.closed,
                                    "status_log_closed_time": comm.status_log_closed_time,
                                    "dme_detail": comm.dme_detail,
                                    "dme_notes_type": comm.dme_notes_type,
                                    "dme_notes_external": comm.dme_notes_external,
                                    "due_by_datetime": str(comm.due_by_date)
                                    + " "
                                    + str(comm.due_by_time),
                                    "due_by_date": convert_date(comm.due_by_date),
                                    "due_by_time": comm.due_by_time,
                                    "dme_action": comm.dme_action,
                                    "z_createdTimeStamp": comm.z_createdTimeStamp,
                                }
                                return_datas.append(return_data)
                            else:
                                opened_comms_cnt += 1
                        else:
                            if comm.closed:
                                closed_comms_cnt += 1
                            else:
                                opened_comms_cnt += 1

                            return_data = {
                                "b_bookingID_Visual": booking.b_bookingID_Visual,
                                "b_status": booking.b_status,
                                "vx_freight_provider": booking.vx_freight_provider,
                                "puCompany": booking.puCompany,
                                "deToCompanyName": booking.deToCompanyName,
                                "v_FPBookingNumber": booking.v_FPBookingNumber,
                                "id": comm.id,
                                "fk_booking_id": comm.fk_booking_id,
                                "priority_of_log": comm.priority_of_log,
                                "assigned_to": comm.assigned_to,
                                "query": comm.query,
                                "dme_com_title": comm.dme_com_title,
                                "closed": comm.closed,
                                "status_log_closed_time": comm.status_log_closed_time,
                                "dme_detail": comm.dme_detail,
                                "dme_notes_type": comm.dme_notes_type,
                                "dme_notes_external": comm.dme_notes_external,
                                "due_by_datetime": str(comm.due_by_date)
                                + " "
                                + str(comm.due_by_time),
                                "due_by_date": convert_date(comm.due_by_date),
                                "due_by_time": comm.due_by_time,
                                "dme_action": comm.dme_action,
                                "z_createdTimeStamp": comm.z_createdTimeStamp,
                            }
                            return_datas.append(return_data)

            if sort_by_date == "true":
                return_datas = _.sort_by(return_datas, "due_by_date", reverse=True)

            return_datas = _.chain(return_datas).map(lambda x: reverse_date(x)).value()

            return JsonResponse(
                {
                    "comms": return_datas,
                    "cnts": {
                        "opened_cnt": opened_comms_cnt,
                        "closed_cnt": closed_comms_cnt,
                        "all_cnt": all_cnt,
                        "selected_cnt": -1,
                    },
                }
            )
        else:
            comms = Dme_comm_and_task.objects.all()
            bookings = Bookings.objects.all()
            return_datas = []
            closed_comms_cnt = 0
            opened_comms_cnt = 0
            all_cnt = 0

            # Filter on comms
            if sort_type == "comms":
                if sort_field is None:
                    comms = comms.order_by("-id")
                else:
                    comms = comms.order_by(sort_field)

            # Simple search & Column fitler
            if len(simple_search_keyword) > 0:
                new_comms = comms.filter(
                    Q(id__icontains=simple_search_keyword)
                    | Q(priority_of_log__icontains=simple_search_keyword)
                    | Q(assigned_to__icontains=simple_search_keyword)
                    | Q(dme_notes_type__icontains=simple_search_keyword)
                    | Q(query__icontains=simple_search_keyword)
                    | Q(dme_action__icontains=simple_search_keyword)
                    | Q(status_log_closed_time__icontains=simple_search_keyword)
                    | Q(dme_detail__icontains=simple_search_keyword)
                    | Q(dme_notes_external__icontains=simple_search_keyword)
                    | Q(due_by_date__icontains=simple_search_keyword)
                    | Q(due_by_time__icontains=simple_search_keyword)
                )

                if len(new_comms) == 0 and is_booking_filtered == False:
                    comms = []
                elif len(new_comms) > 0:
                    comms = new_comms
            else:
                # Column Comms filter
                try:
                    column_filter = column_filters["id"]
                    comms = comms.filter(id__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["priority_of_log"]
                    comms = comms.filter(priority_of_log__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["assigned_to"]
                    comms = comms.filter(assigned_to__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_notes_type"]
                    comms = comms.filter(dme_notes_type__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["query"]
                    comms = comms.filter(query__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_action"]
                    comms = comms.filter(dme_action__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["status_log_closed_time"]
                    comms = comms.filter(
                        status_log_closed_time__icontains=column_filter
                    )
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_detail"]
                    comms = comms.filter(dme_detail__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["dme_notes_external"]
                    comms = comms.filter(dme_notes_external__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["due_by_date"]
                    comms = comms.filter(due_by_date__icontains=column_filter)
                except KeyError:
                    column_filter = ""
                try:
                    column_filter = column_filters["due_by_time"]
                    comms = comms.filter(due_by_time__icontains=column_filter)
                except KeyError:
                    column_filter = ""

            for comm in comms:
                for booking in bookings:
                    if comm.fk_booking_id == booking.pk_booking_id:
                        all_cnt += 1

                        if (int)(booking.id) == (int)(booking_id):
                            if active_tab_ind == 1:
                                if comm.closed:
                                    closed_comms_cnt += 1
                                else:
                                    opened_comms_cnt += 1

                                    return_data = {
                                        "b_bookingID_Visual": booking.b_bookingID_Visual,
                                        "b_status": booking.b_status,
                                        "vx_freight_provider": booking.vx_freight_provider,
                                        "puCompany": booking.puCompany,
                                        "deToCompanyName": booking.deToCompanyName,
                                        "v_FPBookingNumber": booking.v_FPBookingNumber,
                                        "id": comm.id,
                                        "fk_booking_id": comm.fk_booking_id,
                                        "priority_of_log": comm.priority_of_log,
                                        "assigned_to": comm.assigned_to,
                                        "query": comm.query,
                                        "dme_com_title": comm.dme_com_title,
                                        "closed": comm.closed,
                                        "status_log_closed_time": comm.status_log_closed_time,
                                        "dme_detail": comm.dme_detail,
                                        "dme_notes_type": comm.dme_notes_type,
                                        "dme_notes_external": comm.dme_notes_external,
                                        "due_by_datetime": str(comm.due_by_date)
                                        + " "
                                        + str(comm.due_by_time),
                                        "due_by_date": convert_date(comm.due_by_date),
                                        "due_by_time": comm.due_by_time,
                                        "dme_action": comm.dme_action,
                                        "z_createdTimeStamp": comm.z_createdTimeStamp,
                                    }
                                    return_datas.append(return_data)
                            elif active_tab_ind == 2:
                                if comm.closed:
                                    closed_comms_cnt += 1

                                    return_data = {
                                        "b_bookingID_Visual": booking.b_bookingID_Visual,
                                        "b_status": booking.b_status,
                                        "vx_freight_provider": booking.vx_freight_provider,
                                        "puCompany": booking.puCompany,
                                        "deToCompanyName": booking.deToCompanyName,
                                        "v_FPBookingNumber": booking.v_FPBookingNumber,
                                        "id": comm.id,
                                        "fk_booking_id": comm.fk_booking_id,
                                        "priority_of_log": comm.priority_of_log,
                                        "assigned_to": comm.assigned_to,
                                        "query": comm.query,
                                        "dme_com_title": comm.dme_com_title,
                                        "closed": comm.closed,
                                        "status_log_closed_time": comm.status_log_closed_time,
                                        "dme_detail": comm.dme_detail,
                                        "dme_notes_type": comm.dme_notes_type,
                                        "dme_notes_external": comm.dme_notes_external,
                                        "due_by_datetime": str(comm.due_by_date)
                                        + " "
                                        + str(comm.due_by_time),
                                        "due_by_date": convert_date(comm.due_by_date),
                                        "due_by_time": comm.due_by_time,
                                        "dme_action": comm.dme_action,
                                        "z_createdTimeStamp": comm.z_createdTimeStamp,
                                    }
                                    return_datas.append(return_data)
                                else:
                                    opened_comms_cnt += 1
                            else:
                                if comm.closed:
                                    closed_comms_cnt += 1
                                else:
                                    opened_comms_cnt += 1

                                return_data = {
                                    "b_bookingID_Visual": booking.b_bookingID_Visual,
                                    "b_status": booking.b_status,
                                    "vx_freight_provider": booking.vx_freight_provider,
                                    "puCompany": booking.puCompany,
                                    "deToCompanyName": booking.deToCompanyName,
                                    "v_FPBookingNumber": booking.v_FPBookingNumber,
                                    "id": comm.id,
                                    "fk_booking_id": comm.fk_booking_id,
                                    "priority_of_log": comm.priority_of_log,
                                    "assigned_to": comm.assigned_to,
                                    "query": comm.query,
                                    "dme_com_title": comm.dme_com_title,
                                    "closed": comm.closed,
                                    "status_log_closed_time": comm.status_log_closed_time,
                                    "dme_detail": comm.dme_detail,
                                    "dme_notes_type": comm.dme_notes_type,
                                    "dme_notes_external": comm.dme_notes_external,
                                    "due_by_datetime": str(comm.due_by_date)
                                    + " "
                                    + str(comm.due_by_time),
                                    "due_by_date": convert_date(comm.due_by_date),
                                    "due_by_time": comm.due_by_time,
                                    "dme_action": comm.dme_action,
                                    "z_createdTimeStamp": comm.z_createdTimeStamp,
                                }
                                return_datas.append(return_data)

            if sort_by_date == "true":
                return_datas = _.sort_by(return_datas, "due_by_date", reverse=True)

            return_datas = _.chain(return_datas).map(lambda x: reverse_date(x)).value()

            return JsonResponse(
                {
                    "comms": return_datas,
                    "cnts": {
                        "opened_cnt": opened_comms_cnt,
                        "closed_cnt": closed_comms_cnt,
                        "all_cnt": all_cnt,
                        "selected_cnt": -1,
                    },
                }
            )

    @action(detail=True, methods=["put"])
    def update_comm(self, request, pk, format=None):
        dme_comm_and_task = Dme_comm_and_task.objects.get(pk=pk)

        if (
            dme_comm_and_task.closed != request.data["closed"]
            and request.data["closed"]
        ):
            request.data["status_log_closed_time"] = datetime.now()
        elif (
            dme_comm_and_task.closed != request.data["closed"]
            and not request.data["closed"]
        ):
            request.data["status_log_closed_time"] = None

        serializer = CommSerializer(dme_comm_and_task, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def create_comm(self, request, pk=None):
        if request.data["closed"]:
            request.data["status_log_closed_time"] = datetime.now()
        serializer = CommSerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                new_note_data = {
                    "comm": serializer.data["id"],
                    "dme_notes": request.data["dme_notes"],
                    "dme_notes_type": request.data["notes_type"],
                    "note_date_updated": request.data["due_by_date"],
                    "note_time_updated": request.data["due_by_time"],
                    "dme_notes_no": 1,
                    "username": "Stephen",
                }
                note_serializer = NoteSerializer(data=new_note_data)

                try:
                    if note_serializer.is_valid():
                        note_serializer.save()
                    else:
                        return Response(
                            note_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                        )
                except Exception as e:
                    # print('Exception 01: ', e)
                    return Response(
                        note_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception 02: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def get_available_creators(self, request, pk=None):
        users = User.objects.all()
        creators = []

        for user in users:
            user_permission = UserPermissions.objects.filter(user_id=user.id).first()
            if user_permission and user_permission.can_create_comm:
                creators.append(
                    {
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    }
                )

        return JsonResponse({"creators": creators})

    @action(detail=True, methods=["delete"])
    def delete_comm(self, request, pk, format=None):
        comm = Dme_comm_and_task.objects.get(pk=pk)

        try:
            notes = Dme_comm_notes.objects.filter(comm=comm)

            for note in notes:
                note.delete()

            comm.delete()
            return JsonResponse({"status": "Successfully deleted a comm"})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({"error": "Can not delete Comm"})


class NotesViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_notes(self, request, pk=None):
        user_id = self.request.user.id
        comm_id = self.request.GET["commId"]

        # print('@20 - comm_id: ', comm_id)

        notes = Dme_comm_notes.objects.filter(comm_id=comm_id).order_by("-id")

        return_datas = []
        if len(notes) == 0:
            return JsonResponse({"notes": []})
        else:
            for note in notes:
                return_data = {
                    "id": note.id,
                    "username": note.username,
                    "dme_notes": note.dme_notes,
                    "dme_notes_type": note.dme_notes_type,
                    "dme_notes_no": note.dme_notes_no,
                    "note_date_created": note.note_date_created,
                    "note_date_updated": note.note_date_updated,
                    "note_time_created": note.note_time_created,
                    "note_time_updated": note.note_time_updated,
                }
                return_datas.append(return_data)
            return JsonResponse({"notes": return_datas})

    @action(detail=True, methods=["put"])
    def update_note(self, request, pk, format=None):
        dme_comm_note = Dme_comm_notes.objects.get(pk=pk)
        serializer = NoteSerializer(dme_comm_note, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def create_note(self, request, pk=None):
        serializer = NoteSerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"])
    def delete_note(self, request, pk, format=None):
        note = Dme_comm_notes.objects.get(pk=pk)

        try:
            note.delete()
            return JsonResponse({"status": "Successfully deleted a note"})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({"error": "Can not delete Note"})


class PackageTypesViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_packagetypes(self, request, pk=None):
        packageTypes = Dme_package_types.objects.all()

        return_datas = []
        if len(packageTypes) == 0:
            return JsonResponse({"packageTypes": []})
        else:
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
        dme_employee = (
            DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )

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
        if len(all_booking_status) == 0:
            return JsonResponse({"all_booking_status": []})
        else:
            for booking_status in all_booking_status:
                return_data = {
                    "id": booking_status.id,
                    "dme_delivery_status": booking_status.dme_delivery_status,
                }
                return_datas.append(return_data)
            return JsonResponse({"all_booking_status": return_datas})


class StatusHistoryViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        pk_booking_id = self.request.GET.get("pk_booking_id")
        return_data = []

        try:
            resultObjects = []
            resultObjects = (
                Dme_status_history.objects.select_related()
                .filter(fk_booking_id=pk_booking_id)
                .order_by("-id")
            )
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "notes": resultObject.notes,
                        "status_last": resultObject.status_last,
                        "event_time_stamp": resultObject.event_time_stamp,
                        "dme_notes": resultObject.dme_notes,
                        "z_createdTimeStamp": resultObject.z_createdTimeStamp,
                        "dme_status_detail": resultObject.dme_status_detail,
                        "dme_status_action": resultObject.dme_status_action,
                        "dme_status_linked_reference_from_fp": resultObject.dme_status_linked_reference_from_fp,
                    }
                )
            return JsonResponse({"history": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"history": ""})

    @action(detail=False, methods=["post"])
    def save_status_history(self, request, pk=None):
        serializer = StatusHistorySerializer(data=request.data)

        try:
            if serializer.is_valid():
                booking = Bookings.objects.get(
                    pk_booking_id=request.data["fk_booking_id"]
                )

                if request.data["status_last"] == "In Transit":
                    calc_collect_after_status_change(
                        request.data["fk_booking_id"], request.data["status_last"]
                    )
                elif request.data["status_last"] == "Delivered":
                    booking.z_api_issue_update_flag_500 = 0
                    booking.delivery_booking = datetime.now()
                    booking.save()

                tempo.push_via_api(booking)
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["put"])
    def update_status_history(self, request, pk, format=None):
        status_history = Dme_status_history.objects.get(pk=pk)
        serializer = StatusHistorySerializer(status_history, data=request.data)

        try:
            if serializer.is_valid():
                if request.data["status_last"] == "In Transit":
                    calc_collect_after_status_change(
                        request.data["fk_booking_id"], request.data["status_last"]
                    )
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FPViewSet(viewsets.ViewSet):
    serializer_class = FpSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Fp_freight_providers.objects.all().order_by(
                "fp_company_name"
            )
            for resultObject in resultObjects:
                if not resultObject.fp_inactive_date:
                    return_data.append(
                        {
                            "id": resultObject.id,
                            "fp_company_name": resultObject.fp_company_name,
                            "fp_address_country": resultObject.fp_address_country,
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
        return_data = []

        try:
            resultObjects = []
            resultObjects = Fp_freight_providers.objects.create(
                fp_company_name=request.data["fp_company_name"],
                fp_address_country=request.data["fp_address_country"],
            )

            return JsonResponse({"results": resultObjects})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

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
                        "z_downloadedByAccount": resultObject.z_downloadedByAccount,
                        "z_downloadedTimeStamp": resultObject.z_downloadedTimeStamp,
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
                    "z_downloadedByAccount": resultObject.z_downloadedByAccount,
                    "z_downloadedTimeStamp": resultObject.z_downloadedTimeStamp,
                }
            )
            return JsonResponse({"results": return_data})
        except Exception as e:
            print("@Exception", e)
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
    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = DME_Options.objects.all()
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "option_name": resultObject.option_name,
                        "option_value": resultObject.option_value,
                        "option_description": resultObject.option_description,
                        "option_schedule": resultObject.option_schedule,
                        "start_time": resultObject.start_time,
                        "end_time": resultObject.end_time,
                        "start_count": resultObject.start_count,
                        "end_count": resultObject.end_count,
                        "elapsed_seconds": resultObject.elapsed_seconds,
                        "is_running": resultObject.is_running,
                        "z_createdByAccount": resultObject.z_createdByAccount,
                        "z_createdTimeStamp": resultObject.z_createdTimeStamp,
                        "z_downloadedByAccount": resultObject.z_downloadedByAccount,
                        "z_downloadedTimeStamp": resultObject.z_downloadedTimeStamp,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"error": str(e)})

    @action(detail=True, methods=["put"])
    def edit(self, request, pk, format=None):
        dme_options = DME_Options.objects.get(pk=pk)
        serializer = OptionsSerializer(dme_options, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
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
        dme_employee = (
            DME_employees.objects.select_related()
            .filter(fk_id_user=request.user.id)
            .first()
        )

        if dme_employee is not None:
            user_type = "DME"
            fields_to_exclude = []
        else:
            user_type = "CLIENT"
            fields_to_exclude = ["fee", "mu_percentage_fuel_levy"]

        fk_booking_id = request.GET["fk_booking_id"]
        queryset = (
            API_booking_quotes.objects.filter(fk_booking_id=fk_booking_id)
            .exclude(service_name="Air Freight")
            .order_by("client_mu_1_minimum_values")
        )
        serializer = ApiBookingQuotesSerializer(
            queryset, many=True, fields_to_exclude=fields_to_exclude
        )
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
def download(request):
    body = literal_eval(request.body.decode("utf8"))
    download_option = body["downloadOption"]
    file_paths = []

    if download_option == "pricing-only":
        file_name = body["fileName"]
    elif download_option == "manifest":
        z_manifest_url = body["z_manifest_url"]
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
    elif download_option == "label":
        if booking.z_label_url and len(booking.z_label_url) > 0:
            file_paths.append(f"{settings.STATIC_PUBLIC}/pdfs/{booking.z_label_url}")
            booking.z_downloaded_shipping_label_timestamp = datetime.now()
            booking.save()
    elif download_option == "manifest":
        file_paths.appned(f"{settings.STATIC_PUBLIC}/pdfs/{z_manifest_url}")
    elif download_option == "pod":
        if booking.z_pod_url is not None and len(booking.z_pod_url) > 0:
            file_paths.append(f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_url}")
            booking.z_downloaded_pod_timestamp = timezone.now()
            booking.save()
    elif download_option == "pod_sog":
        if booking.z_pod_signed_url and len(booking.z_pod_signed_url) > 0:
            file_paths.append(
                f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_signed_url}"
            )
            booking.z_downloaded_pod_sog_timestamp = timezone.now()
            booking.save()
    elif download_option == "new_pod":
        if booking.z_downloaded_pod_timestamp is None:
            if booking.z_pod_url and len(booking.z_pod_url) > 0:
                file_paths.append(f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_url}")
                booking.z_downloaded_pod_timestamp = timezone.now()
                booking.save()
    elif download_option == "new_pod_sog":
        if booking.z_downloaded_pod_sog_timestamp is None:
            if booking.z_pod_signed_url and len(booking.z_pod_signed_url) > 0:
                file_paths.append(
                    f"{settings.STATIC_PUBLIC}/imgs/{booking.z_pod_signed_url}"
                )
                booking.z_downloaded_pod_sog_timestamp = timezone.now()
                booking.save()
    elif download_option == "connote":
        if booking.z_connote_url and len(booking.z_connote_url) is not 0:
            file_paths.append(
                f"{settings.STATIC_PRIVATE}/connotes/" + booking.z_connote_url
            )
            booking.z_downloaded_connote_timestamp = timezone.now()
            booking.save()
    elif download_option == "new_connote":
        if booking.z_downloaded_pod_timestamp is None:
            if booking.z_connote_url and len(booking.z_connote_url) > 0:
                file_paths.append(
                    f"{settings.STATIC_PRIVATE}/connotes/" + booking.z_connote_url
                )
                booking.z_downloaded_connote_timestamp = timezone.now()
                booking.save()
    elif download_option == "label_and_connote":
        if booking.z_connote_url and len(booking.z_connote_url) > 0:
            file_paths.append(
                f"{settings.STATIC_PRIVATE}/connotes/" + booking.z_connote_url
            )
            booking.z_downloaded_connote_timestamp = timezone.now()
            booking.save()
        if booking.z_label_url and len(booking.z_label_url) > 0:
            file_paths.append(f"{settings.STATIC_PUBLIC}/pdfs/{booking.z_label_url}")
            booking.z_downloaded_shipping_label_timestamp = timezone.now()
            booking.save()

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
    elif file_option in ["pricing-only"]:
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

    return JsonResponse(
        {
            "filename": file_name,
            "status": "success",
            "message": "Deleted successfully!",
        },
        status=200,
    )


@api_view(["POST"])
@permission_classes((AllowAny,))
def generate_csv(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body.get("vx_freight_provider", None)
    file_paths = []
    label_names = []

    if len(booking_ids) == 0:
        return JsonResponse(
            {"filename": "", "status": "No bookings to build CSV"}, status=400
        )

    if not vx_freight_provider:
        vx_freight_provider = Bookings.objects.get(
            id=booking_ids[0]
        ).vx_freight_provider

    has_error = _generate_csv(booking_ids, vx_freight_provider.lower())

    if has_error:
        return JsonResponse({"status": "Failed to create CSV"}, status=400)
    else:
        for booking_id in booking_ids:
            booking = Bookings.objects.get(id=booking_id)

            if vx_freight_provider.lower() == "cope":
                ############################################################################################
                # This is a comment this is what I did and why to make this happen 05/09/2019 pete walbolt #
                ############################################################################################
                booking.b_dateBookedDate = get_sydney_now_time()
                status_history.create(booking, "Booked", request.user.username)
                booking.b_status = "Booked"
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
            elif vx_freight_provider == "dhl":
                booking.b_dateBookedDate = get_sydney_now_time()
                status_history.create(booking, "Booked", request.user.username)
                booking.b_status = "Booked"
                booking.save()

        return JsonResponse({"status": "Created CSV successfully"}, status=200)


@api_view(["POST"])
@permission_classes((AllowAny,))
def generate_xml(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body["vx_freight_provider"]

    if len(booking_ids) == 0:
        return JsonResponse(
            {"success": "success", "status": "No bookings to build XML"}
        )

    try:
        booked_list = build_xml(booking_ids, vx_freight_provider, 1)

        if len(booked_list) == 0:
            return JsonResponse({"success": "success"})
        else:
            return JsonResponse(
                {"error": "Found set has booked bookings", "booked_list": booked_list}
            )
    except Exception as e:
        # print('generate_xml error: ', e)
        return JsonResponse({"error": "error"})


@api_view(["POST"])
@permission_classes((AllowAny,))
def generate_manifest(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body["vx_freight_provider"]
    user_name = body["username"]

    try:
        filenames = build_manifest(booking_ids, vx_freight_provider, user_name)
        file_paths = []

        if vx_freight_provider.upper() == "TASFR":
            for filename in filenames:
                file_paths.append(f"{settings.STATIC_PUBLIC}/pdfs/tas_au/{filename}")
        elif vx_freight_provider.upper() == "DHL":
            for filename in filenames:
                file_paths.append(f"{settings.STATIC_PUBLIC}/pdfs/dhl_au/{filename}")

        zip_subdir = "manifest_files"
        zip_filename = "%s.zip" % zip_subdir

        s = io.BytesIO()
        zf = zipfile.ZipFile(s, "w")

        for index, filename in enumerate(filenames):
            zip_path = os.path.join(zip_subdir, file_paths[index])
            zf.write(file_paths[index], "manifest_files/" + filename)
        zf.close()

        response = HttpResponse(s.getvalue(), "application/x-zip-compressed")
        response["Content-Disposition"] = "attachment; filename=%s" % zip_filename
        return response
    except Exception as e:
        # print("generate_mainifest error: ", e)
        return JsonResponse({"error": "error"})


@api_view(["POST"])
@permission_classes((AllowAny,))
def generate_pdf(request):
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
        # print('generate_pdf error: ', e)
        return JsonResponse({"error": "error"})


@api_view(["GET"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def getAttachmentsHistory(request):
    fk_booking_id = request.GET.get("fk_booking_id")
    return_data = []

    try:
        resultObjects = []
        resultObjects = Dme_attachments.objects.select_related().filter(
            fk_id_dme_booking=fk_booking_id
        )
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
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
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
            resultObjects = Utl_suburbs.objects.select_related().filter(state=stateName)

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
            resultObjects = Utl_suburbs.objects.select_related().filter(
                postal_code=postalCode
            )

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
    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Utl_sql_queries.objects.all()
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "sql_title": resultObject.sql_title,
                        "sql_query": resultObject.sql_query,
                        "sql_description": resultObject.sql_description,
                        "sql_notes": resultObject.sql_notes,
                        "z_createdByAccount": resultObject.z_createdByAccount,
                        "z_createdTimeStamp": resultObject.z_createdTimeStamp,
                        "z_modifiedByAccount": resultObject.z_modifiedByAccount,
                        "z_modifiedTimeStamp": resultObject.z_modifiedTimeStamp,
                    }
                )
            return JsonResponse({"results": return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": str(e)})

    @action(detail=True, methods=["get"])
    def get(self, request, pk, format=None):
        return_data = []
        try:
            resultObjects = []
            resultObject = Utl_sql_queries.objects.get(pk=pk)

            return_data.append(
                {
                    "id": resultObject.id,
                    "sql_title": resultObject.sql_title,
                    "sql_query": resultObject.sql_query,
                    "sql_description": resultObject.sql_description,
                    "sql_notes": resultObject.sql_notes,
                    "z_createdByAccount": resultObject.z_createdByAccount,
                    "z_createdTimeStamp": resultObject.z_createdTimeStamp,
                    "z_modifiedByAccount": resultObject.z_modifiedByAccount,
                    "z_modifiedTimeStamp": resultObject.z_modifiedTimeStamp,
                }
            )
            return JsonResponse({"results": return_data})
        except Exception as e:
            print("@Exception", e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def add(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Utl_sql_queries.objects.create(
                sql_title=request.data["sql_title"],
                sql_query=request.data["sql_query"],
                sql_description=request.data["sql_description"],
                sql_notes=request.data["sql_notes"],
            )

            return JsonResponse({"results": request.data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": str(e)})

    @action(detail=True, methods=["put"])
    def edit(self, request, pk, format=None):
        data = Utl_sql_queries.objects.get(pk=pk)

        try:
            Utl_sql_queries.objects.filter(pk=pk).update(
                sql_query=request.data["sql_query"],
                sql_description=request.data["sql_description"],
                sql_notes=request.data["sql_notes"],
            )
            return JsonResponse({"results": request.data})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({"results": str(e)})

    @action(detail=True, methods=["delete"])
    def delete(self, request, pk, format=None):
        data = Utl_sql_queries.objects.get(pk=pk)

        try:
            data.delete()
            return JsonResponse({"results": fp_freight_providers})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({"results": ""})

    @action(detail=False, methods=["post"])
    def validate(self, request, pk=None):
        return_data = []
        query_tables = tables_in_query(request.data["sql_query"])
        # return JsonResponse({"results": str(query_tables)})
        if re.search("select", request.data["sql_query"], flags=re.IGNORECASE):
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
                    # print('@Exception', e)
                    return JsonResponse({"error": str(e)})
        else:
            return JsonResponse({"error": "Sorry only SELECT statement allowed"})

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

        if upload_option == "import":
            uploader = request.POST["uploader"]
            file_name = upload_lib.upload_import_file(user_id, file, uploader)
        elif upload_option in ["pod", "label", "attachment"]:
            booking_id = request.POST.get("bookingId", None)
            file_name = upload_lib.upload_attachment_file(
                user_id, file, booking_id, upload_option
            )
        elif upload_option == "pricing-only":
            file_name = upload_lib.upload_pricing_only_file(
                user_id, username, file, upload_option
            )

        return Response(file_name)


class FilesViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        file_type = request.GET["fileType"]
        dme_files = DME_Files.objects.filter(file_type=file_type).order_by(
            "-z_createdTimeStamp"
        )[:50]
        serializer = FilesSerializer(dme_files, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = FilesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VehiclesViewSet(viewsets.ViewSet):
    serializer_class = VehiclesSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = FP_vehicles.objects.all()

            for resultObject in resultObjects:
                fp_freight_provider = Fp_freight_providers.objects.filter(id=resultObject.freight_provider_id).first()
                return_data.append(
                    {
                        "id": resultObject.id,
                        "description": resultObject.description,
                        "dim_UOM": resultObject.dim_UOM,
                        "max_length": resultObject.max_length,
                        "max_width": resultObject.max_width,
                        "max_height": resultObject.max_height,
                        "mass_UOM": resultObject.mass_UOM,
                        "pallets": resultObject.pallets,
                        "pallet_UOM": resultObject.pallet_UOM,
                        "max_pallet_length": resultObject.max_pallet_length,
                        "max_pallet_height": resultObject.max_pallet_height,
                        "base_charge": resultObject.base_charge,
                        "min_charge": resultObject.min_charge,
                        "limited_state": resultObject.limited_state,
                        "freight_provider": fp_freight_provider.fp_company_name,
                        "max_mass": resultObject.max_mass,
                    }
                )

            return JsonResponse({"results": return_data})
        except Exception as e:
            return JsonResponse({"results": str(e)})


class TimingsViewSet(viewsets.ViewSet):
    serializer_class = TimingsSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = FP_timings.objects.all()

            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "time_UOM": resultObject.time_UOM,
                        "min": resultObject.min,
                        "max": resultObject.max,
                        "booking_cut_off_time": resultObject.booking_cut_off_time,
                        "collected_by": resultObject.collected_by,
                        "delivered_by": resultObject.delivered_by,
                    }
                )

            return JsonResponse({"results": return_data})
        except Exception as e:
            return JsonResponse({"results": str(e)})


class AvailabilitiesViewSet(viewsets.ViewSet):
    serializer_class = AvailabilitiesSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = FP_availabilities.objects.all()
            
            for resultObject in resultObjects:
                fp_freight_provider = Fp_freight_providers.objects.filter(id=resultObject.freight_provider_id).first()
                fp_company_name = ""

                if fp_freight_provider is not None:
                    fp_company_name = fp_freight_provider.fp_company_name

                return_data.append(
                    {
                        "id": resultObject.id,
                        "code": resultObject.code,
                        "mon_start": resultObject.mon_start,
                        "mon_end": resultObject.mon_end,
                        "tue_start": resultObject.tue_start,
                        "tue_end": resultObject.tue_end,
                        "wed_start": resultObject.wed_start,
                        "wed_end": resultObject.wed_end,
                        "thu_start": resultObject.thu_start,
                        "thu_end": resultObject.thu_end,
                        "fri_start": resultObject.fri_start,
                        "fri_end": resultObject.fri_end,
                        "sat_start": resultObject.sat_start,
                        "sat_end": resultObject.sat_end,
                        "sun_start": resultObject.sun_start,
                        "sun_end": resultObject.sun_end,
                        "freight_provider": fp_company_name,
                    }
                )

            return JsonResponse({"results": return_data})
        except Exception as e:
            return JsonResponse({"results": str(e)})

class CostsViewSet(viewsets.ViewSet):
    serializer_class = CostsSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = FP_costs.objects.all()
            
            for resultObject in resultObjects:
                return_data.append(
                    {
                        "id": resultObject.id,
                        "UOM_charge": resultObject.UOM_charge,
                        "start_qty": resultObject.start_qty,
                        "end_qty": resultObject.end_qty,
                        "basic_charge": resultObject.basic_charge,
                        "min_charge": resultObject.min_charge,
                        "per_UOM_charge": resultObject.per_UOM_charge,
                        "oversize_premium": resultObject.oversize_premium,
                        "oversize_price": resultObject.oversize_price,
                        "m3_to_kg_factor": resultObject.m3_to_kg_factor,
                        "dim_UOM": resultObject.dim_UOM,
                        "price_up_to_length": resultObject.price_up_to_length,
                        "price_up_to_width": resultObject.price_up_to_width,
                        "price_up_to_height": resultObject.price_up_to_height,
                        "weight_UOM": resultObject.weight_UOM,
                        "price_up_to_weight": resultObject.price_up_to_weight,
                        "max_length": resultObject.max_length,
                        "max_width": resultObject.max_width,
                        "max_height": resultObject.max_height,
                        "max_weight": resultObject.max_weight,
                    }
                )

            return JsonResponse({"results": return_data})
        except Exception as e:
            return JsonResponse({"results": str(e)})


class PricingRulesViewSet(viewsets.ViewSet):
    serializer_class = PricingRulesSerializer

    @action(detail=False, methods=["get"])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = FP_pricing_rules.objects.all()
          

            for resultObject in resultObjects:
                fp_freight_provider = Fp_freight_providers.objects.filter(id=resultObject.freight_provider_id).first()
                fp_company_name = ""

                if fp_freight_provider is not None:
                    fp_company_name = fp_freight_provider.fp_company_name

                return_data.append(
                    {
                        "id": resultObject.id,
                        "service_type": resultObject.service_type,
                        "service_timing_code": resultObject.service_timing_code,
                        "calc_type": resultObject.calc_type,
                        "charge_rule": resultObject.charge_rule,
                        "cost_id": resultObject.cost_id,
                        "timing_id": resultObject.timing_id,
                        "vehicle_id": resultObject.vehicle_id,
                        "both_way": resultObject.both_way,
                        "pu_zone": resultObject.pu_zone,
                        "pu_state": resultObject.pu_state,
                        "pu_postal_code": resultObject.pu_postal_code,
                        "pu_suburb": resultObject.pu_suburb,
                        "de_zone": resultObject.de_zone,
                        "de_state": resultObject.de_state,
                        "de_postal_code": resultObject.de_postal_code,
                        "de_suburb": resultObject.de_suburb,
                        "freight_provider": fp_company_name,
                    }
                )

            return JsonResponse({"results": return_data})
        except Exception as e:
            return JsonResponse({"results": str(e)})
