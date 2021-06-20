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


def get_suitable_pallets(bok_2s, pallets):
    # occupied pallet space percent in case of packing different line items in one pallet
    available_percent = 80

    # prepaer pallets data
    pallets_data = []
    for pallet in pallets:
        length = max(pallet.length, pallet.width) / 1000
        width = min(pallet.length, pallet.width) / 1000
        height = pallet.height / 1000
        total_cubic = length * width * height
        available_cubic = total_cubic * available_percent / 100
        pallets_data.append({
            'length': length,
            'width': width,
            'height': height,
            'total_cubic': total_cubic,
            'available_cubic': available_cubic
        })

    # prepare lines data
    lines_data = []
    for item in bok_2s:
        line_length = _get_dim_amount(item.l_004_dim_UOM) * item.l_005_dim_length
        line_width = _get_dim_amount(item.l_004_dim_UOM) * item.l_006_dim_width
        length = max(line_length, line_width)
        width = min(line_length, line_width)
        height = _get_dim_amount(item.l_004_dim_UOM) * item.l_007_dim_height
        cubic = length * width * height

        available_pallets, min_pallet_cubic, smallest_pallet = [], None, None
        for index, pallet in enumerate(pallets_data):
            if pallet['length'] >= length and pallet['width'] >= width and pallet['height'] >= height:
                if min_pallet_cubic is None or pallet['total_cubic'] < min_pallet_cubic:
                    min_pallet_cubic = pallet['total_cubic']
                    smallest_pallet = index
                available_pallets.append(index)

        lines_data.append({
            'length': length,
            'width': width,
            'height': height,
            'quantity': item.l_002_qty,
            'cubic': cubic,
            'available_pallets': available_pallets,
            'smallest_pallet': smallest_pallet
        })

    # sort lines data in descending order of greater of length and width
    sorted(lines_data, key=lambda k: k['length'], reverse=True) 

    palletized, non_palletized = [], []
    for index, line in enumerate(lines_data):
        if line['quantity'] > 0:
            # check if there is suitable pallet
            if not line['smallest_pallet']:
                non_palletized.append({
                    'line_index': index,
                    'quantity': line['quantity']
                })
            else:
                for pallet_item in palletized:
                    # check if items can be packed in previously packed pallets
                    if pallet_item['pallet_index'] in line['available_pallets'] and pallet_item['remaining_space'] > line['cubic'] and line['quantity']:
                        packable_count = min(
                            math.floor(pallet_item['remaining_space'] / line['cubic']), 
                            line['quantity']
                        )
                        pallet_item['remaining_space'] -= packable_count * line['cubic']
                        pallet_item['lines'].append({
                            'line_index': index,
                            'quantity': packable_count
                        })
                        line['quantity'] -= packable_count
                
                # check if new pallet needs to be used
                if line['quantity']:
                    for i in iter(int, 1):
                        if line['quantity']:
                            packable_count = min(
                                math.floor(pallets_data[line['smallest_pallet']]['total_cubic'] / line['cubic']), 
                                line['quantity']
                            )
                            line['quantity'] -= packable_count
                            needed_space = packable_count * line['cubic']

                            # check if pallet is packed with items of same line
                            if needed_space > pallets_data[line['smallest_pallet']]['available_cubic'] and needed_space <= pallets_data[line['smallest_pallet']]['total_cubic']:
                                palletized.append({
                                    'pallet_index': line['smallest_pallet'],
                                    'remaining_space': 0,
                                    'lines': [
                                        {
                                            'line_index': index,
                                            'quantity': packable_count
                                        }
                                    ]
                                })

                            else:
                                palletized.append({
                                    'pallet_index': line['smallest_pallet'],
                                    'remaining_space': pallets_data[line['smallest_pallet']]['available_cubic'] - needed_space,
                                    'lines': [
                                        {
                                            'line_index': index,
                                            'quantity': packable_count
                                        }
                                    ]
                                })

                        else:
                            break

        else:
            continue
    
    return {
        'palletized': palletized,
        'non_palletized': non_palletized
    }