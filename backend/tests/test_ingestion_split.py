"""Chunk-boundary tests for the semantic splitter.

A fake embedder keeps these deterministic and offline — no model download, no
Qdrant, no graph singleton.
"""
from storage.ingestion import IngestionPipeline


class FakeEmbedder:
    """Maps each sentence to a unit vector chosen by a marker in its text.

    Sentences sharing a marker are identical (cosine similarity 1.0); different
    markers are orthogonal (0.0), so breaks land exactly where markers change.
    """
    def embed_documents(self, sentences):
        vectors = []
        for s in sentences:
            if "PUMP" in s:
                vectors.append([1.0, 0.0, 0.0])
            elif "VALVE" in s:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def test_breaks_chunk_when_topic_changes():
    pipeline = IngestionPipeline()
    text = "The PUMP is rated. The PUMP runs hot. The VALVE is shut. The VALVE leaks."
    chunks = pipeline._semantic_split(text, embedder=FakeEmbedder())

    assert len(chunks) == 2
    assert "PUMP" in chunks[0] and "VALVE" not in chunks[0]
    assert "VALVE" in chunks[1] and "PUMP" not in chunks[1]


def test_keeps_one_chunk_when_topic_is_uniform():
    pipeline = IngestionPipeline()
    text = "The PUMP is rated. The PUMP runs hot. The PUMP was serviced."
    chunks = pipeline._semantic_split(text, embedder=FakeEmbedder())
    assert len(chunks) == 1


def test_single_sentence_returns_itself():
    pipeline = IngestionPipeline()
    assert pipeline._semantic_split("Only one sentence here", embedder=FakeEmbedder()) == [
        "Only one sentence here"
    ]


def test_no_sentence_is_dropped():
    pipeline = IngestionPipeline()
    text = "The PUMP is rated. The VALVE is shut. The PUMP runs hot."
    chunks = pipeline._semantic_split(text, embedder=FakeEmbedder())
    joined = " ".join(chunks)
    for sentence in ["The PUMP is rated.", "The VALVE is shut.", "The PUMP runs hot."]:
        assert sentence in joined


def test_fixed_size_fallback_covers_whole_document():
    pipeline = IngestionPipeline()
    text = "abcdefghij" * 200  # 2000 chars
    chunks = pipeline._fixed_size_split(text, chunk_size=512, overlap=50)
    assert len(chunks) > 1
    assert chunks[0].startswith("abcdefghij")
    # Overlapping windows must still reach the end of the document.
    assert text[-10:] in chunks[-1]
