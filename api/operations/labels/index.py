import logging
from base64 import b64encode

from api.models import (
    Bookings,
    Fp_freight_providers,
    FPRouting,
    FP_zones,
    Booking_lines_data,
)
from api.common import trace_error
from api.fp_apis.utils import gen_consignment_num
from api.convertors import pdf
from api.operations.labels import (
    ship_it,
    dhl,
    hunter,
    hunter_normal,
    hunter_thermal,
    tnt,
    allied,
    startrack,
    default,
    small_label,
)

logger = logging.getLogger(__name__)


def get_barcode(booking, booking_lines, pre_data, line_index=1, sscc_cnt=1):
    """
    Get barcode for label
    """
    result = None

    if pre_data["fp_name"] == "hunter":
        result = hunter.gen_barcode(booking, booking_lines, line_index, sscc_cnt)
    elif pre_data["fp_name"] == "tnt":
        result = tnt.gen_barcode(booking, booking_lines, line_index, sscc_cnt)
    elif pre_data["fp_name"] == "startrack":
        result = startrack.gen_barcode(booking, pre_data['v_FPBookingNumber'], line_index)
    else:  # "auspost", "startrack", "TNT", "State Transport"
        result = ship_it.gen_barcode(booking, booking_lines, line_index, sscc_cnt)

    return result


def _get_pre_data(booking):
    _pre_data = {}
    fp_name = booking.vx_freight_provider.lower()
    _pre_data["fp_name"] = fp_name
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    _pre_data["fp_id"] = fp.pk
    _pre_data["color_code"] = fp.hex_color_code
    v_FPBookingNumber = gen_consignment_num(
        booking.vx_freight_provider, booking.b_bookingID_Visual, booking.kf_client_id, booking
    )
    _pre_data["v_FPBookingNumber"] = v_FPBookingNumber

    if fp_name == "dhl":
        pass
    elif fp_name == "hunter":
        pass
    elif fp_name == "tnt":
        lines_data = Booking_lines_data.objects.filter(
            fk_booking_id=booking.pk_booking_id
        ).only("fk_booking_lines_id", "gap_ra", "modelNumber")
        _pre_data["lines_data"] = lines_data
        _pre_data["lines_data_cnt"] = lines_data.count()

        """
        Let's assume service group EXP
        Using the D records relating to that service group, establish the origin depot thaservices the consignment’s origin postcode.
        This should appear in section 3 of the routing label preceded by “Ex “.
        """
        crecords = FPRouting.objects.filter(
            freight_provider=12,
            dest_suburb=booking.de_To_Address_Suburb,
            dest_postcode=booking.de_To_Address_PostalCode,
            dest_state=booking.de_To_Address_State,
            data_code="C"
            # routing_group=routing_group,
        ).only("orig_depot_except", "gateway", "onfwd", "sort_bin")

        routing = None
        orig_depot = ""
        if crecords.exists():
            drecord = (
                FPRouting.objects.filter(
                    freight_provider=12,
                    orig_postcode=booking.pu_Address_PostalCode,
                    # routing_group=routing_group,
                    orig_depot__isnull=False,
                    data_code="D",
                )
                .only("orig_depot")
                .first()
            )

            if drecord:
                orig_depot = drecord.orig_depot
                for crecord in crecords:
                    if crecord.orig_depot_except == drecord.orig_depot:
                        routing = crecord
                        break

            if not routing:
                routing = (
                    FPRouting.objects.filter(
                        freight_provider=12,
                        dest_suburb=booking.de_To_Address_Suburb,
                        dest_postcode=booking.de_To_Address_PostalCode,
                        dest_state=booking.de_To_Address_State,
                        orig_depot_except__isnull=True,
                        data_code="C"
                        # routing_group=routing_group,
                    )
                    .only("orig_depot_except", "gateway", "onfwd", "sort_bin")
                    .first()
                )

            logger.info(
                f"#113 [TNT LABEL] Found FPRouting: {routing}, {routing.gateway}, {routing.onfwd}, {routing.sort_bin}, {orig_depot}"
            )

            _pre_data["routing"] = routing
            _pre_data["orig_depot"] = orig_depot
        else:
            msg = f"#114 [TNT LABEL] FPRouting does not exist: {booking.de_To_Address_Suburb}, {booking.de_To_Address_PostalCode}, {booking.de_To_Address_State}, {routing_group}"
            logger.info(msg)
    elif fp_name == "allied":
        try:
            carrier = FP_zones.objects.get(
                state=booking.de_To_Address_State,
                suburb=booking.de_To_Address_Suburb,
                postal_code=booking.de_To_Address_PostalCode,
                fk_fp=fp.pk,
            ).carrier
            _pre_data["carrier"] = carrier
        except FP_zones.DoesNotExist:
            _pre_data["carrier"] = ""
        except Exception as e:
            logger.info(f"#110 [ALLIED LABEL] Error: {str(e)}")
    elif fp_name == "startrack":
        pass
    else:  # "Century", "ATC", "JasonL In house"
        try:
            carrier = FP_zones.objects.get(
                state=booking.de_To_Address_State,
                suburb=booking.de_To_Address_Suburb,
                postal_code=booking.de_To_Address_PostalCode,
                fk_fp=fp.pk,
            ).carrier
            _pre_data["carrier"] = carrier
        except FP_zones.DoesNotExist:
            _pre_data["carrier"] = ""
        except Exception as e:
            logger.info(f"#110 [ALLIED LABEL] Error: {str(e)}")

    return _pre_data


def _build_sscc_label(
    booking,
    file_path,
    pre_data,
    lines=[],
    label_index=0,
    sscc=None,
    sscc_cnt=1,
    one_page_label=False,
):
    try:
        if pre_data["fp_name"] == "dhl":
            file_path, file_name = dhl.build_label(
                booking,
                file_path,
                pre_data,
                lines,
                label_index,
                sscc,
                sscc_cnt,
                one_page_label,
            )
        elif pre_data["fp_name"] == "hunter":
            file_path, file_name = hunter_normal.build_label(
                booking,
                file_path,
                pre_data,
                lines,
                label_index,
                sscc,
                sscc_cnt,
                one_page_label,
            )
        elif pre_data["fp_name"] == "tnt":
            file_path, file_name = tnt.build_label(
                booking,
                file_path,
                pre_data,
                lines,
                label_index,
                sscc,
                sscc_cnt,
                one_page_label,
            )
        elif pre_data["fp_name"] == "allied":
            file_path, file_name = allied.build_label(
                booking,
                file_path,
                pre_data,
                lines,
                label_index,
                sscc,
                sscc_cnt,
                one_page_label,
            )
        elif pre_data["fp_name"] == "startrack":
            file_path, file_name = startrack.build_label(
                booking,
                file_path,
                pre_data,
                lines,
                label_index,
                sscc,
                sscc_cnt,
                one_page_label,
            )
        else:  # "Century", "ATC", "JasonL In house"
            file_path, file_name = default.build_label(
                booking,
                file_path,
                pre_data,
                lines,
                label_index,
                sscc,
                sscc_cnt,
                one_page_label,
            )

        return file_path, file_name
    except Exception as e:
        trace_error.print()
        logger.error(f"[LABEL] error: {str(e)}")
        return None


def build_small_label(
    booking,
    file_path,
    lines=[],
    label_index=0,
    sscc=None,
    sscc_cnt=1,
    one_page_label=False,
):
    fp_name = booking.vx_freight_provider.lower()

    try:
        file_path, file_name = small_label.build_label(
            booking, file_path, lines, label_index, sscc, sscc_cnt, one_page_label
        )

        return file_path, file_name
    except Exception as e:
        trace_error.print()
        logger.error(f"[LABEL] error: {str(e)}")
        return None


def build_label(
    booking,
    file_path,
    total_qty,
    sscc_list=[],
    sscc_lines=[],
    need_base64=False,
    need_zpl=False,
    scanned_items=[],
):
    label_data = {"urls": [], "labels": []}
    logger.info(f"@368 - building label with SSCC...\n sscc_lines: {sscc_lines}")

    # Prepare data
    pre_data = _get_pre_data(booking)

    label_index = len(scanned_items)
    for index, sscc in enumerate(sscc_list):
        file_path, file_name = _build_sscc_label(
            booking=booking,
            file_path=file_path,
            pre_data=pre_data,
            lines=sscc_lines[sscc],
            label_index=label_index,
            sscc=sscc,
            sscc_cnt=total_qty,
            one_page_label=False,
        )

        for _line in sscc_lines[sscc]:
            label_index += _line.e_qty

        label_url = f"{file_path}/{file_name}"
        label_data["urls"].append(label_url)
        label = {}
        label["sscc"] = sscc
        label["barcode"] = get_barcode(
            booking, sscc_lines[sscc], pre_data, index + 1, len(sscc_list)
        )

        if need_base64:
            label["base64"] = str(pdf.pdf_to_base64(label_url))[2:-1]

        if need_zpl:
            # Convert label into ZPL format
            msg = f"@369 converting LABEL({label_url}) into ZPL format..."
            logger.info(msg)

            # Plum ZPL printer requries portrait label
            if booking.vx_freight_provider.lower() in ["hunter", "tnt"]:
                label_url = pdf.rotate_pdf(label_url)

            result = pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")

            if not result:
                msg = f"Please contact DME support center. <bookings@deliver-me.com.au>"
                raise Exception(msg)

            with open(label_url[:-4] + ".zpl", "rb") as zpl:
                label["zpl"] = str(b64encode(zpl.read()))[2:-1]

        label_data["labels"].append(label)

    # # Set consignment number
    # booking.v_FPBookingNumber = gen_consignment_num(
    #     booking.vx_freight_provider,
    #     booking.b_bookingID_Visual,
    #     booking.kf_client_id,
    #     booking,
    # )
    # booking.save()
    return label_data
