def dgre(param):
    if param["has_dangerous_item"] and param.vx_service_name == "Road Express":
        return {
            "name": "Dangerous Goods (Road Express)",
            "description": "Surcharge per consignment. In addition, the MHP Fee will apply per item to each and all items consigned under the same consignment note where that consignment "
            + "contains Dangerous Goods, including any non-Dangerous Goods items consigned under that consignment note. (Dangerous Goods consignment notes are to contain Dangerous Goods items only.)",
            "value": 60 * param["total_qty"],
        }
    else:
        return None


def dgere(param):
    if param["has_dangerous_item"] and param.vx_service_name != "Road Express":
        return {
            "name": "Dangerous Goods (Road Express)",
            "description": "Surcharge per consignment. In addition, the MHP Fee will apply per item to each and all items consigned under the same consignment note where that consignment "
            + "contains Dangerous Goods, including any non-Dangerous Goods items consigned under that consignment note. (Dangerous Goods consignment notes are to contain Dangerous Goods items only.)",
            "value": 200 * param["total_qty"],
        }
    else:
        return None


# def ah(booking, booking_lines):

# def ph(booking, booking_lines):

# def rm(booking, booking_lines):

# if pickup address is remote_area:
#     return {
#         'name': 'Remote Area Pickup (RMP)',
#         'description': 'Pick-up from a remote area within Australia. Click here to view a list of our Remote Areas.',
#         'value': 30
#     }
# elif deliver to area is remote area:
#     return {
#         'name': 'Remote Area Delivery (RMD)',
#         'description': 'Delivery to a remote area within Australia. Click here to view a list of our Remote Areas.',
#         'value': 30
#     }
# else:
#     return None


def rsp(param):
    if param["pu_address_type"] == "residential":
        return {
            "name": "Residential Pickup (RSP)",
            "description": "Fee per consignment for pick up from a residential address4.",
            "value": 5,
        }
    else:
        return None


def rsp30(param):
    if (
        param["pu_address_type"] == "residential"
        and param["max_weight"] >= 30
        and param["max_weight"] < 100
    ):
        return {
            "name": "Heavyweight Residential Pickup (RSP30)",
            "description": "Fee per consignment for pick up from a residential address4 with a chargeable weight5 of 30kg and over, but less than 100kg."
            + "6 This fee will be applied in addition to any other fee or surcharge in relation to the consignment, including the existing Residential Delivery "
            + "Fee (RSD) and/or Residential Pickup Fee (RSP) of $5 per consignment for delivery to and/or pickup from a residential address4.",
            "value": 55,
        }
    else:
        return None


def rsp100(param):
    if param["pu_address_type"] == "residential" and param["max_weight"] >= 100:
        return {
            "name": "Heavyweight Residential Pickup (RSP100)",
            "description": "Fee per consignment for pick up from a residential address4 with a chargeable weight5 of 100kg and over."
            + "6 This fee will be applied in addition to any other fee or surcharge in relation to the consignment, including the existing "
            + "Residential Delivery Fee (RSD) and/or Residential Pickup Fee (RSP) of $5 per consignment for delivery to and/or pickup from a residential address4.",
            "value": 175,
        }
    else:
        return None


def rsd(param):
    if param["de_to_address_type"] == "residential":
        return {
            "name": "Residential Delivery (RSD)",
            "description": "Fee per consignment for delivery to a residential address4. ",
            "value": 5,
        }
    else:
        return None


def rsd30(param):
    if (
        param["de_to_address_type"] == "residential"
        and param["max_weight"] >= 30
        and param["max_weight"] < 100
    ):
        return {
            "name": "Heavyweight Residential Delivery (RSD30)",
            "description": "Fee per consignment for delivery from a residential address4 with a chargeable weight5 of 30kg and over, but less than 100kg. "
            + "6 This fee will be applied in addition to any other fee or surcharge in relation to the consignment, including the existing Residential Delivery "
            + "Fee (RSD) and/or Residential Pickup Fee (RSP) of $5 per consignment for delivery to and/or pickup from a residential address4.",
            "value": 55,
        }
    else:
        return None


def rsd100(param):
    if param["de_to_address_type"] == "residential" and param["max_weight"] >= 100:
        return {
            "name": "Heavyweight Residential Delivery (RSD100)",
            "description": "Fee per consignment for delivery from a residential address4 with a chargeable weight5 of 100kg and over."
            + "6 This fee will be applied in addition to any other fee or surcharge in relation to the consignment, including the existing Residential Delivery Fee (RSD) "
            + "and/or Residential Pickup Fee (RSP) of $5 per consignment for delivery to and/or pickup from a residential address4. "
            + "4 ’Residential address’ means a home or private residence, including locations where a business is operated from the home or private residence, "
            + "and/or a shipment in which the shipper has designated the delivery/pickup address as residential. "
            + "5 This fee will be applied to each consignment’s chargeable weight, which is the greater of the dead weight and the cubic weight, "
            + "calculated in accordance with the TNT Australia Pty Limited Terms and Conditions of Carriage and other services. "
            + "6 Weight limitations will be subject to TNT’s health and safety guidelines and/or operation constraints.",
            "value": 175,
        }
    else:
        return None


def os0(param):
    if param["max_dimension"] >= 1.5 and param["max_dimension"] < 2:
        return {
            "name": "Oversize Freight (OS0)",
            "description": "Oversize freight where any one dimension (length, height or width) exceeds 1.49 metres.",
            "value": 10,
        }
    else:
        return None


def os1(param):
    if param["max_dimension"] >= 2 and param["max_dimension"] < 3:
        return {
            "name": "Oversize Freight (OS1)",
            "description": "Oversize freight where any one dimension (length, height or width) exceeds 1.99 metres.",
            "value": 30,
        }
    else:
        return None


def os2(param):
    if param["max_dimension"] >= 3 and param["max_dimension"] < 4:
        return {
            "name": "Oversize Freight (OS2)",
            "description": "Oversize freight where any one dimension (length, height or width) exceeds 2.99 metres.",
            "value": 40,
        }
    else:
        return None


def os3(param):
    if param["max_dimension"] >= 4 and param["max_dimension"] < 5:
        return {
            "name": "Oversize Freight (OS3)",
            "description": "Oversize freight where any one dimension (length, height or width) exceeds 3.99 metres.",
            "value": 250,
        }
    else:
        return None


def os4(param):
    if param["max_dimension"] >= 5 and param["max_dimension"] < 6:
        return {
            "name": "Oversize Freight (OS4)",
            "description": "Oversize freight where any one dimension (length, height or width) exceeds 4.99 metres.",
            "value": 450,
        }
    else:
        return None


def os5(param):
    if param["max_dimension"] >= 6 and param["max_dimension"] < 25:
        return {
            "name": "Oversize Freight (OS5)",
            "description": "Oversize freight where any one dimension (length, height or width) exceeds 5.99 metres.",
            "value": 600,
        }
    else:
        return None


def lr(param):
    if (
        param["de_to_address_state"].lower() == "wa"
        and param["de_to_address_city"] != "Perth"
        and param["vx_service_name"]
        in ["Road Express", "Fashion Express", "Technology Express"]
    ):
        return {
            "name": "Western Australia Regional Surcharge(LR)",
            "description": "10% - Surcharge effective 06/01/2013 (where applicable)"
            + "For all shipments travelling to Western Australia regional/country locations, excluding Perth and applicable to the following services:"
            + "Road Express (XPDD) Fashion Express (FASH) Technology Express (COMP) Examples Sydney (SYD) to Tom Price (TPR) - Surcharge applies Brisbane (BNE) to Perth (PTH) - Surcharge doesn't apply "
            + "Perth (PTH) to Albany (ABY) - Surcharge applies Albany (ABY) t Perth (PTH) - Surcharge applies Perth (PTH) to Perth (PTH) - Surcharge doesn't apply "
            + "Perth (PTH) to Melbourne (MEL) - Surcharge doesn't apply",
            "value": "10%",
        }
    else:
        return None


def tnt():
    return [
        dgre,
        dgere,
        rsp,
        rsp30,
        rsp100,
        rsd,
        rsd30,
        rsd100,
        os0,
        os1,
        os2,
        os3,
        os4,
        os5,
        lr,
    ]
