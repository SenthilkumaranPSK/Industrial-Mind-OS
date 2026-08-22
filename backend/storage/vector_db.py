import logging
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

class VectorDBClient:
    def __init__(self, collection_name: str = "imos_collection"):
        # Use local disk path so vectors persist across backend restarts
        try:
            import os
            db_path = os.path.join(os.path.dirname(__file__), "..", "qdrant_data")
            os.makedirs(db_path, exist_ok=True)
            self.client = QdrantClient(path=db_path)  # Disk-persisted local storage
            self.collection_name = collection_name
            self._init_collection()
            logger.info("Connected to Vector Database (Mocked Qdrant in-memory)")
        except Exception as e:
            logger.error(f"Failed to connect to Vector DB: {e}")
            self.client = None

    def _init_collection(self, vector_size: int = 384):
        """Initializes the collection if not exists. Defaults to 384 for sentence-transformers all-MiniLM-L6-v2."""
        if not self.client: return
        
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            logger.info(f"Initializing vector collection '{self.collection_name}' with dimension {vector_size}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

    def upsert_vectors(self, vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        """Insert embedded document chunks into the DB"""
        if not self.client or not vectors: return
        
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=payloads[i] if payloads else {}
            )
            for i, vector in enumerate(vectors)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Upserted {len(vectors)} chunk vectors into {self.collection_name}")

    def search(self, query_vector: List[float], limit: int = 5, file_filter: List[str] = None) -> List[Any]:
        """Semantic search over vectors with optional filename filtering"""
        if not self.client: return []
        
        query_filter = None
        if file_filter:
            from qdrant_client.http import models as rest
            query_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="file_name",
                        match=rest.MatchAny(any=file_filter)
                    )
                ]
            )
            logger.info(f"Searching with file filter: {file_filter}")
        else:
            logger.info(f"Searching for top {limit} matches in vector DB (unfiltered)")

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit
        )
        return results.points if hasattr(results, 'points') else results

    def delete_by_filename(self, filename: str):
        """Delete chunks from DB based on file_name payload"""
        if not self.client: return
        try:
            from qdrant_client.http import models as rest
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="file_name",
                            match=rest.MatchValue(value=filename)
                        )
                    ]
                )
            )
            logger.info(f"Deleted vectors for file: {filename}")
        except Exception as e:
            logger.error(f"Failed to delete {filename} from Vector DB: {e}")

vector_db = VectorDBClient()
