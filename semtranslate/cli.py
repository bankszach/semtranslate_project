from __future__ import annotations
import os, sys, json, argparse, datetime, io, glob as globmod
from typing import Dict, Any, List, Tuple
from .io import read_jsonl
from .translate import retryable_call
from .prompt import build_policy

def _context_window(records: List[Dict[str, Any]], i: int) -> Tuple[str|None, str|None]:
    before = records[i-1]["he"]["pointed"] if i-1 >=0 and "he" in records[i-1] else None
    after = records[i+1]["he"]["pointed"] if i+1 < len(records) and "he" in records[i+1] else None
    return before, after

def translate_file(in_path: str, out_path: str, model: str, temperature: float, context: int,
                   policy_overrides: Dict[str, Any], workers: int, force: bool, store: bool,
                   merge: bool=False) -> None:
    recs = list(read_jsonl(in_path))
    existing = {}
    if not force and os.path.exists(out_path):
        for line in read_jsonl(out_path):
            existing[line["id"]] = line

    policy = build_policy(policy_overrides)
    now = datetime.datetime.utcnow().isoformat() + "Z"

    from concurrent.futures import ThreadPoolExecutor
    results = [None]*len(recs)

    def work(i: int):
        r = recs[i]
        if r["id"] in existing and not force:
            results[i] = existing[r["id"]]
            return
        before, after = (None, None)
        if context > 0:
            before, after = _context_window(recs, i)
        try:
            obj = retryable_call(r, policy, model, temperature, before, after, None, store) or {}
        except Exception:
            obj = {}
        if merge:
            out_obj = dict(r)
            out_obj.update({
                "translation": obj.get("translation", ""),
                "alts": obj.get("alts") or [],
                "notes": obj.get("notes") or [],
                "model": model,
                "created_at": now
            })
        else:
            out_obj = {
                "id": r["id"], "ref": r.get("ref"),
                "translation": obj.get("translation", ""),
                "alts": obj.get("alts") or [],
                "notes": obj.get("notes") or [],
                "model": model, "created_at": now
            }
        results[i] = out_obj

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for i in range(len(recs)):
            ex.submit(work, i)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(results)} lines → {out_path}")

def translate_folder(in_dir: str, out_dir: str, glob: str|None=None, glob_pat: str|None=None, merge: bool=False, **kwargs):
    pattern = glob or glob_pat or "*.jsonl"
    paths = sorted(globmod.glob(os.path.join(in_dir, pattern)))
    for p in paths:
        base = os.path.basename(p)
        out = os.path.join(out_dir, base)
        translate_file(p, out, merge=merge, **kwargs)

def main():
    ap = argparse.ArgumentParser(description="Semantic translation over JSONL verse objects")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("translate")
    t.add_argument("--in", dest="in_path", required=True)
    t.add_argument("--out", dest="out_path", required=True)
    t.add_argument("--model", default="gpt-4o-mini")
    t.add_argument("--temperature", type=float, default=0.2)
    t.add_argument("--context", type=int, default=1)
    t.add_argument("--workers", type=int, default=4)
    t.add_argument("--force", action="store_true")
    t.add_argument("--store", action="store_true")
    t.add_argument("--divine-name", dest="divine_name", default=None)
    t.add_argument("--register", dest="register", default=None)
    t.add_argument("--max-alts", dest="max_alternatives", type=int, default=None)

    tf = sub.add_parser("translate-folder")
    tf.add_argument("--in_dir", required=True)
    tf.add_argument("--out_dir", required=True)
    tf.add_argument("--glob", default="*.jsonl")
    tf.add_argument("--model", default="gpt-4o-mini")
    tf.add_argument("--temperature", type=float, default=0.2)
    tf.add_argument("--context", type=int, default=1)
    tf.add_argument("--workers", type=int, default=4)
    tf.add_argument("--force", action="store_true")
    tf.add_argument("--store", action="store_true")
    tf.add_argument("--merge", action="store_true", help="Write merged objects (original + translation) to output")
    tf.add_argument("--divine-name", dest="divine_name", default=None)
    tf.add_argument("--register", dest="register", default=None)
    tf.add_argument("--max-alts", dest="max_alternatives", type=int, default=None)

    args = vars(ap.parse_args())
    cmd = args.pop("cmd")
    policy_overrides = {k: v for k, v in list(args.items()) if k in {"divine_name","register","max_alternatives"} and v is not None}
    # Remove policy-related args (including None values) from passthrough kwargs
    for k in ["divine_name", "register", "max_alternatives"]:
        args.pop(k, None)

    if cmd == "translate":
        translate_file(policy_overrides=policy_overrides, **args)
    else:
        translate_folder(policy_overrides=policy_overrides, **args)

if __name__ == "__main__":
    main()
