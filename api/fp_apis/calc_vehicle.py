import json
import logging
from django.core import serializers

logger = logging.getLogger("dme_api")

vehicles = [
{'desc': 'Courier', 'length': 0.8, 'width': 0.5, 'height': 0.5},
{'desc': 'Station Wagon', 'length': 1.2, 'width': 0.7, 'height': 0.7},
{'desc': 'Ute', 'length': 1.5, 'width': 1, 'height': 1},
{'desc': '1 Ton Van/Tray', 'length': 2.4, 'width': 1.8, 'height': 1.6},
{'desc': '2 Ton Tray', 'length': 3.6, 'width': 1.8, 'height': 1.6},
{'desc': '4 Ton Tray', 'length': 4.3, 'width': 2.4, 'height': 1.8},
{'desc': '6 Ton Tray', 'length': 5.2, 'width': 2.4, 'height': 1.8},
{'desc': '8 Ton Tray', 'length': 6, 'width': 2.4, 'height': 2},
{'desc': '12 Ton Tray', 'length': 7.3, 'width': 2.4, 'height': 2},
{'desc': '4 Ton Tuatliner', 'length': 4.3, 'width': 2.4, 'height': 2.1},
{'desc': '6 Ton Tuatliner', 'length': 5.2, 'width': 2.4, 'height': 2.4},
{'desc': '8 Ton Tuatliner', 'length': 6, 'width': 2.4, 'height': 2.4},
{'desc': '12 Ton Tuatliner', 'length': 7.3, 'width': 2.4, 'height': 2.4},
{'desc': '14 Ton Tuatliner', 'length': 8.4, 'width': 2.4, 'height': 2.4},
{'desc': '1 Ton Van', 'length': 2.4, 'width': 1.2, 'height': 1.2},
{'desc': 'Double Drop Deck Tautliner', 'length': 21, 'width': 2.4, 'height': 3.2},
{'desc': 'Double Tautliner', 'length': 21, 'width': 2.4, 'height': 3.2},
{'desc': 'Extendable Trailer', 'length': 22, 'width': 2.4, 'height': 3.2},
{'desc': 'Flat Top', 'length': 13.2, 'width': 2.4, 'height': 3.2},
{'desc': 'Transit van', 'length': 3.2, 'width': 1.6, 'height': 1.7},
{'desc': 'Panel van', 'length': 1.5, 'width': 1.2, 'height': 1.2},
]

print(vehicles)
def find_vehicle(payload):
    print('@@@ - find_vehicle')
    try:
        sum_cube = 0
        max_width = 0
        max_height = 0
        max_length = 0
        for item in payload['items']:
            print(item)
            
            # Take the largest length of length, width and height on the largest package
            if max_length < item['length']:
                max_length = item['length']

            if max_width < item['width']:
                max_width = item['width']

            if max_height < item['height']:
                max_height = item['height']

            # Work out the cube of all the packages and add together

            cube = item['width'] * item['height'] * item['length']
            # conversion to meter
            # cube = cube / 1000000
            sum_cube += cube * item['quantity']

        print('Max height = ', max_height)
        print('Max width = ', max_width)
        print('Max length = ', max_length)
        print('Sum Cube = ', sum_cube)
        for vehicle in vehicles:
            vehicle_cube = vehicle['width'] * vehicle['height'] * vehicle['length']
            print('vehicle cube', vehicle_cube)

    except Exception as e:
        print(f"Error: {e}")

    print('*** find_vehicle')