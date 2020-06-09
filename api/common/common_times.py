import pytz
from datetime import timedelta, datetime

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


def convert_to_AU_SYDNEY_tz(time):
    if not time:
        return None

    try:
        sydney_time = SYDNEY_TZ.localize(time)
        sydney_time = sydney_time + timedelta(hours=10)
    except:
        sydney_time = time + timedelta(hours=10)

    return sydney_time


def convert_to_UTC_tz(time):
    if not time:
        return None

    try:
        sydney_time = UTC_TZ.localize(time)
        sydney_time = sydney_time - timedelta(hours=10)
    except:
        sydney_time = time - timedelta(hours=10)

    return sydney_time
