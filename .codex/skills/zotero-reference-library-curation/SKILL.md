---
name: zotero-reference-library-curation
description: Curate an entire source reference library into the KNI Zotero Importer at $ZOTERO_IMPORT_REPO. Use when Codex must read a bounded paper list or reference-library tab, create or select a primary project collection, enrich and import every reference, organize selected secondary thematic hubs, reconcile prior memberships, and verify the final live Zotero structure. Do not use for a single citation, input formatting alone, routine live operations, or importer code changes.
---

# Zotero Reference Library Curation

Resolve the active importer checkout before using repository commands:

```sh
export ZOTERO_IMPORT_REPO="$(git rev-parse --show-toplevel)"
test -f "$ZOTERO_IMPORT_REPO/run_kni_zotero_importer.py" || exit 1
```


## What This Skill Is

Use this skill for the complete lifecycle of turning a source bibliography into a coherent Zotero library. It answers: **How do we import, organize, and verify an entire reference library without scattering or losing references?**

The skill preserves one primary project or manuscript collection as the complete source of truth, then adds a small number of centralized thematic hubs for cross-functional discovery. It covers source inventory, metadata enrichment, backend import, collection architecture, membership cleanup, and provider readback.

## How It Differs

- `zotero-import-batch-formatting`: formats citations into importer text; no live curation.
- `zotero-import-live-runbook`: executes and verifies a defined Zotero operation.
- `zotero-import-safe-maintenance`: changes importer code and tests.
- This skill coordinates the end-to-end reference-library outcome using the formatting and live-operation workflows.

## Scope Check

Confirm the source is a bounded reference library, bibliography, document tab, or paper set intended for `$ZOTERO_IMPORT_REPO`. Do not edit the source document unless the user separately requests it.

Read `references/curation-workflow.md` before creating a collection, importing references, or reorganizing memberships.

## Required Outcome

- Every in-scope source is inventoried exactly once.
- Every reference remains in one confirmed primary project collection.
- Each reference has at most one planned secondary hub by default.
- Non-PubMed sources retain an explicit item type, exact title, DOI or URL, and a stated metadata proof boundary.
- Live writes occur only after a zero-error dry run and explicit authorization.
- Final provider readback proves counts, identifiers, notes, and collection memberships.

## Safety Boundaries

- Treat source retrieval and analysis as read-only unless the user explicitly authorizes source edits.
- Confirm abbreviated collection names with the user; do not infer a long document title as the collection name.
- Add destination memberships before removing old memberships.
- Use membership-only cleanup; never delete a top-level item when reorganizing collections.
- Preserve unrelated historical memberships unless the user authorizes broader cleanup.
- On any version conflict or ambiguous duplicate, force a live refresh and rebuild the remaining plan.
- Stop when fresh provider readback satisfies the agreed invariants; do not perform extra cleanup.
