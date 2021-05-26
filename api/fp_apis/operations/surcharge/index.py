import math
import logging

from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter

from api.fp_apis.operations.surcharge.tnt import tnt
from api.fp_apis.operations.surcharge.allied import allied
from api.fp_apis.operations.surcharge.hunter import hunter

logger = logging.getLogger(__name__)


def get_available_surcharge_opts(booking, lines):
    m3_to_kg_factor = 250
    dead_weight, cubic_weight, total_qty, total_cubic = 0, 0, 0
    lengths, widths, heights, diagonals = [], [], [], []
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

    max_dimension = max(lengths + widths + heights)

    required_params = {
        "pu_address_type": booking["pu_Address_Type"],
        "de_to_address_type": booking["de_To_AddressType"],
        "de_to_address_state": booking["de_To_Address_State"],
        "de_to_address_city": booking["de_To_Address_City"],
        "dead_weight": dead_weight,
        "cubic_weight": cubic_weight,
        "total_cubic": total_cubic,
        "max_weight": max(dead_weight, cubic_weight),
        "min_weight": min(dead_weight, cubic_weight),
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

    applicable_surcharges, surcharge_opt_funcs = [], []
    if booking["vx_freight_provider"].lower() == "tnt":
        surcharge_opt_funcs = tnt()
    elif booking["vx_freight_provider"].lower() == "allied":
        surcharge_opt_funcs = allied()
    elif booking["vx_freight_provider"].lower() == "hunter":
        surcharge_opt_funcs = hunter()

    for opt_func in surcharge_opt_funcs:
        result = opt_func(required_params)

        if result:
            applicable_surcharges.append(result)

    return applicable_surcharges
