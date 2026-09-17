from ..errors import APIError


def validate_selection(selection):
    if (not isinstance(selection, dict)
            or selection.get("type") not in ("node", "edge", "person")
            or not isinstance(selection.get("id"), str)
            or not selection["id"].strip() or len(selection["id"]) > 512):
        raise APIError("Select a node or relationship to generate AI insight.", 400)


NETWORK_LIMIT = 40


def build_network_context(network):
    """Whole-network context: used when a question is asked without selecting a record."""
    network = network or {"nodes": [], "edges": []}
    nodes = network["nodes"][:NETWORK_LIMIT]
    ids = {node["id"] for node in nodes}
    edges = [edge for edge in network["edges"]
             if edge["source"] in ids and edge["target"] in ids][:NETWORK_LIMIT + 20]
    return {
        "selection": {"type": "network", "record": None},
        "nodes": nodes,
        "relationships": edges,
        "analysis": network_analysis(network, None),
        "limitations": {
            "networkTruncated": bool(network.get("truncated")),
            "connectionsOmitted": len(network["edges"]) > len(edges) or len(network["nodes"]) > len(nodes),
            "scope": f"The whole displayed network, up to {NETWORK_LIMIT} records and their links. "
                     "No single record is selected. Graph steps do not prove personal association. "
                     "Evidence and review status may be missing; recorded claims are not automatically verified.",
        },
    }


def build_insight_context(network, selection):
    if selection is None:
        return build_network_context(network)
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
        "analysis": network_analysis(network, selected if kind != "edge" else None),
        "nodes": [node for node in network["nodes"] if node["id"] in ids],
        "relationships": edges,
        "limitations": {
            "networkTruncated": bool(network.get("truncated")),
            "connectionsOmitted": len(connected) > len(edges),
            "scope": "Selected record and at most 25 immediate connections. Graph steps do not prove personal association. Evidence and review status may be missing; recorded claims are not automatically verified.",
        },
    }


ROLE_LABELS = {"SUSPECT IN", "WITNESS IN", "MENTIONED IN"}
PLACE_LABELS = {"RESIDES IN", "SEEN AT"}


def network_analysis(network, selected, limit=5):
    """Patterns a small model cannot reliably compute from raw graph JSON.

    Every item names the records it is derived from. Shared records are listed as
    leads to check, never as proof that people know each other.
    """
    # Missing fields are tolerated: older graph rows can lack a label or kind.
    nodes = {node["id"]: {**node, "kind": node.get("kind") or "Record", "label": node.get("label") or node["id"]}
             for node in network["nodes"]}
    neighbours, labelled = {}, []
    for edge in network["edges"]:
        if edge.get("source") in nodes and edge.get("target") in nodes:
            edge = {**edge, "label": edge.get("label") or ""}
            neighbours.setdefault(edge["source"], set()).add(edge["target"])
            neighbours.setdefault(edge["target"], set()).add(edge["source"])
            labelled.append(edge)

    def name(node_id):
        node = nodes[node_id]
        return f"{node['label']} ({node['kind']})"

    unverified = sum(1 for edge in labelled if (edge.get("reviewStatus") or "unverified") != "verified")
    missing_evidence = sum(1 for edge in labelled if not edge.get("evidence"))
    summary = {
        "records_in_network": {kind: sum(1 for node in nodes.values() if node["kind"] == kind)
                               for kind in sorted({node["kind"] for node in nodes.values()})},
        "relationships_unverified": unverified,
        "relationships_without_evidence": missing_evidence,
    }
    if selected is None:
        # Whole-network questions: the same patterns, computed across every record shown.
        pairs, hubs = {}, []
        for node_id, node in nodes.items():
            people = sorted(nodes[item]["label"] for item in neighbours.get(node_id, set())
                            if nodes[item]["kind"] == "Person")
            if node["kind"] != "Person" and len(people) >= 2:
                hubs.append({"record": name(node_id), "people": people[:8], "count": len(people)})
            for first in people:
                for second in people:
                    if first < second:
                        pairs.setdefault((first, second), []).append(name(node_id))
        hubs.sort(key=lambda item: -item["count"])
        observations = [f"{item['record']} links {item['count']} people: {', '.join(item['people'])}."
                        for item in hubs[:4]]
        observations += [f"{first} and {second} appear together in {len(records)} record(s): {', '.join(sorted(records))}."
                         for (first, second), records in
                         sorted(pairs.items(), key=lambda item: -len(item[1]))[:3] if len(records) > 1]
        if unverified or missing_evidence:
            observations.append(f"{unverified} of {len(labelled)} relationships are unverified; "
                                f"{missing_evidence} have no recorded evidence.")
        return {**summary, "key_observations": observations[:7]}
    me = selected["id"]
    if me not in nodes:
        return summary
    direct = [edge for edge in labelled if me in (edge["source"], edge["target"])]
    other = lambda edge: edge["target"] if edge["source"] == me else edge["source"]  # noqa: E731

    roles = {}
    for edge in direct:
        if edge["label"] in ROLE_LABELS and nodes[other(edge)]["kind"] == "Case":
            roles.setdefault(edge["label"], []).append(nodes[other(edge)]["label"])
    # People who appear in the same records as the selected one, ranked by how many.
    shared = []
    for node_id, node in nodes.items():
        if node_id == me or node["kind"] != "Person":
            continue
        common = neighbours.get(me, set()) & neighbours.get(node_id, set())
        if common:
            shared.append({"person": node["label"], "shared_records": sorted(name(item) for item in common)})
    shared.sort(key=lambda item: (-len(item["shared_records"]), item["person"]))
    # Records around the selection that connect several people (e.g. one case, many suspects).
    hubs = []
    for node_id in neighbours.get(me, set()):
        people = sorted(nodes[item]["label"] for item in neighbours.get(node_id, set())
                        if item != me and nodes[item]["kind"] == "Person")
        if len(people) >= 2:
            hubs.append({"record": name(node_id), "other_people": people[:8], "count": len(people)})
    hubs.sort(key=lambda item: -item["count"])
    # A place the person resides in or was seen at that is also a case's place of occurrence.
    places = {other(edge): edge["label"] for edge in direct
              if edge["label"] in PLACE_LABELS and nodes[other(edge)]["kind"] == "Location"}
    overlaps = []
    for edge in labelled:
        if edge["label"] == "OCCURRED AT" and edge["target"] in places:
            overlaps.append({"place": nodes[edge["target"]]["label"], "person_link": places[edge["target"]],
                             "case": nodes[edge["source"]]["label"]})
    cases = [nodes[other(edge)] for edge in direct if nodes[other(edge)]["kind"] == "Case"]
    typed = {edge["source"] for edge in labelled if edge["label"] == "OF TYPE"}
    untyped = sorted({case["label"] for case in cases if case["id"] not in typed})
    direct_unverified = sum(1 for edge in direct if (edge.get("reviewStatus") or "unverified") != "verified")
    # Plain sentences for a small model to reason from; each names its records.
    subject = nodes[me]["label"]
    observations = []
    if roles:
        observations.append(f"{subject} is recorded as " + "; ".join(
            f"{label.lower()} {len(items)} case(s): {', '.join(sorted(items))}" for label, items in sorted(roles.items())) + ".")
    for item in shared[:3]:
        cases_shared = [record for record in item["shared_records"] if record.endswith("(Case)")]
        if len(item["shared_records"]) >= 2 or len(cases_shared) >= 1:
            observations.append(f"{item['person']} appears with {subject} in {len(item['shared_records'])} record(s): "
                                f"{', '.join(item['shared_records'])}.")
    for item in overlaps[:2]:
        link = "resides" if item["person_link"] == "RESIDES IN" else "was seen"
        observations.append(f"{item['place']}, where {subject} {link}, is also the place of occurrence of {item['case']}.")
    for item in hubs[:2]:
        observations.append(f"{item['record']} links {subject} with {item['count']} other people: {', '.join(item['other_people'])}.")
    if direct_unverified or untyped:
        observations.append(f"{direct_unverified} of {len(direct)} direct links are unverified"
                            + (f"; no crime type is recorded for {', '.join(untyped)}" if untyped else "") + ".")
    return {
        **summary,
        "key_observations": observations[:7],
        "selected_roles_by_case": roles,
        "people_sharing_records_with_selected": shared[:limit],
        "records_linking_several_people": hubs[:limit],
        "places_also_linked_to_a_case": overlaps[:limit],
        "evidence_gaps": {
            "direct_links_unverified": direct_unverified,
            "direct_links_without_evidence": sum(1 for edge in direct if not edge.get("evidence")),
            "cases_without_recorded_crime_type": untyped,
        },
    }
