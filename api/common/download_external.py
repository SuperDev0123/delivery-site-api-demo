import requests


def pdf(url, booking):
    try:
        request = requests.get(url, stream=True)
        label_name = f"{booking.pu_Address_State}_{booking.b_clientReference_RA_Numbers}_{booking.v_FPBookingNumber}.pdf"
        file_path = (
            f"/opt/s3_public/pdfs/{booking.vx_freight_provider.lower()}_au/{label_name}"
        )  # Dev & Prod
        # file_path = f"/Users/admin/work/goldmine/dme_api/static/pdfs/{booking.vx_freight_provider.lower()}_au/{label_name}" # Local (Test Case)
        file = open(file_path, "wb+")

        for block in request.iter_content(1024 * 8):
            if not block:
                break

            file.write(block)
        file.close()

        return f"{booking.vx_freight_provider.lower()}_au/{label_name}"
    except Exception as e:
        booking.b_error_Capture = f"Error while download pdf: {e}"
        return None
