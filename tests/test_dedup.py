import json

from conftest import ROOT
from pipeline import deduplicate_texts


def test_exact_duplicates_collapse():
    texts = ["The cat sat on the mat.", "The cat sat on the mat.", "Quantum physics is hard."]
    assert deduplicate_texts(texts) == ["The cat sat on the mat.", "Quantum physics is hard."]


def test_near_duplicates_collapse():
    texts = [
        "The quick brown fox jumps over the lazy dog today.",
        "The quick brown fox jumps over the lazy dog tomorrow.",
    ]
    assert len(deduplicate_texts(texts)) == 1


def test_distinct_documents_are_kept():
    texts = [
        "Medical diagnosis identifies a disease from symptoms and tests.",
        "Food technology innovates production and preservation.",
        "Orbital mechanics governs how satellites keep their altitude.",
    ]
    assert len(deduplicate_texts(texts)) == 3


def test_first_occurrence_wins():
    assert deduplicate_texts(["First version.", "First version."]) == ["First version."]


def test_empty_input():
    assert deduplicate_texts([]) == []


def test_topic_dataset_removal_count():
    # Measured on the course-provided dataset; the naive exact-string baseline removes about 20.
    with open(ROOT / "data" / "topic_dataset.json") as f:
        texts = [item["text"] for item in json.load(f)["data"]]
    kept = deduplicate_texts(texts)
    assert (len(texts), len(kept)) == (219, 188)
