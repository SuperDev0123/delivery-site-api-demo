def _get_dim_amount(dim_uom):
    uom = dim_uom.lower()

    if uom == "km" or uom == "kms" or uom == "kilometer" or uom == "kilometers":
        return 1000
    elif uom == "m" or uom == "ms" or uom == "meter" or uom == "meters":
        return 1
    elif uom == "cm" or uom == "cms" or uom == "centimeter" or uom == "centimeters":
        return 0.01
    elif uom == "mm" or uom == "mms" or uom == "millimeter" or uom == "millimeters":
        return 0.001


def _get_weight_amount(weight_uom):
    uom = weight_uom.lower()

    if uom == "t" or uom == "ts" or uom == "ton" or uom == "tons":
        return 1000
    elif uom == "kg" or uom == "kgs" or uom == "kilogram" or uom == "kilograms":
        return 1
    elif uom == "g" or uom == "gs" or uom == "gram" or uom == "grams":
        return 0.001


# type: dim, weight
def get_ratio(uom1, uom2, type):
    if type == "dim":
        return _get_dim_amount(uom1.lower()) / _get_dim_amount(uom2.lower())
    elif type == "weight":
        return _get_weight_amount(uom1.lower()) / _get_weight_amount(uom2.lower())
