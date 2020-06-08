import pytz
from datetime import timedelta, datetime


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
    sydney_tz = pytz.timezone("Australia/Sydney")

    try:
        sydney_time = sydney_tz.localize(time)
    except:
        sydney_time = sydney_time + timedelta(hours=10)

    return sydney_time


def convert_to_UTC_tz(time):
    sydney_tz = pytz.timezone("UTC")

    try:
        sydney_time = sydney_tz.localize(time)
    except:
        print("@1 - ", time)
        sydney_time = time - timedelta(hours=10)

    return sydney_time
