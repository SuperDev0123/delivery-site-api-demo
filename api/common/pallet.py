import math
import logging

from api.common.ratio import _get_dim_amount, _get_weight_amount

logger = logging.getLogger(__name__)


def get_number_of_pallets(booking_lines, pallet):
    if len(booking_lines) == 0:
        logger.info(f"No Booking Lines to deliver")
        return None, None

    if not pallet:
        logger.info(f"No Pallet")
        return None, None

    pallet_height = 2.1
    pallet_weight = 500
    m3_to_kg_factor = 250
    pallet_dimensions = [pallet.length / 1000, pallet.width / 1000, pallet_height]
    pallet_dimensions.sort()
    pallet_cube = pallet_dimensions[0] * pallet_dimensions[1] * pallet_dimensions[2] * 0.8

    palletized_lines, unpalletized_lines, line_dimensions, sum_cube, unpalletized_dead_weight, unpalletized_cubic_weight = [], [], [], 0, 0, 0

    for item in booking_lines:
        length = _get_dim_amount(item.l_004_dim_UOM) * item.l_005_dim_length
        width = _get_dim_amount(item.l_004_dim_UOM) * item.l_006_dim_width
        height = _get_dim_amount(item.l_004_dim_UOM) * item.l_007_dim_height
        line_dimensions = [length, width, height]
        line_dimensions.sort()

        if (
            line_dimensions[0] <= pallet_dimensions[0]
            and line_dimensions[1] <= pallet_dimensions[1]
            and line_dimensions[2] <= pallet_dimensions[2]
        ):
            palletized_lines.append(item)
            sum_cube += width * height * length * item.l_002_qty
        else:
            unpalletized_lines.append(item)
            unpalletized_dead_weight += item.l_002_qty * item.l_009_weight_per_each * _get_weight_amount(item.l_008_weight_UOM)
            unpalletized_cubic_weight += length * width * height * m3_to_kg_factor

    unpalletized_weight = max(unpalletized_dead_weight, unpalletized_cubic_weight)    
    number_of_pallets_for_unpalletized = math.ceil(unpalletized_weight / pallet_weight)
    number_of_pallets_for_palletized = math.ceil(sum_cube / pallet_cube)

    return number_of_pallets_for_palletized + number_of_pallets_for_unpalletized
