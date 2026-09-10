from ..errors import APIError


def validate_selection(selection):
    if (not isinstance(selection, dict)
            or selection.get("type") not in ("node", "edge", "person")
            or not isinstance(selection.get("id"), str)
            or not selection["id"].strip() or len(selection["id"]) > 512):
        raise APIError("Select a node or relationship to generate AI insight.", 400)


def build_insight_context(network, selection):
    validate_selection(selection)
    network = network or {"nodes": [], "edges": []}
    kind, record_id = selection["type"], selection["id"]
    records = network["edges"] if kind == "edge" else network["nodes"]
    selected = next((item for item in records if
                     (str(item.get("personId")) if kind == "person" else item["id"]) == record_id), None)
    if selected is None:
        raise APIError("Selection is no longer available in this network. Select another record.", 404)
    connected = ([selected] if kind == "edge" else
                 [edge for edge in network["edges"] if selected["id"] in (edge["source"], edge["target"])])
    edges = connected[:25]
    ids = {endpoint for edge in edges for endpoint in (edge["source"], edge["target"])}
    if kind != "edge":
        ids.add(selected["id"])
    return {
        "selection": {"type": "edge" if kind == "edge" else "node", "record": selected},
        "nodes": [node for node in network["nodes"] if node["id"] in ids],
        "relationships": edges,
        "limitations": {
            "networkTruncated": bool(network.get("truncated")),
            "connectionsOmitted": len(connected) > len(edges),
            "scope": "Selected record and at most 25 immediate connections. Graph steps do not prove personal association. Evidence and review status may be missing; recorded claims are not automatically verified.",
        },
    }
