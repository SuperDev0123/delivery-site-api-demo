def el0(param):
    if param['max_dimension'] >= 1.5 and param['max_dimension'] < 2.5:
        return {
            'name': 'Excess Lengths: 2.5m up to/not incl. 4.0m13 ',
            'description': '',
            'value': 10
        }
    else:
        return None


def el1(param):
    if param['max_dimension'] >= 2.5 and param['max_dimension'] < 6:
        return {
            'name': 'Excess Lengths: 4.0m up to/not incl. 6.0m13 ',
            'description': '',
            'value': 50
        }
    else:
        return None


# dummy value for below two
def el2(param):
    if param["max_dimension"] >= 6:
        return {
            'name': 'Excess Lengths: 6.0m and greater13 ',
            'description': '',
            'value': 200
        }
    else:
        return None

def bdra0(param):
    if param['de_to_address_type'].lower() == 'residential' and param['max_average_weight'] >= 34 and param['max_average_weight'] < 50:
        return {
            'name': 'Bulk Delivery to Residential Address - Average dead or cubic weight per item 34-49kg',
            'description': '',
            'value': 10 
        }
    else:
        return None

def bdra1(param):
    if param['de_to_address_type'].lower() == 'residential' and param['max_average_weight'] >= 50 and param['max_average_weight'] < 75:
        return {
            'name': 'Bulk Delivery to Residential Address - Average dead or cubic weight per item 50-74kg',
            'description': '',
            'value': 20 
        }
    else:
        return None

def bdra2(param):
    if param['de_to_address_type'].lower() == 'residential' and param['max_average_weight'] >= 75 and param['max_average_weight'] < 100:
        return {
            'name': 'Bulk Delivery to Residential Address - Average dead or cubic weight per item 75-99kg',
            'description': '',
            'value': 30 
        }
    else:
        return None

def bdra3(param):
    if param['de_to_address_type'].lower() == 'residential' and param['max_average_weight'] >= 100:
        return {
            'name': 'Bulk Delivery to Residential Address - Average dead or cubic weight per item 100kg or greater',
            'description': '',
            'value': 50 
        }
    else:
        return None

def hunter():
    return {
        'order': [
            bdra0,
            bdra1,
            bdra2,
            bdra3
        ],
        'line': [
            el0,
            el1,
            el2,
        ]
    }
