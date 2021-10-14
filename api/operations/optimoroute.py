from django.conf import settings
import requests
import json
import logging

logger = logging.getLogger(__name__)

def update_driver(data):
    # Request body sample
    # {
    # "externalId": "3945300304540",
    # "date": "2019-09-25",
    # "workTimeFrom": "09:30",
    # "workTimeTo": "18:00"
    # }
    url = f"{settings.OPTIMOROUTE_API_URL}update_driver_parameters?key={settings.OPTIMOROUTE_API_KEY}"
    response = requests.post(url, data=json.dumps(data))
    result = response.json()
    print('Driver Update Result', result)
    if (result['success']):
        return True
    else:
        logger.error(f"Planning routes via Optimoroute failed - {result['code']}")
        return False

def push_orders(bookings):
    result = {
        'success': [],
        'failed': []
    }
    for booking in bookings:
        order = {
            'operation': 'CREATE',
            'orderNo': str(booking.id),
            'date': booking.de_Deliver_By_Date.strftime('%Y-%m-%d'),
            'duration': 10,
            # 'priority': 'H',
            'type': 'D',
            # 'assignedTo': {'externalId': 'DRV001', 'serial': '001'},
            # 'assignedTo': {},
            'location': {
                # 'locationNo': '',
                'address': f"{booking.de_To_Address_Street_1}, {booking.de_To_Address_Suburb}, {booking.de_To_Address_State} {booking.de_To_Address_PostalCode}, {booking.de_To_Address_Country}",
                'locationName': booking.deToCompanyName,
                # 'latitude': 42.365142,
                # 'longitude': -71.052882,
                # 'checkInTime': 0,
                'acceptPartialMatch': True
            },
            # 'timeWindows': [{
            #     'twFrom': '8:00',
            #     'twTo': '17:00'
            # }],
            # 'allowedWeekdays': ['mon', 'tue', 'wed', 'thu', 'fri'],
            # 'allowedDates': {},
            # 'skills': ['SK001'],
            # 'vehicleFeatures': [],
            # 'notes': 'Notify manager',
            # 'email': 'joe.customer@example.com',
            # 'phone': '',
            # 'customField1': '300',
            # 'notificationPreference': 'email'
        }
        url = f"{settings.OPTIMOROUTE_API_URL}create_order?key={settings.OPTIMOROUTE_API_KEY}"
        res = requests.post(url, data=json.dumps(order)).json()
        if (res['success']):
            result['success'].append(booking.id)
        else:
            logger.error(f"Push order via Optimoroute failed - {res['code']} : {res['message']}")
            result['failed'].append({
                'id': booking.id,
                'code': res['code'],
                'message': res['message']
            })
    return result


def start_planning(date):
    data={ 'date': date }
    url = f"{settings.OPTIMOROUTE_API_URL}start_planning?key={settings.OPTIMOROUTE_API_KEY}"
    response = requests.post(url, data=json.dumps(data))
    result = response.json()
    print('Planning Route Result', result)
    if (result['success']):
        return result['planningId']
    else:
        logger.error(f"Planning routes via Optimoroute failed - {result['code']}")
        return None


def stop_planning(id):
    data={ 'planningId': id }
    url = f"{settings.OPTIMOROUTE_API_URL}stop_planning?key={settings.OPTIMOROUTE_API_KEY}"
    response = requests.post(url, data=json.dumps(data))
    result = response.json()
    print(' Stop Planning Route Result', result)
    if (result['success']):
        return True
    else:
        logger.error(f"Stop planning routes via Optimoroute failed - {result['code']}")
        return False


def get_planning_status(id):
    url = f"{settings.OPTIMOROUTE_API_URL}get_planning_status?key={settings.OPTIMOROUTE_API_KEY}&planningId={id}"
    response = requests.get(url)
    result = response.json()
    print('Planning status', result)
    if (result['success']):
        return {
            'status': result['status'],
            'percentageComplete': result['percentageComplete']
        }
    else:
        logger.error(f"Get planning status via Optimoroute failed - {result['code']} : {result['status']}")
        return {
            'status': result['status'],
            'code': result['code']
        }


def get_routes(date):
    url = f"{settings.OPTIMOROUTE_API_URL}get_routes?key={settings.OPTIMOROUTE_API_KEY}&date={date}"
    response = requests.get(url)
    result = response.json()
    print('Routes', result)
    if (result['success']):
        return result['routes']
    else:
        logger.error(f"Get routes via Optimoroute failed - {result['code']} : {result['message']}")
        return []

