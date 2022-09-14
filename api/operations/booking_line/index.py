from api.common.constants import PALLETS, SKIDS


def handle_zero(line, client=None):
    if (
        line["l_005_dim_length"] == 0
        or line["l_006_dim_width"] == 0
        or line["l_007_dim_height"] == 0
        or line["l_009_weight_per_each"] == 0
    ):
        zero_dims = []
        if not line["l_005_dim_length"]:
            zero_dims.append("length")

        if not line["l_006_dim_width"]:
            zero_dims.append("width")

        if not line["l_007_dim_height"]:
            zero_dims.append("height")

        if not line["l_009_weight_per_each"]:
            zero_dims.append("weight")

        # Anchor Packaging Pty Ltd
        if client and client.dme_account_num == "49294ca3-2adb-4a6e-9c55-9b56c0361953":
            line["l_003_item"] += f" (ZERO Dims - {', '.join(zero_dims)})"
            line["l_004_dim_UOM"] = "m"
            line["l_008_weight_UOM"] = "kg"
            line["l_005_dim_length"] = line["l_005_dim_length"] or 0.25
            line["l_006_dim_width"] = line["l_006_dim_width"] or 0.25
            line["l_007_dim_height"] = line["l_007_dim_height"] or 0.25
            line["l_009_weight_per_each"] = line["l_009_weight_per_each"] or 1
        # JasonL
        elif (
            client and client.dme_account_num == "1af6bcd2-6148-11eb-ae93-0242ac130002"
        ):
            if line["l_001_type_of_packaging"] in SKIDS:
                line["l_003_item"] += f" (ZERO Dims - {', '.join(zero_dims)})"
                line["l_004_dim_UOM"] = "m"
                line["l_008_weight_UOM"] = "kg"
                line["l_005_dim_length"] = line["l_005_dim_length"] or 1.2
                line["l_006_dim_width"] = line["l_006_dim_width"] or 1.2
                line["l_007_dim_height"] = line["l_007_dim_height"] or 1.2
                line["l_009_weight_per_each"] = line["l_009_weight_per_each"] or 100
            else:
                line["l_003_item"] += f" (ZERO Dims - {', '.join(zero_dims)})"
                line["l_004_dim_UOM"] = "m"
                line["l_008_weight_UOM"] = "kg"
                line["l_005_dim_length"] = line["l_005_dim_length"] or 1
                line["l_006_dim_width"] = line["l_006_dim_width"] or 0.8
                line["l_007_dim_height"] = line["l_007_dim_height"] or 1
                line["l_009_weight_per_each"] = line["l_009_weight_per_each"] or 50
        else:
            line["l_003_item"] += f" (ZERO Dims - {', '.join(zero_dims)})"
            line["l_004_dim_UOM"] = "m"
            line["l_008_weight_UOM"] = "kg"
            line["l_005_dim_length"] = line["l_005_dim_length"] or 0.5
            line["l_006_dim_width"] = line["l_006_dim_width"] or 0.5
            line["l_007_dim_height"] = line["l_007_dim_height"] or 0.5
            line["l_009_weight_per_each"] = line["l_009_weight_per_each"] or 1

    return line
