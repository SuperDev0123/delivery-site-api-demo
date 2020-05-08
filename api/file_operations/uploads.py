import os
from datetime import datetime
from django.conf import settings

from api.common import trace_error
from api.models import (
    Bookings,
    DME_employees,
    DME_clients,
    Client_employees,
    Fp_freight_providers,
    DME_Files,
)
from api.utils import (
    clearFileCheckHistory,
    getFileCheckHistory,
    save2Redis,
)


def get_upload_status(request):
    return JsonResponse({"status_code": 0})

    # result = getFileCheckHistory(request.GET.get("filename"))
    #
    # if result == 0:
    #     return JsonResponse({"status_code": 0})
    # elif result == "success":
    #     return JsonResponse({"status_code": 1})
    # else:
    #     return JsonResponse({"status_code": 2, "errors": result})


def _save_import_file(dme_account_num, file, client_company_name):
    if settings.ENV in ["prod", "dev"]:  # PROD & DEV
        file_path = (
            f"/var/www/html/dme_api/media/onedrive/{str(dme_account_num)}_{file.name}"
            if client_company_name != "Tempo"
            else f"/dme_sftp/tempo_au/pickup_ext/{file.name}"
        )
    else:  # LOCAL
        file_path = f"./static/uploaded/{file.name}"

    if not os.path.isdir(file_path):
        os.makedirs(file_path)

    with open(file_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    # clearFileCheckHistory(f"str(dme_account_num)_{file.name}")


def upload_import_file(user_id, file, uploader):
    dme_employee = DME_employees.objects.filter(fk_id_user=user_id).first()
    user_type = "DME" if dme_employee else "CLIENT"

    if user_type == "DME":
        dme_account_num = DME_clients.objects.get(company_name=uploader).dme_account_num
        client_company_name = "DME"
    else:
        client_employee = Client_employees.objects.get(fk_id_user=int(user_id))
        dme_account_num = client_employee.fk_id_dme_client.dme_account_num
        client_company_name = DME_clients.objects.get(
            pk_id_dme_client=client_employee.fk_id_dme_client_id
        ).company_name

    file_name = f"{str(dme_account_num)}_{file.name}"

    save2Redis(file_name + "_l_000_client_acct_number", dme_account_num)
    _save_import_file(dme_account_num, file, client_company_name)
    return file_name


def upload_attachment_file(user_id, file, booking_id, upload_option):
    try:
        try:
            client = DME_clients.objects.get(pk_id_dme_client=user_id)
        except DME_clients.DoesNotExist as e:
            client = "dme"

        booking = Bookings.objects.get(id=booking_id)
        fp = Fp_freight_providers.objects.get(
            fp_company_name=booking.vx_freight_provider
        )
        name, extension = os.path.splitext(file.name)

        if upload_option == "attachment":
            fp_dir_name = (
                f"{fp.fp_company_name.lower()}_{fp.fp_address_country.lower()}"
            )
            file_path = f"{settings.STATIC_PUBLIC}/attachments/{fp_dir_name}/"

            if not os.path.isdir(file_path):
                os.makedirs(file_path)

            file_name = (
                f"{name}-{str(datetime.now().strftime('%Y%m%d_%H%M%S'))}{extension}"
            )
            full_path = f"{file_path}/{file_name}"
        elif upload_option in ["label", "pod"]:
            fp_dir_name = (
                f"{fp.fp_company_name.lower()}_{fp.fp_address_country.lower()}"
            )

            if upload_option == "label":
                file_path = f"{settings.STATIC_PUBLIC}/pdfs/{fp_dir_name}/"
            else:
                file_path = f"{settings.STATIC_PUBLIC}/imgs/{fp_dir_name}/"

            if not os.path.isdir(file_path):
                os.makedirs(file_path)

            if upload_option == "label":
                file_name = f"DME{str(booking.b_bookingID_Visual)}{extension}"
                booking.z_label_url = f"{fp.fp_company_name.lower()}_{fp.fp_address_country.lower()}/{file_name}"
            elif upload_option == "pod" and not "sog" in name.lower():
                file_name = f"POD_DME{str(booking.b_bookingID_Visual)}{extension}"
                booking.z_pod_url = f"{fp.fp_company_name.lower()}_{fp.fp_address_country.lower()}/{file_name}"
            elif upload_option == "pod" and "sog" in name.lower():
                file_name = f"POD_SOG_DME{str(booking.b_bookingID_Visual)}{extension}"
                booking.z_pod_signed_url = f"{fp.fp_company_name.lower()}_{fp.fp_address_country.lower()}/{file_name}"

            full_path = f"{file_path}/{file_name}"
            booking.save()

        with open(full_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        if upload_option == "attachment":
            dme_attachment = Dme_attachments(
                fk_id_dme_client=client,
                fk_id_dme_booking=booking.pk_booking_id,
                fileName=full_path,
                linkurl="22",
                upload_Date=datetime.now(),
            )
            dme_attachment.save()

        return {
            "status": "success",
            "file_path": f"{fp_dir_name}/{file_name}",
            "type": upload_option,
        }
    except Exception as e:
        trace_error.print()
        return {
            "status": "failed",
            "type": upload_option,
        }


def upload_pricing_only_file(user_id, username, file, upload_option):
    dme_file = DME_Files.objects.create(
        file_name=f"{file.name}",
        z_createdByAccount=username,
        file_type="pricing-only",
        file_extension="xlsx",
        note="Uploaded to get Pricings only",
    )

    file_index = DME_Files.objects.all().order_by("id").last().id
    dir_path = f"./static/uploaded/pricing_only/indata/"
    full_path = f"./static/uploaded/pricing_only/indata/{file_index}__{file.name}"

    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)

    with open(full_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    dme_file.file_name = f"{file_index}__{file.name}"
    dme_file.file_path = full_path
    dme_file.save()
    return {
        "status": "success",
        "file_name": f"{file_index}__{file.name}",
        "type": upload_option,
    }


def upload_pricing_rule_file(user_id, username, file, upload_option, rule_type):
    dme_file = DME_Files.objects.create(
        file_name=f"{file.name}",
        z_createdByAccount=username,
        file_type="pricing-rule",
        file_extension="xlsx",
        note="Uploaded to import Pricings Rules sheet",
    )

    file_index = DME_Files.objects.all().order_by("id").last().id
    dir_path = f"./static/uploaded/pricing_rule/indata/"
    full_path = (
        f"./static/uploaded/pricing_rule/indata/{file_index}__{rule_type}__{file.name}"
    )

    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)

    with open(full_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    dme_file.file_name = f"{file_index}__{rule_type}__{file.name}"
    dme_file.file_path = full_path
    dme_file.save()
    return {
        "status": "success",
        "file_name": dme_file.file_name,
        "type": upload_option,
    }
