import math
import logging

from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.models import Booking_lines

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
    pallet_length = max(pallet.length, pallet.width) / 1000
    pallet_width = min(pallet.length, pallet.width) / 1000
    pallet_cube = pallet_length * pallet_width * pallet_height * 0.8

    (
        palletized_lines,
        unpalletized_line_pks,
        line_dimensions,
        sum_cube,
        unpalletized_dead_weight,
        unpalletized_cubic_weight,
    ) = ([], [], [], 0, 0, 0)

    for item in booking_lines:
        line_length = _get_dim_amount(item.l_004_dim_UOM) * item.l_005_dim_length
        line_width = _get_dim_amount(item.l_004_dim_UOM) * item.l_006_dim_width
        length = max(line_length, line_width)
        width = min(line_length, line_width)
        height = _get_dim_amount(item.l_004_dim_UOM) * item.l_007_dim_height

        if (
            length <= pallet_length
            and width <= pallet_width
            and height <= pallet_height
        ):
            palletized_lines.append(item)
            sum_cube += width * height * length * item.l_002_qty
        else:
            unpalletized_line_pks.append(item.pk)
            unpalletized_dead_weight += (
                item.l_002_qty
                * item.l_009_weight_per_each
                * _get_weight_amount(item.l_008_weight_UOM)
            )
            unpalletized_cubic_weight += length * width * height * m3_to_kg_factor

    unpalletized_weight = max(unpalletized_dead_weight, unpalletized_cubic_weight)
    number_of_pallets_for_unpalletized = math.ceil(unpalletized_weight / pallet_weight)
    number_of_pallets_for_palletized = math.ceil(sum_cube / pallet_cube)

    return number_of_pallets_for_palletized, unpalletized_line_pks


def get_suitable_pallet(bok_2s, pallets):
    lengths, widths, heights = [], [], []
    for item in bok_2s:
        line_length = _get_dim_amount(item.l_004_dim_UOM) * item.l_005_dim_length
        line_width = _get_dim_amount(item.l_004_dim_UOM) * item.l_006_dim_width

        # Daniel need to see this.
        # length = max(line_length, line_width)
        # width = min(line_length, line_width)
        length = line_length
        width = line_width

        height = _get_dim_amount(item.l_004_dim_UOM) * item.l_007_dim_height

        lengths.append(length)
        widths.append(width)
        heights.append(height)

    max_length = max(lengths)
    max_width = max(widths)
    max_height = max(heights)

    available_pallets, non_available_pallets = [], []
    for index, pallet in enumerate(pallets):
        pallet_length = max(pallet.length, pallet.width) / 1000
        pallet_width = min(pallet.length, pallet.width) / 1000
        pallet_height = pallet.height / 1000

        if (
            pallet_length >= max_length
            and pallet_width >= max_width
            and pallet_height >= max_height
        ):
            available_pallets.append(
                {
                    "index": index,
                    "cubic_meter": pallet_length * pallet_width * pallet_height,
                }
            )
        else:
            non_available_pallets.append(
                {
                    "index": index,
                    "cubic_meter": pallet_length * pallet_width * pallet_height,
                }
            )

    min_cubic, max_cubic, pallet_index = 100000, 0, 0
    if available_pallets:
        for pallet in available_pallets:
            if pallet["cubic_meter"] < min_cubic:
                min_cubic = pallet["cubic_meter"]
                pallet_index = pallet["index"]
        return pallet_index

    else:
        for pallet in non_available_pallets:
            if pallet["cubic_meter"] > max_cubic:
                max_cubic = pallet["cubic_meter"]
                pallet_index = pallet["index"]
        return pallet_index
