---
name: zotero-import-batch-formatting
description: Prepare valid text batches for the KNI Zotero Importer at $ZOTERO_IMPORT_REPO. Use when converting PMIDs, citations, URLs, paper lists, notes, or mixed references into this repo's structured input without performing live Zotero writes. Use zotero-reference-library-curation for an entire source library, zotero-import-live-runbook for live operations, and zotero-import-safe-maintenance for code changes.
---

# Zotero Import Batch Formatting

Resolve the active importer checkout before using repository commands:

```sh
export ZOTERO_IMPORT_REPO="$(git rev-parse --show-toplevel)"
test -f "$ZOTERO_IMPORT_REPO/run_kni_zotero_importer.py" || exit 1
```


## Overview

Use this skill to prepare importer-ready text blocks for `$ZOTERO_IMPORT_REPO`. It answers: **How should these references be represented as importer input?** It does not operate Zotero, curate an entire library architecture, or change importer code.

## Scope Check

Before acting, confirm the user wants input for this repo's KNI Zotero Importer or has named `$ZOTERO_IMPORT_REPO`. If not, stop using this skill.

## Formatting Workflow

1. Read `references/input-format.md`.
2. Require a destination collection for every entry. If collection names are absent or ambiguous, ask a targeted clarification question before producing or running importer input.
3. Decide with the user whether each article belongs in an existing collection or warrants a novel collection.
4. For novel collections, treat `Create Missing Collections` / `--create-missing-collections` as an explicit confirmed choice, not a default.
5. Prefer full block format for mixed or complex entries.
6. Use compact pipe format only for simple PMID-centric batches when readability remains high.
7. Preserve user-provided tags and notes. Split tags with semicolons.
8. For article imports, include a semi-detailed paper summary in `Note`, capped at 500 words.
9. For non-PMID items, include `Type`, `Title`, and usually `URL`.
10. For a project-level library, distinguish the primary collection from optional thematic hubs. Default to one primary collection plus at most one secondary hub per reference unless the user requests broader overlap.
11. For membership-only updates to existing items, omit `Note` and `Tags`; use PMID first, DOI second, and exact title only when a stable identifier is unavailable.
12. Do not invent PMIDs, DOIs, URLs, collection names, or tags.

## Output

Return only the batch text unless the user asks for explanation. If fields are missing, provide a short validation note before the batch.

## Optional Validation

If a file is created for the batch, validate with:

```bash
python3 run_kni_zotero_importer.py --stdin-file <input-file> --dry-run
```
