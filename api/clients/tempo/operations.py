import logging

from api.models import Client_warehouses

logger = logging.getLogger(__name__)

def find_warehouse(bok_1, bok_2s):
    LOG_ID = "[TEMPO WAREHOUSE FIND]"
    state = bok_1.get('b_031_b_pu_address_state')

    if not state:
        raise Exception('PickUp State is missing!')

    l_003_item = bok_2s[0].get('l_003_item') or ""
    
    logger.info(f"{LOG_ID} state: {state}, l_003_item: {l_003_item}")

    if l_003_item.upper() == 'AK5821S6WOS':
        warehouse_code = 'TEMPO_XTENSIVE'
    elif l_003_item.upper() == 'MICROWAVE' or 'MICROWAVE' in l_003_item.upper() or 'MWO' in l_003_item.upper():
        if state.upper() in ['ACT', 'NSW', 'NT', 'SA', 'TAS', 'VIC']:
            warehouse_code = 'TEMPO_REWORX'
        elif state.upper() in ['QLD']:
            warehouse_code = 'TEMPO_REWORX_CARGO'
        elif state.upper() in ['WA']:
            warehouse_code = 'TEMPO_REWORX_QLS'
    else:
        if state.upper() in ['ACT', 'NSW']:
            warehouse_code = 'TEMPO_AMERICAN'
        elif state.upper() in ['NT', 'SA', 'TAS', 'VIC']:
            warehouse_code = 'TEMPO_XTENSIVE'
        elif state.upper() in ['QLD']:
            warehouse_code = 'TEMPO_REWORX_CARGO'
        elif state.upper() in ['WA']:
            warehouse_code = 'TEMPO_REWORX_QLS'

    if not warehouse_code:
        error_msg = f'Can`t find warehouse with this state: {state}'
        logger.error(f'{LOG_ID} {error_msg}')
        raise Exception(error_msg)

    warehouse = Client_warehouses.objects.get(client_warehouse_code=warehouse_code)
    return warehouse
