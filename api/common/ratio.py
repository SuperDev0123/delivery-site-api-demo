def _get_dim_amount(dim_uom):
    uom = dim_uom.lower()

    if uom in ["km", "kms", "kilometer", "kilometers"]:
        return 1000
    elif uom in ["m", "ms", "meter", "meters"]:
        return 1
    elif uom in ["cm", "cms", "centimeter", "centimeters"]:
        return 0.01
    elif uom in ["mm", "mms", "millimeter", "millimeters"]:
        return 0.001


def _get_weight_amount(weight_uom):
    uom = weight_uom.lower()

    if uom in ["t", "ts", "ton", "tons"]:
        return 1000
    elif uom in ["kg", "kgs", "kilogram", "kilograms"]:
        return 1
    elif uom in ["g", "gs", "gram", "grams"]:
        return 0.001


def get_ratio(uom1, uom2, type):
    if type == "dim":
        return _get_dim_amount(uom1.lower()) / _get_dim_amount(uom2.lower())
    elif type == "weight":
        return _get_weight_amount(uom1.lower()) / _get_weight_amount(uom2.lower())


def _m3_to_kg(booking_lines, m3_to_kg_factor):
    total_kgs = 0
    max_length = 0
    max_width = 0
    max_height = 0

    for item in booking_lines:
        length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength
        width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
        height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight

        max_length = length if max_length < length else max_length
        max_width = width if max_width < width else max_width
        max_height = height if max_height < height else max_height

    total_kgs += max_length * max_width * max_height * m3_to_kg_factor

    return total_kgs
