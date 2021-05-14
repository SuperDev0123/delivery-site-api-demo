import math
import logging

from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter

from api.models import Booking_lines

from api.fp_apis.operations.surcharge.tnt import tnt

logger = logging.getLogger(__name__)

def get_available_surcharge_opts(booking):

    lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
    # if len(booking_lines) == 0:
    #     logger.info(f"No Booking Lines to deliver")
    #     return None, None

    m3_to_kg_factor = 250
    dead_weight, cubic_weight, total_qty = 0, 0, 0
    lengths, widths, heights, diagonals = [], [], [], []
    has_dangerous_item = False

    for item in lines:
        total_qty += item.e_qty
        dead_weight += item.e_weightPerEach * _get_weight_amount(item.e_weightUOM) * item.e_qty
        cubic_weight += get_cubic_meter(item.e_dimLength, item.e_dimWidth, item.e_dimHeight, item.e_dimUOM, item.e_qty) * m3_to_kg_factor

        lengths.append(item.e_dimLength * _get_dim_amount(item.e_dimUOM))
        widths.append(item.e_dimWidth * _get_dim_amount(item.e_dimUOM))
        heights.append(item.e_dimHeight * _get_dim_amount(item.e_dimUOM))
        diagonals.append(math.sqrt(item.e_dimLength ** 2 + item.e_dimWidth ** 2 + item.e_dimHeight ** 2) * _get_dim_amount(item.e_dimUOM))

        if item.e_dangerousGoods:
            has_dangerous_item = True
        
        max_dimension = max(lengths + widths + heights)

    to_be_considered = {
        'pu_address_type': booking.pu_Address_Type,
        'de_to_address_type': booking.de_To_AddressType,
        'de_to_address_state': booking.de_To_Address_State,
        'de_to_address_city': booking.de_To_Address_City,
        'dead_weight': dead_weight,
        'cubic_weight': cubic_weight,
        'max_weight': max(dead_weight, cubic_weight),
        'min_weight': min(dead_weight, cubic_weight),
        'max_dimension': max_dimension,
        'max_length': max(lengths),
        'min_length': min(lengths),
        'max_width': max(widths),
        'min_width': min(widths),
        'max_height': max(heights),
        'min_height': min(heights),
        'max_diagonal': max(diagonals),
        'min_diagonal': min(diagonals),
        'total_qty': total_qty,
        'vx_service_name': booking.vx_serviceName,
        'has_dangerous_item': has_dangerous_item,
        'is_tail_lift': booking.b_booking_tail_lift_pickup or booking.b_booking_tail_lift_deliver
    }

    print(to_be_considered)


    applicable_surcharges, get_surcharges = [], []
    if booking.vx_freight_provider.lower() == 'tnt':
        get_surcharges = tnt()

    for func in get_surcharges:
        item = func(to_be_considered)
        if item:
            applicable_surcharges.append(item)

    return {
        'fp_name': booking.vx_freight_provider,
        'surcharges': applicable_surcharges
    }










