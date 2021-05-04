from django.db.models import Q
from rest_framework.exceptions import ValidationError

from api.models import Client_Products


def _append_line(results, line, qty):
    """
    if same e_item_type(model_number), then merge both
    """
    is_new = True

    for index, result in enumerate(results):
        if result["e_item_type"] == line["e_item_type"]:
            results[index]["qty"] += line["qty"]
            is_new = False
            break

    if is_new:
        results.append(line)

    return results


def get_product_items(bok_2s, client, has_parent_product):
    """
    get all items from array of "model_number" and "qty"
    """
    results = []

    for bok_2 in bok_2s:
        model_number = bok_2.get("model_number")
        qty = bok_2.get("qty")
        # "Jason L"
        zbl_121_integer_1 = bok_2.get("sequence")

        if not model_number or not qty:
            raise ValidationError(
                "'model_number' and 'qty' are required for each booking_line"
            )

        products = Client_Products.objects.filter(
            child_model_number=model_number, parent_model_number=model_number
        )

        if products and not has_parent_product:  # Ignore parent Product
            continue

        products = Client_Products.objects.filter(
            Q(parent_model_number=model_number) | Q(child_model_number=model_number)
        ).filter(fk_id_dme_client=client)

        if products.count() == 0:
            raise ValidationError(
                f"Can't find Product with provided 'model_number'({model_number})."
            )
        else:
            product = products.first()
            line = {
                "e_item_type": product.child_model_number,
                "description": product.description,
                "qty": product.qty * qty,
                "e_dimUOM": product.e_dimUOM,
                "e_weightUOM": product.e_weightUOM,
                "e_dimLength": product.e_dimLength,
                "e_dimWidth": product.e_dimWidth,
                "e_dimHeight": product.e_dimHeight,
                "e_weightPerEach": product.e_weightPerEach,
                "zbl_121_integer_1": zbl_121_integer_1,
            }
            results = _append_line(results, line, qty)

    return results


def find_missing_model_numbers(bok_2s, client):
    _missing_model_numbers = []

    for bok_2 in bok_2s:
        model_number = bok_2.get("model_number")
        products = Client_Products.objects.filter(
            Q(parent_model_number=model_number) | Q(child_model_number=model_number)
        ).filter(fk_id_dme_client=client)

        if not products.exists():
            _missing_model_numbers.append(model_number)

    return _missing_model_numbers
