from __future__ import annotations
import json, textwrap, yaml
from typing import Dict, Any

DEFAULT_SYSTEM_PROMPT = """
You are a scholarly translator producing a **semantic** English rendering of ancient text.
Your top priority is **meaning preservation and discourse function**. Do NOT paraphrase creatively.
Avoid smoothing metaphors or wordplay; keep parallelism and repeated structures visible.
Return only the structured JSON defined by the schema; no commentary.

Rules:
- Translate for **meaning over form**. Prefer clarity over archaism unless meaning would be lost.
- Preserve rhetorical devices (anaphora like “How long…”, inclusios, parallel cola) as line breaks when present.
- Do not add interpretive theology or modern idiom.
- Alternatives: If there are up to N materially different viable renderings (see `policy.max_alternatives`), include them concisely in `alts`.
- Editorial policy: respect `policy` (divine name handling, register, max_alternatives).
- Divine names must be source-driven:
  • If יהוה occurs, render according to policy (e.g., "YHWH" | "LORD" | "Adonai").
  • If only אֱלֹהִים occurs (and not יהוה), render as "God" (or "Elohim" only if explicitly instructed), never "YHWH".
  • If יהוה אֱלֹהִים occurs, render as "YHWH God" (or per policy mapping).
- No prefaces, no explanations — structured JSON only.
"""

def build_policy(meta: Dict[str, Any]) -> Dict[str, Any]:
    p = {
        "divine_name": meta.get("divine_name", "YHWH"),
        "register": meta.get("register", "neutral"),
        "footnotes": bool(meta.get("footnotes", False)),
        "max_alternatives": int(meta.get("max_alternatives", 2)),
    }
    return p

def response_schema() -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "semantic_translation",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "translation": {"type": "string"},
                    "alts": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                    "notes": {"type": "array", "items": {"type": "string"}, "maxItems": 3}
                },
                "required": ["translation"]
            },
            "strict": True
        }
    }

def build_user_input(rec: Dict[str, Any], policy: Dict[str, Any], context: Dict[str, str]|None=None) -> str:
    he = rec.get("he", {})
    src_unpointed = he.get("unpointed") or ""
    src = he.get("pointed") or he.get("accents") or src_unpointed or ""
    ref = rec.get("ref", rec.get("id", ""))
    parasha = rec.get("parasha")
    ctx_before = context.get("before") if context else None
    ctx_after = context.get("after") if context else None

    # Divine-name lexical tags derived from source Hebrew
    unp = src_unpointed or ""
    has_yhwh = "יהוה" in unp
    has_elohim = "אלהים" in unp
    has_yhwh_elohim = "יהוה אלהים" in unp or (
        has_yhwh and has_elohim and ("יהוה" in unp and "אלהים" in unp and unp.find("יהוה") < unp.find("אלהים"))
    )
    name_tags = {
        "yhwh": bool(has_yhwh),
        "elohim": bool(has_elohim),
        "yhwh_elohim": bool(has_yhwh_elohim),
    }

    parts = []
    parts.append(f"REF: {ref}")
    if parasha: parts.append(f"PARASHA: {parasha}")
    parts.append("SOURCE_HEBREW (pointed):")
    parts.append(src)
    parts.append("\nNAME_TAGS: " + json.dumps(name_tags, ensure_ascii=False))

    if ctx_before:
        parts.append("\nCONTEXT_BEFORE:")
        parts.append(ctx_before)
    if ctx_after:
        parts.append("\nCONTEXT_AFTER:")
        parts.append(ctx_after)

    parts.append("\nPOLICY: " + json.dumps(policy, ensure_ascii=False))

    return "\n".join(parts)
