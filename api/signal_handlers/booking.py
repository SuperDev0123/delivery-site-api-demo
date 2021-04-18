import logging
from datetime import datetime

from api.models import Bookings, Booking_lines, Api_booking_confirmation_lines
from api.fp_apis.utils import get_status_category_from_status

logger = logging.getLogger("dme_api")


def pre_save_handler(instance):
    if instance.id is None:  # new object will be created
        pass

    else:
        previous = Bookings.objects.get(id=instance.id)

        if (
            previous.dme_status_detail != instance.dme_status_detail
        ):  # field will be updated
            instance.dme_status_detail_updated_by = "user"
            instance.prev_dme_status_detail = previous.dme_status_detail
            instance.dme_status_detail_updated_at = datetime.now()

        if previous.b_status != instance.b_status:
            # Set Booking's status category
            instance.b_booking_Category = get_status_category_from_status(
                instance.b_status
            )

            try:
                if instance.b_status == "In Transit":
                    booking_Lines_cnt = Booking_lines.objects.filter(
                        fk_booking_id=instance.pk_booking_id
                    ).count()
                    fp_scanned_cnt = Api_booking_confirmation_lines.objects.filter(
                        fk_booking_id=instance.pk_booking_id, tally__gt=0
                    ).count()

                    dme_status_detail = ""
                    if (
                        instance.b_given_to_transport_date_time
                        and not instance.fp_received_date_time
                    ):
                        dme_status_detail = "In transporter's depot"
                    if instance.fp_received_date_time:
                        dme_status_detail = "Good Received by Transport"

                    if fp_scanned_cnt > 0 and fp_scanned_cnt < booking_Lines_cnt:
                        dme_status_detail = dme_status_detail + " (Partial)"

                    instance.dme_status_detail = dme_status_detail
                    instance.dme_status_detail_updated_by = "user"
                    instance.prev_dme_status_detail = previous.dme_status_detail
                    instance.dme_status_detail_updated_at = datetime.now()
                elif instance.b_status == "Delivered":
                    instance.dme_status_detail = ""
                    instance.dme_status_detail_updated_by = "user"
                    instance.prev_dme_status_detail = previous.dme_status_detail
                    instance.dme_status_detail_updated_at = datetime.now()
            except Exception as e:
                logger.info(f"Error 515 {e}")
                pass
