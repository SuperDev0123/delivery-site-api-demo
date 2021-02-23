from api.models import Bookings, Booking_lines
from api.operations.labels.index import build_label
from api.convertors import pdf

booking = Bookings.objects.get(pk=71660)
lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
line_01 = lines.last()

build_label(booking, 'static/built_in/', [line_01])
label_url = './static/built_in/NSW_132292_113566.pdf'
pdf.pdf_to_zpl(label_url, label_url[:-4] + ".zpl")