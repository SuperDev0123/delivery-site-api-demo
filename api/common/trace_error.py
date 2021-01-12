import traceback

from django.conf import settings


def print():
    if settings.ENV in ["local"]:
        traceback.print_exc()
