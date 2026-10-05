import logging
import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)


class VectorDBClient:
    def __init__(self, collection_name: str = "imos_collection"):
        # QDRANT_URL points at a real Qdrant server (needed to run more than one
        # backend process). Unset falls back to local disk mode, which holds an
        # exclusive lock on its directory and therefore allows a single process only.
        try:
            qdrant_url = os.getenv("QDRANT_URL")
            if qdrant_url:
                self.client = QdrantClient(url=qdrant_url, api_key=os.getenv("QDRANT_API_KEY"))
                logger.info(f"Connected to Qdrant server at {qdrant_url}")
            else:
                db_path = os.path.join(os.path.dirname(__file__), "..", "qdrant_data")
                os.makedirs(db_path, exist_ok=True)
                self.client = QdrantClient(path=db_path)  # Disk-persisted local storage
                logger.info("Connected to Qdrant in local disk mode (single process only)")
            self.collection_name = collection_name
            self._init_collection()
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

    @staticmethod
    def _owner_clause(owner_id: Optional[str]):
        """
        Matches points owned by this user plus legacy points that predate scoping
        (no user_id in the payload), so older data doesn't silently disappear.
        """
        from qdrant_client.http import models as rest
        return [
            rest.FieldCondition(key="user_id", match=rest.MatchValue(value=str(owner_id))),
            rest.IsEmptyCondition(is_empty=rest.PayloadField(key="user_id")),
        ]

    def _build_filter(self, file_filter: List[str] = None, owner_id: Optional[str] = None):
        from qdrant_client.http import models as rest
        must = []
        if file_filter:
            must.append(rest.FieldCondition(key="file_name", match=rest.MatchAny(any=file_filter)))
        should = self._owner_clause(owner_id) if owner_id is not None else None
        if not must and not should:
            return None
        return rest.Filter(must=must or None, should=should)

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

    def search(self, query_vector: List[float], limit: int = 5, file_filter: List[str] = None,
               owner_id: Optional[str] = None) -> List[Any]:
        """Semantic search over vectors, scoped to the owner and optionally to a file allowlist."""
        if not self.client: return []

        query_filter = self._build_filter(file_filter, owner_id)
        logger.info(f"Vector search (limit={limit}, files={file_filter or 'all'}, owner={owner_id})")

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit
        )
        return results.points if hasattr(results, 'points') else results

    def list_filenames(self, owner_id: Optional[str] = None, page_size: int = 500) -> List[str]:
        """
        Every distinct file_name this user owns, scrolling the whole collection.

        Paginates deliberately: a single large document can exceed any one page of
        points and would otherwise hide every other file from the listing.
        """
        if not self.client:
            return []

        filenames: List[str] = []
        seen = set()
        offset = None
        try:
            while True:
                points, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=self._build_filter(owner_id=owner_id),
                    limit=page_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for pt in points:
                    fname = pt.payload.get("file_name")
                    if fname and fname not in seen:
                        seen.add(fname)
                        filenames.append(fname)
                if offset is None or not points:
                    break
        except Exception as e:
            logger.warning(f"Could not scroll vector DB for file list: {e}")
        return filenames

    def count_by_filename(self, filename: str, owner_id: Optional[str] = None) -> int:
        """How many points this user has for a filename — used to check ownership before deleting."""
        if not self.client:
            return 0
        try:
            from qdrant_client.http import models as rest
            flt = self._build_filter(file_filter=[filename], owner_id=owner_id)
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=flt,
                exact=True,
            )
            return result.count
        except Exception as e:
            logger.warning(f"Could not count points for {filename}: {e}")
            return 0

    def delete_by_filename(self, filename: str, owner_id: Optional[str] = None) -> int:
        """Delete this user's chunks for a file. Returns how many points were removed."""
        if not self.client: return 0
        try:
            removed = self.count_by_filename(filename, owner_id)
            if removed == 0:
                return 0
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=self._build_filter(file_filter=[filename], owner_id=owner_id),
            )
            logger.info(f"Deleted {removed} vectors for file: {filename}")
            return removed
        except Exception as e:
            logger.error(f"Failed to delete {filename} from Vector DB: {e}")
            return 0


vector_db = VectorDBClient()
