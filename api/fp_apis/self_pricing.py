from api.models import *
import logging

def is_in_zone(zone_code, suburb, postal_code, state):
    zones = FP_zones.objects.filter(zone=zone_code)

    if zones:
        for zone in zones:
            if zone.suburb and zone.suburb != suburb:
                continue
            if zone.postal_code and zone.postal_code != postal_code:
                continue
            if zone.state and zone.state != state:
                continue

            return True

    return False


def address_filter(booking, rules):
    pu_suburb = booking.pu_Address_Suburb
    pu_postal_code = booking.pu_Address_PostalCode
    pu_state = booking.pu_Address_State

    de_suburb = booking.de_To_Address_Suburb
    de_postal_code = booking.de_To_Address_PostalCode
    de_state = booking.de_To_Address_State

    filtered_rules = []
    for rule in rules:
        if rule.pu_suburb and rules.pu_suburb != pu_suburb:
            continue

        if rules.de_suburb and rules.de_suburb != de_suburb:
            continue

        if rules.pu_postal_code and rules.pu_postal_code != pu_postal_code:
            continue

        if rules.de_postal_code and rules.de_postal_code != de_postal_code:
            continue

        if rules.pu_state and rules.pu_state != pu_postal_code:
            continue

        if rules.de_state and rules.de_state != de_postal_code:
            continue

        if rules.pu_zone:
            if not is_in_zone(rules.pu_zone, pu_suburb, pu_postal_code, pu_state):
                continue

        if rules.de_zone:
            if not is_in_zone(rules.de_zone, de_suburb, de_postal_code, de_state):
                continue

        filtered_rules.append(rule)


def get_pricing(fp_name, booking):
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    rules = FP_pricing_rules.objects.filter(freight_provider_id=fp.id)

    rules = address_filter(booking, rules)

    if not rules:
        
