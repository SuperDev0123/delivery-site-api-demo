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


def get_product_items(bok_2s, ignore_product=False):
    """
    get all items from array of "model_number" and "qty"
    """
    results = []

    for bok_2 in bok_2s:
        model_number = bok_2.get("model_number")
        qty = bok_2.get("qty")

        if not model_number or not qty:
            raise ValidationError(
                {
                    "success": False,
                    "results": [],
                    "message": "'model_number' and 'qty' are required for each booking_line",
                }
            )

        products = Client_Products.objects.filter(
            Q(parent_model_number=model_number) | Q(child_model_number=model_number)
        )

        if products.count() == 0:
            raise ValidationError(
                {
                    "success": False,
                    "results": [],
                    "message": f"Can't find Product with provided 'model_number'({model_number}).",
                },
            )
        elif products.count() == 1:
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
            }

            results = _append_line(results, line, qty)
        elif products.count() > 1 and not ignore_product:
            child_items = products.exclude(
                child_model_number=model_number, parent_model_number=model_number
            )

            for item in child_items:
                line = {
                    "e_item_type": item.child_model_number,
                    "description": item.description,
                    "qty": item.qty * qty,
                    "e_dimUOM": item.e_dimUOM,
                    "e_weightUOM": item.e_weightUOM,
                    "e_dimLength": item.e_dimLength,
                    "e_dimWidth": item.e_dimWidth,
                    "e_dimHeight": item.e_dimHeight,
                    "e_weightPerEach": item.e_weightPerEach,
                }
                results = _append_line(results, line, qty)

    return results


def find_missing_model_numbers(bok_2s):
    _missing_model_numbers = []

    for bok_2 in bok_2s:
        model_number = bok_2.get("model_number")
        products = Client_Products.objects.filter(
            Q(parent_model_number=model_number) | Q(child_model_number=model_number)
        )

        if not products.exists():
            _missing_model_numbers.append(model_number)

    return _missing_model_numbers
