from src.collection_map import CollectionResolver
from src.parser import parse_entries


def test_parse_entries_reads_multiple_blocks() -> None:
    text = """
Collection: 01 KNI - Clinical & Translational Psychiatry
PMID: 29477251
Tags: seminal; clinical-core
Note: Network meta-analysis comparing antidepressants.

Collection: PMC (recent, interesting)
Type: blog post
Title: Example implementation note
URL: https://example.org/note
Tags: commentary; implementation
Note: Example note.
"""
    entries = parse_entries(text)
    assert len(entries) == 2
    assert entries[0].pmid == "29477251"
    assert entries[0].tags == ["seminal", "clinical-core"]
    assert entries[1].resolved_item_type() == "blogPost"
    assert entries[1].url == "https://example.org/note"


def test_collection_resolver_accepts_existing_names_and_aliases() -> None:
    resolver = CollectionResolver(
        {
            "00 KNI- Foundational Texts & Reviews": "AAA11111",
            "09 KNI - Health Economics, Reimbursement & Integrated Care Finance": "BBB22222",
            "PMC (recent, interesting)": "CCC33333",
        }
    )
    resolved = resolver.resolve("00 KNI - Foundational Texts & Major Reviews")
    assert resolved.resolved_name == "00 KNI- Foundational Texts & Reviews"
    assert resolved.key == "AAA11111"

    direct = resolver.resolve("PMC (recent, interesting)")
    assert direct.key == "CCC33333"


def test_parse_compact_pipe_delimited_entry() -> None:
    text = (
        "1) 00 KNI - Foundational Texts & Major Reviews | PMID 8632988 | "
        "tags seminal; biomarker-neuroimaging | "
        "note Early structural MRI anchor paper linking recurrent MDD with hippocampal atrophy."
    )
    entry = parse_entries(text)[0]
    assert entry.collection_name == "00 KNI - Foundational Texts & Major Reviews"
    assert entry.pmid == "8632988"
    assert entry.tags == ["seminal", "biomarker-neuroimaging"]
    assert entry.note.startswith("Early structural MRI anchor paper")


def test_parse_varied_labeled_input() -> None:
    text = """
- COLLECTION = 09 KNI - Health Economics, Reimbursement & Integrated Care Finance
PubMed ID - 25121991
Article Title: Cost-effectiveness of collaborative care for depression in UK primary care
Keywords: economics; collaborative-care
Summary: First line of note
second line of note
"""
    entry = parse_entries(text)[0]
    assert entry.collection_name == "09 KNI - Health Economics, Reimbursement & Integrated Care Finance"
    assert entry.pmid == "25121991"
    assert entry.title == "Cost-effectiveness of collaborative care for depression in UK primary care"
    assert entry.tags == ["economics", "collaborative-care"]
    assert entry.note == "First line of note\nsecond line of note"


def test_parse_nullish_pmid_as_missing() -> None:
    text = """
Collection: PMC (recent, interesting)
PMID: n/a
Type: blog post
Title: Example implementation note
URL: https://example.org/note
"""
    entry = parse_entries(text)[0]
    assert entry.pmid == ""
    assert entry.resolved_item_type() == "blogPost"
