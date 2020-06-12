import pytz
from datetime import date, timedelta, datetime

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
