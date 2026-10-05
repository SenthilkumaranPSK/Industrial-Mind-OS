import logging
import re
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# Fallback parser settings, used only when semantic splitting fails.
FALLBACK_CHUNK_SIZE = 512
FALLBACK_CHUNK_OVERLAP = 50


class IngestionPipeline:
    def _fixed_size_split(self, text: str,
                          chunk_size: int = FALLBACK_CHUNK_SIZE,
                          overlap: int = FALLBACK_CHUNK_OVERLAP) -> list[str]:
        """Plain sliding-window splitter used when semantic splitting raises."""
        if not text:
            return []
        step = max(1, chunk_size - overlap)
        return [text[i:i + chunk_size] for i in range(0, len(text), step) if text[i:i + chunk_size].strip()]

    def _semantic_split(self, text: str, threshold: float = 0.70, embedder=None) -> list[str]:
        """
        Splits text into semantically coherent chunks by identifying
        topical transitions via embedding distance (cosine similarity).

        `embedder` is injectable so this can be tested without loading the model.
        """
        import numpy as np

        # 1. Split into base sentences/segments
        # Improved regex for standard sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < 2:
            return [text]

        if embedder is None:
            from core.embeddings import LocalEmbedder
            embedder = LocalEmbedder.get_embedder()
        embeddings = np.array(embedder.embed_documents(sentences))

        chunks = []
        current_chunk = [sentences[0]]

        for i in range(len(sentences) - 1):
            # Calculate cosine similarity between consecutive sentences
            # cos_sim = (A . B) / (||A|| * ||B||)
            denom = np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
            sim = float(np.dot(embeddings[i], embeddings[i + 1]) / denom) if denom else 0.0

            if sim < threshold:
                # Semantic break detected!
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i + 1]]
            else:
                current_chunk.append(sentences[i + 1])

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords (words >= 4 chars, no stopwords) from text."""
        stopwords = {
            "about","after","again","all","also","always","am","an","and","any","are","around",
            "as","at","be","because","been","before","being","between","both","but","by","can",
            "cannot","could","did","do","does","doing","down","during","each","either","enough",
            "especially","etc","even","ever","every","few","first","for","found","from","further",
            "get","give","given","go","going","good","got","group","had","has","have","having",
            "he","her","here","hers","herself","him","himself","his","how","however","i","if",
            "in","into","is","it","its","itself","just","keep","know","large","let","like",
            "likely","local","long","made","make","many","may","me","might","more","most","much",
            "must","my","myself","need","never","no","nor","not","now","of","off","often","on",
            "once","only","or","other","our","ours","ourselves","out","over","own","part","place",
            "point","put","right","same","see","seem","several","shall","she","should","since",
            "so","some","still","such","take","than","that","the","their","theirs","them",
            "themselves","then","there","these","they","thing","things","think","this","those",
            "though","three","through","to","too","under","until","up","upon","us","use","used",
            "using","very","want","was","way","we","well","went","were","what","when","where",
            "whether","which","while","who","whom","whose","why","will","with","within","without",
            "would","yes","yet","you","your","yours","yourself","yourselves"
        }
        words = re.findall(r'\b[A-Za-z][a-z]{3,}\b', text)
        seen = set()
        keywords = []
        for w in words:
            lw = w.lower()
            if lw not in stopwords and lw not in seen:
                seen.add(lw)
                keywords.append(w)
        return keywords[:20]  # cap per chunk

    def process_document(self, filename: str, content: str) -> list[dict]:
        """
        Chunks the document using semantic splitting and returns formatted nodes.
        """
        logger.info(f"Applying Semantic Splitting to document '{filename}'.")

        try:
            chunks = self._semantic_split(content)
            logger.info(f"Successfully split '{filename}' into {len(chunks)} semantic chunks.")
        except Exception as e:
            logger.error(f"Semantic splitting failed for {filename}: {e}. Falling back to fixed-size parsing.")
            chunks = self._fixed_size_split(content)

        return [
            {
                "id": str(uuid.uuid4()),
                "text": chunk_text,
                "metadata": {"file_name": filename, "chunk_index": i},
            }
            for i, chunk_text in enumerate(chunks)
        ]

    def populate_graph(self, filename: str, chunks: list[dict], owner_id: Optional[str] = None,
                       max_chunks: Optional[int] = None):
        """
        Builds graph edges from extracted keywords per chunk.

        Processes every chunk by default. Writes are batched into a single save —
        serializing the graph per edge made a full document prohibitively slow,
        which is why this used to be capped at the first 100 chunks.
        """
        from storage.graph_db import graph_db

        selected = chunks[:max_chunks] if max_chunks else chunks
        if max_chunks and len(chunks) > max_chunks:
            logger.warning(
                f"populate_graph: only indexing {max_chunks} of {len(chunks)} chunks from '{filename}'; "
                f"the remainder will be searchable by vector but absent from the graph."
            )

        edge_count = 0
        for chunk in selected:
            kws = self._extract_keywords(chunk.get("text", ""))
            for i in range(len(kws) - 1):
                graph_db.add_relationship(
                    kws[i], "co-occurs-with", kws[i + 1],
                    metadata={"source": filename, "owner_id": str(owner_id) if owner_id else None},
                    autosave=False,
                )
                edge_count += 1

        graph_db.save()
        logger.info(f"Populated graph with {edge_count} edges from '{filename}' across {len(selected)} chunks.")


ingestion_pipeline = IngestionPipeline()
