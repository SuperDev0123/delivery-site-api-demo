from api.models import Api_booking_confirmation_lines


def create(booking, items):
    if booking.vx_freight_provider and booking.vx_freight_provider.lower() in [
        "startrack",
        "auspost",
    ]:
        for item in items:
            book_con = Api_booking_confirmation_lines(
                fk_booking_id=booking.pk_booking_id,
                api_item_id=item["item_id"],
            ).save()
    else:
        book_con = Api_booking_confirmation_lines(
            fk_booking_id=booking.pk_booking_id,
            label_code=items[0]["label_code"],
        ).save()
