import json
from pathlib import Path as FilePath
from unittest.mock import AsyncMock

import pytest
from neo4j.graph import Graph, Node, Path

from backend1.services.network import (
    NETWORK_PATH_LIMIT,
    NETWORK_QUERY,
    fetch_network,
    serialize_network,
)
from backend1.utils.avatar import color_for_id, initials_avatar


@pytest.fixture
def native_graph():
    graph = Graph()
    a = Node(
        graph,
        "person-a",
        1,
        ["Person"],
        {"person_id": "P001", "name": "Mohit Chawla", "alias": "MC", "city": "Delhi"},
    )
    b = Node(graph, "case-b", 2, ["Case"], {"case_id": "C001"})
    c = Node(graph, "person-c", 3, ["Person"], {"person_id": "P002", "name": "Jane Doe"})

    def relationship(element_id, start, end):
        edge = graph.relationship_type("INVOLVED_IN")(
            graph, element_id, 1, {"source": "synthetic_demo", "reason": "Example"}
        )
        edge._start_node = start
        edge._end_node = end
        return edge

    return a, b, c, relationship


def test_matches_express_graph_and_avatar(native_graph):
    a, b, c, relationship = native_graph
    records = [
        {"path": Path(a, relationship("ab", a, b), relationship("cb", c, b))},
        {"path": Path(a)},
    ]
    expected = json.loads((FilePath(__file__).parent / "fixtures/express_outputs.json").read_text())
    assert serialize_network(records) == expected["network"]
    assert initials_avatar("Mohit Chawla", color_for_id("P001")) == expected["avatar"]


def test_deduplicates_minimum_depth_parallel_edges_and_isolated(native_graph):
    a, b, c, relationship = native_graph
    records = [
        {"path": Path(a, relationship("ab", a, b), relationship("cb", c, b))},
        {"path": Path(a, relationship("ac", a, c))},
        {"path": Path(a, relationship("ab", a, b))},
        {"path": Path(a, relationship("ab2", a, b))},
    ]
    graph = serialize_network(records)
    assert len(graph["nodes"]) == 3 and len(graph["edges"]) == 4
    assert next(node for node in graph["nodes"] if node["id"] == "person-c")["depth"] == 1
    assert next(edge for edge in graph["edges"] if edge["id"] == "cb")["source"] == "person-c"
    assert serialize_network([]) == {"nodes": [], "edges": []}
    isolated = serialize_network([{"path": Path(a)}])
    assert isolated["nodes"][0]["depth"] == 0 and isolated["edges"] == []


async def test_network_query_binding_truncation_and_errors(native_graph):
    a, *_ = native_graph
    query = AsyncMock(return_value=[{"path": Path(a)}] * NETWORK_PATH_LIMIT)
    graph = await fetch_network("P001' injected", query)
    query.assert_awaited_once_with(NETWORK_QUERY, {"id": "P001' injected"})
    assert not graph["truncated"] and graph["pathLimit"] == NETWORK_PATH_LIMIT
    query.return_value.append({"path": Path(a)})
    assert (await fetch_network("P001", query))["truncated"]
    query.return_value = []
    assert await fetch_network("missing", query) is None
    query.side_effect = RuntimeError("offline")
    with pytest.raises(RuntimeError):
        await fetch_network("P001", query)


async def test_network_endpoint_uses_native_paths(officer_client, graph, native_graph):
    a, b, c, relationship = native_graph
    graph.run.return_value = [{"path": Path(a, relationship("ab", a, b), relationship("cb", c, b))}]
    response = await officer_client.get("/api/criminals/P001/network")
    assert response.status_code == 200
    assert len(response.json()["nodes"]) == 3
    assert response.json()["edges"][1]["source"] == "person-c"
    graph.run.assert_awaited_once_with(NETWORK_QUERY, {"id": "P001"})
