import os
import json
import logging
import subprocess

from django.conf import settings

logger = logging.getLogger("dme_api")


def get_picked_items(order_num, sscc):
    LOG_ID = "[SSCC CSV READER]"

    if settings.ENV != "local":  # Only on DEV or PROD
        logger.info(f"@300 {LOG_ID} Running .sh script...")
        cmd_dir = "/home/ubuntu/jason_l/JasonL01_full_0.1/JasonL01_full"
        cmd_file = os.path.join(cmd_dir, "JasonL01_full_run.sh")
        subprocess.call([cmd_file], cwd=cmd_dir)
        logger.info(f"@301 {LOG_ID} Finish running .sh")

    if settings.ENV == "local":
        file_path = "/Users/juli/Desktop/sscc.csv"
    else:
        file_path = "/home/ubuntu/jason_l/JasonL01_full_0.1/JasonL01_full/sscc.csv"

    csv_file = open(file_path)
    logger.info(f"@320 {LOG_ID} File({file_path}) opened!")
    filtered_lines = []

    for i, line in enumerate(csv_file):
        if str(order_num) == line.split("|")[2].strip():
            if sscc and sscc != line.split("|")[1].strip():
                continue

            filtered_lines.append(
                {
                    "sscc": line.split("|")[1].strip(),
                    "timestamp": line.split("|")[9][:19],
                    "is_repacked": True,
                    "package_type": line.split("|")[8][:3],
                    "items": [
                        {
                            "sequence": int(float(line.split("|")[0])),
                            "qty": int(float(line.split("|")[3])),
                        }
                    ],
                    "dimensions": {
                        "width": float(line.split("|")[5]),
                        "height": float(line.split("|")[6]),
                        "length": float(line.split("|")[4]),
                        "unit": "m",
                    },
                    "weight": {"weight": float(line.split("|")[7]), "unit": "kg"},
                }
            )

    logger.info(f"@328 {LOG_ID} Finish reading CSV! Count: {len(filtered_lines)}")
    logger.info(f"@329 {LOG_ID} {json.dumps(filtered_lines, indent=2, sort_keys=True)}")
    return filtered_lines
