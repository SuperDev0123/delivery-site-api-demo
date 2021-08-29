import uuid
import logging

from django.db import transaction
from django.db.models import Q

from api.models import Bookings, Booking_lines, Booking_lines_data, Pallet
from api.serializers import BookingLineSerializer, BookingLineDetailSerializer
from api.common.pallet import get_palletized_by_ai

logger = logging.getLogger(__name__)


def auto_repack(booking, repack_status, need_soft_delete=False):
    LOG_ID = "[BOOKING AUTO REPACK]"
    logger.info(f"@830 {LOG_ID} Booking: {booking}, Repack Status: {repack_status}")
    lines = (
        booking.lines()
        .filter(Q(packed_status=Booking_lines.ORIGINAL) | Q(packed_status__isnull=True))
        .filter(is_deleted=False)
    )
    auto_repacked_lines = []

    # Select suitable pallet and get required pallets count
    pallets = Pallet.objects.all()
    palletized, non_palletized = get_palletized_by_ai(lines, pallets)
    logger.info(
        f"@831 {LOG_ID} Palletized: {palletized}\nNon-Palletized: {non_palletized}"
    )

    # Create one PAL Line
    for item in non_palletized:  # Non Palletized
        auto_repacked_lines.append(item)

    for palletized_item in palletized:  # Palletized
        pallet = pallets[palletized_item["pallet_index"]]

        total_weight = 0
        for _iter in palletized_item["lines"]:
            line_in_pallet = _iter["line_obj"]
            total_weight += (
                line_in_pallet.e_weightPerEach
                * _iter["quantity"]
                / palletized_item["quantity"]
            )

        new_line = {}
        new_line["fk_booking_id"] = booking.pk_booking_id
        new_line["pk_booking_lines_id"] = str(uuid.uuid1())
        new_line["e_type_of_packaging"] = "PAL"
        new_line["e_qty"] = palletized_item["quantity"]
        new_line["e_item"] = "Auto repacked item"
        new_line["e_dimUOM"] = "mm"
        new_line["e_dimLength"] = pallet.length
        new_line["e_dimWidth"] = pallet.width
        new_line["e_dimHeight"] = palletized_item["packed_height"] * 1000
        new_line["e_weightPerEach"] = round(total_weight, 2)
        new_line["e_weightUOM"] = "KG"
        new_line["is_deleted"] = False
        new_line["packed_status"] = Booking_lines.AUTO_PACK

        line_serializer = BookingLineSerializer(data=new_line)
        if line_serializer.is_valid():
            # Create LineData
            for _iter in palletized_item["lines"]:
                line = _iter["line_obj"]  # line_in_pallet
                bok_3 = {}
                bok_3["fk_booking_id"] = booking.pk_booking_id
                bok_3["fk_booking_lines_id"] = new_line["pk_booking_lines_id"]
                bok_3["itemSerialNumbers"] = line.zbl_131_decimal_1  # Sequence
                bok_3["quantity"] = line.e_qty
                bok_3["itemDescription"] = line.e_item
                bok_3["modelNumber"] = line.e_item_type

                line_data_serializer = BookingLineDetailSerializer(data=bok_3)
                if line_data_serializer.is_valid():
                    line_data_serializer.save()

                    # Soft delete `line in pallet`
                    line.is_deleted = need_soft_delete
                    line.save()
                else:
                    message = f"Serialiser Error - {line_data_serializer.errors}"
                    logger.info(f"@834 {LOG_ID} {message}")
                    raise Exception(message)

            line_serializer.save()
            auto_repacked_lines.append(new_line)
        else:
            message = f"Serialiser Error - {line_serializer.errors}"
            logger.info(f"@835 {LOG_ID} {message}")
            raise Exception(message)

    logger.info(f"@839 {LOG_ID} Booking: {booking} --- Finished successfully!")


def manual_repack(booking, repack_status):
    """
    Duplicate line and lineData for `manual` repacked status

    @params:
        booking:
        repack_status: 'manual-from-original' | 'manual-from-auto'
    """
    LOG_ID = "[LINE & LINEDATA BULK DUPLICATION]"
    logger.info(f"@840 {LOG_ID} Booking: {booking}, Repack Status: {repack_status}")

    if repack_status == "manual-from-original":
        lines = (
            booking.lines()
            .filter(
                Q(packed_status=Booking_lines.ORIGINAL) | Q(packed_status__isnull=True)
            )
            .filter(is_deleted=False)
        )
    else:
        lines = (
            booking.lines()
            .filter(Q(packed_status=Booking_lines.AUTO_PACK))
            .filter(is_deleted=False)
        )

    if lines.count() == 0:
        logger.info(f"@841 {LOG_ID} Booking: {booking} --- No lines to be duplicated!")
        return

    for line in lines:
        line_datas = Booking_lines_data.objects.filter(
            fk_booking_lines_id=line.pk_booking_lines_id
        )

        line.pk = None
        line.pk_booking_lines_id = str(uuid.uuid4())
        line.packed_status = Booking_lines.MANUAL_PACK
        line.save()

        for line_data in line_datas:
            line_data.pk = None
            line.fk_booking_lines_id = line.pk_booking_lines_id
            line.save()

    logger.info(
        f"@849 {LOG_ID} Booking: {booking} --- Finished successfully! {len(lines)} Lines are duplicated."
    )
