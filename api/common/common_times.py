import pytz
from datetime import timedelta, datetime


def get_sydney_now_time(return_type="char"):
    # sydney_tz = pytz.timezone("Australia/Sydney")
    # sydney_now = sydney_tz.localize(datetime.utcnow())
    # sydney_now = sydney_now + timedelta(hours=10)
    sydney_now = datetime.now()

    if return_type == "char":
        return sydney_now.strftime("%Y-%m-%d %H:%M:%S")
    elif return_type == "ISO":
        return sydney_now.strftime("%Y-%m-%dT%H:%M:%S")
    elif return_type == "datetime":
        return sydney_now
