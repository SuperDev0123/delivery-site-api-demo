import logging

from api.operations.pronto_xi.apis import get_order, send_info_back_to_pronto

logger = logging.getLogger(__name__)


def populate_bok(bok_1):
    LOG_ID = "[PPB]"  # PRONTO POPULATE BOK
    logger.info(f"@620 {LOG_ID} inital bok_1: {bok_1}")
    order, lines = get_order(bok_1["b_client_order_num"])

    if order["b_client_order_num"] != bok_1["b_client_order_num"]:
        raise Exception({"success": False, "message": "Wrong Order is feched."})

    for property in bok_1:
        order[property] = bok_1[property]

    logger.info(f"@629 {LOG_ID} Finished!\n result: {order}")
    return order, lines


def send_info_back(bok_1, quote):
    LOG_ID = "[PSIB]"  # PRONTO SEND INFO BACK
    logger.info(f"@630 {LOG_ID} bok_1 ID: {bok_1.pk}, quote ID: {quote.pk}")

    result = send_info_back_to_pronto(bok_1, quote)

    logger.info(f"@639 {LOG_ID} Finished!")
    return result
