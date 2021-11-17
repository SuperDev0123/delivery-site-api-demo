from api.models import Bookings, Booking_lines

# Filter fully `run out` Bookings with Children - In short, no more child can be made
def get_run_out_bookings(bookings):
    _run_out_booking_pks = []
    created_withs = []
    pk_booking_ids = []
    queryset = bookings.only("id", "pk_booking_id", "b_bookingID_Visual")

    for booking in queryset:
        created_withs.append(f"Child of #{booking.b_bookingID_Visual}")
        pk_booking_ids.append(booking.pk_booking_id)

    children = Bookings.objects.filter(x_booking_Created_With__in=created_withs).only(
        "id", "pk_booking_id", "vx_freight_provider", "x_booking_Created_With"
    )

    for child in children:
        pk_booking_ids.append(child.pk_booking_id)

    lines = Booking_lines.objects.filter(
        fk_booking_id__in=pk_booking_ids,
        is_deleted=False,
        packed_status=Booking_lines.ORIGINAL,
    ).only("pk_lines_id", "e_item", "e_qty")

    for booking in queryset:
        booking_children = []
        booking_lines = []
        child_lines = []

        # Get booking_children and child_lines
        for child in children:
            if (
                f"Child of #{booking.b_bookingID_Visual}"
                == child.x_booking_Created_With
            ):
                booking_children.append(child)

            for line in lines:
                if child.pk_booking_id == line.fk_booking_id:
                    child_lines.append(line)

        # Get booking_lines
        for line in lines:
            if booking.pk_booking_id == line.fk_booking_id:
                booking_lines.append(line)

        for line in booking_lines:
            qty_in_stock = line.e_qty

            for _line in child_lines:
                if line.e_item == _line.e_item:
                    qty_in_stock -= _line.e_qty

            if qty_in_stock > 0:
                _run_out_booking_pks.append(booking.id)
                break

    return _run_out_booking_pks
