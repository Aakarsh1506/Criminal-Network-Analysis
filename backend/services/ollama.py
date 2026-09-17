"""Local structured extraction through Ollama's native chat API."""

import json
import logging

from ..errors import APIError
from .investigator_chat import SCHEMA, format_answer, messages_for

logger = logging.getLogger("uvicorn.error.extraction")


async def explain_insight(client, settings, context, *, thinking=False):
    """Generate an investigator insight with the locally running Ollama model."""
    chat_context = json.loads(context) if thinking else None
    messages = messages_for(chat_context) if thinking else [
        {"role": "system", "content": (
            "Act as an investigative analyst. Write an AI insight under 300 words with the "
            "sections **Recorded facts**, **Investigator insight** and **Suggested checks**. "
            "Use only supplied records. The \"analysis\" field lists patterns already computed "
            "from the graph: roles by case, people sharing records with the selection, records "
            "linking several people, places also linked to a case, and evidence gaps. In "
            "Investigator insight, explain which of these patterns matter and present each as "
            "\"Possible lead:\" with the records it rests on and what would confirm or rule it out. "
            "Suggested checks: 2-4 bullet points naming the specific record, person or document to "
            "examine. Do not invent facts, infer guilt, predict criminality, or treat shared "
            "attributes as proof of association. Cite supplied IDs."
        )},
        {"role": "user", "content": context},
    ]
    response = await client.post(
        settings.ollama_base_url.rstrip("/") + "/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": messages,
            **({"format": SCHEMA} if thinking else {}),
            "stream": False,
            # Hidden reasoning made qwen3:1.7b spend its whole budget before answering
            # (3-minute timeouts, empty answers). The graph patterns are computed server-side,
            # so the model answers directly: about 25 s instead of timing out.
            "think": False,
            "keep_alive": "10m",
            "options": {"temperature": 0.2, "num_predict": 900 if thinking else 1200, "num_ctx": 16384},
        },
        timeout=settings.ollama_timeout,
    )
    if response.status_code == 404:
        raise APIError(
            "Ollama model not found. Run `ollama pull` with the model named in OLLAMA_MODEL.",
            503,
        )
    if not response.is_success:
        raise APIError("Ollama could not generate an insight. Check the local Ollama server.", 502)
    body = response.json()
    message = body.get("message") or {}
    answer = message.get("content") or body.get("response")
    if not isinstance(answer, str) or not answer.strip():
        raise APIError("Ollama returned an empty insight. Please try again.", 502)
    if body.get("done_reason") == "length":
        raise APIError("The AI answer was cut short. Please retry your question.", 502)
    return format_answer(answer, ((chat_context.get("analysis") or {}).get("key_observations") if isinstance(chat_context, dict) else None)) if thinking else answer.strip()


async def extraction_choice(client, settings, messages, schema, max_tokens):
    response = await client.post(
        settings.ollama_base_url.rstrip("/") + "/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": messages,
            "format": schema,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {"temperature": 0, "num_predict": max_tokens, "num_ctx": 16384},
        },
        timeout=settings.ollama_timeout,
    )
    if response.status_code == 404:
        raise APIError(
            "Ollama model or endpoint not found. Check OLLAMA_BASE_URL and run "
            "ollama pull with the model named in OLLAMA_MODEL.", 503,
        )
    if response.status_code == 400:
        raise APIError(
            "Ollama rejected the extraction request. Update Ollama and check OLLAMA_MODEL "
            "supports structured output and think=false (default: qwen3:4b).", 502,
        )
    if not response.is_success:
        raise APIError("Ollama extraction failed. Check the local Ollama server and retry.", 502)
    body = response.json()
    if not body.get("done"):
        raise APIError("Ollama extraction was incomplete. Retry processing.", 502)
    logger.info(
        "Ollama extraction: input=%s output=%s duration_ns=%s load_ns=%s finish=%s limit=%s",
        body.get("prompt_eval_count"), body.get("eval_count"),
        body.get("total_duration"), body.get("load_duration"),
        body.get("done_reason"), max_tokens,
    )
    return {"message": body["message"], "finish_reason": body.get("done_reason")}
