import math
import logging

from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter

from api.fp_apis.operations.surcharge.tnt import tnt
from api.fp_apis.operations.surcharge.allied import allied
from api.fp_apis.operations.surcharge.hunter import hunter

from api.models import Booking_lines, Surcharge, Fp_freight_providers

logger = logging.getLogger(__name__)


def build_dict_data(booking_obj, line_objs, quote_obj, data_type):
    """
    Build `Booking` and `Lines` for Surcharge
    """
    booking = {}
    lines = []

    if data_type == "bok_1":
        booking = {
            "pu_Address_Type": booking_obj.b_027_b_pu_address_type,
            "pu_Address_State": booking_obj.b_031_b_pu_address_state,
            "pu_Address_PostalCode": booking_obj.b_033_b_pu_address_postalcode,
            "pu_Address_Suburb": booking_obj.b_032_b_pu_address_suburb,
            "de_To_Address_State": booking_obj.b_057_b_del_address_state,
            "de_To_Address_PostalCode": booking_obj.b_059_b_del_address_postalcode,
            "de_To_Address_Suburb": booking_obj.b_058_b_del_address_suburb,
            "de_To_AddressType": booking_obj.b_053_b_del_address_type,
            "pu_tail_lift": booking_obj.b_019_b_pu_tail_lift,
            "del_tail_lift": booking_obj.b_041_b_del_tail_lift,
            "vx_serviceName": quote_obj.service_name,
            "vx_freight_provider": quote_obj.freight_provider,
            "client_id": booking_obj.fk_client_id,
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
    else:
        booking = {
            "pu_Address_Type": booking_obj.pu_Address_Type,
            "pu_Address_State": booking_obj.pu_Address_State,
            "pu_Address_PostalCode": booking_obj.pu_Address_PostalCode,
            "pu_Address_Suburb": booking_obj.pu_Address_Suburb,
            "de_To_AddressType": booking_obj.de_To_AddressType,
            "de_To_Address_State": booking_obj.de_To_Address_State,
            "de_To_Address_PostalCode": booking_obj.de_To_Address_PostalCode,
            "de_To_Address_Suburb": booking_obj.de_To_Address_Suburb,
            "pu_tail_lift": booking_obj.b_booking_tail_lift_pickup,
            "del_tail_lift": booking_obj.b_booking_tail_lift_deliver,
            "vx_serviceName": quote_obj.service_name,
            "vx_freight_provider": quote_obj.freight_provider,
            "client_id": booking_obj.kf_client_id,
        }

        for line_obj in line_objs:
            line = {
                "pk": line_obj.pk_lines_id,
                "e_type_of_packaging": line_obj.e_type_of_packaging,
                "e_qty": int(line_obj.e_qty),
                "e_item": line_obj.e_item,
                "e_dimUOM": line_obj.e_dimUOM,
                "e_dimLength": line_obj.e_dimLength,
                "e_dimWidth": line_obj.e_dimWidth,
                "e_dimHeight": line_obj.e_dimHeight,
                "e_weightUOM": line_obj.e_weightUOM,
                "e_weightPerEach": line_obj.e_weightPerEach,
                "e_dangerousGoods": False,
            }
            lines.append(line)

    return booking, lines


def clac_surcharges(booking_obj, line_objs, quote_obj, data_type="bok_1"):
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

        item_cubic_weight = (
            get_cubic_meter(
                line["e_dimLength"],
                line["e_dimWidth"],
                line["e_dimHeight"],
                line["e_dimUOM"],
                1,
            )
            * m3_to_kg_factor
        )
        item_dead_weight = line["e_weightPerEach"] * _get_weight_amount(
            line["e_weightUOM"]
        )
        is_pallet = line["e_type_of_packaging"].lower() == "pallet"
        if is_pallet:
            item_max_weight = max(item_cubic_weight, item_dead_weight)
        else:
            item_max_weight = item_dead_weight

        lines_data.append(
            {
                "pk": line["pk"],
                "max_dimension": max(
                    line["e_dimLength"], line["e_dimWidth"], line["e_dimHeight"]
                )
                * _get_dim_amount(line["e_dimUOM"]),
                "length": line["e_dimLength"] * _get_dim_amount(line["e_dimUOM"]),
                "width": line["e_dimWidth"] * _get_dim_amount(line["e_dimUOM"]),
                "max_weight": math.ceil(item_max_weight),
                "is_pallet": is_pallet,
                "quantity": line["e_qty"],
                "pu_address_state": booking["pu_Address_State"],
                "pu_address_postcode": booking["pu_Address_PostalCode"],
                "pu_address_suburb": booking["pu_Address_Suburb"],
                "de_to_address_state": booking["de_To_Address_State"],
                "de_to_address_postcode": booking["de_To_Address_PostalCode"],
                "de_to_address_suburb": booking["de_To_Address_Suburb"],
                "vx_freight_provider": booking["vx_freight_provider"],
                "vx_service_name": booking["vx_serviceName"],
                "is_jason_l": booking["client_id"]
                == "1af6bcd2-6148-11eb-ae93-0242ac130002",
            }
        )

    max_dimension = max(lengths + widths + heights)
    dead_weight = math.ceil(dead_weight)
    cubic_weight = math.ceil(cubic_weight)

    order_data = {
        "pu_address_type": booking["pu_Address_Type"] or "",
        "pu_address_state": booking["pu_Address_State"],
        "pu_address_postcode": booking["pu_Address_PostalCode"],
        "pu_address_suburb": booking["pu_Address_Suburb"],
        "de_to_address_type": booking["de_To_AddressType"] or "",
        "de_to_address_state": booking["de_To_Address_State"],
        "de_to_address_postcode": booking["de_To_Address_PostalCode"],
        "de_to_address_suburb": booking["de_To_Address_Suburb"],
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
        "vx_freight_provider": booking["vx_freight_provider"],
        "vx_service_name": booking["vx_serviceName"],
        "has_dangerous_item": has_dangerous_item,
        "is_tail_lift": booking["pu_tail_lift"] or booking["del_tail_lift"],
        "is_jason_l": booking["client_id"] == "1af6bcd2-6148-11eb-ae93-0242ac130002",
    }

    surcharges, surcharge_opt_funcs = [], []
    if booking["vx_freight_provider"].lower() == "tnt":
        surcharge_opt_funcs = tnt()
    # elif booking["vx_freight_provider"].lower() == "allied":
    #     surcharge_opt_funcs = allied()
    elif booking["vx_freight_provider"].lower() == "hunter":
        surcharge_opt_funcs = hunter()

    for opt_func in surcharge_opt_funcs["order"]:
        result = opt_func(order_data)

        if result:
            surcharges.append(result)

    if booking["vx_freight_provider"].lower() == "allied":
        pass
        # line_surcharges = []
        # for opt_func in surcharge_opt_funcs["line"]:
        #     for line in lines_data:
        #         result = opt_func(line)

        #         if result:
        #             line_surcharges.append(
        #                 {
        #                     "pk": line["pk"],
        #                     "quantity": line["quantity"],
        #                     "name": result["name"],
        #                     "description": result["description"],
        #                     "value": result["value"],
        #                 }
        #             )
        # line_surcharge_dict = {}
        # for item in line_surcharges:
        #     if item["name"] not in line_surcharge_dict:
        #         line_surcharge_dict[item["name"]] = {
        #             "name": item["name"],
        #             "description": item["description"],
        #             "value": item["value"] * item["quantity"],
        #             "lines": [
        #                 {
        #                     "pk": item["pk"],
        #                     "quantity": item["quantity"],
        #                     "value": item["value"],
        #                 }
        #             ],
        #         }
        #     else:
        #         line_surcharge_dict[item["name"]]["value"] += (
        #             item["value"] * item["quantity"]
        #         )
        #         line_surcharge_dict[item["name"]]["lines"].append(
        #             {
        #                 "pk": item["pk"],
        #                 "quantity": item["quantity"],
        #                 "value": item["value"],
        #             }
        #         )

        # surcharges += list(line_surcharge_dict.values())
    else:
        for opt_func in surcharge_opt_funcs["line"]:
            line_surcharges, total, temp = [], 0, {}
            for line in lines_data:
                result = opt_func(line)

                if result:
                    temp = result
                    line_surcharges.append(
                        {
                            "pk": line["pk"],
                            "quantity": line["quantity"],
                            "value": result["value"],
                        }
                    )
                    total += line["quantity"] * result["value"]
            if line_surcharges:
                surcharges.append(
                    {
                        "name": temp["name"],
                        "description": temp["description"],
                        "value": total,
                        "lines": line_surcharges,
                    }
                )

    return surcharges


def get_surcharges(quote):
    return Surcharge.objects.filter(quote=quote)


def get_surcharges_total(quote):
    _total = 0
    surcharges = get_surcharges(quote)

    for surcharge in surcharges.filter(line_id__isnull=True):
        _total += surcharge.amount

    return _total


def gen_surcharges(booking_obj, line_objs, quote_obj, data_type="bok_1"):
    """
    Surcharge table management

    - Delete existing of Quote
    - Calc new surcharge opts
    - Create new Surcharge objects
    """

    result = []
    total = 0

    # Do not process for `Allied` Quote
    if quote_obj.freight_provider.lower() == "allied":
        return result

    # Delete existing Surcharges
    Surcharge.objects.filter(quote=quote_obj).delete()

    # Calc new surcharge opts
    surcharges = clac_surcharges(booking_obj, line_objs, quote_obj, data_type)

    # Create new Surcharge objects
    fp = Fp_freight_providers.objects.get(
        fp_company_name__iexact=quote_obj.freight_provider
    )

    for surcharge in surcharges:
        surcharge_obj = Surcharge()
        surcharge_obj.quote = quote_obj
        surcharge_obj.name = surcharge["name"]
        surcharge_obj.amount = surcharge["value"]
        surcharge_obj.fp = fp
        surcharge_obj.save()
        total += float(surcharge["value"])
        result.append(surcharge_obj)

        lines = surcharge.get("lines")
        if lines:
            for line in lines:
                surcharge_obj = Surcharge()
                surcharge_obj.quote = quote_obj
                surcharge_obj.name = surcharge["name"]
                surcharge_obj.amount = line["value"]
                surcharge_obj.line_id = line["pk"]
                surcharge_obj.qty = line["quantity"]
                surcharge_obj.fp = fp
                surcharge_obj.save()
                result.append(surcharge_obj)

    if total:  # Update Quote's surchargeTotal
        quote_obj.x_price_surcharge = total
        quote_obj.save()

    return result
