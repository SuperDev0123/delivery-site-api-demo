def is_pallet(packaging_type):
    if not packaging_type:
        return False

    _packaging_type = packaging_type.lower()
    if (
        "pallet" in _packaging_type
        or "plt" in _packaging_type
        or "pal" in _packaging_type
    ):
        return True
    else:
        return False
