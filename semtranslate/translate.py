from __future__ import annotations
import os, time, json
from typing import Dict, Any, Optional
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from .prompt import DEFAULT_SYSTEM_PROMPT, response_schema, build_user_input, build_policy

def _client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_model(rec: Dict[str, Any], policy: Dict[str, Any], model: str="gpt-4o-mini", temperature: float=0.2,
               context_before: Optional[str]=None, context_after: Optional[str]=None,
               extra_instructions: Optional[str]=None, store: bool=False) -> Dict[str, Any]:
    client = _client()

    system = DEFAULT_SYSTEM_PROMPT
    if extra_instructions:
        system = f"{system}\n\nAdditional instructions:\n{extra_instructions}"

    user_input = build_user_input(rec, policy, {"before": context_before, "after": context_after})

    # Use Chat Completions with JSON object response
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    data = json.loads(content)
    # Normalize to expected schema
    if not isinstance(data, dict):
        data = {"translation": str(data), "alts": [], "notes": []}
    if "translation" not in data:
        if isinstance(data.get("verse"), dict) and "text" in data["verse"]:
            data = {
                "translation": data["verse"].get("text", ""),
                "alts": data["verse"].get("alts", []) or [],
                "notes": data["verse"].get("notes", []) or [],
            }
        elif "text" in data:
            data = {
                "translation": data.get("text", ""),
                "alts": data.get("alts", []) or [],
                "notes": data.get("notes", []) or [],
            }
        else:
            data = {"translation": json.dumps(data, ensure_ascii=False), "alts": [], "notes": []}
    # Coerce translation to string if nested or JSON-encoded
    tr = data.get("translation")
    if isinstance(tr, dict):
        # Common shapes: {text: str, alts: [...] } or {translation: str}
        data["translation"] = tr.get("text") or tr.get("translation") or json.dumps(tr, ensure_ascii=False)
        # Merge alts/notes if present inside nested object
        if "alts" in tr and not data.get("alts"):
            data["alts"] = tr.get("alts") or []
        if "notes" in tr and not data.get("notes"):
            data["notes"] = tr.get("notes") or []
    elif isinstance(tr, str) and tr.strip().startswith("{"):
        try:
            tr_obj = json.loads(tr)
            inner = tr_obj
            if isinstance(tr_obj.get("verse"), dict):
                inner = tr_obj["verse"]
            data["translation"] = inner.get("text") or inner.get("translation") or json.dumps(inner, ensure_ascii=False)
            if "alts" in tr_obj and not data.get("alts"):
                data["alts"] = tr_obj.get("alts") or []
            if "notes" in tr_obj and not data.get("notes"):
                data["notes"] = tr_obj.get("notes") or []
        except Exception:
            pass
    # Ensure list fields exist
    data.setdefault("alts", [])
    data.setdefault("notes", [])
    return data

def retryable_call(*args, **kwargs) -> Dict[str, Any]:
    backoff = 1.0
    for attempt in range(8):
        try:
            return call_model(*args, **kwargs)
        except (RateLimitError, APITimeoutError):
            import time; time.sleep(backoff); backoff = min(backoff*2, 30)
        except APIError as e:
            if 500 <= getattr(e, 'status_code', 500) < 600:
                import time; time.sleep(backoff); backoff = min(backoff*2, 30)
            else:
                raise
    raise RuntimeError("Max retries exceeded")
