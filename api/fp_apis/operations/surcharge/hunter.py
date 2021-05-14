def el0(param):
    if param['max_dimension'] >= 2.5 and param['max_dimension'] < 4:
        return {
            'name': 'Excess Lengths: 2.5m up to/not incl. 4.0m13 ',
            'description': '',
            'value': 50
        }
    else:
        return None

def el1(param):
    if param['max_dimension'] >= 4 and param['max_dimension'] < 6:
        return {
            'name': 'Excess Lengths: 4.0m up to/not incl. 6.0m13 ',
            'description': '',
            'value': 100
        }
    else:
        return None

# dummy value for below two
def el2(param):
    if param['max_dimension'] >= 6:
        return {
            'name': 'Excess Lengths: 6.0m and greater13 ',
            'description': '',
            'value': 150
        }
    else:
        return None

def rsd(param):
    if param['de_to_address_type'] == 'residential':
        return {
            'name': 'Deliveries to Private Addresses',
            'description': '',
            'value': 10 
        }
    else:
        return None

def hunter():
    return [
        el0,
        el1,
        el2,
        rsd
    ]
