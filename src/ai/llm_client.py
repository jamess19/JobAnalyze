"""
Single seam for calling the LLM provider. Swapping providers later
(Claude, another OpenAI-compatible provider, a local model) means editing
this file only — nothing else in src/ai/ imports a provider SDK or REST
shape directly.

Currently backed by Groq's free-tier, OpenAI-compatible chat completions API.
"""

import json
import os
import re
import time

import requests

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MAX_RATE_LIMIT_RETRIES = 2
_DEFAULT_RETRY_SECONDS = 10.0
_RETRY_AFTER_IN_MESSAGE = re.compile(r"try again in ([\d.]+)s")


class LlmClientError(Exception):
    pass


def call_llm(prompt: str, want_json: bool = False, timeout: int = 30) -> str:
    """Call the LLM and return the assistant's raw text response.

    Retries with backoff on HTTP 429 (rate limit) — Groq's free tier has a
    tight tokens-per-minute budget that a single eval run can exhaust; a
    dumb immediate failure there isn't a real defect in the feature.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LlmClientError("GROQ_API_KEY not set in environment")

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    if want_json:
        # Groq (OpenAI-compatible) JSON mode — the prompt must itself ask for
        # JSON, which schema_context.py's prompts already do.
        payload["response_format"] = {"type": "json_object"}

    for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
        try:
            resp = requests.post(
                _GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as e:
            raise LlmClientError(f"Groq request failed: {e}") from e

        if resp.status_code == 429 and attempt < _MAX_RATE_LIMIT_RETRIES:
            time.sleep(_seconds_to_wait(resp))
            continue

        if resp.status_code != 200:
            raise LlmClientError(f"Groq API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LlmClientError(f"Unexpected Groq response shape: {str(data)[:500]}") from e

    raise LlmClientError("unreachable")  # loop always returns or raises above


def _seconds_to_wait(resp: "requests.Response") -> float:
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    match = _RETRY_AFTER_IN_MESSAGE.search(resp.text or "")
    if match:
        return float(match.group(1)) + 0.5  # small buffer past the server's estimate
    return _DEFAULT_RETRY_SECONDS


def parse_json_response(text: str) -> dict:
    """Some providers wrap JSON output in ```json fences — strip them defensively."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError as e:
        raise LlmClientError(f"Could not parse JSON from LLM response: {text[:300]}") from e
