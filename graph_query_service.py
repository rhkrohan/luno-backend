"""
Graph Query Service for Knowledge Graph

Provides graph algorithms for querying and traversing the knowledge graph:
- BFS/DFS traversal
- Cluster detection
- Path finding
- Subgraph extraction
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class GraphQueryService:
    """Service for querying and traversing the knowledge graph"""

    def __init__(self, db):
        """
        Initialize graph query service

        Args:
            db: Firestore database client
        """
        self.db = db

    def get_related_entities(self, user_id: str, child_id: str, entity_id: str,
                            max_depth: int = 2, edge_types: Optional[List[str]] = None,
                            min_weight: float = 0.5) -> Dict:
        """
        BFS traversal to find related entities

        Args:
            user_id: Parent user ID
            child_id: Child ID
            entity_id: Starting entity ID
            max_depth: Maximum traversal depth (default: 2)
            edge_types: Optional list of edge types to traverse (None = all types)
            min_weight: Minimum edge weight threshold (default: 0.5)

        Returns:
            Dict with:
                entities: {depth: [entity_dicts]}
                edges: [edge_dicts]
                totalEntities: int
                totalEdges: int
        """
        try:
            logger.debug(f"[GraphQuery] Finding related entities for {entity_id}, max_depth={max_depth}")

            entities_by_depth = defaultdict(list)
            visited_entities = set()
            all_edges = []

            # BFS queue: (entity_id, current_depth)
            queue = deque([(entity_id, 0)])
            visited_entities.add(entity_id)

            # Get starting entity
            start_entity = self._get_entity(user_id, child_id, entity_id)
            if start_entity:
                entities_by_depth[0].append(start_entity)

            while queue:
                current_id, depth = queue.popleft()

                if depth >= max_depth:
                    continue

                # Get edges for current entity
                edges = self._get_entity_edges(user_id, child_id, current_id, edge_types, min_weight)

                for edge in edges:
                    # Determine neighbor (other end of edge)
                    if edge['sourceEntityId'] == current_id:
                        neighbor_id = edge['targetEntityId']
                    else:
                        neighbor_id = edge['sourceEntityId']

                    # Skip if already visited
                    if neighbor_id in visited_entities:
                        continue

                    # Get neighbor entity
                    neighbor = self._get_entity(user_id, child_id, neighbor_id)
                    if not neighbor:
                        continue

                    # Add to results
                    visited_entities.add(neighbor_id)
                    entities_by_depth[depth + 1].append(neighbor)
                    all_edges.append(edge)
                    queue.append((neighbor_id, depth + 1))

            return {
                'entities': dict(entities_by_depth),
                'edges': all_edges,
                'totalEntities': len(visited_entities),
                'totalEdges': len(all_edges)
            }

        except Exception as e:
            logger.error(f"[GraphQuery] Error finding related entities: {e}", exc_info=True)
            return {'entities': {}, 'edges': [], 'totalEntities': 0, 'totalEdges': 0}

    def get_entity_neighbors(self, user_id: str, child_id: str, entity_id: str,
                            edge_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get immediate neighbors of an entity

        Args:
            user_id: Parent user ID
            child_id: Child ID
            entity_id: Entity ID
            edge_type: Optional edge type filter
            limit: Maximum number of neighbors to return

        Returns:
            List of neighbor entity dicts with edge info
        """
        try:
            edges = self._get_entity_edges(user_id, child_id, entity_id,
                                          [edge_type] if edge_type else None,
                                          min_weight=0.0)

            neighbors = []
            seen_ids = set()

            for edge in edges:
                # Determine neighbor
                if edge['sourceEntityId'] == entity_id:
                    neighbor_id = edge['targetEntityId']
                else:
                    neighbor_id = edge['sourceEntityId']

                if neighbor_id in seen_ids:
                    continue

                seen_ids.add(neighbor_id)

                # Get neighbor entity
                neighbor = self._get_entity(user_id, child_id, neighbor_id)
                if neighbor:
                    neighbor['edgeWeight'] = edge['weight']
                    neighbor['edgeType'] = edge['edgeType']
                    neighbors.append(neighbor)

            # Sort by edge weight descending
            neighbors.sort(key=lambda x: x['edgeWeight'], reverse=True)

            return neighbors[:limit]

        except Exception as e:
            logger.error(f"[GraphQuery] Error getting neighbors: {e}", exc_info=True)
            return []

    def find_interest_clusters(self, user_id: str, child_id: str,
                               min_cluster_size: int = 2) -> List[Dict]:
        """
        Detect interest clusters using connected components on temporal_cooccurrence edges

        Args:
            user_id: Parent user ID
            child_id: Child ID
            min_cluster_size: Minimum entities in cluster (default: 2)

        Returns:
            List of cluster dicts: {clusterId, label, size, entities}
        """
        try:
            logger.debug(f"[GraphQuery] Finding interest clusters for child {child_id}")

            # Get all interest/topic entities
            entities = self._get_entities_by_types(user_id, child_id, ['interest', 'topic'])

            if len(entities) < min_cluster_size:
                return []

            # Get temporal cooccurrence edges (weight >= 0.6)
            edges_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("edges")

            edges = list(edges_ref.where("edgeType", "==", "temporal_cooccurrence")\
                                  .where("weight", ">=", 0.6).stream())

            # Build adjacency list
            adjacency = defaultdict(set)
            entity_ids = {e['id'] for e in entities}

            for edge_doc in edges:
                edge = edge_doc.to_dict()
                source = edge['sourceEntityId']
                target = edge['targetEntityId']

                # Only include edges between interest/topic entities
                if source in entity_ids and target in entity_ids:
                    adjacency[source].add(target)
                    adjacency[target].add(source)

            # Find connected components using DFS
            visited = set()
            clusters = []
            cluster_id = 0

            for entity in entities:
                entity_id = entity['id']

                if entity_id in visited:
                    continue

                # DFS to find connected component
                component = []
                stack = [entity_id]

                while stack:
                    current = stack.pop()

                    if current in visited:
                        continue

                    visited.add(current)
                    component.append(current)

                    # Add neighbors to stack
                    for neighbor in adjacency.get(current, set()):
                        if neighbor not in visited:
                            stack.append(neighbor)

                # Only keep clusters >= min size
                if len(component) >= min_cluster_size:
                    # Get entity details for cluster
                    cluster_entities = [e for e in entities if e['id'] in component]

                    # Generate cluster label from top entities
                    top_entities = sorted(cluster_entities, key=lambda x: x.get('strength', 0), reverse=True)[:3]
                    label = " & ".join([e['name'] for e in top_entities])

                    clusters.append({
                        'clusterId': f"cluster_{cluster_id}",
                        'label': label,
                        'size': len(component),
                        'entities': cluster_entities
                    })

                    cluster_id += 1

            logger.debug(f"[GraphQuery] Found {len(clusters)} clusters")
            return clusters

        except Exception as e:
            logger.error(f"[GraphQuery] Error finding clusters: {e}", exc_info=True)
            return []

    def extract_context_subgraph(self, user_id: str, child_id: str,
                                 seed_entities: List[str],
                                 max_entities: int = 15,
                                 depth: int = 1) -> Dict:
        """
        Extract relevant subgraph for LLM context from seed entities

        Args:
            user_id: Parent user ID
            child_id: Child ID
            seed_entities: List of seed entity IDs
            max_entities: Maximum entities in subgraph
            depth: Traversal depth

        Returns:
            Dict with entities and edges
        """
        try:
            logger.debug(f"[GraphQuery] Extracting subgraph from {len(seed_entities)} seeds")

            all_entities = []
            all_edges = []
            visited = set()

            # BFS from all seeds
            queue = deque()
            for seed_id in seed_entities:
                queue.append((seed_id, 0))
                visited.add(seed_id)

            while queue and len(all_entities) < max_entities:
                entity_id, current_depth = queue.popleft()

                # Get entity
                entity = self._get_entity(user_id, child_id, entity_id)
                if entity:
                    entity['isSeed'] = entity_id in seed_entities
                    all_entities.append(entity)

                if current_depth >= depth:
                    continue

                # Get edges (high weight only for context)
                edges = self._get_entity_edges(user_id, child_id, entity_id, min_weight=0.7)

                for edge in edges:
                    # Determine neighbor
                    if edge['sourceEntityId'] == entity_id:
                        neighbor_id = edge['targetEntityId']
                    else:
                        neighbor_id = edge['sourceEntityId']

                    if neighbor_id not in visited and len(all_entities) < max_entities:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, current_depth + 1))
                        all_edges.append(edge)

            return {
                'entities': all_entities,
                'edges': all_edges,
                'totalEntities': len(all_entities),
                'totalEdges': len(all_edges)
            }

        except Exception as e:
            logger.error(f"[GraphQuery] Error extracting subgraph: {e}", exc_info=True)
            return {'entities': [], 'edges': [], 'totalEntities': 0, 'totalEdges': 0}

    def get_prerequisite_chain(self, user_id: str, child_id: str,
                               entity_id: str, max_depth: int = 3) -> List[Dict]:
        """
        Get learning prerequisites by following learning_pathway edges backwards

        Args:
            user_id: Parent user ID
            child_id: Child ID
            entity_id: Starting entity ID
            max_depth: Maximum chain depth

        Returns:
            List of prerequisite entities (ordered from most prerequisite to entity)
        """
        try:
            logger.debug(f"[GraphQuery] Finding prerequisite chain for {entity_id}")

            prerequisites = []
            visited = set([entity_id])
            current = entity_id

            for _ in range(max_depth):
                # Get learning_pathway edges where current entity is the TARGET
                edges_ref = self.db.collection("users").document(user_id)\
                    .collection("children").document(child_id)\
                    .collection("edges")

                # Find edges pointing TO this entity
                edges = list(edges_ref.where("edgeType", "==", "learning_pathway")\
                                      .where("targetEntityId", "==", current).stream())

                # Filter for prerequisite edges
                prereq_edges = []
                for edge_doc in edges:
                    edge = edge_doc.to_dict()
                    if edge.get('attributes', {}).get('prerequisite', False):
                        prereq_edges.append(edge)

                if not prereq_edges:
                    break

                # Get highest weight prerequisite
                prereq_edges.sort(key=lambda e: e['weight'], reverse=True)
                best_edge = prereq_edges[0]

                prereq_id = best_edge['sourceEntityId']

                if prereq_id in visited:
                    break

                # Get prerequisite entity
                prereq_entity = self._get_entity(user_id, child_id, prereq_id)
                if prereq_entity:
                    prerequisites.insert(0, prereq_entity)  # Insert at front
                    visited.add(prereq_id)
                    current = prereq_id
                else:
                    break

            return prerequisites

        except Exception as e:
            logger.error(f"[GraphQuery] Error getting prerequisite chain: {e}", exc_info=True)
            return []

    def find_learning_path(self, user_id: str, child_id: str,
                          start_entity_id: str, target_entity_id: str,
                          max_depth: int = 5) -> Optional[List[Dict]]:
        """
        Find shortest learning pathway using BFS (only follows learning_pathway edges)

        Args:
            user_id: Parent user ID
            child_id: Child ID
            start_entity_id: Starting entity ID
            target_entity_id: Target entity ID
            max_depth: Maximum path length

        Returns:
            List of entities in path (start to target) or None if no path found
        """
        try:
            logger.debug(f"[GraphQuery] Finding path from {start_entity_id} to {target_entity_id}")

            # BFS with path tracking
            queue = deque([(start_entity_id, [start_entity_id])])
            visited = set([start_entity_id])

            while queue:
                current_id, path = queue.popleft()

                if len(path) > max_depth:
                    continue

                if current_id == target_entity_id:
                    # Found path! Get entities
                    entities = []
                    for entity_id in path:
                        entity = self._get_entity(user_id, child_id, entity_id)
                        if entity:
                            entities.append(entity)
                    return entities

                # Get outgoing learning_pathway edges
                edges_ref = self.db.collection("users").document(user_id)\
                    .collection("children").document(child_id)\
                    .collection("edges")

                edges = list(edges_ref.where("edgeType", "==", "learning_pathway")\
                                      .where("sourceEntityId", "==", current_id).stream())

                for edge_doc in edges:
                    edge = edge_doc.to_dict()
                    next_id = edge['targetEntityId']

                    if next_id not in visited:
                        visited.add(next_id)
                        queue.append((next_id, path + [next_id]))

            logger.debug(f"[GraphQuery] No path found")
            return None

        except Exception as e:
            logger.error(f"[GraphQuery] Error finding path: {e}", exc_info=True)
            return None

    # Helper methods

    def _get_entity(self, user_id: str, child_id: str, entity_id: str) -> Optional[Dict]:
        """Get entity by ID"""
        try:
            entity_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("entities").document(entity_id)

            entity_doc = entity_ref.get()

            if entity_doc.exists:
                return entity_doc.to_dict()

            return None

        except Exception as e:
            logger.error(f"[GraphQuery] Error getting entity {entity_id}: {e}")
            return None

    def _get_entity_edges(self, user_id: str, child_id: str, entity_id: str,
                         edge_types: Optional[List[str]] = None,
                         min_weight: float = 0.0) -> List[Dict]:
        """
        Get all edges connected to an entity

        Since Firestore doesn't support OR queries, we need two separate queries
        """
        try:
            edges_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("edges")

            all_edges = []
            seen_ids = set()

            # Query 1: Edges where entity is source
            query1 = edges_ref.where("sourceEntityId", "==", entity_id)
            if min_weight > 0:
                query1 = query1.where("weight", ">=", min_weight)

            for edge_doc in query1.stream():
                edge = edge_doc.to_dict()
                if edge_types is None or edge['edgeType'] in edge_types:
                    if edge['id'] not in seen_ids:
                        all_edges.append(edge)
                        seen_ids.add(edge['id'])

            # Query 2: Edges where entity is target
            query2 = edges_ref.where("targetEntityId", "==", entity_id)
            if min_weight > 0:
                query2 = query2.where("weight", ">=", min_weight)

            for edge_doc in query2.stream():
                edge = edge_doc.to_dict()
                if edge_types is None or edge['edgeType'] in edge_types:
                    if edge['id'] not in seen_ids:
                        all_edges.append(edge)
                        seen_ids.add(edge['id'])

            return all_edges

        except Exception as e:
            logger.error(f"[GraphQuery] Error getting edges for {entity_id}: {e}")
            return []

    def _get_entities_by_types(self, user_id: str, child_id: str,
                               entity_types: List[str]) -> List[Dict]:
        """Get all entities of specified types"""
        try:
            entities_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("entities")

            all_entities = []

            for entity_type in entity_types:
                query = entities_ref.where("type", "==", entity_type)
                for doc in query.stream():
                    all_entities.append(doc.to_dict())

            return all_entities

        except Exception as e:
            logger.error(f"[GraphQuery] Error getting entities by type: {e}")
            return []
