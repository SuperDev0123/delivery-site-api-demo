def gen_consignment(booking):
    if booking.v_FPBookingNumber:
        return booking.v_FPBookingNumber

    warehouse = booking.fk_client_warehouse
    warehouse.connote_number += 1
    warehouse.save()

    if warehouse.client_warehouse_code == "BIO - RIC":
        prefix = "56R"
        return f"{prefix}Z2{str(warehouse.connote_number).zfill(7)}"
    elif warehouse.client_warehouse_code == "BIO - FDM":
        prefix = "BBB"
        return f"{prefix}Z1{str(warehouse.connote_number).zfill(7)}"
    else:
        return ""
