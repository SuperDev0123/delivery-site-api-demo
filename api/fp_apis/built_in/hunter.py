import math
import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *
from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.common.constants import PALLETS
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.utils import get_m3_to_kg_factor

logger = logging.getLogger(__name__)


def get_pricing(fp_name, booking, booking_lines, pu_zones, de_zones):
    LOG_ID = "[BIP HUNTER]"  # BUILT-IN PRICING
    pricies = []

    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]
    pu_zone = get_zone_code(booking.pu_Address_PostalCode, fp, pu_zones)
    de_zone = get_zone_code(booking.de_To_Address_PostalCode, fp, de_zones)
    if not pu_zone or not de_zone:
        raise Exception(
            f"Not supported postal_code. [PU: {booking.pu_Address_PostalCode}({pu_zone}), DE: {booking.de_To_Address_PostalCode}({de_zone})]"
        )
    fp_rules = FP_pricing_rules.objects.filter(freight_provider_id=fp.id,pu_zone=pu_zone,de_zone=de_zone).order_by("id")
    if not fp_rules: 
        return pricies

    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {service_type.upper()}")

        # rules = FP_pricing_rules.objects.filter(
        #     freight_provider_id=fp.id,
        #     service_type=service_type,
        #     pu_zone=pu_zone,
        #     de_zone=de_zone,
        # ).order_by("id")
        rules = []
        for fp_rule in fp_rules:
            if (fp_rule.service_type.lower() == service_type.lower()):
                rules.append(fp_rule)
        logger.info(
            f"@830 {LOG_ID} Filtered Addresses: {len(rules)}, PU, DE zone: {pu_zone}, {de_zone}"
        )

        kg_price = 0
        pallet_price = 0
        kg_lines = []
        pallet_lines = []
        for line in booking_lines:
            if line.e_type_of_packaging.upper() in PALLETS:
                pallet_lines.append(line)
            else:
                kg_lines.append(line)

        if kg_lines:  # For KG lines
            # Weight Filter
            logger.info(
                f"{LOG_ID} Applying weight filter... rules cnt: {len(rules)}"
            )
            rules = weight_filter(kg_lines, rules, fp)
            logger.info(f"{LOG_ID} Filtered rules - {rules}")
            if not rules:
                continue

            cost = rules[0].cost
            logger.info(f"{LOG_ID} Final cost - {cost}")
            net_price = cost.basic_charge or 0
            m3_to_kg_factor = 250
            dead_weight, cubic_weight = 0, 0

            for item in kg_lines:
                dead_weight += (
                    item.e_weightPerEach
                    * _get_weight_amount(item.e_weightUOM)
                    * item.e_qty
                )
                cubic_weight += (
                    get_cubic_meter(
                        item.e_dimLength,
                        item.e_dimWidth,
                        item.e_dimHeight,
                        item.e_dimUOM,
                        item.e_qty,
                    )
                    * m3_to_kg_factor
                )

            chargable_weight = math.ceil(
                dead_weight if dead_weight > cubic_weight else cubic_weight
            )
            net_price += float(cost.per_UOM_charge or 0) * (
                chargable_weight - (cost.start_qty or 0)
            )
            logger.info(
                f"{LOG_ID} cost: ({cost.basic_charge, cost.per_UOM_charge}), chargable_weight: {chargable_weight}"
            )

            if cost.min_charge and net_price < cost.min_charge:
                net_price = cost.min_charge

            kg_price = net_price

        if pallet_lines:  # For Pallet lines
            # Size(dim) Filter
            if fp.rule_type.rule_type_code in ["rule_type_01", "rule_type_02"]:
                rules = dim_filter(booking, pallet_lines, rules, fp)

                if not rules:
                    continue

            net_price = 0
            logger.info(f"{LOG_ID} {fp_name.upper()} - filtered rules - {rules}")
            rules = weight_filter(pallet_lines, rules, fp)
            cost = find_cost(pallet_lines, rules, fp)
            logger.info(f"{LOG_ID} Final cost - {cost}")
            net_price = cost.basic_charge
            dead_weight, cubic_weight = 0, 0

            for item in pallet_lines:
                dead_weight += (
                    item.e_weightPerEach
                    * _get_weight_amount(item.e_weightUOM)
                    * item.e_qty
                )
                dim_amount = _get_dim_amount(item.e_dimUOM)
                weight_amount = _get_weight_amount(item.e_weightUOM)
                m3_to_kg_factor = get_m3_to_kg_factor(
                    fp_name="hunter",
                    data={
                        "is_pallet": True,
                        "item_length": dim_amount * item.e_dimLength,
                        "item_width": dim_amount * item.e_dimWidth,
                        "item_height": dim_amount * item.e_dimHeight,
                        "item_dead_weight": weight_amount * item.e_weightPerEach,
                    },
                )
                cubic_weight += (
                    get_cubic_meter(
                        item.e_dimLength,
                        item.e_dimWidth,
                        item.e_dimHeight,
                        item.e_dimUOM,
                        item.e_qty,
                    )
                    * m3_to_kg_factor
                )

            chargable_weight = math.ceil(
                dead_weight if dead_weight > cubic_weight else cubic_weight
            )
            net_price += float(cost.per_UOM_charge or 0) * (
                chargable_weight - (cost.start_qty or 0)
            )
            logger.info(
                f"{LOG_ID} cost: #{cost}({cost.basic_charge, cost.per_UOM_charge}), chargable_weight: {chargable_weight}"
            )

            if cost.min_charge and net_price < cost.min_charge:
                net_price = cost.min_charge

            pallet_price = net_price

        logger.info(f"{LOG_ID} KG price: {kg_price}, Pallet price: {pallet_price}")
        rule = list(filter(lambda rule: rule.cost_id == cost.id, rules))[0]
        if not rule.etd:
            continue
        price = {
            "netPrice": kg_price + pallet_price,
            "totalTaxes": 0,
            "serviceName": f"{rule.service_type}",
            "etd": rule.etd.fp_delivery_time_description,
        }
        pricies.append(price)

    return pricies
