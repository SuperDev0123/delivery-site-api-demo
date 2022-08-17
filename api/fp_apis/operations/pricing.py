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
    SPECIAL_FPS,
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


def build_special_fp_pricings(booking, booking_lines, packed_status):
    # Get manually entered surcharges total
    try:
        manual_surcharges_total = booking.get_manual_surcharges_total()
    except:
        manual_surcharges_total = 0

    postal_code = int(booking.de_To_Address_PostalCode or 0)
    quote_0 = API_booking_quotes()
    quote_0.api_results_id = ""
    quote_0.fk_booking_id = booking.pk_booking_id
    quote_0.fk_client_id = booking.b_client_name
    quote_0.account_code = None
    quote_0.etd = 3
    quote_0.fee = 0
    quote_0.service_code = None
    quote_0.tax_value_1 = 0
    quote_0.tax_value_1 = 0
    quote_0.client_mu_1_minimum_values = 0
    quote_0.packed_status = packed_status
    quote_0.x_price_surcharge = manual_surcharges_total
    quote_0.mu_percentage_fuel_levy = 0

    # JasonL (SYD - SYD)
    if booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002" and (
        (postal_code >= 1000 and postal_code <= 2249)
        or (postal_code >= 2760 and postal_code <= 2770)
    ):
        quotes = API_booking_quotes.objects.filter(
            fk_booking_id=booking.pk_booking_id,
            is_used=False,
            freight_provider="Century",
        )

        quote_3 = quotes.first() if quotes else quote_0
        quote_3.pk = None
        quote_3.freight_provider = "In House Fleet"
        quote_3.service_name = None

        if quotes:
            quote_3.client_mu_1_minimum_values -= 1
        else:
            quote_3.client_mu_1_minimum_values = 75

        quote_3.save()

    # JasonL & BSD
    if (
        booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002"
        or booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8"
    ):
        # restrict delivery postal code
        if (
            postal_code
            and (
                (  # Metro / CBD Melbourne
                    (postal_code >= 3000 and postal_code <= 3207)
                    or (postal_code >= 8000 and postal_code <= 8499)
                )
                or (  # Metro / CBD Brisbane
                    (postal_code >= 4000 and postal_code <= 4207)
                    or (postal_code >= 9000 and postal_code <= 9499)
                )
                # or (  # Metro Adelaide
                #     (postal_code >= 5000 and postal_code <= 5199)
                #     or (postal_code >= 5900 and postal_code <= 5999)
                # )
            )
            # Restrict same state
            and booking.pu_Address_State
            and booking.de_To_Address_State
            and booking.pu_Address_State.lower() != booking.de_To_Address_State.lower()
        ):
            quote_1 = quote_0
            quote_1.freight_provider = "Deliver-ME"
            result = get_self_pricing(quote_1.freight_provider, booking, booking_lines)
            quote_1.fee = result["price"]["inv_cost_quoted"]
            quote_1.client_mu_1_minimum_values = result["price"]["inv_sell_quoted"]
            quote_1.tax_value_5 = result["price"]["inv_dme_quoted"]
            quote_1.service_name = result["price"]["service_name"]
            quote_1.save()

    # Plum & JasonL & BSD & Cadrys & Ariston Wire & Anchor Packagin & Pricing Only
    if (
        booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000004"
        or booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002"
        or booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8"
        or booking.kf_client_id == "f821586a-d476-434d-a30b-839a04e10115"
        or booking.kf_client_id == "15732b05-d597-419b-8dc5-90e633d9a7e9"
        or booking.kf_client_id == "49294ca3-2adb-4a6e-9c55-9b56c0361953"
        or booking.kf_client_id == "461162D2-90C7-BF4E-A905-0242ac130003"
    ):
        quote_2 = quote_0
        quote_2.pk = None
        quote_2.fee = 0
        quote_2.client_mu_1_minimum_values = 0
        quote_2.freight_provider = "Customer Collect"
        quote_2.tax_value_5 = None
        quote_2.save()


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
    LOG_ID = "[PRICING]"
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
        client_fps = Client_FP.objects.filter(client=client, is_active=True)
    except:
        client = None
        client_fps = []

    try:
        for packed_status in packed_statuses:
            _booking_lines = []
            if not booking_lines:
                _booking_lines = Booking_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id,
                    is_deleted=False,
                    packed_status=packed_status,
                )
            else:
                for booking_line in booking_lines:
                    if booking_line.packed_status != packed_status:
                        continue
                    _booking_lines.append(booking_line)

            if not _booking_lines:
                continue

            # Special Pricings
            # try:
            #     if (
            #         not is_pricing_only
            #         and booking.b_dateBookedDate
            #         and booking.vx_freight_provider == "Deliver-ME"
            #     ):
            #         build_special_fp_pricings(booking, _booking_lines, packed_status)
            # except:
            #     build_special_fp_pricings(booking, _booking_lines, packed_status)
            #     _loop_process(
            #         booking,
            #         _booking_lines,
            #         is_pricing_only,
            #         packed_status,
            #         client,
            #         pu_zones,
            #         de_zones,
            #         client_fps,
            #     )

            # Normal Pricings
            _loop_process(
                booking,
                _booking_lines,
                is_pricing_only,
                packed_status,
                client,
                pu_zones,
                de_zones,
                client_fps,
            )
            build_special_fp_pricings(booking, _booking_lines, packed_status)

        # JasonL + SA -> ignore Allied
        if (
            booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002"
            and booking.de_To_Address_State.upper() == "SA"
        ):
            quotes = API_booking_quotes.objects.filter(
                fk_booking_id=booking.pk_booking_id,
                is_used=False,
                freight_provider="Allied",
            ).update(is_used=True)

        quotes = API_booking_quotes.objects.filter(
            fk_booking_id=booking.pk_booking_id, is_used=False
        ).order_by("client_mu_1_minimum_values")

        return booking, True, "Retrieved all Pricing info", quotes
    except Exception as e:
        trace_error.print()
        logger.error(f"{LOG_ID} Booking: {booking}, Error: {e}")
        return booking, False, str(e), []


def _loop_process(
    booking,
    booking_lines,
    is_pricing_only,
    packed_status,
    client,
    pu_zones,
    de_zones,
    client_fps,
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
                client_fps,
            )
        )
    finally:
        loop.close()

    quotes = API_booking_quotes.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_used=False, packed_status=packed_status
    )
    fp_names = [quote.freight_provider for quote in quotes]
    fps = Fp_freight_providers.objects.filter(fp_company_name__in=fp_names)

    if quotes.exists():
        if client:
            # Interpolate gaps (for Plum client now)
            quotes = interpolate_gaps(quotes, client)

        # Calculate Surcharges
        for quote in quotes:
            if quote.freight_provider in SPECIAL_FPS:  # skip Special FPs
                continue

            for fp in fps:
                if quote.freight_provider.lower() == fp.fp_company_name.lower():
                    quote_fp = fp
                    break

            gen_surcharges(booking, booking_lines, quote, client, quote_fp, "booking")

        # Apply Markups (FP Markup and Client Markup)
        quotes = apply_markups(quotes, client, fps, client_fps)

        # Confirm visible
        quotes = _confirm_visible(booking, booking_lines, quotes)


async def _pricing_process(
    booking,
    booking_lines,
    is_pricing_only,
    packed_status,
    pu_zones,
    de_zones,
    client_fps,
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
                client_fps,
            ),
            timeout=PRICING_TIME,
        )
    except asyncio.TimeoutError:
        logger.info(f"#990 [PRICING] - {PRICING_TIME}s Timeout! stop threads! ;)")


async def pricing_workers(
    booking,
    booking_lines,
    is_pricing_only,
    packed_status,
    pu_zones,
    de_zones,
    client_fps,
):
    # Schedule n pricing works *concurrently*:
    _workers = set()
    logger.info("#910 [PRICING] - Building Pricing workers...")

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
                and booking.vx_freight_provider not in SPECIAL_FPS
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
