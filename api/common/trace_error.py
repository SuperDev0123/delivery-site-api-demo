import traceback

from django.conf import settings


def print():
    if settings.ENV not in ["local"]:
        traceback.print_exc()
