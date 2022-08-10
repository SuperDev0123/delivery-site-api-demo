import logging
import traceback

from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.utils import get_m3_to_kg_factor
from api.common.constants import PALLETS, SKIDS

logger = logging.getLogger(__name__)


def get_percentage(vehicle_name):
    if vehicle_name == "DD000068_220602_SYD-BRIS":
        return 0.179232637
    elif vehicle_name == "DD000067_220602_SYD-MEL":
        return 0.364994415
    elif vehicle_name == "DD000066_220531_SYD-BRIS":
        return 0.693141088
    elif vehicle_name == "DD000065_220531_SYD-MEL":
        return 0.490593249
    elif vehicle_name == "DD000064_220526_SYD-BRIS":
        return 0.251430306
    elif vehicle_name == "DD000063_220526_SYD-MEL":
        return 0.479248422
    elif vehicle_name == "DD000062_220524_SYD-BRIS":
        return 0.410106605
    elif vehicle_name == "DD000061_220524_SYD-MEL":
        return 0.429010078
    elif vehicle_name == "DD000060_220519_SYD-BRIS":
        return 0.192198242
    elif vehicle_name == "DD000059_220519_SYD-MEL":
        return 0.243234701
    elif vehicle_name == "DD000058_220517_SYD-BRIS":
        return 0.803339364
    elif vehicle_name == "DD000057_220517_SYD-MEL":
        return 0.519657358
    elif vehicle_name == "DD000056_220512_SYD-BRIS":
        return 0.396012142
    elif vehicle_name == "DD000055_220512_SYD-MEL":
        return 0.912916141
    elif vehicle_name == "DD000054_220510_SYD-BRIS":
        return 0.139105877
    elif vehicle_name == "DD000053_220510_SYD-MEL":
        return 0.538214182
    elif vehicle_name == "DD000052_220506_SYD-BRIS":
        return 0.256985915
    elif vehicle_name == "DD000051_220506_SYD-MEL":
        return 0.37461219
    elif vehicle_name == "DD000050_220504_SYD-BRIS":
        return 0.256810588
    elif vehicle_name == "DD000049_220504_SYD-MEL":
        return 0.449258378
    elif vehicle_name == "DD000085_220624_SYD-ADE":
        return 0.099681156
    elif vehicle_name == "DD000084_220623_SYD-BRIS":
        return 0.122718006
    elif vehicle_name == "DD000083_220623_SYD-MEL":
        return 0.186970204
    elif vehicle_name == "DD000082_220621_SYD-BRIS":
        return 0.30804763
    elif vehicle_name == "DD000081_220621_SYD-MEL":
        return 0.157097135
    elif vehicle_name == "DD000078_22614SYD-BRIS":
        return 0.054553424
    elif vehicle_name == "DD000077_220616_SYD-MEL":
        return 0.395903837
    elif vehicle_name == "DD000076_220614_SYD-BRIS":
        return 0.128757164
    elif vehicle_name == "DD000075_220614_SYD-MEL":
        return 0.36842466
    elif vehicle_name == "DD000073_220609_SYD-BRIS":
        return 0.12467219
    elif vehicle_name == "DD000072_220609_SYD-MEL":
        return 0.324398737
    elif vehicle_name == "DD000071_220607_SYD-BRIS":
        return 0.23483337
    elif vehicle_name == "DD000070_220607_SYD-MEL":
        return 0.658705525
    else:
        return 1


def get_pricing(booking, booking_lines):
    LOG_ID = "[Linehaul Pricing]"
    service_name = None
    postal_code = int(booking.de_To_Address_PostalCode or 0)
    inv_cost_quoted, inv_sell_quoted, inv_dme_quoted = 0, 0, 0
    old_inv_cost_quoted, old_inv_sell_quoted, old_inv_dme_quoted = 0, 0, 0

    for index, line in enumerate(booking_lines):
        is_pallet = (
            line.e_type_of_packaging.upper() in PALLETS
            or line.e_type_of_packaging.upper() in SKIDS
        )
        dim_ratio = _get_dim_amount(line.e_dimUOM)
        length = line.e_dimLength * dim_ratio
        width = line.e_dimWidth * dim_ratio

        # Get Utilised height
        need_update = True
        if not is_pallet:
            need_update = False
        height = line.e_dimHeight * dim_ratio
        if height > 1.4:
            need_update = False
        height = 1.4 if need_update else height

        cubic_meter = get_cubic_meter(
            line.e_dimLength,
            line.e_dimWidth,
            height / dim_ratio,
            line.e_dimUOM,
            1,
        )

        # Set smallert to `length`
        if length > width:
            temp = length
            length = width
            width = temp

        # JasonL
        if booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002":
            # Final Mile Delivery Fee
            fm_fee_cost = 50
            fm_fee_sell = 60

            if (
                "best assembly" in booking.deToCompanyName.lower()
                or "jl fitouts" in booking.deToCompanyName.lower()
                or "steadfast logistics" in booking.deToCompanyName.lower()
            ):
                # The reason is the linehaul delivers to them and we don't deliver to any customer from there.
                # They are the end customer.
                fm_fee_cost = 0
                fm_fee_sell = 0

            if (postal_code >= 3000 and postal_code <= 3207) or (
                postal_code >= 8000 and postal_code <= 8499
            ):  # Melbourne
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (118.06 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (145.83 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (145.83 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (177.08 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (218.75 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (218.75 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (177.08 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (218.75 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (218.75 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (65.88 * cubic_meter + fm_fee_cost) * line.e_qty
                    _value = 18 if 81.38 * cubic_meter < 18 else 81.38 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
            elif (postal_code >= 4000 and postal_code <= 4207) or (
                postal_code >= 9000 and postal_code <= 9499
            ):  # Brisbane
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (187.50 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (222.22 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (222.22 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (281.25 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (444.44 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (444.44 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (281.25 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (444.44 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (444.44 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        104.68 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 165.34 * cubic_meter < 18 else 165.34 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
            elif (postal_code >= 5000 and postal_code <= 5199) or (
                postal_code >= 5900 and postal_code <= 5999
            ):  # Adelaide
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (232.36 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (261.11 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (261.11 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (348.54 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (522.22 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (522.22 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (348.54 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (522.22 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (522.22 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        129.67 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 194.28 * cubic_meter < 18 else 194.28 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty

        # BSD
        elif booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8":
            # Final Mile Delivery Fee
            fm_fee_cost = 55
            fm_fee_sell = 65

            if (postal_code >= 3000 and postal_code <= 3207) or (
                postal_code >= 8000 and postal_code <= 8499
            ):  # Melbourne
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (118.06 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (152.78 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (152.78 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (177.08 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (229.17 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (229.17 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (177.08 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (229.17 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (229.17 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        65.88 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 85.26 * cubic_meter < 18 else 85.26 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
            elif (postal_code >= 4000 and postal_code <= 4207) or (
                postal_code >= 9000 and postal_code <= 9499
            ):  # Brisbane
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (177.08 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (222.22 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (222.22 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (265.63 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (444.44 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (444.44 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (265.63 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (444.44 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (444.44 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        98.32 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 165.34 * cubic_meter < 18 else 165.34 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
            elif (postal_code >= 5000 and postal_code <= 5199) or (
                postal_code >= 5900 and postal_code <= 5999
            ):  # Adelaide
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (232.36 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (265.56 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (265.56 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (348.54 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (531.11 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (531.11 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (348.54 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (531.11 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (531.11 - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        129.67 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 197.59 * cubic_meter < 18 else 197.59 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / get_percentage(booking.b_booking_project)
                        + fm_fee_sell
                    ) * line.e_qty

        is_big_item = length > 1.2 or width > 1.2 or height > 1.4
        logger.info(f"{LOG_ID} Is Big Item: {is_big_item}")
        if fm_fee_cost > 0 and (
            is_big_item
            or (booking.de_no_of_assists and int(booking.de_no_of_assists) > 1)
        ):
            inv_cost_quoted += 25 * line.e_qty
            inv_sell_quoted += 30 * line.e_qty

        if booking.pu_no_of_assists and int(booking.pu_no_of_assists) > 1:
            inv_cost_quoted += 25 * line.e_qty
            inv_sell_quoted += 30 * line.e_qty

        # Logs
        net_inv_cost_quoted = inv_cost_quoted - old_inv_cost_quoted
        net_inv_sell_quoted = inv_sell_quoted - old_inv_sell_quoted

        try:
            logger.info(
                f"{LOG_ID} {booking.b_bookingID_Visual} ({booking.b_client_name})"
            )
        except:
            logger.info(f"{LOG_ID} {booking.pk_booking_id}")

            logger.info(f"{LOG_ID} Case: {case}, Final mile fee: {fm_fee_sell}")
            logger.info(f"{LOG_ID} {length} {width} {height} {cubic_meter}")
            logger.info(
                f"{LOG_ID} index: {index + 1}/{len(booking_lines)} cost: {net_inv_cost_quoted} sell: {net_inv_sell_quoted}"
            )
        old_inv_cost_quoted = inv_cost_quoted
        old_inv_sell_quoted = inv_sell_quoted

    logger.info(f"{LOG_ID} Total cost: {inv_cost_quoted} Total sell: {inv_sell_quoted}")
    return {
        "inv_cost_quoted": inv_cost_quoted,
        "inv_sell_quoted": inv_sell_quoted,
        "inv_dme_quoted": inv_dme_quoted,
        "service_name": service_name,
    }
