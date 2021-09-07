def ptl(param):
    if int(param["pu_tail_lift"]) != 0:
        return {
            "name": "Tail-Gate(pickup)",
            "description": "Applied when there is tail lift pickup. If service is express, then 110% is applied",
            "value": 52.9396 * 1.1 if 'express' in param['vx_service_name'].lower() else 52.9396,
        }
    else:
        return None


def dtl(param):
    if int(param["de_tail_lift"]) != 0:
        return {
            "name": "Tail-Gate(delivery)",
            "description": "Applied when there is tail lift delivery. If service is express, then 110% is applied",
            "value": 52.9396 * 1.1 if 'express' in param['vx_service_name'].lower() else 52.9396,
        }
    else:
        return None


def camerons():
    return {
        "order": [ptl, dtl],
        "line": [],
    }
