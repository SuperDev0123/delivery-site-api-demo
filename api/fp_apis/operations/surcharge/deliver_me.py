from cgi import parse_multipart


def jasonl():
    def line_fee(param):
        pu_postal = int(param["pu_address_postcode"])
        de_postal = int(param["de_to_address_postcode"])
        pallet_w = param["width"]
        pallet_l = param["length"]
        is_pallet = param["is_pallet"]

        if is_pallet:
            if (de_postal >= 3000 and de_postal <= 3207) or (
                de_postal >= 8000 and de_postal <= 8499
            ):  # Melbourne
                if pallet_w <= 1.2 and pallet_l <= 1.2:
                    return {
                        "name": "Pallet 1.2W * 1.2L or less (SYD - MEL)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - MEL (65%)",
                        "value": 156.15,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.6:
                    return {
                        "name": "Up to Pallet 1.2W * 1.6L (SYD - MEL)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - MEL (50%)",
                        "value": 204.23,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.85:
                    return {
                        "name": "Up to Pallet 1.2W * 1.6L (SYD - MEL)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - MEL (50%)",
                        "value": 204.23,
                    }
            elif (de_postal >= 4000 and de_postal <= 4207) or (
                de_postal >= 9000 and de_postal <= 9499
            ):  # Brisbane
                if pallet_w <= 1.2 and pallet_l <= 1.2:
                    return {
                        "name": "Pallet 1.2W * 1.2L or less (SYD - BRIS)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (65%)",
                        "value": 207.73,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.6:
                    return {
                        "name": "Up to Pallet 1.2W * 1.6L (SYD - BRIS)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (50%)",
                        "value": 355.45,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.85:
                    return {
                        "name": "Up to Pallet 1.2W * 1.85L (SYD - BRIS)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (50%)",
                        "value": 355.45,
                    }
            elif (de_postal >= 5000 and de_postal <= 5199) or (
                de_postal >= 5900 and de_postal <= 5999
            ):  # Adelaide
                if pallet_w <= 1.2 and pallet_l <= 1.2:
                    return {
                        "name": "Pallet 1.2W * 1.2L or less (SYD - ADE)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - ADE (65%)",
                        "value": 249.39,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.6:
                    return {
                        "name": "Up to Pallet 1.2W * 1.6L (SYD - ADE)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - ADE (50%)",
                        "value": 438.79,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.85:
                    return {
                        "name": "Up to Pallet 1.2W * 1.85L (SYD - ADE)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - ADE (50%)",
                        "value": 438.79,
                    }
        else:
            if (de_postal >= 3000 and de_postal <= 3207) or (
                de_postal >= 8000 and de_postal <= 8499
            ):  # Melbourne
                return {
                    "name": "Non Pallet, per CBM (SYD - MEL)",
                    "description": "Deliver-ME Direct (Into Premises) SYD - MEL (65%)",
                    "value": 131.54 * param["one_item_cubic_meter"],
                }
            elif (de_postal >= 4000 and de_postal <= 4207) or (
                de_postal >= 9000 and de_postal <= 9499
            ):  # Brisbane
                return {
                    "name": "Non Pallet, per CBM (SYD - BRIS)",
                    "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (50%)",
                    "value": 206.55 * param["one_item_cubic_meter"],
                }
            elif (de_postal >= 5000 and de_postal <= 5199) or (
                de_postal >= 5900 and de_postal <= 5999
            ):  # Adelaide
                return {
                    "name": "Non Pallet, per CBM (SYD - ADE)",
                    "description": "Deliver-ME Direct (Into Premises) SYD - ADE (50%)",
                    "value": 247.89 * param["one_item_cubic_meter"],
                }

    def pu_tail_fee(param):
        if param["pu_tail_lift"] and int(param["pu_tail_lift"]) > 1:
            return {
                "name": "PU tail lift man (Pickup)",
                "description": "Additional Service fee for 2 man",
                "value": 30,
            }
        else:
            return None

    def de_tail_fee(param):
        if param["de_tail_lift"] and int(param["de_tail_lift"]) > 1:
            return {
                "name": "DE tail lift man (Delivery)",
                "description": "Additional Service fee for 2 man",
                "value": 30,
            }
        else:
            return None

    return {
        "order": [pu_tail_fee, de_tail_fee],
        "line": [line_fee],
    }


def bsd():
    def line_fee(param):
        pu_postal = int(param["pu_address_postcode"])
        de_postal = int(param["de_to_address_postcode"])
        pallet_w = param["width"]
        pallet_l = param["length"]
        is_pallet = param["is_pallet"]

        if is_pallet:
            if (de_postal >= 3000 and de_postal <= 3207) or (
                de_postal >= 8000 and de_postal <= 8499
            ):  # Melbourne
                if pallet_w <= 1.2 and pallet_l <= 1.2:
                    return {
                        "name": "Pallet 1.2W * 1.2L or less (SYD - MEL)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - MEL (65%)",
                        "value": 168.15,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.6:
                    return {
                        "name": "Up to Pallet 1.2W * 1.6L (SYD - MEL)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - MEL (50%)",
                        "value": 216.23,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.85:
                    return {
                        "name": "Up to Pallet 1.2W * 1.85L (SYD - MEL)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - MEL (50%)",
                        "value": 216.23,
                    }
            elif (de_postal >= 4000 and de_postal <= 4207) or (
                de_postal >= 9000 and de_postal <= 9499
            ):  # Brisbane
                if pallet_w <= 1.2 and pallet_l <= 1.2:
                    return {
                        "name": "Pallet 1.2W * 1.2L or less (SYD - BRIS)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (65%)",
                        "value": 219.73,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.6:
                    return {
                        "name": "Up to Pallet 1.2W * 1.6L (SYD - BRIS)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (50%)",
                        "value": 367.45,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.85:
                    return {
                        "name": "Up to Pallet 1.2W * 1.85L (SYD - BRIS)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (50%)",
                        "value": 367.45,
                    }
            elif (de_postal >= 5000 and de_postal <= 5199) or (
                de_postal >= 5900 and de_postal <= 5999
            ):  # Adelaide
                if pallet_w <= 1.2 and pallet_l <= 1.2:
                    return {
                        "name": "Pallet 1.2W * 1.2L or less (SYD - ADE)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - ADE (65%)",
                        "value": 261.39,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.6:
                    return {
                        "name": "Up to Pallet 1.2W * 1.6L (SYD - ADE)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - ADE (50%)",
                        "value": 450.79,
                    }
                elif pallet_w <= 1.2 and pallet_l <= 1.85:
                    return {
                        "name": "Up to Pallet 1.2W * 1.85L (SYD - ADE)",
                        "description": "Deliver-ME Direct (Into Premises) SYD - ADE (50%)",
                        "value": 450.79,
                    }
        else:
            if (de_postal >= 3000 and de_postal <= 3207) or (
                de_postal >= 8000 and de_postal <= 8499
            ):  # Melbourne
                return {
                    "name": "Non Pallet CBM (SYD - MEL)",
                    "description": "Deliver-ME Direct (Into Premises) SYD - MEL (65%)",
                    "value": 143.54,
                }
            elif (de_postal >= 4000 and de_postal <= 4207) or (
                de_postal >= 9000 and de_postal <= 9499
            ):  # Brisbane
                return {
                    "name": "Non Pallet CBM (SYD - BRIS)",
                    "description": "Deliver-ME Direct (Into Premises) SYD - BRIS (50%)",
                    "value": 218.55,
                }
            elif (de_postal >= 5000 and de_postal <= 5199) or (
                de_postal >= 5900 and de_postal <= 5999
            ):  # Adelaide
                return {
                    "name": "Non Pallet CBM (SYD - ADE)",
                    "description": "Deliver-ME Direct (Into Premises) SYD - ADE (50%)",
                    "value": 255.89,
                }

    def pu_tail_fee(param):
        if param["pu_tail_lift"] and int(param["pu_tail_lift"]) > 1:
            return {
                "name": "Additional fee (Pickup)",
                "description": "Additional Service fee for 2 man",
                "value": 30,
            }
        else:
            return None

    def de_tail_fee(param):
        if param["de_tail_lift"] and int(param["de_tail_lift"]) > 1:
            return {
                "name": "Additional fee (Delivery)",
                "description": "Additional Service fee for 2 man",
                "value": 30,
            }
        else:
            return None

    return {
        "order": [pu_tail_fee, de_tail_fee],
        "line": [line_fee],
    }
