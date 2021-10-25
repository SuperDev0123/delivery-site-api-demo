from zplgrf import GRF
from base64 import b64decode, b64encode

try:
    from PyPDF2 import PdfFileReader, PdfFileWriter
except ImportError:
    from pyPdf import PdfFileReader, PdfFileWriter

from api.operations.email_senders import send_email_to_admins
from api.common import trace_error


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
        send_email_to_admins("PDF covertion error", error_msg)
        return False


def pdf_to_base64(pdf_path):
    try:
        f = open(pdf_path, "rb")
        return b64encode(f.read())
    except Exception as e:
        error_msg = f"@301 Error on pdf_to_base64(): {str(e)}"
        send_email_to_admins("PDF covertion error", error_msg)
        return False


def pdf_to_zpl(pdf_path, zpl_path):
    try:
        with open(pdf_path, "rb") as pdf:
            pages = GRF.from_pdf(pdf.read(), "DEMO")
            f = open(zpl_path, "w")

            for grf in pages:
                f.write(grf.to_zpl(compression=2, quantity=1, print_mode="T"))

            f.close()
            return True
    except Exception as e:
        trace_error.print()
        error_msg = f"@301 Error on pdf_to_zpl(): {str(e)}"
        send_email_to_admins("PDF covertion error", error_msg)
        return False


def rotate_pdf(input_path):
    try:
        pdf_in = open(input_path, 'rb')
        pdf_reader = PdfFileReader(pdf_in)
        pdf_writer = PdfFileWriter()
        for pagenum in range(pdf_reader.numPages):
            page = pdf_reader.getPage(pagenum)
            page.rotateClockwise(90)
            pdf_writer.addPage(page)
        output_path = input_path[:-4] + '_rotated.pdf'
        pdf_out = open(output_path, 'wb')
        pdf_writer.write(pdf_out)
        pdf_out.close()
        pdf_in.close()
        return output_path
    except Exception as e:
        trace_error.print()
        error_msg = f"@301 Error on rotate_pdf(): {str(e)}"
        send_email_to_admins("PDF rotation error", error_msg)
        return False


def pdf_merge(input_files, output_file_url):
    input_streams = []
    output_stream = open(output_file_url, "w+b")

    try:
        # First open all the files, then produce the output file, and
        # finally close the input files. This is necessary because
        # the data isn't read from the input files until the write
        # operation. Thanks to
        # https://stackoverflow.com/questions/6773631/problem-with-closing-python-pypdf-writing-getting-a-valueerror-i-o-operation/6773733#6773733
        writer = PdfFileWriter()

        for input_file in input_files:
            input_streams.append(open(input_file, "rb"))

        for reader in map(PdfFileReader, input_streams):
            for n in range(reader.getNumPages()):
                writer.addPage(reader.getPage(n))

        writer.write(output_stream)
    finally:
        for f in input_streams:
            f.close()

        output_stream.close()
