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
    pallet_dims = [pallet.length / 1000, pallet.width / 1000, pallet_height]
    pallet_dims.sort()
    pallet_cube = pallet_dims[0] * pallet_dims[1] * pallet_dims[2] * 0.8

    (
        palletized_lines,
        unpalletized_lines,
        line_dimensions,
        sum_cube,
        unpalletized_dead_weight,
        unpalletized_cubic_weight,
    ) = ([], [], [], 0, 0, 0)

    for item in booking_lines:
        length = _get_dim_amount(item.l_004_dim_UOM) * item.l_005_dim_length
        width = _get_dim_amount(item.l_004_dim_UOM) * item.l_006_dim_width
        height = _get_dim_amount(item.l_004_dim_UOM) * item.l_007_dim_height
        line_dimensions = [length, width, height]
        line_dimensions.sort()

        if (
            line_dimensions[0] <= pallet_dims[0]
            and line_dimensions[1] <= pallet_dims[1]
            and line_dimensions[2] <= pallet_dims[2]
        ):
            palletized_lines.append(item)
            sum_cube += width * height * length * item.l_002_qty
        else:
            unpalletized_lines.append(item)
            unpalletized_dead_weight += (
                item.l_002_qty
                * item.l_009_weight_per_each
                * _get_weight_amount(item.l_008_weight_UOM)
            )
            unpalletized_cubic_weight += length * width * height * m3_to_kg_factor

    unpalletized_weight = max(unpalletized_dead_weight, unpalletized_cubic_weight)
    number_of_pallets_for_unpalletized = math.ceil(unpalletized_weight / pallet_weight)
    number_of_pallets_for_palletized = math.ceil(sum_cube / pallet_cube)

    return number_of_pallets_for_palletized + number_of_pallets_for_unpalletized

def get_pallet_index(booking, pallets):
    booking_lines = Booking_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id
    )

    first_lengths, second_lengths, third_lengths = [], [], []
    for item in booking_lines:
        length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength
        width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
        height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight
        line_dimensions = [length, width, height]
        line_dimensions.sort()

        first_lengths.append(line_dimensions[0])
        second_lengths.append(line_dimensions[1])
        third_lengths.append(line_dimensions[2])

    max_dimensions = [
        max(first_lengths),
        max(second_lengths),
        max(third_lengths)
    ]

    available_pallets, non_available_pallets = [], []
    index = 0
    for pallet in pallets:
        dimensions = [pallet.length / 1000, pallet.width / 1000, pallet.height / 1000]
        dimensions.sort()
        if dimensions[0] >= max_dimensions[0] and dimensions[1] >= max_dimensions[1] and dimensions[2] >= max_dimensions[2]:
            available_pallets.append({
                'index': index,
                'cubic_meter': pallet.length * pallet.width * pallet.height / 1000000
            })
        else:
            non_available_pallets.append({
                'index': index,
                'cubic_meter': pallet.length * pallet.width * pallet.height / 1000000
            })
        index += 1

    print('available', available_pallets)
    print('non_available', non_available_pallets)
    min_cubic, max_cubic, pallet_index = 10000, 0, 0
    if available_pallets:
        for item in available_pallets:
            if item['cubic_meter'] < min_cubic:
                min_cubic = item['cubic_meter']
                pallet_index = item['index']
        return pallet_index

    else:
        for item in non_available_pallets:
            if item['cubic_meter'] > max_cubic:
                max_cubic = item['cubic_meter']
                pallet_index = item['index']
        return pallet_index

