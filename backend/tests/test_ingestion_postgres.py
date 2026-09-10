"""Run against an isolated database using CNA_TEST_PGHOST and CNA_TEST_PGPORT."""

import os
from dataclasses import replace

import pytest

from backend.db import Database
from backend.errors import APIError
from backend.services.extraction import Extraction
from backend.services.ingestion_store import persist_extraction

# Matches the supplied dump's columns and constraints; geometry is unused by ingestion.
BASE_SCHEMA = """
CREATE TABLE persons (person_id varchar(20) PRIMARY KEY, name varchar(100) NOT NULL,
 alias varchar(100), dob date, age integer, height_cm integer, state varchar(100),
 city varchar(100), last_seen date, family_known text, photo varchar(255),
 record_status varchar(100) NOT NULL);
CREATE TABLE crime_types (crime_id serial PRIMARY KEY, crime_name varchar(100) UNIQUE NOT NULL,
 description text);
CREATE TABLE locations (location_id serial PRIMARY KEY, city varchar(100) NOT NULL,
 state varchar(100) NOT NULL, latitude numeric(10,7), longitude numeric(10,7), geom text);
CREATE TABLE cases (case_id varchar(20) PRIMARY KEY, person_id varchar(20) NOT NULL REFERENCES persons,
 crime_id integer REFERENCES crime_types, case_month date, location_name varchar(150),
 case_status varchar(100), location_id integer REFERENCES locations);
"""


@pytest.fixture
async def real_db(settings):
    host = os.environ.get("CNA_TEST_PGHOST")
    if not host:
        pytest.skip("Set CNA_TEST_PGHOST to an isolated test database")
    from uuid import uuid4

    import psycopg
    from psycopg import sql

    database_name = "cna_test_" + uuid4().hex
    options = {
        "host": host,
        "port": int(os.environ["CNA_TEST_PGPORT"]),
        "user": os.environ.get("USER", "postgres"),
        "dbname": "postgres",
        "autocommit": True,
    }
    async with await psycopg.AsyncConnection.connect(**options) as conn:
        await conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    database = Database(
        replace(
            settings,
            pg_host=host,
            pg_port=options["port"],
            pg_user=options["user"],
            pg_database=database_name,
        )
    )
    await database.open()
    try:
        await database.query(BASE_SCHEMA)
        await database.ensure_schema()
        await database.ensure_schema()  # Startup migrations must be repeatable.
        await database.query(
            "INSERT INTO officers (officer_id,username,password_hash,name,org_name) VALUES (1,'tester','hash','Tester','Test')"
        )
        await database.query(
            "INSERT INTO persons (person_id,name,record_status) VALUES ('P001','Alice','Active')"
        )
        await database.query(
            "INSERT INTO crime_types (crime_id,crime_name) VALUES (1,'Robbery'),(10,'Fraud')"
        )
        yield database
    finally:
        await database.close()
        async with await psycopg.AsyncConnection.connect(**options) as conn:
            await conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )


def full_extraction():
    entities = [
        ("a", "Person", "Alice", "P001", []),
        ("b", "Person", "Bob", None, []),
        ("c", "Case", "FIR-2026-1", "FIR-2026-1", []),
        ("o", "Organization", "Acme", "ORG-10", []),
        ("v", "Vehicle", "AB123", "AB123", []),
        ("l", "Location", "Mumbai", None, []),
        ("t", "CrimeType", "Extortion", None, []),
        ("p", "PhoneNumber", "1234567890", "1234567890", []),
    ]
    relationships = [
        ("a", "WITNESS_IN", "c"),
        ("b", "SUSPECT_IN", "c"),
        ("o", "MENTIONED_IN", "c"),
        ("v", "MENTIONED_IN", "c"),
        ("c", "OCCURRED_AT", "l"),
        ("c", "OF_TYPE", "t"),
        ("a", "EMPLOYED_BY", "o"),
        ("o", "OWNS", "v"),
        ("a", "CONTACTED", "b"),
    ]
    return Extraction.model_validate(
        {
            "entities": [
                {"ref": r, "kind": k, "name": n, "identifier": i, "attributes": a, "evidence": n}
                for r, k, n, i, a in entities
            ],
            "relationships": [
                {"subject": s, "predicate": p, "object": o, "evidence": "source quote"}
                for s, p, o in relationships
            ],
        }
    )


async def add_document(db, confirmed=True):
    rows = await db.query("""INSERT INTO officer_documents
        (officer_id,original_name,stored_name,mime_type,size_bytes,source_type,processing_status)
        VALUES (1,'source.txt','source.txt','text/plain',5,'fir','processing') RETURNING document_id""")
    if confirmed:
        await db.query(
            "UPDATE officer_documents SET confirmed_at=now(), confirmed_by=1 WHERE document_id=%s",
            (rows[0]["document_id"],),
        )
    return rows[0]["document_id"]


async def test_persistence_maps_all_kinds_roles_and_repairs_sequence(real_db):
    doc_id = await add_document(real_db)
    result = full_extraction()
    payload = await persist_extraction(real_db, doc_id, result)
    assert len(payload["nodes"]) == 8 and len(payload["edges"]) == 9
    assert (await real_db.query("SELECT COUNT(*) AS n FROM persons"))[0]["n"] == 2
    assert (await real_db.query("SELECT record_status FROM persons WHERE person_id='P001'"))[0][
        "record_status"
    ] == "Active"
    case = (await real_db.query("SELECT * FROM cases"))[0]
    assert case["person_id"] is None  # The witness was not made the primary suspect.
    assert case["crime_id"] > 10  # Supplied dump has a stale sequence.
    assert case["location_id"] is not None
    roles = await real_db.query("SELECT role FROM case_people ORDER BY role")
    assert [row["role"] for row in roles] == ["SUSPECT_IN", "WITNESS_IN"]
    assert (await real_db.query("SELECT state FROM locations"))[0]["state"] is None
    assert payload == await persist_extraction(real_db, doc_id, result)
    assert (await real_db.query("SELECT COUNT(*) AS n FROM extracted_relationships"))[0]["n"] == 9
    second_doc = await add_document(real_db)
    await persist_extraction(real_db, second_doc, result)
    assert (await real_db.query("SELECT COUNT(*) AS n FROM cases"))[0]["n"] == 1
    assert (await real_db.query("SELECT COUNT(*) AS n FROM vehicles"))[0]["n"] == 1
    # Names alone do not merge people from different documents.
    assert (await real_db.query("SELECT COUNT(*) AS n FROM persons WHERE name='Bob'"))[0]["n"] == 2


async def test_sql_failure_rolls_back_entities_and_outbox(real_db):
    doc_id = await add_document(real_db)
    result = full_extraction()
    result.entities[1].attributes = []
    # The second named record deliberately conflicts with an existing explicit ID.
    result.entities[1].identifier = "P001"
    with pytest.raises(APIError, match="conflicts"):
        await persist_extraction(real_db, doc_id, result)
    assert (await real_db.query("SELECT COUNT(*) AS n FROM extracted_entities"))[0]["n"] == 0
    assert (await real_db.query("SELECT graph_payload FROM officer_documents"))[0][
        "graph_payload"
    ] is None


async def test_uploaded_text_flows_through_ai_sql_and_graph(real_db, settings, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    import httpx

    from backend.services import ingestion
    from backend.services.criminals import load_profile
    from backend.services.extraction import validate_extraction

    source = "Alice (P001) witnessed case C100."
    result = Extraction.model_validate(
        {
            "entities": [
                {
                    "ref": "p",
                    "kind": "Person",
                    "name": "Alice",
                    "identifier": "P001",
                    "attributes": [],
                    "evidence": "Alice (P001)",
                },
                {
                    "ref": "c",
                    "kind": "Case",
                    "name": "C100",
                    "identifier": "C100",
                    "attributes": [],
                    "evidence": "case C100",
                },
            ],
            "relationships": [
                {"subject": "p", "predicate": "WITNESS_IN", "object": "c", "evidence": source}
            ],
        }
    )
    validate_extraction(result, source)
    doc_id = await add_document(real_db)
    settings.upload_dir.mkdir(parents=True)
    (settings.upload_dir / "source.txt").write_text(source)
    provider = AsyncMock()
    provider.post.return_value = httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": result.model_dump_json()}, "finish_reason": "stop"}]
        },
    )
    graph = SimpleNamespace(driver=MagicMock(), run=AsyncMock(return_value=[]))
    tx = AsyncMock()
    session = AsyncMock()

    async def write(callback):
        await callback(tx)

    session.execute_write.side_effect = write
    graph.driver.session.return_value.__aenter__.return_value = session
    state = SimpleNamespace(
        db=real_db,
        graph=graph,
        http_client=provider,
        settings=replace(settings, groq_api_key="fake"),
    )
    doc = (await real_db.query("SELECT * FROM officer_documents WHERE document_id=%s", (doc_id,)))[
        0
    ]
    await ingestion.process_document(state, doc)
    saved = (
        await real_db.query("SELECT * FROM officer_documents WHERE document_id=%s", (doc_id,))
    )[0]
    assert saved["processing_status"] == "complete"
    assert saved["extracted_text"] == source
    assert len(saved["extraction"]["entities"]) == 2
    assert "WITNESS_IN" in tx.run.call_args.args[0]
    profile = await load_profile("P001", real_db, graph)
    assert len(profile["criminal"]["cases"]) == 1
    assert provider.post.await_count == 1


async def test_review_gate_then_exact_confirmation(real_db, settings):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import httpx
    from psycopg.types.json import Jsonb

    from backend.app import create_app
    from backend.security import sign_officer_token
    from backend.services.ingestion import process_document

    doc_id = await add_document(real_db, confirmed=False)
    result = full_extraction()
    await real_db.query(
        "UPDATE officer_documents SET extraction=%s, extracted_text='source' WHERE document_id=%s",
        (Jsonb(result.model_dump()), doc_id),
    )
    doc = (await real_db.query("SELECT * FROM officer_documents WHERE document_id=%s", (doc_id,)))[
        0
    ]
    state = SimpleNamespace(settings=settings, db=real_db, graph=AsyncMock())
    await process_document(state, doc)
    assert (await real_db.query("SELECT processing_status FROM officer_documents"))[0][
        "processing_status"
    ] == "awaiting_review"
    assert (await real_db.query("SELECT COUNT(*) AS n FROM extracted_entities"))[0]["n"] == 0
    assert (await real_db.query("SELECT COUNT(*) AS n FROM cases"))[0]["n"] == 0
    with pytest.raises(APIError, match="Review and confirm"):
        await persist_extraction(real_db, doc_id, result)
    app = create_app(settings, database=real_db, graph=state.graph, initialize_schema=False)
    profile = {
        "officerId": 1,
        "username": "tester",
        "name": "Tester",
        "orgName": "Test",
        "role": "officer",
    }
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(
                settings.cookie_name, sign_officer_token({**profile, "officerId": 2}, settings)
            )
            assert (
                await client.post(
                    f"/api/documents/{doc_id}/confirm", json={"extraction": result.model_dump()}
                )
            ).status_code == 409
            client.cookies.set(settings.cookie_name, sign_officer_token(profile, settings))
            changed = result.model_dump()
            changed["entities"][0]["name"] = "Changed"
            assert (
                await client.post(f"/api/documents/{doc_id}/confirm", json={"extraction": changed})
            ).status_code == 409
            response = await client.post(
                f"/api/documents/{doc_id}/confirm", json={"extraction": result.model_dump()}
            )
            assert response.status_code == 200 and response.json()["confirmedAt"]
            assert (
                await client.post(
                    f"/api/documents/{doc_id}/confirm", json={"extraction": result.model_dump()}
                )
            ).status_code == 409
    # Confirmation schedules the write; it does not race the queue by writing here.
    assert (await real_db.query("SELECT COUNT(*) AS n FROM extracted_entities"))[0]["n"] == 0
    payload = await persist_extraction(real_db, doc_id, result)
    assert len(payload["nodes"]) == 8


async def test_location_sentence_and_person_links_survive_saving(real_db):
    result = full_extraction()
    sentence = "Bob resides in Mumbai."
    location = next(e for e in result.entities if e.kind == "Location")
    location.evidence = sentence
    from backend.services.extraction import Relationship

    result.relationships.extend(
        [
            Relationship(
                subject="b", predicate="RESIDES_IN", object=location.ref, evidence=sentence
            ),
            Relationship(
                subject="a",
                predicate="SEEN_AT",
                object=location.ref,
                evidence="Alice was seen in Mumbai.",
            ),
        ]
    )
    payload = await persist_extraction(real_db, await add_document(real_db), result)
    assert {e["predicate"] for e in payload["edges"]} >= {"RESIDES_IN", "SEEN_AT"}
    assert (await real_db.query("SELECT evidence FROM extracted_entities WHERE kind='Location'"))[
        0
    ]["evidence"] == sentence
    await real_db.ensure_schema()
    rows = await real_db.query(
        "SELECT predicate, evidence FROM extracted_relationships WHERE predicate IN ('RESIDES_IN','SEEN_AT') ORDER BY predicate"
    )
    assert rows == [
        {"predicate": "RESIDES_IN", "evidence": sentence},
        {"predicate": "SEEN_AT", "evidence": "Alice was seen in Mumbai."},
    ]


async def test_rejected_relationships_never_enter_sql_or_graph_payload(real_db):
    from types import SimpleNamespace

    from backend.routes.documents import ConfirmBody, confirm_document

    result = full_extraction()
    original = result.model_dump()
    doc_id = await add_document(real_db, confirmed=False)
    from psycopg.types.json import Jsonb

    await real_db.query(
        "UPDATE officer_documents SET processing_status='awaiting_review', extraction=%s WHERE document_id=%s",
        (Jsonb(original), doc_id),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=real_db)))
    await confirm_document(
        doc_id,
        ConfirmBody(extraction=result, rejected_relationship_indices=[0, 1]),
        request,
        {"officerId": 1},
    )
    stored = (
        await real_db.query(
            "SELECT extraction FROM officer_documents WHERE document_id=%s", (doc_id,)
        )
    )[0]["extraction"]
    assert len(stored["excluded_relationships"]) == 2
    assert result.model_dump() == original
    payload = await persist_extraction(real_db, doc_id, Extraction.model_validate(stored))
    assert len(payload["edges"]) == len(result.relationships) - 2
    assert not any(e["predicate"] in {"WITNESS_IN", "SUSPECT_IN"} for e in payload["edges"])
    assert not await real_db.query(
        "SELECT * FROM extracted_relationships WHERE predicate IN ('WITNESS_IN','SUSPECT_IN')"
    )
    with pytest.raises(APIError, match="Draft changed"):
        await confirm_document(doc_id, ConfirmBody(extraction=result), request, {"officerId": 1})
