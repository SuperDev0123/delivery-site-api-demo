BUILT_IN_PRICINGS = {
    "century": {"service_types": ["standard", "vip", "premium"]},
    "camerons": {"service_types": ["standard", "express"]},
    "toll": {"service_types": ["standard", "express"]},
    "demo": {"service_types": ["standard", "vip", "premium"]},
}

ACCOUNT_CODES = {
    "startrack": {
        "test_bed_0": "00956684",  # Original
        "test_bed_1": "00251522",  # ST Premium and ST Express
        "BIO - BON": "10145902",
        "BIO - ROC": "10145593",
        "BIO - CAV": "10145596",
        "BIO - TRU": "10149944",
        "BIO - HAZ": "10145597",
        "BIO - EAS": "10149943",
        "BIO - HTW": "10160226",
    },
    "hunter": {
        "test_bed_1": "DUMMY",
        "live_0": "DELIME",
        "live_1": "DEMELP",
        "live_2": "DMEMEL",
        "live_3": "DMEBNE",
        "live_4": "DMEPAL",
        "live_5": "DEMELK",
        "live_6": "DMEADL",
        "live_bunnings_0": "DELIMB",
        "live_bunnings_1": "DELIMS",
    },
    "tnt": {"live_0": "30021385"},
    "capital": {"live_0": "DMENSW"},
    "sendle": {"test_bed_1": "XXX", "live_0": "XXX"},
    "fastway": {"live_0": "XXX"},
    "allied": {"test_bed_1": "DELVME", "live_0": "DELVME"},
    "dhl": {"live_0": "XXX"},
}

KEY_CHAINS = {
    "startrack": {
        "test_bed_0": {
            "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
            "accountPassword": "xab801a41e663b5cb889",
        },
        "test_bed_1": {
            "accountKey": "71eb98b2-fa8d-4a38-b1b7-6fb2a5c5c486",
            "accountPassword": "x9083d2fed4d50aa2ad5",
        },
        "BIO - BON": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
        "BIO - ROC": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
        "BIO - CAV": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
        "BIO - TRU": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
        "BIO - HAZ": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
        "BIO - EAS": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
        "BIO - HTW": {
            "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134",
            "accountPassword": "x81775935aece65541c9",
        },
    },
    "hunter": {
        "test_bed_1": {"accountKey": "aHh3czpoeHdz", "accountPassword": "hxws"},
        "live_0": {"accountKey": "REVMSU1FOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_1": {"accountKey": "REVNRUxQOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_2": {"accountKey": "RE1FTUVMOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_3": {"accountKey": "RE1FQk5FOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_4": {"accountKey": "RE1FUEFMOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_5": {"accountKey": "REVNRUxLOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_6": {"accountKey": "RE1FQURMOmRlbGl2ZXI=", "accountPassword": "deliver"},
        "live_bunnings_0": {
            "accountKey": "REVMSU1COmRlbGl2ZXIyMA==",
            "accountPassword": "deliver20",
        },
        "live_bunnings_1": {
            "accountKey": "REVMSU1TOmRlbGl2ZXIyMA==",
            "accountPassword": "deliver20",
        },
    },
    "tnt": {
        "live_0": {
            "accountKey": "30021385",
            "accountState": "DELME",
            "accountPassword": "Deliver123",
            "accountUsername": "CIT00000000000098839",
        }
    },
    "capital": {
        "live_0": {
            "accountKey": "eYte9AeLruGYmM78",
            "accountState": "NSW",
            "accountUsername": "deliverme",
        }
    },
    "sendle": {
        "test_bed_1": {
            # "accountKey": "greatroyalone_outloo",
            # "accountPassword": "KJJrS7xDZZfvfQccyrdStKhh",
            "accountKey": "bookings_tempo_deliv",
            "accountPassword": "3KZRdXVpfTkFTPknqzjqDXw6",
        },
        "live_0": {
            "accountKey": "bookings_tempo_deliv",
            "accountPassword": "3KZRdXVpfTkFTPknqzjqDXw6",
        },
    },
    "fastway": {
        "live_0": {
            "accountKey": "ebdb18c3ce966bc3a4e3f115d311b453",
            "accountState": "FAKE_STATE_01",
        }
    },
    "allied": {
        "test_bed_1": {
            "accountKey": "11e328f646051c3decc4b2bb4584530b",
            "accountState": "NSW",
        },
        "live_0": {
            "accountKey": "ce0d58fd22ae8619974958e65302a715",
            "accountState": "NSW",
        },
    },
    "dhl": {
        "live_0": {
            "accountKey": "DELIVER_ME_CARRIER_API",
            "accountPassword": "RGVsaXZlcmNhcnJpZXJhcGkxMjM=",
        }
    },
}

FP_UOM = {
    "startrack": {"dim": "cm", "weight": "kg"},
    "hunter": {"dim": "cm", "weight": "kg"},
    "tnt": {"dim": "cm", "weight": "kg"},
    "capital": {"dim": "cm", "weight": "kg"},
    "sendle": {"dim": "cm", "weight": "kg"},
    "fastway": {"dim": "cm", "weight": "kg"},
    "allied": {"dim": "cm", "weight": "kg"},
    "dhl": {"dim": "cm", "weight": "kg"},
}
