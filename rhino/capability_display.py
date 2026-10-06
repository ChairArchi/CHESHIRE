"""Display-only polygon tessellation and concise Task17 role selection."""


def polygon_display_plan(data):
    """Rhino faces require tri/quads. N-gon fan is explicitly display-only.

    Retain ordered polygon boundaries as MeshNgon groups and map each display
    face to its calculation face. Never feed tessellation back to subdivision.
    """
    faces=[]; source_ids=[]; ngons=[]
    for face in data["faces"]:
        corners=face["vertices"]
        if len(corners)<=4:
            faces.append(corners); source_ids.append(face["id"])
        else:
            first=len(faces)
            for i in range(1,len(corners)-1):
                faces.append([corners[0],corners[i],corners[i+1]]); source_ids.append(face["id"])
            ngons.append(dict(vertices=corners,faces=list(range(first,len(faces))),source_face=face["id"]))
    return faces,source_ids,ngons


def comparison_items(response):
    items=[("C0 SOURCE",response["carrier"]["mesh"],None)]
    for variant in response["variants"]:
        items.append((" / ".join(variant["roles"])+f" G{variant['generation']}",variant["mesh"],None))
    return items
