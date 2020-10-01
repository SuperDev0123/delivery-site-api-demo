from api.models import Client_Products


def get_product_items(parent_model_number):
    lines = []
    products = Client_Products.objects.filter(parent_model_number=parent_model_number)

    if products.count() == 0:
        return None, []
    elif products.count() == 1:
        product = products.first()
        lines = [
            {
                "description": product.description,
                "qty": product.qty,
                "e_dimUOM": product.e_dimUOM,
                "e_weightUOM": product.e_weightUOM,
                "e_dimLength": product.e_dimLength,
                "e_dimWidth": product.e_dimWidth,
                "e_dimHeight": product.e_dimHeight,
                "e_weightPerEach": product.e_weightPerEach,
            }
        ]

        line_data = {
            "model_number": product.parent_model_number,
            "description": product.description,
        }
    elif products.count() > 1:
        items = products.exclude(child_model_number=parent_model_number)
        product = products.filter(child_model_number=parent_model_number).first()

        for item in items:
            line = {
                "description": item.description,
                "qty": item.qty,
                "e_dimUOM": item.e_dimUOM,
                "e_weightUOM": item.e_weightUOM,
                "e_dimLength": item.e_dimLength,
                "e_dimWidth": item.e_dimWidth,
                "e_dimHeight": item.e_dimHeight,
                "e_weightPerEach": item.e_weightPerEach,
            }
            lines.append(line)

        line_data = {
            "model_number": product.parent_model_number,
            "description": product.description,
        }

    return line_data, lines
