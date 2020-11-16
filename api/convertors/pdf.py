from zplgrf import GRF
from base64 import b64decode, b64encode

from django.core.mail import send_mail


def base64_to_pdf(base64, pdf_path):
    try:
        bytes = b64decode(base64, validate=True)

        if bytes[0:4] != b"%PDF":
            raise ValueError("Missing the PDF file signature")

        f = open(pdf_path, "wb")
        f.write(bytes)
        f.close()
        return True
    except Exception as e:
        error_msg = f"@300 Error on base64_to_pdf(): {str(e)}"
        send_mail(
            "PDF covertion error",
            error_msg,
            "Support Center<dme@deliver-me.com.au>",
            ["goldj@deliver-me.com.au", "petew@deliver-me.com.au"],
            fail_silently=False,
        )
        return False


def pdf_to_base64(pdf_path):
    try:
        f = open(pdf_path, "rb")
        return b64encode(f.read())
    except Exception as e:
        error_msg = f"@301 Error on pdf_to_base64(): {str(e)}"
        send_mail(
            "PDF covertion error",
            error_msg,
            "Support Center<dme@deliver-me.com.au>",
            ["goldj@deliver-me.com.au", "petew@deliver-me.com.au"],
            fail_silently=False,
        )
        return False


def pdf_to_zpl(pdf_path, zpl_path):
    try:
        with open(pdf_path, "rb") as pdf:
            pages = GRF.from_pdf(pdf.read(), "DEMO", center_of_pixel=True)
            f = open(zpl_path, "w")

            for grf in pages:
                f.write(grf.to_zpl())

            f.close()
            return True
    except Exception as e:
        error_msg = f"@301 Error on pdf_to_base64(): {str(e)}"
        send_mail(
            "PDF covertion error",
            error_msg,
            "Support Center<dme@deliver-me.com.au>",
            ["goldj@deliver-me.com.au", "petew@deliver-me.com.au"],
            fail_silently=False,
        )
        return False
