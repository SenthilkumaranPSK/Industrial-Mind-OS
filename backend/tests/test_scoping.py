"""Per-user scoping rules for the memory cache and the knowledge graph.

Each test gets its own on-disk store via tmp_path, so nothing here touches the
real memory_cache.json / graph_db.json.
"""
import json

import pytest

import storage.graph_db as graph_db_module
import storage.memory_cache as memory_cache_module
from storage.graph_db import GraphDBClient
from storage.memory_cache import DirectMemoryCache

ALICE = "1"
BOB = "2"


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_cache_module, "CACHE_FILE", str(tmp_path / "cache.json"))
    return DirectMemoryCache()


@pytest.fixture
def graph(tmp_path, monkeypatch):
    monkeypatch.setattr(graph_db_module, "GRAPH_FILE", str(tmp_path / "graph.json"))
    return GraphDBClient()


# --- memory cache -----------------------------------------------------------

def test_users_only_see_their_own_files(cache):
    cache.store_file("alice.txt", "alice secret", owner_id=ALICE)
    cache.store_file("bob.txt", "bob secret", owner_id=BOB)

    assert cache.list_files(ALICE) == ["alice.txt"]
    assert cache.list_files(BOB) == ["bob.txt"]


def test_retrieval_context_is_scoped(cache):
    cache.store_file("alice.txt", "alice secret", owner_id=ALICE)
    cache.store_file("bob.txt", "bob secret", owner_id=BOB)

    contents = [c["content"] for c in cache.get_context(owner_id=BOB)]
    assert contents == ["bob secret"]


def test_user_cannot_delete_another_users_file(cache):
    cache.store_file("alice.txt", "alice secret", owner_id=ALICE)

    assert cache.delete_file("alice.txt", owner_id=BOB) is False
    assert cache.list_files(ALICE) == ["alice.txt"]

    assert cache.delete_file("alice.txt", owner_id=ALICE) is True
    assert cache.list_files(ALICE) == []


def test_file_filter_and_owner_filter_both_apply(cache):
    cache.store_file("a.txt", "a", owner_id=ALICE)
    cache.store_file("b.txt", "b", owner_id=ALICE)
    cache.store_file("c.txt", "c", owner_id=BOB)

    sources = [c["source"] for c in cache.get_context(["a.txt", "c.txt"], owner_id=ALICE)]
    assert sources == ["a.txt"]


def test_legacy_string_entries_are_migrated_and_stay_readable(tmp_path, monkeypatch):
    # Pre-scoping format: filename -> raw document text.
    legacy = tmp_path / "cache.json"
    legacy.write_text(json.dumps({"old.txt": "legacy content"}), encoding="utf-8")
    monkeypatch.setattr(memory_cache_module, "CACHE_FILE", str(legacy))

    cache = DirectMemoryCache()
    assert cache.cache["old.txt"] == {"content": "legacy content", "owner_id": None}
    # Un-owned data isn't orphaned by the upgrade.
    assert cache.list_files(ALICE) == ["old.txt"]
    assert cache.list_files(BOB) == ["old.txt"]


# --- knowledge graph --------------------------------------------------------

def test_graph_traversal_is_scoped(graph):
    graph.add_relationship("pump", "co-occurs-with", "seal",
                           metadata={"source": "alice.pdf", "owner_id": ALICE})
    graph.add_relationship("pump", "co-occurs-with", "valve",
                           metadata={"source": "bob.pdf", "owner_id": BOB})

    alice_ctx = graph.get_context_for_entity("pump", owner_id=ALICE)
    assert [c["content"] for c in alice_ctx] == ["pump -> co-occurs-with -> seal"]

    bob_ctx = graph.get_context_for_entity("pump", owner_id=BOB)
    assert [c["content"] for c in bob_ctx] == ["pump -> co-occurs-with -> valve"]


def test_graph_visualizer_payload_is_scoped(graph):
    graph.add_relationship("pump", "co-occurs-with", "seal",
                           metadata={"source": "alice.pdf", "owner_id": ALICE})
    graph.add_relationship("turbine", "co-occurs-with", "blade",
                           metadata={"source": "bob.pdf", "owner_id": BOB})

    node_ids = {n["id"] for n in graph.get_graph_data(owner_id=ALICE)["nodes"]}
    assert node_ids == {"pump", "seal"}


def test_graph_delete_does_not_touch_another_users_edges(graph):
    graph.add_relationship("pump", "co-occurs-with", "seal",
                           metadata={"source": "shared.pdf", "owner_id": ALICE})
    graph.add_relationship("pump", "co-occurs-with", "valve",
                           metadata={"source": "shared.pdf", "owner_id": BOB})

    # Same filename, two owners: deleting as Alice must leave Bob's edge alone.
    assert graph.delete_by_filename("shared.pdf", owner_id=ALICE) == 1
    assert [c["content"] for c in graph.get_context_for_entity("pump", owner_id=BOB)] == [
        "pump -> co-occurs-with -> valve"
    ]


def test_batched_writes_are_persisted(tmp_path, monkeypatch):
    path = tmp_path / "graph.json"
    monkeypatch.setattr(graph_db_module, "GRAPH_FILE", str(path))
    graph = GraphDBClient()

    graph.add_relationship("a", "co-occurs-with", "b",
                           metadata={"source": "f.pdf", "owner_id": ALICE}, autosave=False)
    assert not path.exists()  # deferred, as the bulk ingest path expects

    graph.save()
    reloaded = GraphDBClient()
    assert reloaded.get_context_for_entity("a", owner_id=ALICE)


def test_case_insensitive_entity_lookup(graph):
    graph.add_relationship("PressureValve", "co-occurs-with", "Regulator",
                           metadata={"source": "manual.pdf", "owner_id": ALICE})

    # Exact match
    assert graph.get_context_for_entity("PressureValve", owner_id=ALICE)
    # Lowercase lookup
    lower_ctx = graph.get_context_for_entity("pressurevalve", owner_id=ALICE)
    assert len(lower_ctx) == 1
    assert "PressureValve -> co-occurs-with -> Regulator" in lower_ctx[0]["content"]
    # Uppercase lookup
    upper_ctx = graph.get_context_for_entity("PRESSUREVALVE", owner_id=ALICE)
    assert len(upper_ctx) == 1

