def el0(param):
    if param["max_dimension"] >= 1.5 and param["max_dimension"] < 2.5:
        return {
            "name": "Excess Lengths (2.5m+)",
            "description": "",
            "value": 10,
        }
    else:
        return None


def el1(param):
    if param["max_dimension"] >= 2.5 and param["max_dimension"] < 6:
        return {
            "name": "Excess Lengths (4.0m+)",
            "description": "",
            "value": 50,
        }
    else:
        return None


# dummy value for below two
def el2(param):
    if param["max_dimension"] >= 6:
        return {
            "name": "Excess Lengths (6.0m+)",
            "description": "",
            "value": 200,
        }
    else:
        return None


def bdra0(param):
    if (
        param["de_to_address_type"].lower() == "residential"
        and param["max_item_weight"] >= 34
        and param["max_item_weight"] < 50
    ):
        return {
            "name": "Bulk Delivery to Residential Address - Average dead or cubic weight per item 34-49kg",
            "description": "",
            "value": 10,
        }
    else:
        return None


def bdra1(param):
    if (
        param["de_to_address_type"].lower() == "residential"
        and param["max_item_weight"] >= 50
        and param["max_item_weight"] < 75
    ):
        return {
            "name": "Bulk Delivery to Residential Address - Average dead or cubic weight per item 50-74kg",
            "description": "",
            "value": 20,
        }
    else:
        return None


def bdra2(param):
    if (
        param["de_to_address_type"].lower() == "residential"
        and param["max_item_weight"] >= 75
        and param["max_item_weight"] < 100
    ):
        return {
            "name": "Bulk Delivery to Residential Address - Average dead or cubic weight per item 75-99kg",
            "description": "",
            "value": 30,
        }
    else:
        return None


def bdra3(param):
    if (
        param["de_to_address_type"].lower() == "residential"
        and param["max_item_weight"] >= 100
    ):
        return {
            "name": "Bulk Delivery to Residential Address - Average dead or cubic weight per item 100kg or greater",
            "description": "",
            "value": 50,
        }
    else:
        return None


def ptl(param):
    if param["pu_tail_lift"] and int(param["pu_tail_lift"]) != 0:
        return {
            "name": "Tail-Lift Truck8(pickup)",
            "description": "",
            "value": 60,
        }
    else:
        return None


def dtl(param):
    if param["de_tail_lift"] and int(param["de_tail_lift"]) != 0:
        return {
            "name": "Tail-Lift Truck8(delivery)",
            "description": "",
            "value": 60,
        }
    else:
        return None


def hunter():
    return {
        "order": [bdra0, bdra1, bdra2, bdra3, ptl, dtl, el0, el1, el2],
        "line": [],
    }
