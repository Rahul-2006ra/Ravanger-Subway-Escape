"""Reusable weighted-graph data structure and Dijkstra pathfinding algorithm.

This module provides an independent, standard-library-only graph component
designed for competitive routing problems. It handles directed and undirected
weighted graphs, zero-cost edges, blocked (infinite-weight) edges, and safely
handles disconnected components and missing nodes.
"""

from __future__ import annotations

import heapq
import itertools
import math
from typing import (
    Any,
    Dict,
    Hashable,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

NodeId = Union[str, int]


class ShortestPathResult(NamedTuple):
    """Result of a shortest-path query.

    Attributes:
        path: Ordered list of node IDs from source to target inclusive,
              or None if target is unreachable.
        cost: Total weight along the path (0.0 if source == target),
              or float('inf') if target is unreachable.
    """

    path: Optional[List[NodeId]]
    cost: float


class WeightedGraph:
    """Directed weighted graph supporting string and integer node identifiers.

    Nodes and edges can be added explicitly, or the graph can wrap/import
    an existing adjacency dictionary without modifying external data.
    """

    def __init__(self) -> None:
        self._adj: Dict[NodeId, Dict[NodeId, float]] = {}

    def add_node(self, node: NodeId) -> None:
        """Add a node if it does not already exist."""
        if node not in self._adj:
            self._adj[node] = {}

    def add_edge(
        self,
        u: NodeId,
        v: NodeId,
        weight: float,
        bidirectional: bool = False,
    ) -> None:
        """Add a directed (or optionally bidirectional) weighted edge.

        Args:
            u: Source node ID.
            v: Destination node ID.
            weight: Edge weight (must be non-negative).
            bidirectional: If True, also adds edge v -> u with the same weight.

        Raises:
            ValueError: If weight is strictly negative.
        """
        if weight < 0:
            raise ValueError(f"Negative edge weight not allowed: {weight} on ({u} -> {v})")

        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = float(weight)

        if bidirectional:
            self._adj[v][u] = float(weight)

    def get_neighbors(self, node: NodeId) -> Mapping[NodeId, float]:
        """Return the outgoing edges from node as {neighbor: weight}."""
        return self._adj.get(node, {})

    def has_node(self, node: NodeId) -> bool:
        """Return True if node exists in the graph."""
        return node in self._adj

    def nodes(self) -> Set[NodeId]:
        """Return a copy of the set of all node IDs."""
        return set(self._adj.keys())

    def to_dict(self) -> Dict[NodeId, Dict[NodeId, float]]:
        """Return a deep copy of the adjacency representation."""
        return {u: dict(neighbors) for u, neighbors in self._adj.items()}

    @classmethod
    def from_dict(cls, data: Mapping[NodeId, Mapping[NodeId, float]]) -> WeightedGraph:
        """Construct a WeightedGraph from an existing nested dictionary."""
        graph = cls()
        for u, neighbors in data.items():
            graph.add_node(u)
            for v, weight in neighbors.items():
                graph.add_edge(u, v, weight)
        return graph


def _extract_neighbors(
    graph: Union[WeightedGraph, Mapping[NodeId, Mapping[NodeId, float]]],
    node: NodeId,
) -> Iterable[Tuple[NodeId, float]]:
    """Helper to safely extract outgoing edges from either WeightedGraph or dict."""
    if isinstance(graph, WeightedGraph):
        return graph.get_neighbors(node).items()
    if isinstance(graph, Mapping):
        neighbors = graph.get(node)
        if neighbors is None:
            return ()
        return neighbors.items()
    return ()


def _contains_node(
    graph: Union[WeightedGraph, Mapping[NodeId, Mapping[NodeId, float]]],
    node: NodeId,
) -> bool:
    """Helper to check if a node exists in graph."""
    if isinstance(graph, WeightedGraph):
        return graph.has_node(node)
    if isinstance(graph, Mapping):
        return node in graph
    return False


def _reconstruct_path(
    predecessor: Mapping[NodeId, NodeId],
    target: NodeId,
) -> List[NodeId]:
    """Reconstruct path from predecessor map back to source."""
    path: List[NodeId] = []
    curr: Optional[NodeId] = target
    while curr is not None:
        path.append(curr)
        curr = predecessor.get(curr)
    path.reverse()
    return path


def _dijkstra_search(
    graph: Union[WeightedGraph, Mapping[NodeId, Mapping[NodeId, float]]],
    source: NodeId,
    target: Optional[NodeId] = None,
) -> Tuple[Dict[NodeId, float], Dict[NodeId, NodeId]]:
    """Internal core Dijkstra search.

    Explores reachable nodes from source. If target is provided, terminates early
    once target is visited.

    Returns:
        (dist, predecessor) mappings for all visited/relaxed nodes.

    Raises:
        ValueError: If a negative edge weight is encountered.
    """
    dist: Dict[NodeId, float] = {source: 0.0}
    predecessor: Dict[NodeId, NodeId] = {}

    # Priority queue: entries are (cost, tie_breaker_counter, node_id)
    # Using a monotonic counter avoids comparing NodeId objects if types differ (e.g. str vs int).
    counter = itertools.count()
    pq: List[Tuple[float, int, NodeId]] = [(0.0, next(counter), source)]
    visited: Set[NodeId] = set()

    while pq:
        curr_dist, _, u = heapq.heappop(pq)

        if u in visited:
            continue
        visited.add(u)

        # Early exit if a specific target was requested and reached
        if target is not None and u == target:
            break

        # Explore outgoing edges
        for v, weight in _extract_neighbors(graph, u):
            if weight < 0:
                raise ValueError(
                    f"Negative edge weight encountered: {weight} on edge ({u} -> {v})"
                )

            # Blocked edge (infinite weight)
            if math.isinf(weight) or weight >= math.inf:
                continue

            new_dist = curr_dist + weight
            if new_dist < dist.get(v, math.inf):
                dist[v] = new_dist
                predecessor[v] = u
                heapq.heappush(pq, (new_dist, next(counter), v))

    return dist, predecessor


def dijkstra_shortest_path(
    graph: Union[WeightedGraph, Mapping[NodeId, Mapping[NodeId, float]]],
    source: NodeId,
    target: NodeId,
) -> ShortestPathResult:
    """Compute the minimum-cost path from source to target using Dijkstra's algorithm.

    This function never mutates the provided graph.

    Edge rules:
        - Negative weights raise ValueError.
        - Infinite weights (float('inf') or math.inf) are treated as blocked and ignored.
        - Zero-weight edges are valid and supported.

    Unreachable rules:
        - If source or target does not exist in the graph, returns (path=None, cost=math.inf).
        - If no finite-cost path connects source to target, returns (path=None, cost=math.inf).
        - If source == target and source is present in the graph, returns (path=[source], cost=0.0).

    Args:
        graph: A WeightedGraph instance or a nested mapping {u: {v: weight}}.
        source: Starting node identifier (string or integer).
        target: Destination node identifier (string or integer).

    Returns:
        ShortestPathResult(path=Optional[List[NodeId]], cost=float)

    Raises:
        ValueError: If any traversed or reachable edge has a negative weight.
    """
    # Quick checks for missing nodes or empty graph
    if not _contains_node(graph, source) or not _contains_node(graph, target):
        return ShortestPathResult(path=None, cost=math.inf)

    # Trivial source == target case
    if source == target:
        return ShortestPathResult(path=[source], cost=0.0)

    dist, predecessor = _dijkstra_search(graph, source, target=target)

    # Check if target was reached with a finite cost
    if target not in dist or math.isinf(dist[target]):
        return ShortestPathResult(path=None, cost=math.inf)

    return ShortestPathResult(
        path=_reconstruct_path(predecessor, target),
        cost=dist[target],
    )


def dijkstra_all(
    graph: Union[WeightedGraph, Mapping[NodeId, Mapping[NodeId, float]]],
    source: NodeId,
) -> Dict[NodeId, ShortestPathResult]:
    """Compute minimum-cost paths from source to all reachable nodes in a single traversal.

    This function never mutates the provided graph.

    Edge rules:
        - Negative weights raise ValueError.
        - Infinite weights (float('inf') or math.inf) are treated as blocked and ignored.
        - Zero-weight edges are valid and supported.

    Unreachable rules:
        - If source is missing from the graph or graph is empty, returns an empty dictionary {}.
        - Only reachable nodes are included in the returned dictionary. Nodes in disconnected
          components or with infinite distance are omitted.
        - The source itself is included with path=[source] and cost=0.0.

    Time Complexity:
        - Search: O((V + E) log V), where V is the number of reachable nodes and E is
          the number of reachable edges.
        - Path reconstruction: O(V * L), where L <= V is the average path length.
        - Total Time: O(E log V + V^2).
    Space Complexity:
        - O(V + E) auxiliary space for distances, predecessors, and the min-heap.

    Args:
        graph: A WeightedGraph instance or a nested mapping {u: {v: weight}}.
        source: Starting node identifier (string or integer).

    Returns:
        Dict[NodeId, ShortestPathResult]: A mapping where keys are all reachable node IDs,
        and values are ShortestPathResult(path=..., cost=...).

    Raises:
        ValueError: If any reachable edge has a negative weight.
    """
    if not _contains_node(graph, source):
        return {}

    dist, predecessor = _dijkstra_search(graph, source, target=None)

    results: Dict[NodeId, ShortestPathResult] = {}
    for node, cost in dist.items():
        results[node] = ShortestPathResult(
            path=_reconstruct_path(predecessor, node),
            cost=cost,
        )

    return results

