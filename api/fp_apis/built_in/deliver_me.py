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
    elif vehicle_name == "DD000107_220802_SYD-MEL":
        return 0.026420593
    elif vehicle_name == "DD000094_220707_SYD-BRIS":
        return 0.234069937
    if vehicle_name == "DD000106_220802_SYD-BRIS":
        return 0.408608548
    if vehicle_name == "DD000107_220802_SYD-MEL":
        return 0.495228266
    if vehicle_name == "DD000108_220804_SYD-BRIS":
        return 0.242411365
    if vehicle_name == "DD000109_220804_SYD-MEL":
        return 0.39405051
    if vehicle_name == "DD000110_220809_SYD-BRIS":
        return 0.180087421
    if vehicle_name == "DD000111_220809_SYD-MEL":
        return 0.849502186
    if vehicle_name == "DD000112_220811_SYD-BRIS":
        return 0.265517241
    if vehicle_name == "DD000113_220811_SYD-MEL":
        return 0.21651287
    if vehicle_name == "DD000114_220816_SYD-BRIS":
        return 0.119681884
    if vehicle_name == "DD000115_220816_SYD-MEL":
        return 0.393795532
    if vehicle_name == "DD000116_220818_SYD-BRIS":
        return 0.116949976
    if vehicle_name == "DD000117_220818_SYD-MEL":
        return 0.332880039
    if vehicle_name == "DD000119_220823_SYD-MEL":
        return 0.165735794
    if vehicle_name == "DD000120_220825_SYD-BRIS":
        return 0.163343856
    if vehicle_name == "DD000121_220825_SYD-MEL":
        return 0.51811559
    if vehicle_name == "DD000123_220830_SYD-MEL":
        return 0.717411365
    if vehicle_name == "DD000126_220902_SYD-MEL":
        return 0.498266667
    if vehicle_name == "DD000127_220902_SYD-BRIS":
        return 0.789779339
    if vehicle_name == "DD000129_220908_SYD-MEL":
        return 0.623690855
    if vehicle_name == "DD000131_220913_SYD-MEL":
        return 0.184905039
    if vehicle_name == "DD000132_220915_SYD-MEL":
        return 0.258118344
    if vehicle_name == "DD000134_220920_SYD-MEL":
        return 0.417169832
    if vehicle_name == "DD000135_220921_SYD-BRIS":
        return 0.249566363
    if vehicle_name == "DD000150_221020_SYD-MEL":
        return 0.560731145
    if vehicle_name == "DD000149_221019_SYD-BRIS":
        return 0.51831156
    if vehicle_name == "DD000148_221018_SYD-MEL":
        return 0.607706664
    if vehicle_name == "DD000146_221013_SYD-MEL_Semi":
        return 0.935031288
    if vehicle_name == "DD000147_221013_SYD-MEL_12_Tonne":
        return 0.536260841
    if vehicle_name == "DD000145_221012_SYD-BRIS":
        return 0.351026457
    if vehicle_name == "DD000144_221011_SYD-MEL":
        return 0.94280382
    if vehicle_name == "DD000143_221006_SYD-MEL":
        return 0.458656274
    if vehicle_name == "DD000142_221005_SYD-BRIS":
        return 0.353452629
    if vehicle_name == "DD000141_221004_SYD-MEL":
        return 0.44821605
    else:
        return 1


def get_pricing(booking, booking_lines):
    LOG_ID = "[Linehaul Pricing]"
    service_name = None

    de_postal = int(booking.de_To_Address_PostalCode or 0)
    pu_suburb = booking.pu_Address_Suburb

    try:
        percentage = booking.v_project_percentage
    except Exception as e:
        percentage = 1

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

        if booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8":
            cubic_meter = get_cubic_meter(
                line.e_dimLength,
                line.e_dimWidth,
                line.e_dimHeight,
                line.e_dimUOM,
                1,
            )
        else:
            cubic_meter = get_cubic_meter(
                line.e_dimLength,
                line.e_dimWidth,
                height / dim_ratio,
                line.e_dimUOM,
                1,
            )

        # Set smallest to `length`
        if length > width:
            temp = length
            length = width
            width = temp

        # JasonL
        if booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002":
            # Final Mile Delivery Fee
            fm_fee_cost = 55
            fm_fee_sell = 65

            if (
                "best assembly" in booking.deToCompanyName.lower()
                or "jl fitouts" in booking.deToCompanyName.lower()
                or "steadfast logistics" in booking.deToCompanyName.lower()
            ):
                # The reason is the linehaul delivers to them and we don't deliver to any customer from there.
                # They are the end customer.
                fm_fee_cost = 0
                fm_fee_sell = 0

            if (
                de_postal == 3800
                or (de_postal >= 3000 and de_postal <= 3207)
                or (de_postal >= 8000 and de_postal <= 8499)
            ):  # Melbourne
                service_name = "Deliver-ME Direct (Into Premises)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (75.93 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (91.11 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (91.11 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (113.89 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (136.67 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (136.67 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (113.89 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (136.67 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (136.67 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (42.37 * cubic_meter + fm_fee_cost) * line.e_qty
                    _value = 18 if 50.58 * cubic_meter < 18 else 50.58 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
            elif (de_postal >= 4000 and de_postal <= 4207) or (
                de_postal >= 9000 and de_postal <= 9499
            ):  # Brisbane
                service_name = "Deliver-ME Direct (Into Premises)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (120.74 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (134.94 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (134.94 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (181.11 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (202.41 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (202.41 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (181.11 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (202.41 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (202.41 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        67.38 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 75.30 * cubic_meter < 18 else 75.30 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
            elif (de_postal >= 5000 and de_postal <= 5199) or (
                de_postal >= 5900 and de_postal <= 5999
            ):  # Adelaide
                service_name = "Deliver-ME Direct (Into Premises)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (190.11 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (213.64 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (213.64 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (285.17 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (320.45 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (320.45 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (285.17 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (320.45 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (320.45 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        106.09 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 119.22 * cubic_meter < 18 else 119.22 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty

        # BSD
        elif booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8":
            # Final Mile Delivery Fee
            fm_fee_cost = 0
            fm_fee_sell = 0

            if (de_postal >= 3000 and de_postal <= 3207) or (
                de_postal >= 8000 and de_postal <= 8499
            ):  # Melbourne
                service_name = "Deliver-ME Direct (Into Premises)"
                case = "CBM type"
                inv_cost_quoted += 124.53 * cubic_meter * line.e_qty
                inv_sell_quoted += 187.96 * cubic_meter * line.e_qty
                inv_dme_quoted += 0
            elif (de_postal >= 4000 and de_postal <= 4207) or (
                de_postal >= 9000 and de_postal <= 9499
            ):  # Brisbane
                service_name = "Deliver-ME Direct (Into Premises)"
                case = "CBM type"
                inv_cost_quoted += 152.64 * cubic_meter * line.e_qty
                inv_sell_quoted += 231.47 * cubic_meter * line.e_qty
                inv_dme_quoted += 0
            elif (de_postal >= 5000 and de_postal <= 5199) or (
                de_postal >= 5900 and de_postal <= 5999
            ):  # Adelaide
                service_name = "Deliver-ME Direct (Into Premises)"
                case = "CBM type"
                inv_cost_quoted += 183.41 * cubic_meter * line.e_qty
                inv_sell_quoted += 279.09 * cubic_meter * line.e_qty
                inv_dme_quoted += 0
            elif (de_postal >= 6000 and de_postal <= 6199) or (
                de_postal >= 6800 and de_postal <= 6999
            ):  # Perth
                service_name = "Deliver-ME Direct (Into Premises)"
                case = "CBM type"
                inv_cost_quoted += 331.66 * cubic_meter * line.e_qty
                inv_sell_quoted += 508.52 * cubic_meter * line.e_qty
                inv_dme_quoted += 0

        # Anchor Packaging
        if booking.kf_client_id == "49294ca3-2adb-4a6e-9c55-9b56c0361953":
            if (
                de_postal == 3800
                or (de_postal >= 3000 and de_postal <= 3207)
                or (de_postal >= 8000 and de_postal <= 8499)
            ) or pu_suburb.lower() == "dandenong south":  # Melbourne | AFS (VIC) -> Sydney
                fm_fee_cost = 40
                fm_fee_sell = 65
                service_name = "Deliver-ME Direct (Into Premises)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (53.30 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (63.96 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (63.96 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (79.95 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (95.95 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (95.95 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (79.95 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (95.95 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (95.95 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (29.74 * cubic_meter + fm_fee_cost) * line.e_qty
                    _value = 18 if 35.69 * cubic_meter < 18 else 35.69 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
            elif (
                (de_postal >= 4000 and de_postal <= 4207)
                or (de_postal >= 9000 and de_postal <= 9499)
            ) or pu_suburb.lower() == "larapinta":  # Brisbane | MD2 (QLD) -> Sydney
                fm_fee_cost = 65
                fm_fee_sell = 75
                service_name = "Deliver-ME Direct (Into Premises)"

                if (
                    is_pallet
                    and length >= 0.8
                    and length <= 1.2
                    and width >= 0.8
                    and width <= 1.2
                    and height <= 1.4
                ):
                    case = "Pallet Type #1"
                    inv_cost_quoted += (94.00 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (104.04 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (104.04 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.2 and width <= 1.6 and height <= 1.4:
                    case = "Pallet Type #2"
                    inv_cost_quoted += (141.00 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (156.06 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (156.06 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                elif length <= 1.2 and width > 1.6 and width <= 1.85 and height <= 1.4:
                    case = "Pallet Type #3"
                    inv_cost_quoted += (141.00 + fm_fee_cost) * line.e_qty
                    inv_sell_quoted += (156.06 + fm_fee_sell) * line.e_qty
                    inv_dme_quoted += (
                        (156.06 - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty
                else:
                    case = "CBM type"
                    inv_cost_quoted += (
                        52.46 * cubic_meter * line.e_qty + fm_fee_cost * line.e_qty
                    )
                    _value = 18 if 58.06 * cubic_meter < 18 else 58.06 * cubic_meter
                    one_inv_sell_quoted = _value + fm_fee_sell
                    inv_sell_quoted += one_inv_sell_quoted * line.e_qty
                    inv_dme_quoted += (
                        (one_inv_sell_quoted - fm_fee_sell)
                        * 0.5
                        / (percentage or get_percentage(booking.b_booking_project))
                        + fm_fee_sell
                    ) * line.e_qty

        if booking.kf_client_id != "9e72da0f-77c3-4355-a5ce-70611ffd0bc8":
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
