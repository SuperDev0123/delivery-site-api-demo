import json
import logging
from django.core import serializers
from api.common import ratio

logger = logging.getLogger("dme_api")

vehicles = [
{"desc": "Courier", "max_length": 0.8, "max_width": 0.5, "max_height": 0.5, "max_pallet_length": 0.8, "max_pallet_width": 0.5, "max_pallet_height": 0.5},
{"desc": "Station Wagon", "max_length": 1.2, "max_width": 0.7, "max_height": 0.7, "max_pallet_length": 1.2, "max_pallet_width": 0.7, "max_pallet_height": 0.7},
{"desc": "Ute", "max_length": 1.5, "max_width": 1, "max_height": 1, "max_pallet_length": 1.5, "max_pallet_width": 1, "max_pallet_height": 1},
{"desc": "1 Ton Van/Tray", "max_length": 2.4, "max_width": 1.8, "max_height": 1.6, "max_pallet_length": 2.4, "max_pallet_width": 1.8, "max_pallet_height": 1.6},
{"desc": "2 Ton Tray", "max_length": 3.6, "max_width": 1.8, "max_height": 1.6,"max_pallet_length": 3.6, "max_pallet_width": 1.8, "max_pallet_height": 1.6 },
{"desc": "4 Ton Tray", "max_length": 4.3, "max_width": 2.4, "max_height": 1.8, "max_pallet_length": 4.3, "max_pallet_width": 2.4, "max_pallet_height": 1.8},
{"desc": "6 Ton Tray", "max_length": 5.2, "max_width": 2.4, "max_height": 1.8, "max_pallet_length": 5.2, "max_pallet_width": 2.4, "max_pallet_height": 1.8},
{"desc": "8 Ton Tray", "max_length": 6, "max_width": 2.4, "max_height": 2, "max_pallet_length": 6, "max_pallet_width": 2.4, "max_pallet_height": 2},
{"desc": "12 Ton Tray", "max_length": 7.3, "max_width": 2.4, "max_height": 2, "max_pallet_length": 7.3, "max_pallet_width": 2.4, "max_pallet_height": 2},
{"desc": "4 Ton Tuatliner", "max_length": 4.3, "max_width": 2.4, "max_height": 2.1, "max_pallet_length": 4.3, "max_pallet_width": 2.4, "max_pallet_height": 2.1},
{"desc": "6 Ton Tuatliner", "max_length": 5.2, "max_width": 2.4, "max_height": 2.4, "max_pallet_length": 5.2, "max_pallet_width": 2.4, "max_pallet_height": 2.4},
{"desc": "8 Ton Tuatliner", "max_length": 6, "max_width": 2.4, "max_height": 2.4, "max_pallet_length": 6, "max_pallet_width": 2.4, "max_pallet_height": 2.4},
{"desc": "12 Ton Tuatliner", "max_length": 7.3, "max_width": 2.4, "max_height": 2.4, "max_pallet_length": 7.3, "max_pallet_width": 2.4, "max_pallet_height": 2.4},
{"desc": "14 Ton Tuatliner", "max_length": 8.4, "max_width": 2.4, "max_height": 2.4, "max_pallet_length": 8.4, "max_pallet_width": 2.4, "max_pallet_height": 2.4},
{"desc": "1 Ton Van", "max_length": 2.4, "max_width": 1.2, "max_height": 1.2, "max_pallet_length": 2.4, "max_pallet_width": 1.2, "max_pallet_height": 1.2},
{"desc": "Double Drop Deck Tautliner", "max_length": 21, "max_width": 2.4, "max_height": 3.2, "max_pallet_length": 21, "max_pallet_width": 2.4, "max_pallet_height": 3.2},
{"desc": "Double Tautliner", "max_length": 21, "max_width": 2.4, "max_height": 3.2, "max_pallet_length": 21, "max_pallet_width": 2.4, "max_pallet_height": 3.2},
{"desc": "Extendable Trailer", "max_length": 22, "max_width": 2.4, "max_height": 3.2, "max_pallet_length": 22, "max_pallet_width": 2.4, "max_pallet_height": 3.2},
{"desc": "Flat Top", "max_length": 13.2, "max_width": 2.4, "max_height": 3.2, "max_pallet_length": 13.2, "max_pallet_width": 2.4, "max_pallet_height": 3.2},
{"desc": "Transit van", "max_length": 3.2, "max_width": 1.6, "max_height": 1.7, "max_pallet_length": 3.2, "max_pallet_width": 1.6, "max_pallet_height": 1.7},
{"desc": "Panel van", "max_length": 1.5, "max_width": 1.2, "max_height": 1.2, "max_pallet_length": 1.5, "max_pallet_width": 1.2, "max_pallet_height": 1.2},
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
            if item["palletType"] == 'Pallet':
                vmax_width  = vehicle["max_width"]
                vmax_height  = vehicle["max_height"]
                vmax_length  = vehicle["max_length"]
            else:
                vmax_width  = vehicle["max_pallet_width"]
                vmax_height  = vehicle["max_pallet_height"]
                vmax_length  = vehicle["max_pallet_length"]
            vehicle_cube = vmax_width * vmax_height * vmax_length

            if (vmax_width >= max_width and vmax_height >= max_height and vmax_length >= max_length and vehicle_cube * 0.8 >= sum_cube):
                    results.append(vehicle)

        if len(results) > 0:
            print(f"Suitable vehicle is {results[0]}")
        else:
            print("Not found vehicle")
    except Exception as e:
        print(f"Error: {e}")

    print("*** find_vehicle")