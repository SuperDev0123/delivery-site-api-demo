import logging

from api.models import Client_employees, Client_warehouses, Utl_suburbs

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


def get_warehouse(client):
    """
    get Client's Warehouse
    """
    LOG_ID = "[GET WHSE]"

    try:
        warehouse = Client_warehouses.objects.get(fk_id_dme_client=client)
        logger.info(f"{LOG_ID} Warehouse: {warehouse}")
        return warehouse
    except Exception as e:
        logger.info(f"{LOG_ID} Client doesn't have Warehouse(s): {client}")
        message = "Issues with warehouse assignment."
        raise Exception(message)


def get_suburb_state(postal_code):
    """
    get `suburb` and `state` from postal_code
    """
    LOG_ID = "[GET ADDRESS]"

    if not postal_code:
        message = "Delivery postal code is required."
        logger.info(f"{LOG_ID} {message}")
        raise Exception(message)

    addresses = Utl_suburbs.objects.filter(postal_code=postal_code)

    if not addresses.exists():
        message = "Suburb and or postal code mismatch please check info and try again."
        logger.info(f"{LOG_ID} {message}")
        raise Exception(message)
    else:
        return addresses[0].state, addresses[0].suburb
