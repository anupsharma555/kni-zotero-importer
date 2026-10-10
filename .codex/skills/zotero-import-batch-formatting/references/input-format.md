# Input Format

Use this reference to prepare text for `$ZOTERO_IMPORT_REPO`.

## Required Shape

Each entry is a block of `Field: value` lines separated by a blank line.

Required:

- `Collection` or `Collections`
- either `PMID` or `Title`

Optional:

- `Tags`
- `Note`
- `Type`
- `URL`
- `DOI`
- `ISBN`

Supported aliases include `Collections`, `Folder`, `Group`, `PubMed ID`, `Article Title`, `Keywords`, `Summary`, `Item Type`, `Source Type`, and `Link`.

## Full Block Example

```text
Collection: 00 KNI - Foundational Texts & Major Reviews
PMID: 8632988
Tags: seminal; biomarker-neuroimaging
Note: Early structural MRI anchor paper linking recurrent MDD with hippocampal atrophy.

Collection: PMC (recent, interesting)
Type: blog post
Title: Example implementation note
URL: https://example.org/implementation-note
Tags: commentary; implementation
Note: Example of a non-PubMed source with URL-driven import.
```

## Compact Example

```text
00 KNI - Foundational Texts & Major Reviews | PMID 8632988 | tags seminal; biomarker-neuroimaging | note Early structural MRI anchor paper linking recurrent MDD with hippocampal atrophy.
```

## Primary Collection Plus Hub

Use semicolon-separated collection names when an initial import should place one item into its primary project collection and one thematic hub:

```text
Collections: FHD 2026; BHEB 19 - LLM Product Benchmarking, Red Teaming & Monitoring
PMID: 12345678
Note: Semi-detailed source summary capped at 500 words.
```

Default to one primary collection plus at most one secondary hub. Do not distribute a reference library across many narrowly related collections merely because each is defensible.

## Membership-Only Update

When an existing Zotero item only needs another collection membership, omit notes and tags so the operation cannot duplicate child notes or add unrelated metadata:

```text
Collection: CHAI 01 - AI Governance
PMID: 12345678
```

For a non-PubMed item, include its exact existing title plus DOI or URL:

```text
Collection: BHEB 19 - LLM Product Benchmarking, Red Teaming & Monitoring
Type: preprint
Title: Example evaluation benchmark
URL: https://example.org/preprint
```

## Rules

- Use exact known collection names when possible.
- Do not guess collections semantically; ask if destination is unclear.
- Treat the project or manuscript collection as the source-of-truth collection. Use a small number of centralized secondary hubs for cross-functional discovery.
- Use semicolons between tags.
- Use `Type` for non-PMID items when the type matters.
- Supported item type labels include `journal article`, `article`, `blog post`, `webpage`, `web page`, `book`, `report`, `conference paper`, `preprint`, and `document`.
- Use `PMID: n/a` only when a source has no PMID and a title is present.
- Do not include an `END` line unless preparing text for CLI paste mode.
