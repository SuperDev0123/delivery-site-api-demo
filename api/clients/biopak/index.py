def reprint_label(params, client):
    """
    get label(already built)
    """
    LOG_ID = "[REPRINT BioPak]"
    b_clientReference_RA_Numbers = params.get("clientReferences")
    item_description = params.get("itemDescription")

    if not b_clientReference_RA_Numbers:
        message = "'clientReferences' is required."
        raise ValidationError(message)
    else:
        b_clientReference_RA_Numbers = b_clientReference_RA_Numbers.split(",")

    bookings = Bookings.objects.filter(
        b_clientReference_RA_Numbers__in=b_clientReference_RA_Numbers,
        b_client_name=client.company_name,
    )
