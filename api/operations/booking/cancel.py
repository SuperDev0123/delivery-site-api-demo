import logging
from api.models import *
from api.serializers import *

logger = logging.getLogger(__name__)

def cancel_booking_by_id(booking_id):
    booking = Bookings.objects.get(id=booking_id)
    if booking:
        data = {
            'b_status': 'Cancelled',
            'b_client_order_num': f"{booking.b_client_order_num}_old",
            'b_client_sales_inv_num': f"{booking.b_client_sales_inv_num}_old"
        }
        serializer = BookingSerializer(booking, data=data)
        if serializer.is_valid():
            serializer.save()

        bok = BOK_1_headers.objects.get(pk_header_id=booking.pk_booking_id)
        if bok:
            bok.b_client_order_num = f"{booking.b_client_order_num}_old"
            bok.b_client_sales_inv_num = f"{booking.b_client_sales_inv_num}_old"
            bok.save()

            return True, serializer.data
        else:
            logger.error(f"Cancel Booking Error: Bok_1_header Not Found With Booking Id {booking_id}")
            return False, {'error': 'Bok_1_header Not Found'}
    else:
        logger.error(f"Cancel Booking Error: Booking Not Found With Id {booking_id}")
        return False, {'error': 'Booking Not Found'}
