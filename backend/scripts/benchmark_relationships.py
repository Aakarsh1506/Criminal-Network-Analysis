"""Evaluate local relationship extraction using synthetic, labelled records only.

Run from the repository root:
  backend/.venv/bin/python -m backend.scripts.benchmark_relationships
No database is used. Results include missing/extra edges as well as time and tokens.
"""

import argparse
import asyncio
import json
import time
from dataclasses import replace

import httpx

from backend.config import Settings
from backend.services.extraction import Entity, extract_chunk, validate_extraction
from backend.services.local_entities import relevant_batches


def samples():
    identities = [("Case", "FIR/2026/9001"), ("Person", "Asha Verma"),
                  ("Person", "Rohan Sen"), ("Person", "Mira Das"),
                  ("Person", "Dev Rao"), ("Location", "Mumbai")]
    clear = (
        "FIR/2026/9001\nAsha Verma witnessed FIR/2026/9001.\n"
        "Rohan Sen is a suspect in FIR/2026/9001.\nMira Das witnessed FIR/2026/9001.\n"
        "Dev Rao is mentioned in FIR/2026/9001.\nAsha Verma contacted Rohan Sen.\n"
        "Rohan Sen contacted Dev Rao.\nDev Rao resides in Mumbai.\n"
        "Mira Das was seen in Mumbai.\nFIR/2026/9001 occurred in Mumbai.\n"
    )
    yield "explicit_facts", clear, identities, {
        ("e1", "WITNESS_IN", "e0"), ("e2", "SUSPECT_IN", "e0"),
        ("e3", "WITNESS_IN", "e0"), ("e4", "MENTIONED_IN", "e0"),
        ("e1", "CONTACTED", "e2"), ("e2", "CONTACTED", "e4"),
        ("e4", "RESIDES_IN", "e5"), ("e3", "SEEN_AT", "e5"),
        ("e0", "OCCURRED_AT", "e5"),
    }
    yield "negation_and_shared_location", (
        "Asha Verma did not contact Rohan Sen.\n"
        "Asha Verma resides in Mumbai.\nRohan Sen resides in Mumbai.\n"
        "Sharing a city does not establish contact between them.\n"
    ), [("Person", "Asha Verma"), ("Person", "Rohan Sen"), ("Location", "Mumbai")], {
        ("e0", "RESIDES_IN", "e2"), ("e1", "RESIDES_IN", "e2"),
    }
    people = ["Asha Verma", "Rohan Sen", "Mira Das", "Dev Rao", "Neha Jain", "Kabir Shah",
              "Leela Nair", "Nitin Bose", "Priya Roy", "Vivek Sethi", "Tara Patel", "Aman Das"]
    dense = "FIR/2026/9002\n" + "".join(
        f"{name} witnessed FIR/2026/9002.\n{name} resides in Mumbai.\n" for name in people
    )
    identities = [("Case", "FIR/2026/9002"), ("Location", "Mumbai")]
    identities.extend(("Person", name) for name in people)
    expected = {(f"e{i+2}", predicate, target) for i in range(len(people))
                for predicate, target in [("WITNESS_IN", "e0"), ("RESIDES_IN", "e1")]}
    yield "dense_rows", dense, identities, expected


async def run(args):
    settings = replace(Settings.from_env(), extraction_provider="ollama")
    outcomes = []
    for name, text, identities, expected in samples():
        if args.sample and name not in args.sample:
            continue
        catalog = [Entity(ref=f"e{i}", kind=kind, name=name, identifier=None,
                          attributes=[], evidence=name) for i, (kind, name) in enumerate(identities)]
        for repeat in range(args.runs):
            calls = []

            async def record(response):
                await response.aread()
                body = response.json()
                calls.append({key: body.get(key) for key in (
                    "prompt_eval_count", "eval_count", "total_duration", "done_reason",
                )})

            batches = list(relevant_batches(text, catalog, settings.ollama_max_tokens))
            found, excluded = set(), 0
            started = time.monotonic()
            error = None
            async with httpx.AsyncClient(event_hooks={"response": [record]}) as client:
                try:
                    for passage, entities in batches:
                        result = await extract_chunk(passage, "fir", settings, client, catalog=entities)
                        validate_extraction(result, text)
                        found.update((r.subject, r.predicate, r.object) for r in result.relationships)
                        excluded += len(result.excluded_relationships)
                except Exception as exc:
                    error = str(exc)
            result = dict(sample=name, run=repeat + 1, model=settings.ollama_model,
                          budget=settings.ollama_max_tokens, seconds=round(time.monotonic()-started, 2),
                          batches=len(batches), calls=calls, correct=len(found & expected),
                          expected=len(expected), missing=sorted(expected-found),
                          extra=sorted(found-expected), excluded=excluded, error=error)
            outcomes.append(result)
            print(json.dumps(result), flush=True)
    return all(not r["missing"] and not r["extra"] and not r["error"] for r in outcomes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--sample", action="append", choices=[s[0] for s in samples()])
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    raise SystemExit(0 if asyncio.run(run(args)) else 1)


if __name__ == "__main__":
    main()
