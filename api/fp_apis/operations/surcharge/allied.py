import math
from api.models import FP_onforwarding
# def cw(param):
#     if :
#         return {
#             'name': 'Cubic Weight',
#             'description': 'All Allied Overnight Express rates are charged on the greater of either the dead weight or the cubic weight of the consignment. ' +
#                 'The cubic conversion factor is 250 kilograms per cubic metre of space.',
#             'value': 60 * param['total_qty']
#         }
#     else:
#         return None

# def lsc0(param):
#     if param['max_dimension'] >= 1.2 and param['max_dimension'] < 2.4:
#         return {
#             'name': 'Lengths [LSC] 1.20-2.39 metre',
#             'description': 'Items that exceed lenghts in any direction will attract a surcharge',
#             'value': 5.4
#         }
#     else:
#         return None

# def lsc1(param):
#     if param['max_dimension'] >= 2.4 and param['max_dimension'] < 3.6:
#         return {
#             'name': 'Lengths [LSC] 2.40-3.59 metre',
#             'description': 'Items that exceed lenghts in any direction will attract a surcharge',
#             'value': 11.93
#         }
#     else:
#         return None

# def lsc2(param):
#     if param['max_dimension'] >= 3.6 and param['max_dimension'] < 4.2:
#         return {
#             'name': 'Lengths [LSC] 3.6-4.19 metre',
#             'description': 'Items that exceed lenghts in any direction will attract a surcharge',
#             'value': 25.4
#         }
#     else:
#         return None

# def lsc3(param):
#     if param['max_dimension'] >= 4.2 and param['max_dimension'] < 4.8:
#         return {
#             'name': 'Lengths [LSC] 4.2-4.79 metre',
#             'description': 'Items that exceed lenghts in any direction will attract a surcharge',
#             'value': 88.61
#         }
#     else:
#         return None

# def lsc4(param):
#     if param['max_dimension'] >= 4.8 and param['max_dimension'] < 6:
#         return {
#             'name': 'Lengths [LSC] 4.8-5.59 metre',
#             'description': 'Items that exceed lenghts in any direction will attract a surcharge',
#             'value': 119.19
#         }
#     else:
#         return None

# def lsc5(param):
#     if param['max_dimension'] >= 6:
#         return {
#             'name': 'Lengths [LSC] over 6 metre',
#             'description': 'Items that exceed lenghts in any direction will attract a surcharge',
#             'value': 153.91
#         }
#     else:
#         return None

# def ws0(param):
#     if param['max_width'] > 1.1 and param['max_width'] <= 1.6:
#         return {
#             'name': 'Width [WS] 1.10-1.60 metre',
#             'description': 'Items that exceed width will attract a surcharge',
#             'value': 7.5
#         }
#     else:
#         return None

# def ws1(param):
#     if param['max_width'] > 1.6 and param['max_width'] <= 2.4:
#         return {
#             'name': 'Width [WS] 1.61-2.4 metre',
#             'description': 'Items that exceed width will attract a surcharge',
#             'value': 10.5
#         }
#     else:
#         return None

# def tl(param):
#     if param['is_tail_lift']:
#         return {
#             'name': 'Tail Lift [TL]',
#             'description': 'For deliveries requiring tail lifts',
#             'value': 44.07
#         }
#     else:
#         return None

# def tm(param):
#     if param['is_tail_lift']:
#         return {
#             'name': '2 Person Deliveries [2M]',
#             'description': 'For deliveries requiring additional helpers',
#             'value': '40.22 * hours'
#         }
#     else:
#         return None

# def tm(param):
#     if param['is_tail_lift']:
#         return {
#             'name': 'Minimum Pick up Fee [MPFEE]',
#             'description': 'A minimum pick up fee is invoked if the total transport charges on freight despatched at any one time ' +
#                 'is less than the minimum pickup fee. If this occurs, the difference between the transport charges and the fee is charged.',
#             'value': 31.26
#         }
#     else:
#         return None

# def hd0(param):
#     if param['de_to_address_type'] == 'residential' and param['max_weight'] < 22:
#         return {
#             'name': 'Home Deliveries [HD] - The Home delivery fee’s would be 40% less than what is shown, so we know it is not the standard price. ',
#             'description': 'For freight being delivered to residential addresses a surcharge per consignment under 22kgs (dead or cubic weight)',
#             'value': 10.6
#         }
#     else:
#         return None

# def hd1(param):
#     if param['de_to_address_type'] == 'residential' and param['max_weight'] >= 22 and param['max_weight'] < 55:
#         return {
#             'name': 'Home Deliveries [HD] - The Home delivery fee’s would be 40% less than what is shown, so we know it is not the standard price. ',
#             'description': 'For freight being delivered to residential addresses a surcharge per consignment between 23 and 55 kgs (dead or cubic weight)',
#             'value': 21.19
#         }
#     else:
#         return None

# def hd2(param):
#     if param['de_to_address_type'] == 'residential' and ((param['dead_weight'] >= 55 and param['dead_weight'] < 90) or (param['cubic_weight'] >= 55 and param['cubic_weight'] < 135)):
#         return {
#             'name': 'Home Deliveries [HD] - The Home delivery fee’s would be 40% less than what is shown, so we know it is not the standard price. ',
#             'description': 'For freight being delivered to residential addresses a surcharge per consignment over 90kgs dead weight or over 136 cubic weight will apply',
#             'value': 74.15
#         }
#     else:
#         return None

# def hd3(param):
#     if param['de_to_address_type'] == 'residential' and (param['dead_weight'] >= 90 or param['cubic_weight'] >= 135):
#         return {
#             'name': 'Home Deliveries [HD] - The Home delivery fee’s would be 40% less than what is shown, so we know it is not the standard price. ',
#             'description': 'For freight being delivered to residential addresses a surcharge per consignment over 90kgs dead weight or over 136 cubic weight will apply',
#             'value': 158.87
#         }
#     else:
#         return None

# dummy values for below 3
def op(param):
    dimensions = [param['max_length'], param['max_width'], param['max_height']]
    dimensions.sort()
    limits = [1.4, 1.2, 1.2]
    pallet_cube = 1.4 * 1.2 * 1.2
    limits.sort()
    if dimensions[0] > limits[0] or dimensions[1] > limits[1] or dimensions[2] > limits[2] or param['max_weight'] > 500:
        return {
            'name': 'Oversize Pallets',
            'description': 'Standard pallet sizes are measured at a maximum of 1.2m x 1.2m x 1.4m and weighed at a maximum of 500 kilograms. ' +
                'Pallets greater than will incur oversize pallet charges, in line with the number of pallet spaces occupied, charged in full ' +
                'pallets. An additional pallet charge will apply.',
            'value': (max(math.ceil(param['total_cubic'] / pallet_cube), math.ceil(param['max_weight'] / 500)) - 1) * 'base_charge'
        }
    else:
        return None

# def bbs(param):
#     if param['max_dimension'] >= 1.4:
#         return {
#             'name': 'Big Bulky Surcharge',
#             'description': 'Where freight travelling extends beyond a pallet space, in any direction, then a surcharge equivalent to double ' + 
#                 'the chargeable weight (the greater of either the cubic or dead weight) of the item travelling is charged.',
#             'value': 0.1 * param['dead_weight']
#         }
#     else:
#         return None

# def mcsp(param):
#     if param['max_weight'] > 175:
#         return {
#             'name': 'Minimum Charge-Skids/ Pallets',
#             'description': 'The minimum charge for a skid is 175 kilograms, and for a pallet is 350 kilograms.  Please note that even if your ' +
#                 'freight is not presented on a pallet or skid, these charges may be applied if items cannot be lifted by one person.',
#             'value': 0.11 * param['dead_weight']
#         }
#     else:
#         return None


# def pd(param):
#     if param['max_dimension'] >= 1.4 or param['max_weight'] > 500:
#         return {
#             'name': 'Pallet Deliveries',
#             'description': 'If items are loaded onto a pallet, and the pallet is to be delivered intact, a full pallet charges will be charged. ' +
#                 'A pallet charge will be made when it takes up a lift space, eg. nothing can be loaded on top of the pallet.',
#             'value': '0.12 unknown'
#         }
#     else:
#         return None

def ofpu(param):
    try:
        pu_onforwarding = FP_onforwarding.objects.get(fp_company_name='Allied', state=param['pu_address_state'], postcode=param['pu_address_postcode'], suburb=param['pu_address_suburb'])
        return {
            'name': 'Onforwarding(Pickup)',
            'description': 'All our rates apply from pick up and to drop, where a delivery made to a nominated regional, country or remote location, ' +
                'as outlined on our Onforwarding matrix, an onforwarding surcharge is applicable.  Please contact Allied Express for a copy of this matrix.',
            'value': pu_onforwarding.price_per_kg
        }
    except Exception as e:
        return None

def ofde(param):
    try:
        de_to_onforwarding = FP_onforwarding.objects.get(fp_company_name='Allied', state=param['de_to_address_state'], postcode=param['de_to_address_postcode'], suburb=param['de_to_address_suburb'])
        return {
            'name': 'Onforwarding(Delivery)',
            'description': 'All our rates apply from pick up and to drop, where a delivery made to a nominated regional, country or remote location, ' +
                'as outlined on our Onforwarding matrix, an onforwarding surcharge is applicable.  Please contact Allied Express for a copy of this matrix.',
            'value': de_onforwarding.price_per_kg
        }
    except Exception as e:
        return None
   
def allied():
    return [
        # op,
        ofpu,
        ofde
        # bbs,
        # mcsp,
        # pd
    ]
