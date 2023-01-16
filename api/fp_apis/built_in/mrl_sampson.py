import logging
import math
import traceback

from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter
from api.fp_apis.utils import get_m3_to_kg_factor
from api.common.constants import PALLETS, SKIDS

logger = logging.getLogger(__name__)

class Quote:
  def __init__(self, from_zone, to_zone, from_suburb, to_suburb, basic_price, per_price, minimum_price, cubic, rebate):
    self.from_zone = from_zone
    self.to_zone = to_zone
    self.from_suburb = from_suburb
    self.to_suburb = to_suburb
    self.basic_price = basic_price
    self.per_price = per_price
    self.minimum_price = minimum_price
    self.cubic = cubic
    self.rebate = rebate

QUOTE_LIST = [
    Quote('SYD', 'MELD', 'SMITHFIELD', 'DERRIMUT DEPOT', 12.50, 0.1145, 65, 333, 2.5),
    Quote('SYD', 'MEL', 'SMITHFIELD', 'MELBOURNE METRO', 12.50, 0.1150, 150, 333, 2.5),
    Quote('SYD', 'BNED', 'SMITHFIELD', 'ARCHERFIELD DEPOT', 12.50, 0.2150, 65, 333, 2.5),
    Quote('SYD', 'BNE', 'SMITHFIELD', 'BRISBANE METRO', 12.50, 0.2550, 150, 333, 2.5),
    Quote('MEL', 'SYD', 'DERRIMUT DEPOT', 'SMITHFIELD', 12.50, 0.2150, 70, 333, 2.5),
    Quote('SYD', 'ADLD', 'SMITHFIELD', 'Green Fields DEPOT', 12.50, 0.3250, 90, 333, 2.5),
    Quote('SYD', 'ADL', 'SMITHFIELD', 'ADELAIDE METRO', 12.50, 0.3750, 150, 333, 2.5),
    Quote('SYD', 'PERD', 'SMITHFIELD', 'Welshpool DEPOT', 12.50, 0.8550, 180, 333, 2.5),
    Quote('SYD', 'PER', 'SMITHFIELD', 'PERTH METRO', 12.50, 0.8950, 250, 333, 2.5),
]
    
def can_use(booking):
    for quote in QUOTE_LIST:
       if(quote.from_suburb.lower() == booking.pu_Address_Suburb.lower() and quote.to_suburb.lower() == booking.de_To_Address_Suburb.lower()):
           return True
    return False

def get_value_by_formula(booking_lines, booking):
    net_price = 0
    for quote in QUOTE_LIST:
        if(quote.from_suburb.lower() == booking.pu_Address_Suburb.lower() and quote.to_suburb.lower() == booking.de_To_Address_Suburb.lower()):
            total_qty = 0
            dead_weight, cubic_weight = 0, 0
            m3_to_kg_factor = 333

            for item in booking_lines:
                dead_weight += (
                    item.e_weightPerEach * _get_weight_amount(item.e_weightUOM) * item.e_qty
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
                total_qty += item.e_qty

            net_price = quote.basic_price or 0
            chargable_weight = dead_weight if dead_weight > cubic_weight else cubic_weight
            net_price += float(quote.per_price or 0) * math.ceil(chargable_weight)

    return net_price

