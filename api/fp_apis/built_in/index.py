import random
import logging

from api.models import Booking_lines
from api.fp_apis.built_in import century, camerons, toll, allied

logger = logging.getLogger("dme_api")


def get_pricing(fp_name, booking, booking_lines=[], is_pricing_only=False):
    LOG_ID = "[BIP]"  # BUILT-IN PRICING
    prices = []
    request_id = f"self-pricing-{str(random.randrange(0, 100000)).zfill(6)}"

    if not booking_lines:
        booking_lines = Booking_lines.objects.filter(
            fk_booking_id=booking.pk_booking_id, is_deleted=False
        )

    try:
        if fp_name.lower() == "camerons":
            prices = camerons.get_pricing(fp_name, booking, booking_lines)
        elif fp_name.lower() == "century":
            prices = century.get_pricing(fp_name, booking, booking_lines)
        elif fp_name.lower() == "toll":
            prices = toll.get_pricing(fp_name, booking, booking_lines)
        elif fp_name.lower() == "allied":
            prices = allied.get_pricing(fp_name, booking, booking_lines)
    except Exception as e:
        message = f"@800 {LOG_ID} {str(e)}"
        logger.info(message)
        pass

    return {
        "price": prices,
        "requestId": request_id,
    }