import pytz
from datetime import date, timedelta, datetime
from api.fp_apis.utils import get_etd_in_hour

SYDNEY_TZ = pytz.timezone("Australia/Sydney")
UTC_TZ = pytz.timezone("UTC")


def get_sydney_now_time(return_type="char"):
    sydney_tz = pytz.timezone("Australia/Sydney")
    sydney_now = sydney_tz.localize(datetime.utcnow())
    sydney_now = sydney_now + timedelta(hours=10)

    if return_type == "char":
        return sydney_now.strftime("%Y-%m-%d %H:%M:%S")
    elif return_type == "ISO":
        return sydney_now.strftime("%Y-%m-%dT%H:%M:%S")
    elif return_type == "datetime":
        return sydney_now


def convert_to_AU_SYDNEY_tz(time, type="datetime"):
    delta = timedelta(hours=10)

    if not time:
        return None

    if type == "datetime":
        try:
            sydney_time = SYDNEY_TZ.localize(time)
            sydney_time = sydney_time + delta
        except:
            sydney_time = time + delta
    else:
        sydney_time = (datetime.combine(date(2, 1, 1), time) + delta).time()

    return sydney_time


def convert_to_UTC_tz(time, type="datetime"):
    delta = timedelta(hours=10)

    if not time:
        return None

    if type == "datetime":
        try:
            sydney_time = UTC_TZ.localize(time)
            sydney_time = sydney_time - delta
        except:
            sydney_time = time - delta
    else:
        sydney_time = (datetime.combine(date(2, 1, 1), time) - delta).time()

    return sydney_time


def beautify_eta(json_results, quotes):
    """
    beautify eta as Days,
    i.e:
        3.51 -> 4 Days
        3.00 -> 3 Days
    """
    _results = []

    for index, result in enumerate(json_results):
        try:
            delta = float(result["eta"]) - round(float(result["eta"]))

            if delta != 0:
                result["readable_eta"] = f"{math.ceil(float(result['eta']))} days"
            else:
                result["readable_eta"] = f"{math.round(float(result['eta']))} days"
        except Exception as e:
            try:
                etd_in_hour = get_etd_in_hour(quotes[index]) / 24
                result["readable_eta"] = f"{math.ceil(etd_in_hour)} days"
            except Exception as e:
                pass

        if "readable_eta" in result and result["readable_eta"] == "1 days":
            result["readable_eta"] = "1 day"

        _results.append(result)

    return _results
