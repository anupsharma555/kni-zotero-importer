# Import Contract

Use this reference before changing importer behavior in `$ZOTERO_IMPORT_REPO`.

## Core Invariants

- Input blocks are separated by blank lines and stop at a line containing only `END`.
- Every parsed entry must include `Collection` and either `PMID` or `Title`.
- Compact one-line entries use pipe-delimited fields, with the first segment as the collection name unless it is an explicit `Collection` label.
- Tags split on semicolons, preserve first-seen casing, and dedupe case-insensitively.
- `PMID` values marked as nullish (`n/a`, `none`, `null`, etc.) become missing PMIDs.
- Item type fallback order is explicit type, PMID-backed `journalArticle`, URL-backed `webpage`, otherwise `document`.
- Unsupported item types should fail clearly.
- Collection resolution is deterministic: exact name, explicit alias, unique normalized name. Do not add semantic guessing.
- Duplicate priority is PMID, DOI, ISBN, normalized title.
- Existing items should be updated with missing collection membership, missing tags, merged Extra identifiers, and missing DOI only.
- Child notes should not be duplicated when semantically equivalent text already exists. Normalize Zotero HTML wrappers and entities before comparing notes.
- Dry runs must not create items, collections, or notes.
- Reports should preserve enough information to retry failed blocks; error CSV rows include `raw_block`.
- `ImportRuntime.refresh()` must clear disk-seeded collection and item caches before live API reads. `--refresh-cache` must return current Zotero item versions suitable for versioned updates.
- A version conflict is a re-read and re-plan boundary. Do not retry the same stale version payload.
- Collection cleanup must remove only the named membership, preserve all other memberships, and never delete the top-level item.
- When reorganizing collections, add the destination membership before removing a superseded membership and verify the final provider state.

## Files

- `src/parser.py`: text-to-entry parsing, field aliases, compact format, nullish PMIDs.
- `src/models.py`: dataclasses and item type mapping.
- `src/collection_map.py`: deterministic collection aliases and normalized matching.
- `src/dedupe.py`: identifier extraction, title normalization, duplicate priority.
- `src/importer.py`: import orchestration, create/update payloads, note checks, report CSVs.
- `src/zotero_client.py`: Zotero API pagination, templates, writes, child notes, collections.
- `src/pubmed_client.py`: PubMed XML fetch and record extraction.
- `src/cache_store.py`: generated local cache read/write and age checks.
- `tests/`: local safety net; prefer fake clients over real API calls.

## Test Prompts

Add or update focused tests for:

- new input labels or compact syntax variants
- collection aliases and ambiguous normalized names
- duplicate matching by identifier and title
- update payloads that append without overwriting existing data
- note dedupe behavior
- error report raw block preservation
- dry-run behavior for missing collection creation
- live refresh after disk-cache seeding
- version-conflict recovery boundaries
- membership-only cleanup that preserves the item and unrelated collections
- note dedupe against Zotero HTML-wrapped content
