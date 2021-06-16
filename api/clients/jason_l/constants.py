NEED_PALLET_GROUP_CODES = [
    "2101",
    "2102",
    "2103",
    "2104",
    "2149",
    "2201",
    "2202",
    "2203",
    "2204",
    "2205",
    "2206",
    "2249",
    "3001",
    "3002",
]

SERVICE_GROUP_CODES = ["FR01", "PM01", "AS01", "AS02"]

DIM_BY_GROUP_CODE = {
    "1001": {
        "description": "Executive Chairs",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.5,
        "width": 0.6,
        "height": 0.7,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "1002": {
        "description": "Workstation Chairs",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.5,
        "width": 0.6,
        "height": 0.7,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "1003": {
        "description": "Office Visitor Chairs",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.5,
        "width": 0.6,
        "height": 0.7,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "1004": {
        "description": "Meeting Room Chairs",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.5,
        "width": 0.6,
        "height": 0.7,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "1005": {
        "description": "Training / Conference Chairs",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.5,
        "width": 0.6,
        "height": 0.7,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "1006": {
        "description": "Drafting Chairs",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.5,
        "width": 0.6,
        "height": 0.7,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "1049": {
        "description": "Office Chairs Other",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.5,
        "width": 0.6,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.08,
        "weight_uom": "kg",
    },
    "1050": {
        "description": "Office Chair Components",
        "class": "OFCH",
        "class_desc": "Office Chairs",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "2101": {
        "description": "Height Adjustable Desks",
        "class": "OFDK",
        "class_desc": "Office Desks",
        "length": 1,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "2150": {
        "description": "Beams",
        "class": "OFDK",
        "class_desc": "Office Desks",
        "length": 1,
        "width": 0.07,
        "height": 0.07,
        "dim_uom": "m",
        "weight": 0.03,
        "weight_uom": "kg",
    },
    "2160": {
        "description": "Legs",
        "class": "OFDK",
        "class_desc": "Office Desks",
        "length": 0.8,
        "width": 0.8,
        "height": 0.06,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "2170": {
        "description": "Tops",
        "class": "OFDK",
        "class_desc": "Office Desks",
        "length": 1.8,
        "width": 0.8,
        "height": 0.03,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "2180": {
        "description": "Other desk components",
        "class": "OFDK",
        "class_desc": "Office Desks",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "3049": {
        "description": "Table Other",
        "class": "OFTA",
        "class_desc": "Office Tables",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "3050": {
        "description": "Office Table Components",
        "class": "OFTA",
        "class_desc": "Office Tables",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "3101": {
        "description": "Pedestals",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 0.62,
        "width": 0.42,
        "height": 0.52,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "3102": {
        "description": "Tambours",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 1.33,
        "width": 0.9,
        "height": 0.45,
        "dim_uom": "m",
        "weight": 0.36,
        "weight_uom": "kg",
    },
    "3103": {
        "description": "Laterals",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 1.33,
        "width": 0.9,
        "height": 0.45,
        "dim_uom": "m",
        "weight": 0.36,
        "weight_uom": "kg",
    },
    "3104": {
        "description": "Caddies",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 0.61,
        "width": 0.9,
        "height": 0.45,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "3105": {
        "description": "Bookcases",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 1.8,
        "width": 0.5,
        "height": 0.5,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "3106": {
        "description": "Lockers",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 1.8,
        "width": 0.5,
        "height": 0.5,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "3107": {
        "description": "Credenza",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 0.61,
        "width": 0.9,
        "height": 0.45,
        "dim_uom": "m",
        "weight": 0.36,
        "weight_uom": "kg",
    },
    "3149": {
        "description": "Storage Others",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "3150": {
        "description": "Storage Components",
        "class": "STOR",
        "class_desc": "Storage",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "3201": {
        "description": "Single Sofa",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 1,
        "width": 1,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.35,
        "weight_uom": "kg",
    },
    "3202": {
        "description": "Double Sofa",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 1.8,
        "width": 1,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.6,
        "weight_uom": "kg",
    },
    "3203": {
        "description": "Triple Sofa",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 2.1,
        "width": 1,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.65,
        "weight_uom": "kg",
    },
    "3204": {
        "description": "Activity Based",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 1,
        "width": 1,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.3,
        "weight_uom": "kg",
    },
    "3205": {
        "description": "Sofa Other",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 1,
        "width": 1,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.3,
        "weight_uom": "kg",
    },
    "3206": {
        "description": "Coffee Table",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 1,
        "width": 1,
        "height": 0.07,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "3207": {
        "description": "Breakout Chair",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 0.5,
        "width": 0.5,
        "height": 0.5,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "3208": {
        "description": "Ottoman",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 0.5,
        "width": 0.5,
        "height": 0.5,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "3209": {
        "description": "Cafe Chair",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 0.5,
        "width": 0.5,
        "height": 0.4,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "3249": {
        "description": "Loose Furniture Other",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 1,
        "width": 1,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.3,
        "weight_uom": "kg",
    },
    "3250": {
        "description": "Loose Furniture Component",
        "class": "LOSE",
        "class_desc": "Loose Furniture",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "3301": {
        "description": "Whiteboards",
        "class": "COMM",
        "class_desc": "Communication",
        "length": 1.8,
        "width": 1.2,
        "height": 0.4,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "3302": {
        "description": "Glassboards",
        "class": "COMM",
        "class_desc": "Communication",
        "length": 1.8,
        "width": 1.2,
        "height": 0.4,
        "dim_uom": "m",
        "weight": 0.3,
        "weight_uom": "kg",
    },
    "3303": {
        "description": "Pinboards",
        "class": "COMM",
        "class_desc": "Communication",
        "length": 1.5,
        "width": 1.2,
        "height": 0.4,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "3349": {
        "description": "Communication Other",
        "class": "COMM",
        "class_desc": "Communication",
        "length": 1.5,
        "width": 1,
        "height": 0.4,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "3350": {
        "description": "Communication Components",
        "class": "COMM",
        "class_desc": "Communication",
        "length": 0.3,
        "width": 0.3,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "3401": {
        "description": "Leads",
        "class": "ELEC",
        "class_desc": "Electrical",
        "length": 0.16,
        "width": 0.08,
        "height": 0.02,
        "dim_uom": "m",
        "weight": 0.02,
        "weight_uom": "kg",
    },
    "3402": {
        "description": "GPO's",
        "class": "ELEC",
        "class_desc": "Electrical",
        "length": 0.16,
        "width": 0.08,
        "height": 0.02,
        "dim_uom": "m",
        "weight": 0.02,
        "weight_uom": "kg",
    },
    "3403": {
        "description": "Power Box",
        "class": "ELEC",
        "class_desc": "Electrical",
        "length": 0.16,
        "width": 0.08,
        "height": 0.02,
        "dim_uom": "m",
        "weight": 0.02,
        "weight_uom": "kg",
    },
    "3449": {
        "description": "Electrical Other",
        "class": "ELEC",
        "class_desc": "Electrical",
        "length": 0.16,
        "width": 0.08,
        "height": 0.02,
        "dim_uom": "m",
        "weight": 0.02,
        "weight_uom": "kg",
    },
    "3501": {
        "description": "Trays",
        "class": "CAMA",
        "class_desc": "Cable Management",
        "length": 1.6,
        "width": 0.05,
        "height": 0.05,
        "dim_uom": "m",
        "weight": 0.02,
        "weight_uom": "kg",
    },
    "3502": {
        "description": "Monitor Arms",
        "class": "CAMA",
        "class_desc": "Cable Management",
        "length": 0.6,
        "width": 0.2,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "3503": {
        "description": "Umbilicals",
        "class": "CAMA",
        "class_desc": "Cable Management",
        "length": 0.3,
        "width": 0.3,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "3504": {
        "description": "CPU Holder",
        "class": "CAMA",
        "class_desc": "Cable Management",
        "length": 0.3,
        "width": 0.3,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "3505": {
        "description": "Cable Cover",
        "class": "CAMA",
        "class_desc": "Cable Management",
        "length": 0.01,
        "width": 0.01,
        "height": 0.01,
        "dim_uom": "m",
        "weight": 0.01,
        "weight_uom": "kg",
    },
    "3549": {
        "description": "Cable Other",
        "class": "CAMA",
        "class_desc": "Cable Management",
        "length": 0.3,
        "width": 0.3,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "3550": {
        "description": "Cable Components",
        "class": "CAMA",
        "class_desc": "Cable Management",
        "length": 0.3,
        "width": 0.3,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "3649": {
        "description": "Accessories Other",
        "class": "ACCE",
        "class_desc": "Accessories",
        "length": 0.3,
        "width": 0.3,
        "height": 0.2,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "4001": {
        "description": "Desk Screens",
        "class": "SCPA",
        "class_desc": "Screens & Partitions",
        "length": 1.8,
        "width": 0.6,
        "height": 0.04,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "4002": {
        "description": "Floor Screens",
        "class": "SCPA",
        "class_desc": "Screens & Partitions",
        "length": 1.8,
        "width": 1.2,
        "height": 0.04,
        "dim_uom": "m",
        "weight": 0.3,
        "weight_uom": "kg",
    },
    "4003": {
        "description": "Partitions",
        "class": "SCPA",
        "class_desc": "Screens & Partitions",
        "length": 1.8,
        "width": 1.2,
        "height": 0.04,
        "dim_uom": "m",
        "weight": 0.2,
        "weight_uom": "kg",
    },
    "4004": {
        "description": "Social Distancing Screen",
        "class": "CROW",
        "class_desc": "Crowd Control",
        "length": 1,
        "width": 1,
        "height": 0.02,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "4005": {
        "description": "Sneeze Guards",
        "class": "CROW",
        "class_desc": "Crowd Control",
        "length": 1,
        "width": 1,
        "height": 0.02,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "4006": {
        "description": "Hygiene Products",
        "class": "CROW",
        "class_desc": "Crowd Control",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "4007": {
        "description": "Desk Screens - Versalink",
        "class": "SCPA",
        "class_desc": "Screens & Partitions",
        "length": 1.8,
        "width": 0.6,
        "height": 0.04,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "4008": {
        "description": "Floor Screens - Versalink",
        "class": "SCPA",
        "class_desc": "Screens & Partitions",
        "length": 1.8,
        "width": 1.2,
        "height": 0.04,
        "dim_uom": "m",
        "weight": 0.3,
        "weight_uom": "kg",
    },
    "4049": {
        "description": "Other Screen & Partitions",
        "class": "SCPA",
        "class_desc": "Screens & Partitions",
        "length": 1.8,
        "width": 1.2,
        "height": 0.04,
        "dim_uom": "m",
        "weight": 0.3,
        "weight_uom": "kg",
    },
    "4050": {
        "description": "Screen Components Other",
        "class": "SCPA",
        "class_desc": "Screens & Partitions",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "5001": {
        "description": "Retracta/Rope Barrier",
        "class": "CROW",
        "class_desc": "Crowd Control",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "5002": {
        "description": "Crowd Control Signs",
        "class": "CROW",
        "class_desc": "Crowd Control",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "5010": {
        "description": "Printed - Signage",
        "class": "SIGN",
        "class_desc": "Printed - Signage",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "5049": {
        "description": "Other Crowd Control products",
        "class": "CROW",
        "class_desc": "Crowd Control",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "5050": {
        "description": "Crowd Control Components",
        "class": "CROW",
        "class_desc": "Crowd Control",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.05,
        "weight_uom": "kg",
    },
    "6001": {
        "description": "Room Booth",
        "class": "RMBT",
        "class_desc": "Room Booth",
        "length": 1.8,
        "width": 1.5,
        "height": 1.5,
        "dim_uom": "m",
        "weight": 1.5,
        "weight_uom": "kg",
    },
    "6002": {
        "description": "Phone Booth",
        "class": "RMBT",
        "class_desc": "Room Booth",
        "length": 1.8,
        "width": 1.5,
        "height": 1.5,
        "dim_uom": "m",
        "weight": 1.5,
        "weight_uom": "kg",
    },
    "7001": {
        "description": "Hospitality Indoor Chair",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 0.6,
        "width": 0.7,
        "height": 0.8,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "7002": {
        "description": "Hospitality Outdoor Chair",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 0.6,
        "width": 0.7,
        "height": 0.8,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "7003": {
        "description": "Hospitality Indoor Stool",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 0.6,
        "width": 0.6,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "7004": {
        "description": "Hospitality Outdoor Stool",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 0.6,
        "width": 0.6,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "7020": {
        "description": "Outdoor Tops",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 1,
        "width": 1,
        "height": 0.04,
        "dim_uom": "m",
        "weight": 0.08,
        "weight_uom": "kg",
    },
    "7027": {
        "description": "Outdoor Table",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 1,
        "width": 1,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.15,
        "weight_uom": "kg",
    },
    "7030": {
        "description": "Outdoor Lounge",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 1.2,
        "width": 1,
        "height": 1,
        "dim_uom": "m",
        "weight": 0.4,
        "weight_uom": "kg",
    },
    "7033": {
        "description": "Ottomans",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 1,
        "width": 1,
        "height": 0.5,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "7049": {
        "description": "Hospitality Others",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
    "7050": {
        "description": "Hospitality Components",
        "class": "HOSP",
        "class_desc": "Hospitality",
        "length": 0.3,
        "width": 0.3,
        "height": 0.3,
        "dim_uom": "m",
        "weight": 0.1,
        "weight_uom": "kg",
    },
}
