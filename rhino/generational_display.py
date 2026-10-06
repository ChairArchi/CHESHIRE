"""Standard-library-only display selection; existing insertion owns offsets/Undo."""


def comparison_items(response):
    items=[("C0 SOURCE",response["carrier"]["mesh"],None)]
    for variant in response["variants"]:
        stages=variant["stages"]
        if not stages:
            continue
        if variant["id"] == "CONTROL_L4":
            stage=stages[-1]
            label=f"L4 CONTROL G{stage['generation']}"
            if variant["status"] != "SUCCESS":
                label+=" (last valid; PARTIAL)"
            items.append((label,stage["mesh"],None))
        else:
            for stage in stages:
                if stage["generation"] in (1,3,5) or stage is stages[-1]:
                    label=f"BEST NEW G{stage['generation']} (partial hierarchy)"
                    if variant["status"] != "SUCCESS" and stage is stages[-1]:
                        label+=" (last valid; PARTIAL)"
                    items.append((label,stage["mesh"],None))
    return items
