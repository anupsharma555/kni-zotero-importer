# Live Runbook

Use this reference for operational work in `$ZOTERO_IMPORT_REPO`.

## Environment

Required variables are loaded from shell environment or `.env` by `ImportRuntime.from_env()`:

- `ZOTERO_LIBRARY_ID`
- `ZOTERO_API_KEY`
- `ZOTERO_LIBRARY_TYPE=user`

Optional PubMed variables:

- `NCBI_API_KEY`
- `NCBI_TOOL`
- `NCBI_EMAIL`

Do not open or print `.env` to validate configuration. If validation is needed, run the importer in dry-run mode and use the resulting missing-variable or auth error without exposing secret values.

## Commands

Run from `$ZOTERO_IMPORT_REPO`.

```bash
python3 -m pytest
python3 run_kni_zotero_importer.py --stdin-file sample_input.txt --dry-run --refresh-cache
python3 run_kni_zotero_importer.py --cli --dry-run --refresh-cache
python3 run_kni_zotero_importer.py --list-collections --refresh-cache
python3 run_kni_zotero_importer.py
$ZOTERO_IMPORT_REPO/launch_kni_zotero_importer.sh
```

Only use live writes after explicit user approval:

```bash
python3 run_kni_zotero_importer.py --stdin-file <input-file> --refresh-cache
python3 run_kni_zotero_importer.py --stdin-file <input-file> --create-missing-collections --refresh-cache
```

For reviewed membership removals, use a cleanup report containing the exact item keys and target collection. Dry-run first, then remove only the `--dry-run` flag after approval:

```bash
python3 run_kni_zotero_importer.py \
  --cleanup-collection-report <cleanup-report.json> \
  --dry-run \
  --refresh-cache
```

Add a replacement or centralized hub membership before removing a superseded membership. A cleanup report changes collection membership only; it must not delete the Zotero item.

## Generated State

- `.cache/zotero_collections.json`: collection cache, up to 24 hours.
- `.cache/zotero_items.json`: top-level item cache, up to 10 minutes.
- `logs/import_report.csv`: all results from latest run.
- `logs/errors.csv`: failed rows from latest run.
- `logs/gui_launcher.log`: detached GUI launcher output.

Use logs for diagnosis, not as source code. Avoid committing generated files.

`--refresh-cache` must bypass these disk-seeded values and retrieve current Zotero collection and item versions. Use it before versioned updates and final provider verification.

## Debugging Failures

1. Identify whether the failure is parse, collection resolution, PubMed fetch, duplicate/update payload, Zotero write, or report writing.
2. For parse failures, preserve the retry block and fix the input format or parser tests.
3. For collection failures, refresh collections from the GUI or rerun after clearing stale cache only if needed.
4. For PubMed failures, verify whether a title fallback exists; PMID-only entries fail if PubMed metadata is unavailable.
5. For Zotero write failures, report the API message and avoid automatic retries that could create duplicate side effects.
6. If `--create-missing-collections` is involved, confirm each new top-level collection name with the user first.
7. For `Item has been modified since specified version`, stop, force a live refresh, rebuild the remaining plan, and retry only the still-needed operations.

## Completion Readback

After live writes, verify the observable outcome from a fresh runtime:

- intended primary collection still contains every expected item
- every added membership resolves to the expected item key
- superseded memberships are absent after cleanup
- unrelated historical memberships remain unless broader cleanup was authorized
- child notes or attachments remain present when the operation was membership-only
