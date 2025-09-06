placeholder

## Merged output (original + translation)
To write outputs that include the original JSONL fields **and** the translation in a single object, add `--merge`
and write to a separate directory, e.g.:

```bash
python -m semtranslate.cli translate-folder   --in_dir ./in-jsonl   --out_dir ./editions/eng.sem.v1_merged   --glob "*.jsonl"   --model gpt-4.1   --context 1   --workers 4   --merge
```

Example merged line:
```json
{
  "id": "Gen.1.1",
  "ref": "Gen 1:1",
  "he": { "accents": "…", "pointed": "…", "unpointed": "…" },
  "tokens": ["…"],
  "parasha": null,
  "translation": "In the beginning…",
  "alts": ["At the start…"],
  "notes": [],
  "model": "gpt-4.1",
  "created_at": "2025-09-06T12:34:56Z"
}
```
