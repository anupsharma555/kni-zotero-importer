# Reference Library Curation Workflow

Use this workflow for a multi-reference source such as a Google Doc reference-library tab, pasted bibliography, manuscript library, or structured paper list.

## 1. Ground the Source

1. Identify the exact document, tab, section, or attachment in scope.
2. Read only the requested source surface and record its current revision when available.
3. Extract one record per displayed source, preserving citation, DOI or URL, source annotation, and section context.
4. Report the source count before formatting. Do not modify the source unless separately authorized.

## 2. Confirm Collection Architecture

1. Ask for or infer only from explicit context a short primary collection name; confirm any novel name before creation.
2. Treat the primary collection as the complete project or manuscript library.
3. Propose a small number of centralized secondary hubs based on actual retrieval needs. Prefer roughly two to five coherent hubs over many one-off collection links.
4. Default to at most one secondary hub per reference. Use tags for additional cross-cutting concepts when tags were supplied or approved.
5. Preserve unrelated historical memberships unless broader cleanup is explicitly authorized.

## 3. Prepare Metadata

1. Use PMID-backed input when a DOI resolves to PubMed so the backend can populate journal metadata.
2. For sources without a PMID, provide the correct supported type, exact title, DOI when present, and canonical URL.
3. Preserve each source annotation as a semi-detailed child note capped at 500 words.
4. Record how many records are PMID-enriched and how many use typed fallback metadata. Do not describe fallback records as fully enriched when authors, venue, date, or volume remain unavailable.
5. Use `zotero-import-batch-formatting` for final block syntax.

## 4. Import the Primary Collection

1. Parse the complete batch locally and require zero formatting errors.
2. Run the repository tests when code changed.
3. Refresh live Zotero collections and items, then dry-run the complete batch with `--create-missing-collections` only when the confirmed primary collection is novel.
4. Summarize creates, updates, skips, errors, and the proposed collection creation.
5. After explicit authorization, run the same validated live batch.
6. From a genuinely fresh runtime, verify the primary collection exists, contains the expected unique item count, and every requested note is present after HTML normalization.

## 5. Add Centralized Secondary Hubs

1. Build a documented mapping from each reference to zero or one secondary hub.
2. Use membership-only importer blocks: omit notes and tags; use PMID, DOI, or exact title fallback only.
3. Dry-run all additions against a live refresh and require every entry to match an existing primary-collection item.
4. Apply authorized additions before removing any prior memberships.

## 6. Reconcile Prior Memberships

1. Snapshot current memberships for the primary-collection items.
2. Limit removals to the reviewed superseded collection memberships. Do not touch unrelated historical memberships.
3. Generate exact-key cleanup reports and dry-run them with `--cleanup-collection-report --refresh-cache`.
4. Confirm each result says collection membership would be removed and the item would not be deleted.
5. Apply authorized cleanup. If an item version conflicts, refresh live state and rebuild only the remaining cleanup plan.

## 7. Final Provider Readback

Verify from a fresh runtime:

- primary collection item count equals the source count
- every primary item resolves by PMID, DOI, or exact normalized title
- every item has exactly the approved secondary-hub count
- hub counts match the reviewed map
- no reviewed superseded memberships remain
- unrelated historical memberships are preserved
- no top-level item, child note, or attachment was deleted by membership cleanup

Report both completed proof and any metadata limitations. Do not rely only on importer receipts or disk-seeded caches.
