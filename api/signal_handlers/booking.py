import logging
from datetime import datetime

from django.conf import settings

from api.models import (
    Bookings,
    Booking_lines,
    Api_booking_confirmation_lines,
    API_booking_quotes,
)
from api.fp_apis.utils import get_status_category_from_status
from api.operations.labels.index import build_label

logger = logging.getLogger(__name__)

if settings.ENV == "local":
    S3_URL = "./static"
elif settings.ENV == "dev":
    S3_URL = "/opt/s3_public"
elif settings.ENV == "prod":
    S3_URL = "/opt/s3_public"


def pre_save_handler(instance):
    LOG_ID = "[BOOKING PRE SAVE]"
    if instance.id is None:  # new object will be created
        pass

    else:
        logger.info(f"{LOG_ID} Booking PK: {instance.id}")
        old = Bookings.objects.get(id=instance.id)

        if old.dme_status_detail != instance.dme_status_detail:  # field will be updated
            instance.dme_status_detail_updated_by = "user"
            instance.prev_dme_status_detail = old.dme_status_detail
            instance.dme_status_detail_updated_at = datetime.now()

        if old.b_status != instance.b_status:
            # Set Booking's status category
            instance.b_status_category = get_status_category_from_status(
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
                    instance.prev_dme_status_detail = old.dme_status_detail
                    instance.dme_status_detail_updated_at = datetime.now()
                elif instance.b_status == "Delivered":
                    instance.dme_status_detail = ""
                    instance.dme_status_detail_updated_by = "user"
                    instance.prev_dme_status_detail = old.dme_status_detail
                    instance.dme_status_detail_updated_at = datetime.now()
            except Exception as e:
                logger.info(f"#505 {LOG_ID} Error {e}")
                pass


def post_save_handler(instance):
    LOG_ID = "[BOOKING POST SAVE]"
    logger.info(f"{LOG_ID} Booking PK: {instance.id}")

    try:
        if (
            instance.vx_freight_provider
            and "[REBUILD_REQUIRED]" in instance.z_label_url
        ):
            # Check if pricings exist for selected FP
            quotes = API_booking_quotes.objects.filter(
                fk_booking_id=instance.pk_booking_id,
                freight_provider__iexact=instance.vx_freight_provider,
            ).order_by("-fee")

            if not quotes:
                instance.b_error_Capture = "Quote doen't exist"

                if instance.z_label_url:
                    instance.z_label_url = instance.z_label_url[18:]

                instance.save()
                return

            # Mapping Pircing info to Booking
            quote = quotes.first()
            instance.vx_account_code = quote.account_code
            instance.vx_serviceName = quote.service_name
            instance.v_service_Type = quote.service_code
            instance.inv_cost_quoted = quote.fee * (1 + quote.mu_percentage_fuel_levy)
            instance.inv_sell_quoted = quote.client_mu_1_minimum_values
            instance.api_booking_quote = quote

            # Build Label
            _fp_name = instance.vx_freight_provider.lower()
            file_path = f"{S3_URL}/pdfs/{_fp_name}_au/"

            if instance.b_client_name == "Jason L":
                lines = Booking_lines.objects.filter(
                    fk_booking_id=instance.pk_booking_id,
                    is_deleted=False,
                    sscc__isnull=False,
                )

                if lines.count() == 0:
                    instance.z_label_url = None
                    instance.save()
                    return instance

                sscc_lines = {}

                for line in lines:
                    if line.sscc not in sscc_lines:
                        sscc_lines[line.sscc] = [line]
                    else:
                        sscc_lines[line.sscc].append(line)

                labeled_ssccs = []
                for sscc in sscc_lines:
                    if sscc in labeled_ssccs:
                        continue

                    file_path, file_name = build_label(
                        booking=instance,
                        file_path=file_path,
                        lines=sscc_lines[sscc],
                        label_index=0,
                        sscc=sscc,
                        one_page_label=True,
                    )

                    # Convert label into ZPL format
                    logger.info(
                        f"@369 {LOG_ID} converting LABEL({file_path}/{file_name}) into ZPL format..."
                    )
                    label_url = f"{file_path}/{file_name}"
            else:
                _fp_name = instance.vx_freight_provider.lower()
                file_path = f"{S3_URL}/pdfs/{_fp_name}_au/"
                file_path, file_name = build_label(
                    booking=instance, file_path=file_path
                )

            instance.z_label_url = f"{_fp_name}_au/{file_name}"
            instance.save()
    except Exception as e:
        logger.info(f"{LOG_ID} Error: {str(e)}")
