import json
import logging
import requests

from django.core.management.base import BaseCommand

from api.models import (
    Bookings,
    Dme_status_history,
    FP_status_history,
    Dme_utl_fp_statuses,
    Utl_dme_status,
)
from api.fp_apis.utils import (
    get_dme_status_from_fp_status,
    get_status_category_from_status,
)


logger = logging.getLogger(__name__)

STATUS_TO_BE_EXCLUDED = [
    "Entered",
    "Ready for Despatch",
    "Ready for Booking",
    "Picking",
    "Picked",
    "Closed",
    "Cancelled",
]

TRANSIT_STATUSES = [
    "In Transit",
    "Returning",
    "Futile",
    "Partially Delivered",
    "Partially In Transit",
    "Delivery Delayed",
    "Scanned into Depot",
    "Carded",
    "Insufficient Address",
    "Picked Up",
    "On-Forwarded",
]


FPS_TO_BE_PROCESSED = ["TNT", "HUNTER", "SENDLE", "ALLIED"]

# PLUM & JasonL
CLIENTS_TO_BE_PROCESSED = [
    "461162D2-90C7-BF4E-A905-000000000004",
    "1af6bcd2-6148-11eb-ae93-0242ac130002",
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("----- Checking status_histories... -----")

        # Prepare data
        # bookings = (
        #     Bookings.objects.all()
        #     .filter(kf_client_id__in=CLIENTS_TO_BE_PROCESSED)
        #     .exclude(b_status__in=STATUS_TO_BE_EXCLUDED)
        #     .only(
        #         "id",
        #         "pk_booking_id",
        #         "b_bookingID_Visual",
        #         "vx_freight_provider",
        #         "b_status",
        #     )
        # )
        bookings = Bookings.objects.filter(b_bookingID_Visual="180007")
        bookings_cnt = bookings.count()
        print(f"    Bookings to process: {bookings_cnt}")

        pk_booking_ids = []
        for booking in bookings:
            pk_booking_ids.append(booking.pk_booking_id)

        dme_shs = Dme_status_history.objects.filter(fk_booking_id__in=pk_booking_ids)
        dme_shs = dme_shs.order_by("id")
        fp_shs = FP_status_history.objects.filter(booking__in=bookings)
        fp_shs = fp_shs.filter(is_active=True).order_by("id")
        status_mappings = Dme_utl_fp_statuses.objects.all()
        category_mappings = Utl_dme_status.objects.all()

        # Processing...
        for booking in bookings:
            b_fp_shs = []

            for fp_sh in fp_shs:
                if booking == fp_sh.booking:
                    b_fp_shs.append(fp_sh)

            expected_shs = get_expected_status_histories(
                booking, b_fp_shs, status_mappings, category_mappings
            )


def get_expected_status_histories(booking, fp_shs, status_mappings, category_mappings):
    fp_name = booking.vx_freight_provider.lower()
    old_category = "Booked"
    expected_shs = []

    for fp_sh in fp_shs:
        dme_status = get_dme_status_from_fp_status(
            fp_name, fp_sh.status, status_mappings
        )
        category = get_status_category_from_status(dme_status, category_mappings)

        if category and category != old_category:
            latest_expected_sh = expected_shs[:-1] if expected_shs else None
            status_old = (
                latest_expected_sh.status_last if latest_expected_sh else "Booked"
            )
            status_last = dme_status
            notes = f"{status_old} --> {status_last}"
            event_time_stamp = fp_sh.event_timestamp
            expected_shs.append(
                {
                    "status_old": status_old,
                    "status_last": status_last,
                    "notes": notes,
                    "event_time_stamp": event_timestamp,
                }
            )
            old_category = category

    print("@111 - ", expected_shs)


def get_dme_status_from_fp_status(fp_name, fp_status, status_mappings):
    rules = []
    status_info = None

    for status_mapping in status_mappings:
        if status_mapping.fp_name.lower() == fp_name:
            rules.append(status_mapping)

    if fp_name.lower() == "allied":
        for rule in rules:
            if "XXX" in rule.fp_lookup_status:
                fp_lookup_status = rule.fp_lookup_status.replace("XXX", "")

                if fp_lookup_status in fp_status:
                    status_info = rule
            elif rule.fp_lookup_status == fp_status:
                status_info = rule
    else:
        for rule in rules:
            if rules.fp_lookup_status == fp_status:
                status_info = rule

    try:
        return status_info.dme_status
    except Exception as e:
        message = f"@101 - Missing status rule: {fp_status}"
        print(message)


def get_status_category_from_status(status, category_mappings):
    if not status:
        return None

    for category_mapping in category_mappings:
        if category_mapping.dme_delivery_status == status:
            return utl_dme_status.dme_delivery_status_category

    message = f"#102 Category not found with this status: {status}"
    print(message)
    return None
