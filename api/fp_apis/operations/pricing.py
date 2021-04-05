import json
import logging
import asyncio
import requests_async
from datetime import datetime

from django.conf import settings
from api.common import trace_error
from api.common.build_object import Struct
from api.common.convert_price import interpolate_gaps, apply_markups
from api.serializers import ApiBookingQuotesSerializer
from api.models import Bookings, Log, API_booking_quotes, Client_FP, FP_Service_ETDs

from api.fp_apis.operations.common import _set_error
from api.fp_apis.self_pricing import get_pricing as get_self_pricing
from api.fp_apis.response_parser import parse_pricing_response
from api.fp_apis.payload_builder import get_pricing_payload
from api.fp_apis.constants import (
    S3_URL,
    PRICING_TIME,
    FP_CREDENTIALS,
    BUILT_IN_PRICINGS,
    DME_LEVEL_API_URL,
    AVAILABLE_FPS_4_FC,
)


logger = logging.getLogger("dme_api")


def pricing(body, booking_id, is_pricing_only=False):
    """
    @params:
        * is_pricing_only: only get pricing info
    """
    booking_lines = []
    booking = None

    # Only quote
    if is_pricing_only and not booking_id:
        booking = Struct(**body["booking"])

        for booking_line in body["booking_lines"]:
            booking_lines.append(Struct(**booking_line))

    if not is_pricing_only:
        booking = Bookings.objects.filter(id=booking_id).first()

        # Delete all pricing info if exist for this booking
        if booking:
            pk_booking_id = booking.pk_booking_id
            booking.api_booking_quote = None  # Reset pricing relation
            booking.save()
            # DME_Error.objects.filter(fk_booking_id=pk_booking_id).delete()
        else:
            return False, "Booking does not exist", None

    # Set is_used flag for existing old pricings
    if booking.pk_booking_id:
        API_booking_quotes.objects.filter(fk_booking_id=booking.pk_booking_id).update(
            is_used=True
        )

    if not booking.puPickUpAvailFrom_Date:
        error_msg = "PU Available From Date is required."

        if not is_pricing_only:
            _set_error(booking, error_msg)

        return False, error_msg, None

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _pricing_process(booking, booking_lines, is_pricing_only)
        )
    finally:
        loop.close()

    quotes = API_booking_quotes.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_used=False
    )

    if quotes.exists():
        # Interpolate gaps (for Plum client now)
        quotes = interpolate_gaps(quotes)

        # Apply Markups (FP Markup and Client Markup)
        quotes = apply_markups(quotes)

    return booking, True, "Retrieved all Pricing info", quotes


async def _pricing_process(booking, booking_lines, is_pricing_only):
    try:
        await asyncio.wait_for(
            pricing_workers(booking, booking_lines, is_pricing_only),
            timeout=PRICING_TIME,
        )
    except asyncio.TimeoutError:
        logger.info(f"#990 [PRICING] - {PRICING_TIME}s Timeout! stop threads! ;)")


async def pricing_workers(booking, booking_lines, is_pricing_only):
    # Schedule n pricing works *concurrently*:
    _workers = set()
    logger.info("#910 [PRICING] - Building Pricing workers...")

    client_fps = Client_FP.objects.prefetch_related("fp").filter(
        client__company_name__iexact=booking.b_client_name, is_active=True
    )

    if client_fps:
        client_fps = list(client_fps.values_list("fp__fp_company_name", flat=True))
        client_fps = [i.lower() for i in client_fps]
    else:
        client_fps = []

    for fp_name in AVAILABLE_FPS_4_FC:
        _fp_name = fp_name.lower()

        # If not allowed for this Client
        if _fp_name not in client_fps:
            continue

        # If no credential
        if _fp_name not in FP_CREDENTIALS and _fp_name not in BUILT_IN_PRICINGS:
            continue

        if _fp_name == "auspost":
            services = FP_Service_ETDs.objects.filter(
                freight_provider__fp_company_name="AUSPost"
            ).only("fp_delivery_time_description", "fp_delivery_service_code")
            logger.info(f"#904 [PRICING] services: {services}")

        if _fp_name in FP_CREDENTIALS:
            fp_client_names = FP_CREDENTIALS[_fp_name].keys()
            b_client_name = booking.b_client_name.lower()

            for client_name in fp_client_names:
                if client_name == "test":
                    pass
                elif b_client_name in fp_client_names and b_client_name != client_name:
                    continue
                elif (
                    b_client_name not in fp_client_names
                    and client_name not in ["dme", "test"]
                    and not is_pricing_only
                ):
                    continue

                logger.info(f"#905 [PRICING] - {_fp_name}, {client_name}")

                for key in FP_CREDENTIALS[_fp_name][client_name].keys():
                    account_detail = FP_CREDENTIALS[_fp_name][client_name][key]

                    # Allow live pricing credentials only on PROD
                    if settings.ENV == "prod" and "test" in key:
                        continue

                    # Pricing only accounts can be used on pricing_only mode
                    if "pricingOnly" in account_detail and not is_pricing_only:
                        continue

                    logger.info(f"#906 [PRICING] - {_fp_name}, {client_name}")

                    if _fp_name == "auspost" and services:
                        for service in services:
                            _worker = _api_pricing_worker_builder(
                                _fp_name,
                                booking,
                                booking_lines,
                                is_pricing_only,
                                account_detail,
                                service.fp_delivery_service_code,
                                service.fp_delivery_time_description,
                            )
                            _workers.add(_worker)
                    else:
                        _worker = _api_pricing_worker_builder(
                            _fp_name,
                            booking,
                            booking_lines,
                            is_pricing_only,
                            account_detail,
                        )
                        _workers.add(_worker)

        elif _fp_name in BUILT_IN_PRICINGS:
            _worker = _built_in_pricing_worker_builder(_fp_name, booking)
            _workers.add(_worker)

    logger.info("#911 [PRICING] - Pricing workers will start soon")
    await asyncio.gather(*_workers)
    logger.info("#919 [PRICING] - Pricing workers finished all")


async def _api_pricing_worker_builder(
    _fp_name,
    booking,
    booking_lines,
    is_pricing_only,
    account_detail,
    service_code=None,
    service_name=None,
):
    payload = get_pricing_payload(
        booking, _fp_name, account_detail, booking_lines, service_code
    )

    if not payload:
        if is_pricing_only:
            message = f"#907 [PRICING] Failed to build payload - {booking.pk_booking_id}, {_fp_name}"
        else:
            message = f"#907 [PRICING] Failed to build payload - {booking.b_bookingID_Visual}, {_fp_name}"

        logger.info(message)
        return None

    url = DME_LEVEL_API_URL + "/pricing/calculateprice"
    logger.info(f"### [PRICING] ({_fp_name.upper()}) API url: {url}")
    logger.info(f"### [PRICING] ({_fp_name.upper()}) Payload: {payload}")

    try:
        response = await requests_async.post(url, params={}, json=payload)
        logger.info(
            f"### [PRICING] Response ({_fp_name.upper()}): {response.status_code}"
        )
        res_content = response.content.decode("utf8").replace("'", '"')
        json_data = json.loads(res_content)
        s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
        logger.info(f"### [PRICING] Response Detail ({_fp_name.upper()}): {s0}")

        if not is_pricing_only:
            Log.objects.create(
                request_payload=payload,
                request_status="SUCCESS",
                request_type=f"{_fp_name.upper()} PRICING",
                response=res_content,
                fk_booking_id=booking.id,
            )

        parse_results = parse_pricing_response(
            response,
            _fp_name,
            booking,
            False,
            service_name,
            payload["spAccountDetails"]["accountCode"],
        )

        if parse_results and not "error" in parse_results:
            for parse_result in parse_results:
                serializer = ApiBookingQuotesSerializer(data=parse_result)

                if serializer.is_valid():
                    serializer.save()
                else:
                    logger.info(f"@401 [PRICING] Serializer error: {serializer.errors}")
    except Exception as e:
        trace_error.print()
        logger.info(f"@402 [PRICING] Exception: {e}")


async def _built_in_pricing_worker_builder(_fp_name, booking):
    results = get_self_pricing(_fp_name, booking)
    parse_results = parse_pricing_response(results, _fp_name, booking, True)

    for parse_result in parse_results:
        if parse_results and not "error" in parse_results:
            serializer = ApiBookingQuotesSerializer(data=parse_result)

            if serializer.is_valid():
                serializer.save()
            else:
                logger.info(f"@402 [PRICING] Serializer error: {serializer.errors}")
