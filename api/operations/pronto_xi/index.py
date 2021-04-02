import logging

from api.operations.pronto_xi.apis import get_order

logger = logging.getLogger("__name__")


def populate_bok(bok_1):
    logger.info(f"@620 [POPULATE BOK] inital bok_1: {bok_1}")
    order, lines = get_order(bok_1["b_client_order_num"])

    if order["b_client_order_num"] != bok_1["b_client_order_num"]:
        raise Exception({"success": False, "message": "Wrong Order is feched."})

    for property in bok_1:
        order[property] = bok_1[property]

    logger.info(f"@629 [POPULATE BOK] Finished!\n result: {order}")
    return order, lines
