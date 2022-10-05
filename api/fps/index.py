from api.models import FP_zones, Client_FP


def get_fp_fl(fp, client, state, postal_code, suburb, client_fp=None):
    """
    Plum & Hunter

    Fuel Levy to Western Australia (Zone 22-26): 31%
    Fuel Levy to Other Regions: 24%
    """
    if (
        fp.fp_company_name.lower() == "hunter"
        and client.dme_account_num == "461162D2-90C7-BF4E-A905-000000000004"
    ):
        fp_zones = FP_zones.objects.filter(
            state=state, postal_code=postal_code, suburb=suburb, fk_fp=13
        )

        if fp_zones.exists():
            fp_zone = fp_zones.first()
            zone_no = int(fp_zone.service)

            if zone_no > 21 and zone_no < 27:
                return 0.31
            else:
                return 0.24

    _client_fp = client_fp
    if not client_fp:
        _client_fp = Client_FP.objects.get(client=client, fp=fp)

    return _client_fp.fuel_levy or fp.fp_markupfuel_levy_percent
