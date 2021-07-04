import logging

from api.models import Client_employees, Client_warehouses, Utl_suburbs
from api.helpers.string import similarity

logger = logging.getLogger(__name__)


def get_client(user):
    """
    get client
    """
    LOG_ID = "[GET CLIENT]"

    try:
        client_employee = Client_employees.objects.get(fk_id_user_id=user.pk)
        client = client_employee.fk_id_dme_client
        logger.info(f"{LOG_ID} Client: {client.company_name}")
        return client
    except Exception as e:
        logger.info(f"{LOG_ID} client_employee does not exist, {str(e)}")
        message = "Permission denied."
        raise Exception(message)


def get_warehouse(client, code=None):
    """
    get Client's Warehouse
    """
    LOG_ID = "[GET WHSE]"

    try:
        if code:
            warehouse = Client_warehouses.objects.get(client_warehouse_code=code)
        else:
            warehouse = Client_warehouses.objects.get(fk_id_dme_client=client)

        logger.info(f"{LOG_ID} Warehouse: {warehouse}")
        return warehouse
    except Exception as e:
        logger.info(f"{LOG_ID} Client doesn't have Warehouse(s): {client}")
        message = "Issues with warehouse assignment."
        raise Exception(message)


def get_suburb_state(postal_code, clue=""):
    """
    get `suburb` and `state` from postal_code

    postal_code: PostalCode
    clue: String which may contains Suburb and State
    """
    LOG_ID = "[GET ADDRESS]"
    logger.info(f"{LOG_ID} postal_code: {postal_code}, clue: {clue}")

    if not postal_code:
        message = "Delivery postal code is required."
        logger.info(f"{LOG_ID} {message}")
        raise Exception(message)

    addresses = Utl_suburbs.objects.filter(postal_code=postal_code)

    if not addresses.exists():
        message = "Suburb and or postal code mismatch please check info and try again."
        logger.info(f"{LOG_ID} {message}")
        raise Exception(message)

    selected_address = None
    if clue:
        for address in addresses:
            for clue_iter in clue.split(", "):
                _clue_iter = clue_iter.lower()
                _clue_iter = _clue_iter.strip()

                if address.suburb.lower() == _clue_iter:
                    selected_address = address

    if not selected_address and not clue:
        selected_address = addresses[0]
    elif not selected_address and clue:
        return None, None

    return selected_address.state, selected_address.suburb


def get_similar_suburb(postal_code, clues):
    """
    get similar(>0.8) suburb from clues
    """
    LOG_ID = "[GET SIMILAR SUBURB]"
    logger.info(f"{LOG_ID} postal_code: {postal_code}, clues: {clues}")

    similar_suburb = None
    addresses = Utl_suburbs.objects.filter(postal_code=postal_code)

    for address in addresses:
        for clue_iter in clues:
            _clue_iter = clue_iter.lower()
            _clue_iter = _clue_iter.strip()

            if similarity(address.suburb.lower(), _clue_iter) > 0.8:
                similar_suburb = addresses.suburb

    return similar_suburb
