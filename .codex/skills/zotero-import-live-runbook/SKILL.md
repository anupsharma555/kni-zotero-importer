---
name: zotero-import-live-runbook
description: Safely operate the KNI Zotero Importer at $ZOTERO_IMPORT_REPO. Use for GUI or CLI runs, batch dry-runs, authorized live imports, collection-membership cleanup, report inspection, cache refreshes, and provider readback. Use zotero-import-batch-formatting to prepare input, zotero-reference-library-curation for a complete library workflow, and zotero-import-safe-maintenance for code changes.
---

# Zotero Import Live Runbook

Resolve the active importer checkout before using repository commands:

```sh
export ZOTERO_IMPORT_REPO="$(git rev-parse --show-toplevel)"
test -f "$ZOTERO_IMPORT_REPO/run_kni_zotero_importer.py" || exit 1
```


## Overview

Use this skill for running or debugging this repo's local importer. It answers: **How do we safely execute and verify this Zotero operation?** Default to dry-run and log inspection before any operation that can write to Zotero.

## Scope Check

Before acting, confirm the current workspace is `$ZOTERO_IMPORT_REPO` or the user explicitly named that path. If not, stop using this skill.

## Operating Modes

Read `references/runbook.md` when performing a real run, interpreting logs, or debugging an import failure.

- GUI launch: use `python3 run_kni_zotero_importer.py` from the repo, or `launch_kni_zotero_importer.sh` when the user wants the detached local launcher.
- File dry-run: use `python3 run_kni_zotero_importer.py --stdin-file <path> --dry-run`.
- CLI paste mode: use `python3 run_kni_zotero_importer.py --cli --dry-run` unless live write is explicitly requested.
- Missing collections: only use `--create-missing-collections` after confirming the requested collection names.
- Membership cleanup: use `--cleanup-collection-report`, dry-run first, and confirm that only collection membership—not the item—is removed.

## Safety Rules

- Never print `.env` values.
- Never run a live import without explicit user confirmation for that batch.
- Use `--refresh-cache` before live duplicate checks or versioned membership updates.
- Add the new destination membership before removing an old one.
- On a version conflict, force a live refresh and rebuild the plan; do not retry a stale payload.
- Avoid showing generated logs wholesale; extract only relevant rows and redact secrets if any appear.
- Treat `.cache/` as local generated state that may be stale.
- If live Zotero or PubMed calls fail due to network or auth, report the root cause and the command used; do not retry write operations blindly.

## Validation

For operational changes or debugging, run `python3 -m pytest` when code changed. For user-provided batches, run a dry-run first and summarize processed count, errors, and retry blocks. After a live write, perform fresh provider readback and verify counts, identifiers, and intended collection memberships rather than relying only on the write receipt.
