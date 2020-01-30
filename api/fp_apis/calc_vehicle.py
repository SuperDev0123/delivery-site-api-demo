import json
import logging
from django.core import serializers
from api.common import ratio

logger = logging.getLogger("dme_api")

vehicles = [
{"desc": "Courier", "length": 0.8, "width": 0.5, "height": 0.5},
{"desc": "Station Wagon", "length": 1.2, "width": 0.7, "height": 0.7},
{"desc": "Ute", "length": 1.5, "width": 1, "height": 1},
{"desc": "1 Ton Van/Tray", "length": 2.4, "width": 1.8, "height": 1.6},
{"desc": "2 Ton Tray", "length": 3.6, "width": 1.8, "height": 1.6},
{"desc": "4 Ton Tray", "length": 4.3, "width": 2.4, "height": 1.8},
{"desc": "6 Ton Tray", "length": 5.2, "width": 2.4, "height": 1.8},
{"desc": "8 Ton Tray", "length": 6, "width": 2.4, "height": 2},
{"desc": "12 Ton Tray", "length": 7.3, "width": 2.4, "height": 2},
{"desc": "4 Ton Tuatliner", "length": 4.3, "width": 2.4, "height": 2.1},
{"desc": "6 Ton Tuatliner", "length": 5.2, "width": 2.4, "height": 2.4},
{"desc": "8 Ton Tuatliner", "length": 6, "width": 2.4, "height": 2.4},
{"desc": "12 Ton Tuatliner", "length": 7.3, "width": 2.4, "height": 2.4},
{"desc": "14 Ton Tuatliner", "length": 8.4, "width": 2.4, "height": 2.4},
{"desc": "1 Ton Van", "length": 2.4, "width": 1.2, "height": 1.2},
{"desc": "Double Drop Deck Tautliner", "length": 21, "width": 2.4, "height": 3.2},
{"desc": "Double Tautliner", "length": 21, "width": 2.4, "height": 3.2},
{"desc": "Extendable Trailer", "length": 22, "width": 2.4, "height": 3.2},
{"desc": "Flat Top", "length": 13.2, "width": 2.4, "height": 3.2},
{"desc": "Transit van", "length": 3.2, "width": 1.6, "height": 1.7},
{"desc": "Panel van", "length": 1.5, "width": 1.2, "height": 1.2},
]

print(vehicles)
def find_vehicle(payload):
    print("@@@ - find_vehicle")
    try:
        sum_cube = 0
        max_width = 0
        max_height = 0
        max_length = 0

        results = []
        for item in payload["items"]:
            print(item)
            
            length = ratio._get_dim_amount("cm") * item["length"] * 5
            width = ratio._get_dim_amount("cm") * item["width"] * 5
            height = ratio._get_dim_amount("cm") * item["height"] * 5

            # Take the largest length of length, width and height on the largest package
            if max_length < length:
                max_length = length

            if max_width < width:
                max_width = width

            if max_height < height:
                max_height = height

            # Work out the cube of all the packages and add together
            cube = width * height * length
            sum_cube += cube * item["quantity"]

        print(f"Max height = {max_height}")
        print(f"Max width = {max_width}")
        print(f"Max length = {max_length}")
        print(f"Sum Cube = {sum_cube}")

        for vehicle in vehicles:
            vehicle_cube = vehicle["width"] * vehicle["height"] * vehicle["length"]

            if vehicle["width"] >= max_width and vehicle["height"] >= max_height and vehicle["length"] >= max_length:
                if vehicle_cube * 0.8 >= sum_cube:
                    results.append(vehicle)

        if len(results) > 0:
            print(f"Suitable vehicle is {results[0]}")
        else:
            print("Not found vehicle")
    except Exception as e:
        print(f"Error: {e}")

    print("*** find_vehicle")