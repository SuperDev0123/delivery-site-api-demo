import logging

from api.operations.pronto_xi.apis import get_order

logger = logging.getLogger("__name__")


def populate_bok(bok):
    logger.info(f"@620 [POPULATE BOK] inital bok: {bok}")
    order = get_order(bok["b_client_order_num"])

    if order["b_client_order_num"] != bok["b_client_order_num"]:
        raise Exception({ra})

    order["shipping_type"] = bok["shipping_type"]
    order["b_client_sales_inv_num"] = bok["b_client_sales_inv_num"]
    logger.info(f"@629 [POPULATE BOK] Finished!\n result bok: {order}")
    return bok
