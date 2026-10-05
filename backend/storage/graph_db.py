import logging
import networkx as nx
import json
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

GRAPH_FILE = os.path.join(os.path.dirname(__file__), "..", "graph_db.json")


class GraphDBClient:
    def __init__(self):
        # We use NetworkX locally to simulate Neo4j behavior instantly for ideathons
        self.graph = nx.MultiDiGraph()
        self._load()
        logger.info(f"Connected to Graph Database (NetworkX with {len(self.graph.nodes)} nodes)")

    def _load(self):
        if os.path.exists(GRAPH_FILE):
            try:
                with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data, multigraph=True)
                logger.info(f"GraphDB: Loaded {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges from disk.")
            except Exception as e:
                logger.warning(f"Could not load graph from disk: {e}")

    def save(self):
        """Serialize the whole graph to disk. Call once per batch, not per edge."""
        try:
            data = nx.node_link_data(self.graph)
            with open(GRAPH_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save graph to disk: {e}")

    # Kept as an alias so existing call sites keep working.
    _save = save

    @staticmethod
    def _visible(edge_data: dict, owner_id: Optional[str]) -> bool:
        """Edges written before per-user scoping have no owner_id and stay globally visible."""
        edge_owner = edge_data.get("owner_id")
        return edge_owner is None or owner_id is None or str(edge_owner) == str(owner_id)

    def add_relationship(self, entity1: str, relationship: str, entity2: str,
                         metadata: dict = None, autosave: bool = True):
        """
        Adds a triple to the graph database.

        Pass autosave=False when writing many edges in a loop and call save() once
        afterwards — serializing the entire graph per edge is O(n^2) on bulk ingest.
        """
        self.graph.add_node(entity1)
        self.graph.add_node(entity2)
        self.graph.add_edge(entity1, entity2, relation=relationship, **(metadata or {}))
        if autosave:
            self.save()
        logger.debug(f"Added Graph Edge: {entity1} -[{relationship}]-> {entity2}")

    def delete_by_filename(self, filename: str, owner_id: Optional[str] = None) -> int:
        """
        Removes edges associated with a file (only those this user may see) and prunes
        orphaned nodes. Returns the number of edges removed.
        """
        edges_to_remove = []
        for u, v, k, data in self.graph.edges(keys=True, data=True):
            matches_file = data.get("source") == filename or data.get("file_name") == filename
            if matches_file and self._visible(data, owner_id):
                edges_to_remove.append((u, v, k))

        if not edges_to_remove:
            return 0

        self.graph.remove_edges_from(edges_to_remove)
        logger.info(f"GraphDB: Removed {len(edges_to_remove)} edges associated with {filename}")

        # Prune orphan nodes (nodes with 0 degree)
        orphans = [node for node, degree in dict(self.graph.degree()).items() if degree == 0]
        if orphans:
            self.graph.remove_nodes_from(orphans)
            logger.info(f"GraphDB: Pruned {len(orphans)} orphaned nodes.")

        self.save()
        return len(edges_to_remove)

    def get_context_for_entity(self, entity: str, depth: int = 2, file_filter: List[str] = None,
                               owner_id: Optional[str] = None) -> List[Dict]:
        if entity not in self.graph:
            # Fallback to case-insensitive match so e.g. 'valve' matches 'Valve'
            matched = next((n for n in self.graph.nodes if str(n).lower() == entity.lower()), None)
            if not matched:
                return []
            entity = matched

        context = []
        # Orientation="original" means we follow the arrows (Out-edges)
        edges = nx.edge_bfs(self.graph, entity, orientation="original")

        for edge_count, edge in enumerate(edges):
            if edge_count >= depth * 8:  # Increased limit for more depth
                break

            src, dst = edge[0], edge[1]
            try:
                # MultiDiGraph returns (u,v,key) in edge_bfs
                key = edge[2] if len(edge) > 2 else 0
                edge_data = self.graph[src][dst][key]

                # Ownership gate: never surface another user's edges
                if not self._visible(edge_data, owner_id):
                    continue

                # Knowledge Gate: Skip if this edge doesn't belong to an allowed file
                if file_filter and edge_data.get("source") not in file_filter:
                    continue

                rel = edge_data.get("relation", "connected_to")
                context.append({
                    "source": f"Graph: {edge_data.get('source', 'System Knowledge')}",
                    "content": f"{src} -> {rel} -> {dst}"
                })
            except Exception as e:
                logger.debug(f"Graph traversal detail skip: {e}")

        return context

    def get_random_entities(self, limit: int = 3, owner_id: Optional[str] = None) -> List[str]:
        """Expose a few random entities for query suggestions."""
        visible = self._visible_node_names(owner_id)
        nodes = [str(n) for n in visible if isinstance(n, str) and len(n) > 3]
        if not nodes:
            return []
        import random
        return random.sample(nodes, min(limit, len(nodes)))

    def _visible_node_names(self, owner_id: Optional[str]) -> set:
        """Nodes touched by at least one edge this user may see."""
        if owner_id is None:
            return set(self.graph.nodes())
        names = set()
        for u, v, data in self.graph.edges(data=True):
            if self._visible(data, owner_id):
                names.add(u)
                names.add(v)
        return names

    def get_graph_data(self, owner_id: Optional[str] = None) -> Dict:
        """Exports the graph in D3 JSON format for the frontend visualizer. Limited to top 300 nodes."""
        visible_nodes = self._visible_node_names(owner_id)

        # Calculate node size based on its degree (importance)
        node_degrees = {n: d for n, d in self.graph.degree() if n in visible_nodes}

        # Sort nodes by degree and keep top 300 to prevent browser crash
        top_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:300]
        allowed_node_names = {n for n, d in top_nodes}

        nodes = [{"id": n, "name": n, "val": degree + 5} for n, degree in top_nodes]

        links = []
        for u, v, data in self.graph.edges(data=True):
            # Only include edges where both nodes are in our top 300 subset
            if u in allowed_node_names and v in allowed_node_names and self._visible(data, owner_id):
                links.append({
                    "source": u,
                    "target": v,
                    "label": data.get("relation", "connected")
                })

        if len(node_degrees) > len(top_nodes):
            logger.info(
                f"GraphDB: capped visualizer payload at {len(top_nodes)} of {len(node_degrees)} nodes."
            )

        return {"nodes": nodes, "links": links, "total_nodes": len(node_degrees), "capped": len(node_degrees) > len(top_nodes)}


graph_db = GraphDBClient()
