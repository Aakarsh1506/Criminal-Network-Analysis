"""Local structured extraction through Ollama's native chat API."""

import logging

from ..errors import APIError

logger = logging.getLogger("uvicorn.error.extraction")


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
        "Ollama extraction: input=%s output=%s duration_ns=%s load_ns=%s",
        body.get("prompt_eval_count"), body.get("eval_count"),
        body.get("total_duration"), body.get("load_duration"),
    )
    return {"message": body["message"], "finish_reason": body.get("done_reason")}
