import numpy
import logging

from api.common.ratio import _get_dim_amount

logger = logging.getLogger("dme_api")

def get_number_of_pallets(booking_lines, pallet):
    if len(booking_lines) == 0:
        logger.info(f"No Booking Lines to deliver")
        return

    if pallet is None:
        logger.info(f"No Pallet")
        return

    pallet_height = 2.438
    pallet_dimensions = [pallet.length / 1000, pallet.width / 1000, pallet_height]
    pallet_dimensions.sort()
    pallet_cube = numpy.prod(pallet_dimensions) * 0.8

    palletized_lines, unpalletized_lines, line_dimensions, sum_cube = [], [], [], 0

    for item in booking_lines:
        length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength
        width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
        height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight

        line_dimensions = [length, width, height]
        line_dimensions.sort()
        if line_dimensions[0] <= pallet_dimensions[0] and line_dimensions[1] <= pallet_dimensions[1] and line_dimensions[2] <= pallet_dimensions[2]:
            palletized_lines.append(item)
            sum_cube += width * height * length * item.e_qty
        else:
            unpalletized_lines.append(item)

    number_of_pallets = sum_cube / pallet_cube

    if number_of_pallets < 1:
        number_of_pallets = 1
    else:
        number_of_pallets = round(number_of_pallets)
            
    return {
        'unpalletized_lines': unpalletized_lines,
        'number_of_pallets': number_of_pallets
    }