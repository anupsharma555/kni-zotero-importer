# KNI Zotero Importer

KNI Zotero Importer is a local Python tool for deterministically creating or updating Zotero items from pasted structured text. It provides a small desktop GUI, terminal input mode, and file-based batch input. The importer writes to Zotero through the Zotero Web API, enriches PMID-backed records from PubMed when available, places items into the correct Zotero collections, applies tags, and appends child notes without creating duplicates.

The project is intended for structured reference intake where the destination collection matters and the import path should remain auditable. It supports journal articles, blog posts, webpages, books, reports, conference papers, preprints, and generic documents.

## Core behavior

- parses pasted entries into structured records
- validates PMID, URL, and item type fields
- resolves collection names deterministically against the live Zotero collection list
- enriches PMID-backed entries from PubMed
- checks duplicates by PMID, DOI, ISBN, and normalized title
- updates existing Zotero items instead of creating duplicates
- adds missing collection membership, tags, and child notes
- supports journal articles, blog posts, webpages, books, reports, conference papers, preprints, and generic documents
- writes run summaries to `logs/import_report.csv` and `logs/errors.csv`

## Requirements

- Python 3.10+
- a Zotero library with API write access
- a Zotero private API key with read/write permissions for the target library
- optional PubMed / NCBI API access for PMID enrichment

Required environment variables:

- `ZOTERO_LIBRARY_ID`
- `ZOTERO_API_KEY`
- `ZOTERO_LIBRARY_TYPE=user`

Optional environment variables:

- `NCBI_API_KEY`
- `NCBI_TOOL`
- `NCBI_EMAIL`

Secrets should be supplied locally via `.env` or shell environment variables. They are not committed to the repository.

## Input format

Each entry is a block of `Field: value` lines separated by a blank line.

The importer also accepts a compact one-line format:

```text
00 KNI - Foundational Texts & Major Reviews | PMID 8632988 | tags seminal; biomarker-neuroimaging | note Early structural MRI anchor paper linking recurrent MDD with hippocampal atrophy.
```

Supported fields:

- `Collection` or `Collections`
- `PMID`
- `Title`
- `Tags`
- `Note`
- `Type`
- `URL`
- `DOI`
- `ISBN`

Example:

```text
Collection: 00 KNI - Foundational Texts & Major Reviews
PMID: 8632988
Tags: seminal; biomarker-neuroimaging
Note: Early structural MRI anchor paper linking recurrent MDD with hippocampal atrophy.

Collection: 08 KNI - Interventional Psychiatry, Neuromodulation & Novel Treatments
PMID: 29282469
Tags: frontier; ketamine; TRD
Note: Esketamine pivotal trial in treatment-resistant depression.

Collection: PMC (recent, interesting)
Type: blog post
Title: Example implementation note
URL: https://example.org/implementation-note
Tags: commentary; implementation
Note: Example of a non-PubMed source with URL-driven import.
```

Rules:

- `Collection` must resolve to an existing Zotero collection name, unless `Create Missing Collections` is enabled.
- The resolver does not guess semantically. It matches exact names first, then deterministic aliases and normalized variants.
- Use `Type` for non-PMID items when the type matters, such as `blog post`, `webpage`, or `book`.
- `Tags` are split on semicolons.

## Setup

Python 3.11+ is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Populate `.env` locally with your Zotero credentials. Do not commit it.

If you prefer shell exports instead of a project-local `.env`, use your shell startup file. Since this environment uses `zsh`, prefer `.zshrc` rather than `.bashrc`.

## Run

Launch the GUI:

```bash
python3 run_kni_zotero_importer.py
```

The GUI now runs imports on a background worker thread, so the window remains responsive while Zotero and PubMed requests are running.

Run in terminal paste mode:

```bash
python3 run_kni_zotero_importer.py --cli
```

Run from a text file:

```bash
python3 run_kni_zotero_importer.py --stdin-file sample_input.txt
```

Dry run without writing to Zotero:

```bash
python3 run_kni_zotero_importer.py --stdin-file sample_input.txt --dry-run
```

Allow the importer to create missing top-level collections:

```bash
python3 run_kni_zotero_importer.py --stdin-file sample_input.txt --create-missing-collections
```

Keyboard Maestro or AppleScript launcher:

```bash
/Users/anup/gitProjects/zotero-import/launch_kni_zotero_importer.sh
```

The launcher script starts the GUI detached from the terminal, so iTerm returns to the prompt immediately and does not remain occupied by the running app.

## Notes on collection resolution

The importer accepts any existing collection in the target Zotero library. It fetches the library collection list at runtime and resolves pasted names deterministically:

1. exact collection name match
2. explicit alias match
3. normalized whitespace and punctuation match if unique

If no existing collection matches, the importer stops that entry and records an error. It does not guess a destination collection.

If `Create Missing Collections` is enabled, the importer creates a missing top-level Zotero collection and then continues the import into that new collection.

## Caching and speed

To reduce repeated startup cost, the importer maintains local cache files under `.cache/`.

- Zotero collections are cached across launches for 24 hours
- the top-level Zotero dedupe index is cached across launches for 10 minutes
- in-memory caches remain active for the lifetime of the GUI session
- successful writes update the local dedupe cache immediately

This reduces repeated collection and item-index fetches on routine runs while keeping the cache reasonably fresh for duplicate prevention.

## Repository hygiene

The repository is intended to include only reusable source code, tests, documentation, and placeholder configuration.

Do not commit:

- `.env`
- `.cache/`
- `.venv/`
- generated logs
- local shell configuration or API keys

## Tests

```bash
pytest
```
