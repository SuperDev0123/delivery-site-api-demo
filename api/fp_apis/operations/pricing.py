import json
import logging
import asyncio
import requests_async
from datetime import datetime

from django.conf import settings
from api.common import trace_error
from api.common.build_object import Struct
from api.common.convert_price import interpolate_gaps, apply_markups
from api.common.booking_quote import set_booking_quote
from api.serializers import ApiBookingQuotesSerializer
from api.models import (
    Bookings,
    Booking_lines,
    Log,
    API_booking_quotes,
    Client_FP,
    FP_Service_ETDs,
    Surcharge,
    DME_clients,
    Fp_freight_providers,
)

from api.fp_apis.operations.common import _set_error
from api.fp_apis.operations.surcharge.index import gen_surcharges
from api.fp_apis.built_in.index import get_pricing as get_self_pricing
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
from api.fp_apis.utils import _convert_UOM


logger = logging.getLogger(__name__)


def _confirm_visible(booking, booking_lines, quotes):
    """
    `Allied` - if DE address_type is `residential` and 2+ Line dim is over 1.2m, then hide it
    """
    for quote in quotes:
        if (
            quote.freight_provider == "Allied"
            and booking.pu_Address_Type == "residential"
        ):
            for line in booking_lines:
                width = _convert_UOM(
                    line.e_dimWidth,
                    line.e_dimUOM,
                    "dim",
                    quote.freight_provider.lower(),
                )
                height = _convert_UOM(
                    line.e_dimHeight,
                    line.e_dimUOM,
                    "dim",
                    quote.freight_provider.lower(),
                )
                length = _convert_UOM(
                    line.e_dimLength,
                    line.e_dimUOM,
                    "dim",
                    quote.freight_provider.lower(),
                )

                if (
                    (width > 120 and height > 120)
                    or (width > 120 and length > 120)
                    or (height > 120 and length > 120)
                ):
                    quote.is_used = True
                    quote.save()
                    return quotes.filter(is_used=False)

    return quotes


def pricing(
    body,
    booking_id,
    is_pricing_only=False,
    packed_statuses=[Booking_lines.ORIGINAL],
    pu_zones=[],
    de_zones=[],
):
    """
    @params:
        * is_pricing_only: only get pricing info
        * packed_statuses: array of options (ORIGINAL, AUTO_PACKED, MANUAL_PACKED, SCANNED_PACKED)
    """
    booking_lines = []
    booking = None

    # Only quote
    if is_pricing_only and not booking_id:
        booking = Struct(**body["booking"])

        for booking_line in body["booking_lines"]:
            booking_lines.append(Struct(**booking_line))

    if not is_pricing_only:
        booking = Bookings.objects.filter(id=booking_id).order_by("id").first()

        if not booking:
            return None, False, "Booking does not exist", None

        # Delete all pricing info if exist for this booking
        pk_booking_id = booking.pk_booking_id
        # set_booking_quote(booking, None)
        # DME_Error.objects.filter(fk_booking_id=pk_booking_id).delete()

    if not booking.puPickUpAvailFrom_Date:
        error_msg = "PU Available From Date is required."

        if not is_pricing_only:
            _set_error(booking, error_msg)

        return None, False, error_msg, None

    # Set is_used flag for existing old pricings
    if booking.pk_booking_id:
        API_booking_quotes.objects.filter(
            fk_booking_id=booking.pk_booking_id,
            is_used=False,
            packed_status__in=packed_statuses,
        ).update(is_used=True)

    try:
        client = DME_clients.objects.get(company_name__iexact=booking.b_client_name)
    except:
        client = None

    if not booking_lines:
        for packed_status in packed_statuses:
            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id,
                is_deleted=False,
                packed_status=packed_status,
            )

            if booking_lines:
                _loop_process(
                    booking,
                    booking_lines,
                    is_pricing_only,
                    packed_status,
                    client,
                    pu_zones,
                    de_zones,
                )
    else:
        for packed_status in packed_statuses:
            _loop_process(
                booking,
                booking_lines,
                is_pricing_only,
                packed_status,
                client,
                pu_zones,
                de_zones,
            )

    quotes = API_booking_quotes.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_used=False
    )

    return booking, True, "Retrieved all Pricing info", quotes


def _loop_process(
    booking, booking_lines, is_pricing_only, packed_status, client, pu_zones, de_zones
):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _pricing_process(
                booking,
                booking_lines,
                is_pricing_only,
                packed_status,
                pu_zones,
                de_zones,
            )
        )
    finally:
        loop.close()

    quotes = API_booking_quotes.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_used=False, packed_status=packed_status
    )
    fp_names = [quote.freight_provider for quote in quotes]
    fps = Fp_freight_providers.objects.filter(fp_company_name__in=fp_names)
    print("@0 - ", fp_names, fps)

    if quotes.exists():
        if client:
            # Interpolate gaps (for Plum client now)
            quotes = interpolate_gaps(quotes, client)

        # Calculate Surcharges
        for quote in quotes:
            print("@1 - ", quote.freight_provider)
            for fp in fps:
                if quote.freight_provider == fp.fp_company_name:
                    quote_fp = fp

            gen_surcharges(booking, booking_lines, quote, client, quote_fp, "booking")

        # Apply Markups (FP Markup and Client Markup)
        quotes = apply_markups(quotes, client, fp)

        # Confirm visible
        quotes = _confirm_visible(booking, booking_lines, quotes)


async def _pricing_process(
    booking, booking_lines, is_pricing_only, packed_status, pu_zones, de_zones
):
    try:
        await asyncio.wait_for(
            pricing_workers(
                booking,
                booking_lines,
                is_pricing_only,
                packed_status,
                pu_zones,
                de_zones,
            ),
            timeout=PRICING_TIME,
        )
    except asyncio.TimeoutError:
        logger.info(f"#990 [PRICING] - {PRICING_TIME}s Timeout! stop threads! ;)")


async def pricing_workers(
    booking, booking_lines, is_pricing_only, packed_status, pu_zones, de_zones
):
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

        try:
            if (
                booking.b_dateBookedDate
                and booking.vx_freight_provider.lower() != _fp_name
            ):
                continue
        except:
            pass

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
                elif b_client_name not in fp_client_names and client_name not in [
                    "dme",
                    "test",
                ]:
                    continue

                logger.info(f"#905 [PRICING] - {_fp_name}, {client_name}")

                for key in FP_CREDENTIALS[_fp_name][client_name].keys():
                    account_detail = FP_CREDENTIALS[_fp_name][client_name][key]

                    # Allow live pricing credentials only on PROD
                    if settings.ENV == "prod" and "test" in key:
                        continue

                    # Allow test credential only Sendle+DEV
                    if (
                        settings.ENV == "dev"
                        and _fp_name == "sendle"
                        and "dme" == client_name
                    ):
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
                                packed_status,
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
                            packed_status,
                            account_detail,
                        )
                        _workers.add(_worker)

        if _fp_name in BUILT_IN_PRICINGS:
            logger.info(f"#908 [BUILT_IN PRICING] - {_fp_name}")
            _worker = _built_in_pricing_worker_builder(
                _fp_name,
                booking,
                booking_lines,
                is_pricing_only,
                packed_status,
                pu_zones,
                de_zones,
            )
            _workers.add(_worker)

    logger.info("#911 [PRICING] - Pricing workers will start soon")
    await asyncio.gather(*_workers)
    logger.info("#919 [PRICING] - Pricing workers finished all")


async def _api_pricing_worker_builder(
    _fp_name,
    booking,
    booking_lines,
    is_pricing_only,
    packed_status,
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
                # We do not get surcharges from Allied api
                # # Allied surcharges
                # surcharges = []

                # if (
                #     parse_result["freight_provider"].lower() == "allied"
                #     and "surcharges" in parse_result
                # ):
                #     surcharges = parse_result["surcharges"]
                #     del parse_result["surcharges"]

                parse_result["packed_status"] = packed_status
                serializer = ApiBookingQuotesSerializer(data=parse_result)
                if serializer.is_valid():
                    quote = serializer.save()

                    # We do not get surcharges from Allied api
                    # for surcharge in surcharges:
                    #     if float(surcharge["amount"]) > 0:
                    #         surcharge_obj = Surcharge()
                    #         surcharge_obj.name = surcharge["name"]
                    #         surcharge_obj.description = surcharge["description"]
                    #         surcharge_obj.amount = float(surcharge["amount"])
                    #         surcharge_obj.quote = quote
                    #         surcharge_obj.fp_id = 2  # Allied(Hardcode)
                    #         surcharge_obj.save()
                else:
                    logger.info(f"@401 [PRICING] Serializer error: {serializer.errors}")
    except Exception as e:
        trace_error.print()
        logger.info(f"@402 [PRICING] Exception: {str(e)}")


async def _built_in_pricing_worker_builder(
    _fp_name,
    booking,
    booking_lines,
    is_pricing_only,
    packed_status,
    pu_zones,
    de_zones,
):
    results = get_self_pricing(
        _fp_name, booking, booking_lines, is_pricing_only, pu_zones, de_zones
    )
    logger.info(
        f"#909 [BUILT_IN PRICING] - {_fp_name}, Result cnt: {len(results['price'])}, Results: {results['price']}"
    )
    parse_results = parse_pricing_response(results, _fp_name, booking, True, None)

    for parse_result in parse_results:
        if parse_results and not "error" in parse_results:
            parse_result["packed_status"] = packed_status
            serializer = ApiBookingQuotesSerializer(data=parse_result)

            if serializer.is_valid():
                serializer.save()
            else:
                logger.info(f"@402 [PRICING] Serializer error: {serializer.errors}")
