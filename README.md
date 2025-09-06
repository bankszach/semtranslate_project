SemTranslate — JSONL-based semantic translation tooling

## Setup
- Python: 3.10+
- Create a virtual environment and install deps:
  
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

- Configure environment variables:
  - Option A — export in your shell:
    
    ```bash
    export OPENAI_API_KEY="your_key"
    ```
  - Option B — use a local `.env` file (ignored by Git):
    
    ```bash
    cp .env.example .env
    # edit .env to set OPENAI_API_KEY
    ```
    Note: `.env` is not auto-loaded by the app. To load it, either `export` the variables before running, use a tool like `direnv`, or run the command prefixed with `set -a; source .env; set +a`.

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

## Basic usage

Translate a single file:

```bash
python -m semtranslate.cli translate \
  --in ./in-jsonl/Genesis.jsonl \
  --out ./editions/eng.sem.v1/Genesis.jsonl \
  --model gpt-4o-mini \
  --context 1 \
  --workers 4
```

Translate a folder of JSONL files (example uses `--merge`):

```bash
python -m semtranslate.cli translate-folder \
  --in_dir ./in-jsonl \
  --out_dir ./editions/eng.sem.v1_merged \
  --glob "*.jsonl" \
  --model gpt-4o-mini \
  --context 1 \
  --workers 4 \
  --merge
```

## Notes
- Secrets safety: `.env`, `.venv/` and other local files are ignored by Git via `.gitignore`.
- If you ever accidentally commit secrets, rotate them and force-push after purging history.
- Local safety net: a pre-commit hook blocks committing `.env` and obvious secrets. If you cloned fresh, enable hooks with:

  ```bash
  git config core.hooksPath .githooks
  ```

  Bypass (not recommended): `ALLOW_SECRET_COMMIT=1 git commit -m "..."`
