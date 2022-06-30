from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.utils import get_m3_to_kg_factor
from api.common.constants import PALLETS


def get_pricing(booking, booking_lines):
    service_name = None
    postal_code = int(booking.de_To_Address_PostalCode or 0)
    inv_cost_quoted, inv_sell_quoted = 0, 0

    for line in booking_lines:
        is_pallet = line.e_type_of_packaging.upper() in PALLETS
        length = line.e_dimLength * _get_dim_amount(line.e_dimUOM)
        width = line.e_dimWidth * _get_dim_amount(line.e_dimUOM)
        height = line.e_dimHeight * _get_dim_amount(line.e_dimUOM)
        cubic_meter = get_cubic_meter(
            line.e_dimLength,
            line.e_dimWidth,
            line.e_dimHeight,
            line.e_dimUOM,
            1,
        )

        # Set smallert to `length`
        if length > width:
            temp = length
            length = width
            width = temp

        # JasonL
        if booking.kf_client_id == "1af6bcd2-6148-11eb-ae93-0242ac130002":
            if (postal_code >= 3000 and postal_code <= 3207) or (
                postal_code >= 8000 and postal_code <= 8499
            ):  # Melbourne
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if is_pallet and length <= 1.2 and width <= 1.2:
                    inv_cost_quoted += 167.86 * line.e_qty
                    inv_sell_quoted += 198.89 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.6:
                    inv_cost_quoted += 224.29 * line.e_qty
                    inv_sell_quoted += 268.33 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.85:
                    inv_cost_quoted += 224.29 * line.e_qty
                    inv_sell_quoted += 268.33 * line.e_qty
                else:
                    inv_cost_quoted += 81.45 * cubic_meter * line.e_qty
                    inv_sell_quoted += 137.50 * cubic_meter * line.e_qty
            elif (postal_code >= 4000 and postal_code <= 4207) or (
                postal_code >= 9000 and postal_code <= 9499
            ):  # Brisbane
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if is_pallet and length <= 1.2 and width <= 1.2:
                    inv_cost_quoted += 234.25 * line.e_qty
                    inv_sell_quoted += 265.56 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.6:
                    inv_cost_quoted += 323.88 * line.e_qty
                    inv_sell_quoted += 471.11 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.85:
                    inv_cost_quoted += 323.88 * line.e_qty
                    inv_sell_quoted += 471.11 * line.e_qty
                else:
                    inv_cost_quoted += 155.03 * cubic_meter * line.e_qty
                    inv_sell_quoted += 212.94 * cubic_meter * line.e_qty
            elif (postal_code >= 5000 and postal_code <= 5199) or (
                postal_code >= 5900 and postal_code <= 5999
            ):  # Adelaide
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if is_pallet and length <= 1.2 and width <= 1.2:
                    inv_cost_quoted += 287.36 * line.e_qty
                    inv_sell_quoted += 321.11 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.6:
                    inv_cost_quoted += 403.54 * line.e_qty
                    inv_sell_quoted += 582.22 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.85:
                    inv_cost_quoted += 403.54 * line.e_qty
                    inv_sell_quoted += 582.22 * line.e_qty
                else:
                    inv_cost_quoted += 184.67 * cubic_meter * line.e_qty
                    inv_sell_quoted += 254.28 * cubic_meter * line.e_qty
        # BSD
        elif booking.kf_client_id == "9e72da0f-77c3-4355-a5ce-70611ffd0bc8":
            if (postal_code >= 3000 and postal_code <= 3207) or (
                postal_code >= 8000 and postal_code <= 8499
            ):  # Melbourne
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if is_pallet and length <= 1.2 and width <= 1.2:
                    inv_cost_quoted += 167.86 * line.e_qty
                    inv_sell_quoted += 206.06 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.6:
                    inv_cost_quoted += 224.29 * line.e_qty
                    inv_sell_quoted += 279.08 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.85:
                    inv_cost_quoted += 224.29 * line.e_qty
                    inv_sell_quoted += 279.08 * line.e_qty
                else:
                    inv_cost_quoted += 81.45 * cubic_meter * line.e_qty
                    inv_sell_quoted += 141.5 * cubic_meter * line.e_qty
            elif (postal_code >= 4000 and postal_code <= 4207) or (
                postal_code >= 9000 and postal_code <= 9499
            ):  # Brisbane
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if is_pallet and length <= 1.2 and width <= 1.2:
                    inv_cost_quoted += 234.25 * line.e_qty
                    inv_sell_quoted += 272.44 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.6:
                    inv_cost_quoted += 323.88 * line.e_qty
                    inv_sell_quoted += 484.89 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.85:
                    inv_cost_quoted += 323.88 * line.e_qty
                    inv_sell_quoted += 484.89 * line.e_qty
                else:
                    inv_cost_quoted += 155.03 * cubic_meter * line.e_qty
                    inv_sell_quoted += 218.07 * cubic_meter * line.e_qty
            elif (postal_code >= 5000 and postal_code <= 5199) or (
                postal_code >= 5900 and postal_code <= 5999
            ):  # Adelaide
                service_name = "Deliver-ME Direct (Into Premises) (50%)"

                if is_pallet and length <= 1.2 and width <= 1.2:
                    inv_cost_quoted += 287.36 * line.e_qty
                    inv_sell_quoted += 325.56 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.6:
                    inv_cost_quoted += 403.54 * line.e_qty
                    inv_sell_quoted += 591.11 * line.e_qty
                elif is_pallet and length <= 1.2 and width <= 1.85:
                    inv_cost_quoted += 403.54 * line.e_qty
                    inv_sell_quoted += 591.11 * line.e_qty
                else:
                    inv_cost_quoted += 184.67 * cubic_meter * line.e_qty
                    inv_sell_quoted += 257.59 * cubic_meter * line.e_qty

    if booking.pu_no_of_assists and int(booking.pu_no_of_assists) > 1:
        inv_cost_quoted += 30
        inv_sell_quoted += 30

    if booking.de_no_of_assists and int(booking.de_no_of_assists) > 1:
        inv_cost_quoted += 30
        inv_sell_quoted += 30

    return {"inv_cost_quoted": inv_cost_quoted, "inv_sell_quoted": inv_sell_quoted}
