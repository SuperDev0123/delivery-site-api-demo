import logging
import json

from django.http import JsonResponse
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes((AllowAny,))
def st_tracking_webhook(request):
    LOG_ID = "[ST TRACK WEBHOOK]"
    logger.info(f"{LOG_ID} Payload: {request.POST}")

    try:
        return JsonResponse({}, status=200)
    except Exception as e:
        logger.error(f"{LOG_ID} Error: {str(e)}")
        return JsonResponse(
            {"errorCode": "failure", "errorMessage": str(e)}, status=400
        )
