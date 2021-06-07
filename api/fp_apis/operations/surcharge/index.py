import math
import logging

from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter

from api.fp_apis.operations.surcharge.tnt import tnt
from api.fp_apis.operations.surcharge.allied import allied
from api.fp_apis.operations.surcharge.hunter import hunter

from api.models import Booking_lines

logger = logging.getLogger(__name__)

def get_available_surcharge_opts(booking):

    lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
    if len(lines) == 0:
        logger.info(f"No Booking Lines to deliver")
        return None

def build_dict_data(booking_obj, line_objs, quote_obj, data_type):
    booking = {}
    lines = []

    if data_type == "bok_1":
        # Build `Booking` and `Lines` for Surcharge
        booking = {
            "pu_Address_Type": booking_obj.b_027_b_pu_address_type,
            "de_To_AddressType": booking_obj.b_053_b_del_address_type,
            "de_To_Address_State": booking_obj.b_057_b_del_address_state,
            "de_To_Address_City": booking_obj.b_058_b_del_address_suburb,
            "pu_tail_lift": booking_obj.b_019_b_pu_tail_lift,
            "del_tail_lift": booking_obj.b_041_b_del_tail_lift,
            "vx_serviceName": quote_obj.service_name,
            "vx_freight_provider": quote_obj.freight_provider,
        }

        for line_obj in line_objs:
            line = {
                "pk": line_obj.pk_lines_id,
                "e_type_of_packaging": line_obj.l_001_type_of_packaging,
                "e_qty": int(line_obj.l_002_qty),
                "e_item": line_obj.l_003_item,
                "e_dimUOM": line_obj.l_004_dim_UOM,
                "e_dimLength": line_obj.l_005_dim_length,
                "e_dimWidth": line_obj.l_006_dim_width,
                "e_dimHeight": line_obj.l_007_dim_height,
                "e_weightUOM": line_obj.l_008_weight_UOM,
                "e_weightPerEach": line_obj.l_009_weight_per_each,
                "e_dangerousGoods": False,
            }
            lines.append(line)

    return booking, lines


def get_surcharges(booking_obj, line_objs, quote_obj, data_type="bok_1"):
    booking, lines = build_dict_data(booking_obj, line_objs, quote_obj, data_type)

    m3_to_kg_factor = 250
    dead_weight, cubic_weight, total_qty, total_cubic = 0, 0, 0, 0
    lengths, widths, heights, diagonals, lines_data = [], [], [], [], []
    has_dangerous_item = False

    for line in lines:
        total_qty += line["e_qty"]
        dead_weight += (
            line["e_weightPerEach"]
            * _get_weight_amount(line["e_weightUOM"])
            * line["e_qty"]
        )
        total_cubic += get_cubic_meter(
            line["e_dimLength"],
            line["e_dimWidth"],
            line["e_dimHeight"],
            line["e_dimUOM"],
            line["e_qty"],
        )
        cubic_weight += (
            get_cubic_meter(
                line["e_dimLength"],
                line["e_dimWidth"],
                line["e_dimHeight"],
                line["e_dimUOM"],
                line["e_qty"],
            )
            * m3_to_kg_factor
        )

        lengths.append(line["e_dimLength"] * _get_dim_amount(line["e_dimUOM"]))
        widths.append(line["e_dimWidth"] * _get_dim_amount(line["e_dimUOM"]))
        heights.append(line["e_dimHeight"] * _get_dim_amount(line["e_dimUOM"]))
        diagonals.append(
            math.sqrt(
                line["e_dimLength"] ** 2
                + line["e_dimWidth"] ** 2
                + line["e_dimHeight"] ** 2
            )
            * _get_dim_amount(line["e_dimUOM"])
        )

        if line["e_dangerousGoods"]:
            has_dangerous_item = True

        lengths.append(line['e_dimLength'] * _get_dim_amount(line['e_dimUOM']))
        widths.append(line['e_dimWidth'] * _get_dim_amount(line['e_dimUOM']))
        heights.append(line['e_dimHeight'] * _get_dim_amount(line['e_dimUOM']))
        diagonals.append(math.sqrt(line['e_dimLength'] ** 2 + line['e_dimWidth'] ** 2 + line['e_dimHeight'] ** 2) * _get_dim_amount(line['e_dimUOM']))

        if line['e_dangerousGoods']:
            has_dangerous_item = True

        item_cubic_weight = get_cubic_meter(
            line["e_dimLength"],
            line["e_dimWidth"],
            line["e_dimHeight"],
            line["e_dimUOM"],
            1,
        ) * m3_to_kg_factor
        item_dead_weight = line["e_weightPerEach"] * _get_weight_amount(line["e_weightUOM"])
        is_pallet = line['e_type_of_packaging'].lower() == 'pallet'
        if is_pallet:
            item_max_weight = max(item_cubic_weight, item_dead_weight)
        else:
            item_max_weight = item_dead_weight

        lines_data.append({
            'pk': line['pk'],
            'max_dimension': max(line['e_dimLength'], line['e_dimWidth'], line['e_dimHeight']) * _get_dim_amount(line['e_dimUOM']),
            'length': line["e_dimLength"] * _get_dim_amount(line["e_dimUOM"]),
            'width': line["e_dimWidth"] * _get_dim_amount(line["e_dimUOM"]),
            'max_weight': math.ceil(item_max_weight),
            'is_pallet': is_pallet,
            'quantity': line['e_qty']
        })
        
    max_dimension = max(lengths + widths + heights)
    dead_weight = math.ceil(dead_weight)
    cubic_weight = math.ceil(cubic_weight)

    order_data = {
        "pu_address_type": booking["pu_Address_Type"],
        "de_to_address_type": booking["de_To_AddressType"],
        "de_to_address_state": booking["de_To_Address_State"],
        "de_to_address_city": booking["de_To_Address_City"],
        "dead_weight": dead_weight,
        "cubic_weight": cubic_weight,
        "total_cubic": total_cubic,
        "max_weight": max(dead_weight, cubic_weight),
        "min_weight": min(dead_weight, cubic_weight),
        "max_average_weight": max(dead_weight, cubic_weight) / total_qty,
        "min_average_weight": min(dead_weight, cubic_weight) / total_qty,
        "max_dimension": max_dimension,
        "max_length": max(lengths),
        "min_length": min(lengths),
        "max_width": max(widths),
        "min_width": min(widths),
        "max_height": max(heights),
        "min_height": min(heights),
        "max_diagonal": max(diagonals),
        "min_diagonal": min(diagonals),
        "total_qty": total_qty,
        "vx_service_name": booking["vx_serviceName"],
        "has_dangerous_item": has_dangerous_item,
        "is_tail_lift": booking["pu_tail_lift"] or booking["del_tail_lift"],
    }

    print(order_data)

    surcharges, surcharge_opt_funcs = [], []
    if booking['vx_freight_provider'].lower() == "tnt":
        surcharge_opt_funcs = tnt()
    elif booking['vx_freight_provider'].lower() == "allied":
        surcharge_opt_funcs = allied()
    elif booking['vx_freight_provider'].lower() == "hunter":
        surcharge_opt_funcs = hunter()

    for opt_func in surcharge_opt_funcs['order']:
        result = opt_func(order_data)

        if result:
            surcharges.append(result)

    for opt_func in surcharge_opt_funcs['line']:
        line_surcharges, total, temp = [], 0, {}
        for line in lines_data:
            result = opt_func(line)

            if result:
                temp = result
                line_surcharges.append({
                    'pk': line['pk'],
                    'quantity': line['quantity'],
                    'value': result['value']
                })
                total += line['quantity'] * result['value']
        if line_surcharges:
            surcharges.append({
                'name': temp['name'],
                'description': temp['description'],
                'value': total,
                'lines': line_surcharges
            })

    return surcharges