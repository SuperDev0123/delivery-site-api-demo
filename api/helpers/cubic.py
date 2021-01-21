def get_cubic_meter(length, width, height, uom="METER", qty=1):
    value = 0

    if uom.upper() in ["MM", "MILIMETER"]:
        value = qty * length * width * height / 1000000000
    elif uom.upper() in ["CM", "CENTIMETER"]:
        value = qty * length * width * height / 1000000
    elif uom.upper() in ["M", "METER"]:
        value = qty * length * width * height

    return value
