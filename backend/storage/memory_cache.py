import logging
import json
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "memory_cache.json")


class DirectMemoryCache:
    """
    A lightweight memory cache that persists to disk so data survives backend restarts.
    Used by the AdaptiveRetrievalAgent to bypass Qdrant for small documents.

    Entries are {"content": str, "owner_id": str | None}. An owner_id of None marks a
    legacy entry written before per-user scoping existed; those stay readable by
    everyone rather than being silently orphaned.
    """
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if not os.path.exists(CACHE_FILE):
            return
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load memory cache from disk: {e}")
            return

        legacy = []
        for name, value in raw.items():
            if isinstance(value, str):
                # Pre-scoping format: the value was the document text itself.
                self.cache[name] = {"content": value, "owner_id": None}
                legacy.append(name)
            else:
                self.cache[name] = {
                    "content": value.get("content", ""),
                    "owner_id": value.get("owner_id"),
                }
        logger.info(f"DirectMemoryCache: Loaded {len(self.cache)} files from disk.")
        if legacy:
            logger.warning(
                f"DirectMemoryCache: {len(legacy)} un-owned legacy file(s) remain readable by "
                f"all users: {', '.join(legacy[:5])}{'...' if len(legacy) > 5 else ''}"
            )

    def _save(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save memory cache to disk: {e}")

    @staticmethod
    def _visible(entry: dict, owner_id: Optional[str]) -> bool:
        """Legacy (un-owned) entries are visible to everyone; owned ones only to their owner."""
        entry_owner = entry.get("owner_id")
        return entry_owner is None or owner_id is None or str(entry_owner) == str(owner_id)

    def store_file(self, filename: str, content: str, owner_id: Optional[str] = None):
        self.cache[filename] = {"content": content, "owner_id": str(owner_id) if owner_id else None}
        self._save()
        logger.info(f"Stored {filename} entirely in DirectMemoryCache (Bypassing Vector DB).")

    def get_context(self, file_filter: list[str] = None, owner_id: Optional[str] = None) -> list[dict]:
        """Returns context from the cache, filtered by owner and optionally by filename."""
        return [
            {"source": name, "content": entry["content"]}
            for name, entry in self.cache.items()
            if self._visible(entry, owner_id)
            and (not file_filter or name in file_filter)
        ]

    def list_files(self, owner_id: Optional[str] = None) -> list[str]:
        """Filenames this user is allowed to see."""
        return [name for name, entry in self.cache.items() if self._visible(entry, owner_id)]

    def owns(self, filename: str, owner_id: Optional[str]) -> bool:
        entry = self.cache.get(filename)
        return entry is not None and self._visible(entry, owner_id)

    def delete_file(self, filename: str, owner_id: Optional[str] = None) -> bool:
        """Deletes the file if this user may see it. Returns whether anything was removed."""
        entry = self.cache.get(filename)
        if entry is None or not self._visible(entry, owner_id):
            return False
        del self.cache[filename]
        self._save()
        logger.info(f"Deleted {filename} entirely from DirectMemoryCache.")
        return True


memory_cache = DirectMemoryCache()
