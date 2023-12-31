from django.conf import settings


if settings.ENV == "local":
    DME_LEVEL_API_URL = "http://localhost:3000"
    S3_URL = "./static"
elif settings.ENV == "dev":
    DME_LEVEL_API_URL = "http://52.62.109.115:3000"
    S3_URL = "/opt/s3_public"
elif settings.ENV == "prod":
    DME_LEVEL_API_URL = "http://52.62.102.72:3000"
    S3_URL = "/opt/s3_public"


PRICING_TIME = 40  # seconds

# "Camerons", "Toll", "Sendle", "Capital", "Century", "Fastway", "Startrack", "TNT", "Hunter", "AUSPost", "ATC"
AVAILABLE_FPS_4_FC = [
    "Startrack",
    "AUSPost",
    "TNT",
    "Capital",
    "Hunter",
    "Sendle",
    "Allied",
    "Camerons",
    "Toll",
    "Century",
    "ATC",
    "Northline",  # Anchor Packaging
    "Blacks",  # Anchor Packaging
    "Blenner",  # Anchor Packaging
    "Bluestar",  # Anchor Packaging
    "Hi-Trans",  # Anchor Packaging
    "VFS",  # Anchor Packaging
    "Sadleirs",  # Anchor Packaging
    "Followmont",  # Anchor Packaging
    "DXT",  # Anchor Packaging
]

BUILT_IN_PRICINGS = {
    "atc": {"service_types": ["standard", "vip", "express"]},
    "century": {"service_types": ["standard", "vip", "priority"]},
    "camerons": {"service_types": ["standard", "express"]},
    "toll": {"service_types": ["Road Service"]},
    "northline": {"service_types": ["standard"]},
    "blacks": {"service_types": ["Road Service"]},
    "blenner": {"service_types": ["Road Service"]},
    "bluestar": {"service_types": ["Road Service"]},
    "startrack": {"service_types": ["Road Service"]},
    "hi-trans": {"service_types": ["Road Service"]},
    "vfs": {"service_types": ["Road Service"]},
    "sadleirs": {"service_types": ["Road Service"]},
    "followmont": {"service_types": ["Road Service"]},
    "dxt": {"service_types": ["Road Service"]},
    # "tnt": {
    #     "service_types": [
    #         "Overnight - 9:00 Express*",
    #         "Overnight - 10:00 Express",
    #         "Overnight - 12:00 Express",
    #         "Overnight - Express",
    #         "Overnight - Pay As You Go Satchel Express",
    #         "Road Express",
    #         "Technology Express Premium",
    #         "Technology Express Sensitive",
    #         "Time Critical Nationwide",
    #         "Failsafe Security Satchel ",
    #         "Failsafe Secure Service",
    #     ]
    # },
    # "hunter": {"service_types": ["Road Express"]},
    # "allied": {  # Deactivated
    #     "service_types": [
    #         "Road Express",
    #         "Standard Pallet Rate",
    #         "Oversized Pallet Rate",
    #     ]
    # },
    # "sendle": {"service_types": ["Pro"]},
}

FP_CREDENTIALS = {
    "auspost": {
        "test": {
            "test_bed_0": {
                "accountCode": "2006871123",  # eParcel and International (Stephen)
                "accountKey": "77003860-d920-42d8-a776-1643d65ab179",
                "accountPassword": "x06503301e1ddfb58a7a",
            },
        },
    },
    "startrack": {
        "test": {
            "test_bed_0": {
                "accountCode": "00956684",  # Original
                "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                "accountPassword": "xab801a41e663b5cb889",
            },
            "test_bed_1": {
                "accountCode": "00251522",  # ST Premium and ST Express
                "accountKey": "71eb98b2-fa8d-4a38-b1b7-6fb2a5c5c486",
                "accountPassword": "x9083d2fed4d50aa2ad5",
            },
            "test_bed_2": {
                "accountCode": "3006871123",  # Same Day Services (Stephen)
                "accountKey": "77003860-d920-42d8-a776-1643d65ab179",
                "accountPassword": "x06503301e1ddfb58a7a",
            },
            "test_bed_3": {
                "accountCode": "06871123",  # ST Premium and ST Express (Stephen)
                "accountKey": "77003860-d920-42d8-a776-1643d65ab179",
                "accountPassword": "x06503301e1ddfb58a7a",
            },
        },
        "biopak": {
            "BIO - BON": {
                "accountCode": "10145902",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "BIO - ROC": {
                "accountCode": "10145593",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "BIO - CAV": {
                "accountCode": "10145596",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "BIO - TRU": {
                "accountCode": "10149944",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "BIO - HAZ": {
                "accountCode": "10145597",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "BIO - EAS": {
                "accountCode": "10149943",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "BIO - RIC": {
                "accountCode": "10160226",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "VIC-HZ": {
                "accountCode": "10164661",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "SA-HZ": {
                "accountCode": "10164671",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
            "WA-HZ": {
                "accountCode": "10164660",
                "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
                "accountPassword": "x81775935aece65541c9",
            },
        },
    },
    "hunter": {
        "test": {
            "test_bed_1": {
                "accountCode": "APITEST",
                "accountKey": "55010|XXLFNZRLPW",
                "accountPassword": "",
            },
            # "test_bed_2": {
            #     "accountCode": "DUMMY",
            #     "accountKey": "aHh3czpoeHdz",
            #     "accountPassword": "hxws",
            # },
        },
        "dme": {
            # "live_1": {
            #     "accountCode": "DEMELP",
            #     "accountKey": "55010|XXLFNZRLPW",
            #     "accountPassword": "deliver",
            # },
            # "live_3": {
            #     "accountCode": "DMEBNE",
            #     "accountKey": "55010|XXLFNZRLPW",
            #     "accountPassword": "deliver",
            # },
            # "live_4": {
            #     "accountCode": "DMEPAL",
            #     "accountKey": "55010|XXLFNZRLPW",
            #     "accountPassword": "deliver",
            # },
            # "live_5": {
            #     "accountCode": "DEMELK",
            #     "accountKey": "55010|XXLFNZRLPW",
            #     "accountPassword": "deliver",
            # },
            # "live_6": {
            #     "accountCode": "DMEADL",
            #     "accountKey": "55010|XXLFNZRLPW",
            #     "accountPassword": "deliver",
            # },
            "live_7": {
                "accountCode": "DELIME",
                "accountKey": "55010|XXLFNZRLPW",
                "accountPassword": "deliver",
            },
        },
        # "bunnings": {
        #     "live_bunnings_0": {
        #         "accountCode": "DELIMB",
        #         "accountKey": "REVMSU1COmRlbGl2ZXIyMA==",
        #         "accountPassword": "deliver20",
        #     },
        #     "live_bunnings_1": {
        #         "accountCode": "DELIMS",
        #         "accountKey": "REVMSU1TOmRlbGl2ZXIyMA==",
        #         "accountPassword": "deliver20",
        #     },
        # },
        "plum products australia ltd": {
            "live_plum_0": {
                "accountCode": "PLUMPR",
                "accountKey": "55010|XXLFNZRLPW",
                "accountPassword": "deliver",
            },
        },
    },
    "tnt": {
        "dme": {
            "live_0": {
                "accountCode": "30021385",
                "accountKey": "30021385",
                "accountState": "DELME",
                "accountPassword": "Deliver123",
                "accountUsername": "CIT00000000000098839",
            }
        },
        "jason l": {
            "live_jasonl_0": {
                "accountCode": "21879211",
                "accountKey": "21879211",
                "accountState": "JSONL",
                "accountPassword": "prodTNT123",
                "accountUsername": "CIT00000000000136454",
            },
        },
    },
    "capital": {
        "dme": {
            "live_0": {
                "accountCode": "DMENSW",
                "accountKey": "eYte9AeLruGYmM78",
                "accountState": "NSW",
                "accountUsername": "deliverme",
            }
        }
    },
    "sendle": {
        "test": {
            "test_bed_1": {
                "accountCode": "XXX",
                "accountKey": "greatroyalone_outloo",
                "accountPassword": "KJJrS7xDZZfvfQccyrdStKhh",
            },
        },
        "dme": {
            "live_0": {
                "accountCode": "XXX",
                "accountKey": "bookings_tempo_deliv",
                "accountPassword": "3KZRdXVpfTkFTPknqzjqDXw6",
            }
        },
    },
    "fastway": {
        "dme": {
            "live_0": {
                "accountCode": "XXX",
                "accountKey": "ebdb18c3ce966bc3a4e3f115d311b453",
                "accountState": "FAKE_accountState_01",
            }
        }
    },
    "allied": {
        "test": {
            "test_bed_1": {
                "accountCode": "DELVME",
                "accountKey": "11e328f646051c3decc4b2bb4584530b",
                "accountState": "NSW",
            },
        },
        "dme": {
            "live_0": {
                "accountCode": "DELVME",
                "accountKey": "ce0d58fd22ae8619974958e65302a715",
                "accountState": "NSW",
            }
        },
    },
    "dhl": {
        "dme": {
            "live_0": {
                "accountCode": "XXX",
                "accountKey": "DELIVER_ME_CARRIER_API",
                "accountPassword": "RGVsaXZlcmNhcnJpZXJhcGkxMjM=",
            }
        }
    },
}

FP_UOM = {
    "startrack": {"dim": "cm", "weight": "kg"},
    "auspost": {"dim": "cm", "weight": "kg"},
    "hunter": {"dim": "cm", "weight": "kg"},
    "tnt": {"dim": "cm", "weight": "kg"},
    "capital": {"dim": "cm", "weight": "kg"},
    "sendle": {"dim": "cm", "weight": "kg"},
    "fastway": {"dim": "cm", "weight": "kg"},
    "allied": {"dim": "cm", "weight": "kg"},
    "dhl": {"dim": "cm", "weight": "kg"},
}

SPECIAL_FPS = [
    "Deliver-ME",
    "Customer Pickup",
    "Customer Collect",
    "In House Fleet",
]

# security header for DME_NODE
HEADER_FOR_NODE = {"X-SECURITY-TOKEN": "DELIVER-ME-API"}
