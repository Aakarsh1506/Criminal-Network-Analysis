"""Local structured extraction through Ollama's native chat API."""

import logging

from ..errors import APIError

logger = logging.getLogger("uvicorn.error.extraction")


async def explain_insight(client, settings, context, *, thinking=False):
    """Generate an investigator insight with the locally running Ollama model."""
    chat_prompt = (
        " Answer only the investigator's question in about 100 words. Think through the "
        "evidence internally, then give one concise answer. You may include one brief "
        "sentence labeled 'Investigator insight:' when useful. Do not output headings such "
        "as Gaps, Next Checks, Investigator Question, or Answer, and do not repeat the question."
        if thinking else ""
    )
    response = await client.post(
        settings.ollama_base_url.rstrip("/") + "/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Act as an investigative analyst. Write an AI insight under 300 words "
                        "with sections Recorded facts, Investigative significance, Gaps and "
                        "alternative explanations, and Next checks. Use only supplied records. "
                        "Do not invent facts, infer guilt, predict criminality, or treat shared "
                        "attributes as proof of association. Cite supplied IDs." + chat_prompt
                    ),
                },
                {"role": "user", "content": context},
            ],
            "stream": False,
            "think": thinking,
            "keep_alive": "10m",
            # Thinking tokens and answer tokens share num_predict. Leave enough
            # room for both, otherwise qwen3 can finish with an empty content field.
            "options": {"temperature": 0.2, "num_predict": 800 if thinking else 1200, "num_ctx": 16384},
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
    return answer.strip()


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
