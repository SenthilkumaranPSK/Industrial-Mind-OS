import logging
import re
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.schema import Document
import uuid

logger = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(self):
        # Fallback parser
        self.default_parser = SimpleNodeParser.from_defaults(chunk_size=512, chunk_overlap=50)

    def _semantic_split(self, text: str, threshold: float = 0.70) -> list[str]:
        """
        Splits text into semantically coherent chunks by identifying 
        topical transitions via embedding distance (cosine similarity).
        """
        from core.embeddings import LocalEmbedder
        import numpy as np
        
        # 1. Split into base sentences/segments
        # Improved regex for standard sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < 2:
            return [text]

        embedder = LocalEmbedder.get_embedder()
        embeddings = np.array(embedder.embed_documents(sentences))
        
        chunks = []
        current_chunk = [sentences[0]]
        
        for i in range(len(sentences) - 1):
            # Calculate cosine similarity between consecutive sentences
            # cos_sim = (A . B) / (||A|| * ||B||)
            sim = np.dot(embeddings[i], embeddings[i+1]) / (np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1]))
            
            if sim < threshold:
                # Semantic break detected!
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i+1]]
            else:
                current_chunk.append(sentences[i+1])
                
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
            semantic_chunks = self._semantic_split(content)
            logger.info(f"Successfully split '{filename}' into {len(semantic_chunks)} semantic chunks.")
            
            nodes = []
            for i, chunk_text in enumerate(semantic_chunks):
                nodes.append({
                    "id": str(uuid.uuid4()),
                    "text": chunk_text,
                    "metadata": {"file_name": filename, "chunk_index": i}
                })
            return nodes
        except Exception as e:
            logger.error(f"Semantic splitting failed for {filename}: {e}. Falling back to fixed-size parsing.")
            doc = Document(text=content, id_=str(uuid.uuid4()), metadata={"file_name": filename})
            nodes = self.default_parser.get_nodes_from_documents([doc])
            return [{"id": n.node_id, "text": n.text, "metadata": n.metadata} for n in nodes]

    def populate_graph(self, filename: str, chunks: list[dict]):
        """Builds graph edges from extracted keywords per chunk. Called after embedding completes."""
        from storage.graph_db import graph_db
        edge_count = 0
        for chunk in chunks[:100]:  # process first 100 chunks to keep startup fast
            kws = self._extract_keywords(chunk.get("text", ""))
            for i in range(len(kws) - 1):
                graph_db.add_relationship(kws[i], "co-occurs-with", kws[i + 1],
                                          metadata={"source": filename})
                edge_count += 1
        logger.info(f"Populated graph with {edge_count} edges from '{filename}' across {len(chunks)} chunks.")

ingestion_pipeline = IngestionPipeline()
