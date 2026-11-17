from typing import Dict, List, Set, Any
from data.models import Note
from core.backlink_index import BacklinkIndex

class VaultGraph:
    """
    Knowledge graph data structure representing notes as nodes and links as edges.
    Provides methods for neighborhood exploration, cluster detection, and graph export.
    """
    def __init__(self):
        self.nodes: Dict[str, dict] = {} 
        self.edges: Dict[str, Set[str]] = {} 
        self.directed_edges: List[dict] = []

    def build_graph(self, notes_cache: Dict[str, Note], backlink_index: BacklinkIndex) -> None:
        """
        Builds the graph from notes_cache and backlink_index.
        """
        self.nodes = {}
        self.edges = {path: set() for path in notes_cache}
        self.directed_edges = []
        
        for path, note in notes_cache.items():
            self.nodes[path] = {
                "id": path,
                "title": note.title,
                "tags": note.tags,
                "connections": 0
            }
            
        for target_path, backlinks in backlink_index.index.items():
            for bl in backlinks:
                source_path = bl.source_path
                
                if source_path in self.nodes and target_path in self.nodes:
                    self.edges[source_path].add(target_path)
                    self.edges[target_path].add(source_path)
                    self.directed_edges.append({
                        "source": source_path,
                        "target": target_path,
                        "type": "link"
                    })
                    
        for path in self.nodes:
            self.nodes[path]["connections"] = len(self.edges.get(path, set()))

    def get_neighbors(self, note_path: str, depth: int = 1) -> Set[str]:
        """
        Returns a set of note paths within the specified depth from the source note.
        """
        if note_path not in self.nodes:
            return set()
            
        visited = set([note_path])
        current_level = set([note_path])
        
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for neighbor in self.edges.get(node, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)
            current_level = next_level
            
        visited.remove(note_path)
        return visited

    def get_most_connected(self, n: int = 10) -> List[dict]:
        """
        Returns the top N most connected notes (nodes with highest degree).
        """
        sorted_nodes = sorted(self.nodes.values(), key=lambda x: x["connections"], reverse=True)
        return sorted_nodes[:n]

    def get_clusters(self) -> List[List[str]]:
        """
        Finds connected components (clusters) in the graph.
        Returns a list of clusters, where each cluster is a list of note paths.
        """
        visited = set()
        clusters = []
        
        for node in self.nodes:
            if node not in visited:
                cluster = []
                queue = [node]
                visited.add(node)
                
                while queue:
                    current = queue.pop(0)
                    cluster.append(current)
                    for neighbor in self.edges.get(current, set()):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                clusters.append(cluster)
                
        return clusters

    def to_json(self) -> Dict[str, Any]:
        """
        Exports the graph data in a format suitable for D3.js visualization.
        """
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.directed_edges
        }
