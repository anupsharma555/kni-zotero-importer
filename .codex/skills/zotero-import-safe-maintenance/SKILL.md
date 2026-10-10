---
name: zotero-import-safe-maintenance
description: Review or change KNI Zotero Importer code at $ZOTERO_IMPORT_REPO while preserving parser, dedupe, collection, cache, note, cleanup, reporting, and live-write contracts. Use for implementation and tests, not for formatting references or operating an otherwise working importer.
---

# Zotero Import Safe Maintenance

Resolve the active importer checkout before using repository commands:

```sh
export ZOTERO_IMPORT_REPO="$(git rev-parse --show-toplevel)"
test -f "$ZOTERO_IMPORT_REPO/run_kni_zotero_importer.py" || exit 1
```


## Overview

Use this skill for code and test iterations inside `$ZOTERO_IMPORT_REPO`. It answers: **How do we safely change the importer itself?** The repo writes to a real Zotero library, so preserve deterministic parsing, duplicate prevention, collection resolution, cache freshness, note behavior, membership cleanup, and dry-run safety.

## Scope Check

Before acting, confirm the current workspace is `$ZOTERO_IMPORT_REPO` or the user explicitly named that path. If not, stop using this skill.

## Maintenance Workflow

1. Inspect the current local state first:
   - `git status --short`
   - relevant files under `src/`, `tests/`, `README.md`, `run_kni_zotero_importer.py`, and `launch_kni_zotero_importer.sh`
2. Read `references/import-contract.md` before changing behavior in `src/parser.py`, `src/models.py`, `src/importer.py`, `src/dedupe.py`, `src/collection_map.py`, `src/zotero_client.py`, `src/pubmed_client.py`, or `src/cache_store.py`.
3. Keep diffs minimal and preserve the repo's current module boundaries:
   - parsing in `src/parser.py`
   - item type models in `src/models.py`
   - orchestration and report writing in `src/importer.py`
   - duplicate matching in `src/dedupe.py`
   - collection matching in `src/collection_map.py`
   - network clients in `src/zotero_client.py` and `src/pubmed_client.py`
4. Prefer tests with fake clients/runtimes over live API calls.
5. When changing refresh behavior, prove disk-seeded in-memory caches are invalidated before live reads and that versioned writes use current item versions.
6. When changing note dedupe, normalize Zotero HTML wrappers before comparing semantic note text.
7. Run `python3 -m pytest` after code changes.
8. For runtime behavior that could write to Zotero, use `--dry-run` unless the user explicitly asks for live writes.

## Validation

Use this local validation ladder:

- `python3 -m pytest` for the current suite.
- Add focused unit tests when changing parser aliases, item type mapping, duplicate priority, HTML-normalized note dedupe, collection aliases, cache seeding or invalidation, version conflicts, membership cleanup, CSV columns, or error recovery.
- Do not rely on `.env`, `.cache/`, or `logs/` for tests.

## Safety Rules

- Never print or commit `.env`.
- Do not read or display secrets from `.env` unless the user explicitly asks for secret-management help; even then, redact values.
- Treat `.cache/` and `logs/` as generated local state.
- Do not alter existing user changes unless the task requires working with them.
- Do not create live Zotero items, collections, or notes without explicit user approval.
