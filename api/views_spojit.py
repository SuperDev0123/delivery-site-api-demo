import logging
import requests, json
from datetime import datetime, date, timedelta

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.authentication import TokenAuthentication
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from api.warehouses import index as warehouse
from api.common import trace_error

logger = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([JSONWebTokenAuthentication])
def spojit_push_webhook(request):
    LOG_ID = "[WEBHOOK SPOJIT PUSH]"
    logger.info(f"{LOG_ID} Payload: {request.data}")

    try:
        res_json = warehouse.push_webhook(request.data)
        return JsonResponse({}, status=200)
    except Exception as e:
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"errorCode": "failure", "errorMessage": str(e)}, status=400
        )


@api_view(["POST"])
@authentication_classes([JSONWebTokenAuthentication])
def spojit_scan(request):
    LOG_ID = "[SPOJIT SCAN]"
    logger.info(f"{LOG_ID} Payload: {request.data}")

    try:
        res_json = warehouse.scanned(request.data)
        return JsonResponse(res_json, status=200)
    except Exception as e:
        trace_error.print()
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"errorCode": "failure", "errorMessage": str(e)}, status=400
        )


@api_view(["GET"])
@authentication_classes([JSONWebTokenAuthentication])
def spojit_reprint_label(request):
    LOG_ID = "[SPOJIT REPRINT LABEL]"
    logger.info(f"{LOG_ID} Payload: {request.GET}")

    try:
        res_json = warehouse.reprint_label(request.GET)
        return JsonResponse(res_json, status=200)
    except Exception as e:
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"errorCode": "failure", "errorMessage": str(e)}, status=400
        )


@api_view(["POST"])
@authentication_classes([JSONWebTokenAuthentication])
def spojit_ready(request):
    LOG_ID = "[SPOJIT READY]"
    logger.info(f"{LOG_ID} Payload: {request.POST}")

    try:
        res_json = warehouse.ready(request.data)
        return JsonResponse(res_json, status=200)
    except Exception as e:
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"errorCode": "failure", "errorMessage": str(e)}, status=400
        )


@api_view(["POST"])
@authentication_classes([JSONWebTokenAuthentication])
def spojit_manifest(request):
    LOG_ID = "[SPOJIT MANIFEST]"
    logger.info(f"{LOG_ID} Payload: {request.POST}")

    try:
        res_json = warehouse.manifest(request.data)
        return JsonResponse(res_json, status=200)
    except Exception as e:
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"errorCode": "failure", "errorMessage": str(e)}, status=400
        )
