import logging
import json
import os
from typing import Dict

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "memory_cache.json")

class DirectMemoryCache:
    """
    A lightweight memory cache that persists to disk so data survives backend restarts.
    Used by the AdaptiveRetrievalAgent to bypass Qdrant for small documents.
    """
    def __init__(self):
        self.cache: Dict[str, str] = {}
        self._load()

    def _load(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"DirectMemoryCache: Loaded {len(self.cache)} files from disk.")
            except Exception as e:
                logger.warning(f"Could not load memory cache from disk: {e}")

    def _save(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save memory cache to disk: {e}")

    def store_file(self, filename: str, content: str):
        self.cache[filename] = content
        self._save()
        logger.info(f"Stored {filename} entirely in DirectMemoryCache (Bypassing Vector DB).")

    def get_context(self, file_filter: list[str] = None) -> list[dict]:
        """Returns context from the cache, optionally filtered by filename"""
        if file_filter:
            return [{"source": name, "content": content} for name, content in self.cache.items() if name in file_filter]
        return [{"source": name, "content": content} for name, content in self.cache.items()]

    def delete_file(self, filename: str):
        if filename in self.cache:
            del self.cache[filename]
            self._save()
            logger.info(f"Deleted {filename} entirely from DirectMemoryCache.")

memory_cache = DirectMemoryCache()
