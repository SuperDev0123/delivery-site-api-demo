import io
import os
import zipfile
from django.http import HttpResponse


def download_from_disk(zip_subdir_name, file_paths):
    zip_subdir = zip_subdir_name
    zip_filename = "%s.zip" % zip_subdir

    s = io.BytesIO()
    zf = zipfile.ZipFile(s, "w")

    for index, file_path in enumerate(file_paths):
        if os.path.isfile(file_path):
            file_name = file_path.split("/")[-1]
            zf.write(file_path, f"{zip_subdir_name}/{file_name}")
    zf.close()

    response = HttpResponse(s.getvalue(), "application/x-zip-compressed")
    response["Content-Disposition"] = "attachment; filename=%s" % zip_filename
    return response


"""
# TODO: implement properly 
    
    # PYTHON CODE to download from HTTP url

    # if "https://ap-prod" in booking.z_label_url:  
    #     request = requests.get(booking.z_label_url, stream=True)

    #     if request.status_code != requests.codes.ok:
    #         continue

    #     label_name = f"{booking.pu_Address_State}_{booking.b_clientReference_RA_Numbers}_{booking.v_FPBookingNumber}.pdf"
    #     file_path = f"settings.STATIC_PUBLIC/pdfs/atc_au/{label_name}"  # Dev & Prod
    #     # file_path = f"./static/pdfs/atc_au/{label_name}" # Local (Test Case)
    #     file = open(file_path, "wb+")
    #     for block in request.iter_content(1024 * 8):
    #         if not block:
    #             break

    #         file.write(block)
    #     file.close()
    #     file_paths.append(file_path)
    #     label_names.append(label_name)
"""
