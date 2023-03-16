import json
import logging
import requests
import threading
from datetime import datetime

from django.conf import settings
from api.common import trace_error
from api.common.build_object import Struct
from api.common.convert_price import interpolate_gaps, apply_markups
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
    HEADER_FOR_NODE,
)
from api.clients.jason_l.operations import get_total_sales, get_value_by_formula
from api.fp_apis.built_in.mrl_sampson import (
    can_use as can_use_mrl_sampson,
    get_value_by_formula as get_price_of_mrl_sampson,
    get_etd_by_formula,
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


def can_use_linehaul(booking):
    if (
        booking.pu_Address_State
        and booking.de_To_Address_State
        and booking.pu_Address_State.lower() == booking.de_To_Address_State.lower()
    ):
        return False

    de_postal = int(booking.de_To_Address_PostalCode or 0)
    pu_state = booking.pu_Address_State
    pu_postal = int(booking.pu_Address_PostalCode or 0)
    pu_suburb = booking.pu_Address_Suburb

    if not de_postal or not pu_postal:
        return False

    # JasonL & BSD
    if (
        booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002"
        or booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8"
    ) and (
        (  # Metro / CBD Melbourne
            de_postal == 3800
            or (de_postal >= 3000 and de_postal <= 3207)
            or (de_postal >= 8000 and de_postal <= 8499)
        )
        or (  # Metro / CBD Brisbane
            (de_postal >= 4000 and de_postal <= 4207)
            or (de_postal >= 9000 and de_postal <= 9499)
        )
        # or (  # Metro Adelaide
        #     (de_postal >= 5000 and de_postal <= 5199)
        #     or (de_postal >= 5900 and de_postal <= 5999)
        # )
    ):
        return True

    # Anchor Packaging
    if booking.kf_client_id == "49294ca3-2adb-4a6e-9c55-9b56c0361953":
        # MD1 (NSW) -> Mel | MD1 (NSW) -> BSD
        if (
            pu_suburb
            and pu_suburb.lower() == "chester hill"
            and (
                (  # Metro / CBD Melbourne
                    de_postal == 3800
                    or (de_postal >= 3000 and de_postal <= 3207)
                    or (de_postal >= 8000 and de_postal <= 8499)
                )
                or (  # Metro / CBD Brisbane
                    (de_postal >= 4000 and de_postal <= 4207)
                    or (de_postal >= 9000 and de_postal <= 9499)
                )
            )
        ):
            return True

        # AFS (VIC) -> Sydney Metro
        if (
            pu_suburb
            and pu_suburb.lower() == "dandenong south"
            and (
                (  # Metro / CBD Sydney
                    (de_postal >= 1000 and de_postal <= 2249)
                    or (de_postal >= 2760 and de_postal <= 2770)
                )
            )
        ):
            return True

        # MD2 (QLD) -> Sydney Metro
        if (
            pu_suburb
            and pu_suburb.lower() == "larapinta"
            and (
                (  # Metro / CBD Sydney
                    (de_postal >= 1000 and de_postal <= 2249)
                    or (de_postal >= 2760 and de_postal <= 2770)
                )
            )
        ):
            return True

    return False


def build_special_fp_pricings(booking, booking_lines, packed_status):
    # Get manually entered surcharges total
    try:
        manual_surcharges_total = booking.get_manual_surcharges_total()
    except:
        manual_surcharges_total = 0

    de_postal_code = int(booking.de_To_Address_PostalCode or 0)
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
        (de_postal_code >= 1000 and de_postal_code <= 2249)
        or (de_postal_code >= 2760 and de_postal_code <= 2770)
    ):
        quote_3 = quote_0
        quote_3.pk = None
        quote_3.freight_provider = "In House Fleet"
        quote_3.service_name = None
        value_by_formula = get_value_by_formula(booking_lines)
        logger.info(f"[In House Fleet] value_by_formula: {value_by_formula}")
        quote_3.client_mu_1_minimum_values = value_by_formula
        quote_3.save()

    # JasonL & BSD & Anchor Packaging
    if (
        booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002"
        or booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8"
        or booking.kf_client_id == "49294ca3-2adb-4a6e-9c55-9b56c0361953"
    ):
        if can_use_linehaul(booking):
            quote_1 = quote_0
            quote_1.freight_provider = "Deliver-ME"
            result = get_self_pricing(quote_1.freight_provider, booking, booking_lines)
            quote_1.fee = result["price"]["inv_cost_quoted"]
            quote_1.client_mu_1_minimum_values = result["price"]["inv_sell_quoted"]
            quote_1.tax_value_5 = result["price"]["inv_dme_quoted"]
            quote_1.service_name = result["price"]["service_name"]
            quote_1.save()

    # Plum & JasonL & BSD & Cadrys & Ariston Wire & Anchor Packaging & Pricing Only
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
        quote_2.service_name = None
        quote_2.freight_provider = "Customer Collect"
        quote_2.tax_value_5 = None
        quote_2.save()

    # Plum & JasonL & BSD
    if (
        booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000004"
        or booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002"
        or booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8"
    ):
        if can_use_mrl_sampson(booking):
            quote_3 = quote_0
            quote_3.pk = None
            quote_3.freight_provider = "MRL Sampson"
            quote_3.service_name = None
            value_by_formula = get_price_of_mrl_sampson(booking, booking_lines)
            logger.info(f"[MRL Sampson] value_by_formula: {value_by_formula}")
            quote_3.fee = value_by_formula
            quote_3.etd = get_etd_by_formula(booking)
            quote_3.save()


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
    logger.info(f"{LOG_ID} {booking_id} {packed_statuses}")

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
        threads = []
        entire_booking_lines = []
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
            #         entire_booking_lines += _booking_lines
            #         build_special_fp_pricings(booking, _booking_lines, packed_status)
            # except Exception as e:
            #     pass

            # Normal Pricings
            _threads = build_threads(
                booking,
                _booking_lines,
                is_pricing_only,
                packed_status,
                pu_zones,
                de_zones,
                client_fps,
            )
            threads += _threads
            entire_booking_lines += _booking_lines
            build_special_fp_pricings(booking, _booking_lines, packed_status)

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # timeout=PRICING_TIME,
        # logger.info(f"#990 [PRICING] - {PRICING_TIME}s Timeout! stop threads! ;)")

        _after_process(
            booking,
            entire_booking_lines,
            is_pricing_only,
            client,
            pu_zones,
            de_zones,
            client_fps,
        )

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


def _after_process(
    booking,
    booking_lines,
    is_pricing_only,
    client,
    pu_zones,
    de_zones,
    client_fps,
):
    # JasonL: update `client sales total`
    if booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002":
        try:
            booking.client_sales_total = get_total_sales(booking.b_client_order_num)
            booking.save()
        except Exception as e:
            logger.error(f"Client sales total: {str(e)}")
            booking.client_sales_total = None
            pass

    quotes = API_booking_quotes.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_used=False
    )
    fp_names = [quote.freight_provider for quote in quotes]
    fps = Fp_freight_providers.objects.filter(fp_company_name__in=fp_names)

    if quotes.exists():
        if client:
            # Interpolate gaps (for Plum client now)
            quotes = interpolate_gaps(quotes, client)

        # Calculate Surcharges
        for quote in quotes:
            _booking_lines = []
            quote_fp = None

            if quote.freight_provider in SPECIAL_FPS:  # skip Special FPs
                continue

            for booking_line in booking_lines:
                if booking_line.packed_status != quote.packed_status:
                    continue
                _booking_lines.append(booking_line)

            if not _booking_lines:
                continue

            for fp in fps:
                if quote.freight_provider.lower() == fp.fp_company_name.lower():
                    quote_fp = fp
                    break

            gen_surcharges(booking, _booking_lines, quote, client, quote_fp, "booking")

            # Confirm visible
            quotes = _confirm_visible(booking, _booking_lines, quotes)

        # Apply Markups (FP Markup and Client Markup)
        de_addr = {
            "state": booking.de_To_Address_State,
            "postal_code": booking.de_To_Address_PostalCode,
            "suburb": booking.de_To_Address_Suburb,
        }
        quotes = apply_markups(quotes, client, fps, client_fps, de_addr)


def build_threads(
    booking,
    booking_lines,
    is_pricing_only,
    packed_status,
    pu_zones,
    de_zones,
    client_fps,
):
    # Schedule n pricing works *concurrently*:
    threads = []
    logger.info(
        f"#910 [PRICING] - Building Pricing threads for [{packed_status.upper()}]"
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
                if _fp_name == "startrack":
                    # Only built-in pricing for Startrack
                    continue
                    # pass

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
                    # if _fp_name == "startrack":
                    #     if not booking.b_client_warehouse_code:
                    #         continue
                    #     elif booking.b_client_warehouse_code != key:
                    #         continue

                    logger.info(f"#905 [PRICING] - {key}")
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
                            thread = threading.Thread(
                                target=_api_pricing_worker_builder,
                                args=(
                                    _fp_name,
                                    booking,
                                    booking_lines,
                                    is_pricing_only,
                                    packed_status,
                                    account_detail,
                                    service.fp_delivery_service_code,
                                    service.fp_delivery_time_description,
                                ),
                            )
                            threads.append(thread)
                    else:
                        thread = threading.Thread(
                            target=_api_pricing_worker_builder,
                            args=(
                                _fp_name,
                                booking,
                                booking_lines,
                                is_pricing_only,
                                packed_status,
                                account_detail,
                            ),
                        )
                        threads.append(thread)

        if _fp_name in BUILT_IN_PRICINGS:
            logger.info(f"#908 [BUILT_IN PRICING] - {_fp_name}")
            thread = threading.Thread(
                target=_built_in_pricing_worker_builder,
                args=(
                    _fp_name,
                    booking,
                    booking_lines,
                    is_pricing_only,
                    packed_status,
                    pu_zones,
                    de_zones,
                ),
            )
            threads.append(thread)

    logger.info("#911 [PRICING] - Pricing workers will start soon")
    return threads
    logger.info("#919 [PRICING] - Pricing workers finished all")


def _api_pricing_worker_builder(
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
        response = requests.post(url, params={}, json=payload, headers=HEADER_FOR_NODE)
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
                context = {"booking": booking}
                serializer = ApiBookingQuotesSerializer(
                    data=parse_result, context=context
                )
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


def _built_in_pricing_worker_builder(
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
            context = {"booking": booking}
            serializer = ApiBookingQuotesSerializer(data=parse_result, context=context)

            if serializer.is_valid():
                serializer.save()
            else:
                logger.info(f"@402 [PRICING] Serializer error: {serializer.errors}")
