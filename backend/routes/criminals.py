from fastapi import APIRouter, Depends, Request

from ..errors import APIError, api_errors
from ..security import require_auth
from ..services.criminals import PERSONS_SQL, load_profile, map_person
from ..services.groq import explain_network
from ..services.insight import build_insight_context, validate_selection
from ..services.network import fetch_network
from ..services.ollama import explain_insight

router = APIRouter(
    prefix="/api/criminals", tags=["Criminals"], dependencies=[Depends(require_auth)]
)


@router.get("/", include_in_schema=False)
@router.get("")
async def list_criminals(request: Request, q: str = "", tags: str = "", all: str = ""):
    with api_errors("Failed to load criminals"):
        rows = await request.app.state.db.query(PERSONS_SQL.format(where_clause=""))
        results = [map_person(row) for row in rows]
        query = q.lower().strip()
        wanted_tags = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
        if query or wanted_tags:
            # Match any name, alias, or crime tag; filters use OR semantics.
            results = [
                person
                for person in results
                if (
                    (
                        query
                        and (
                            query in person["name"].lower()
                            or query in (person["alias"] or "").lower()
                        )
                    )
                    or any(tag.lower() in wanted_tags for tag in person["crimeTags"])
                    or (query and any(query in tag.lower() for tag in person["crimeTags"]))
                )
            ]
        elif all != "true":
            # An empty search only lists everyone when explicitly requested.
            results = []
        return results


@router.get("/{person_id}")
async def get_profile(person_id: str, request: Request):
    with api_errors("Failed to load criminal"):
        profile = await load_profile(person_id, request.app.state.db, request.app.state.graph)
        if profile is None:
            raise APIError("Not found", 404)
        return profile


@router.get("/{person_id}/network")
async def get_network(person_id: str, request: Request):
    with api_errors("Failed to load criminal network"):
        network = await fetch_network(person_id, request.app.state.graph.run)
        if network is None:
            raise APIError("Network not found for this person", 404)
        return network


@router.post("/{person_id}/explain")
async def explain(person_id: str, request: Request):
    try:
        body = await request.json()
    except ValueError:
        raise APIError("Select a node or relationship to generate AI insight.", 400) from None
    selection = body.get("selection") if isinstance(body, dict) else None
    validate_selection(selection)
    state = request.app.state
    use_ollama = state.settings.extraction_provider == "ollama"
    if not use_ollama and not state.settings.groq_api_key.strip():
        raise APIError(
            "AI is not configured. Add GROQ_API_KEY to backend/.env and restart the server.", 503
        )
    if state.active_explanations >= 3:
        raise APIError("AI is busy. Please try again shortly.", 429)
    # No await between checking and incrementing: atomic within this worker's event loop.
    state.active_explanations += 1
    try:
        with api_errors("Unable to load records for the AI insight. Please try again."):
            profile = await load_profile(person_id, state.db, state.graph)
            if profile is None:
                raise APIError("Profile not found.", 404)
            network = await fetch_network(person_id, state.graph.run)
            context = build_insight_context(network, selection)
            if use_ollama:
                import json
                explanation = await explain_insight(
                    state.http_client, state.settings,
                    json.dumps(context, ensure_ascii=False, separators=(",", ":")),
                )
            else:
                explanation = await explain_network(
                    profile,
                    insight_context=context,
                    api_key=state.settings.groq_api_key,
                    model=state.settings.groq_model,
                    client=state.http_client,
                )
            return {"explanation": explanation}
    finally:
        # Release the AI slot even if the request fails or is cancelled.
        state.active_explanations -= 1
