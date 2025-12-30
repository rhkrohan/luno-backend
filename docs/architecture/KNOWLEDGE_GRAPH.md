# Knowledge Graph Service - Complete Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Model](#data-model)
4. [Entity Types & Taxonomy](#entity-types--taxonomy)
5. [Edge Types & Relationships](#edge-types--relationships)
6. [Graph Algorithms](#graph-algorithms)
7. [API Reference](#api-reference)
8. [Integration Guide](#integration-guide)
9. [Testing](#testing)
10. [Performance & Optimization](#performance--optimization)
11. [Migration](#migration)

---

## Overview

The **Knowledge Graph Service** is an AI-powered system that automatically extracts and structures knowledge from conversations between children and Luna (an AI companion). It builds rich, longitudinal learning profiles by tracking entities and their relationships over time.

### Key Capabilities

- **Automated Entity Extraction**: Uses GPT-4o-mini to extract 5 entity types from conversations
- **Relationship Mapping**: Tracks 3 types of relationships between entities
- **Temporal Tracking**: Monitors when entities are mentioned and how they evolve
- **Graph Algorithms**: BFS, DFS, clustering, and pathfinding for insight discovery
- **Personalization**: Powers adaptive learning experiences and parent dashboards

### Core Entity Types

1. **Topics** - Subjects discussed (e.g., "Dinosaurs", "Solar System")
2. **Skills** - Demonstrated abilities (e.g., "Counting to 20", "Rhyming")
3. **Interests** - Enthusiasms and engagement patterns (e.g., "Space exploration")
4. **Concepts** - Abstract understanding (e.g., "Extinction", "Gravity")
5. **Personality Traits** - Character attributes (e.g., "Curious", "Creative")

### Core Relationship Types

1. **Temporal Co-occurrence** - Entities discussed together
2. **Learning Pathways** - Prerequisites and skill progression
3. **Emotional Associations** - Emotions connected to topics/interests

---

## Architecture

### Processing Flow

```
┌─────────────────────────────────────────────────────┐
│         Conversation Processing Flow                │
├─────────────────────────────────────────────────────┤
│                                                       │
│  1. Conversation Ends                               │
│         ↓                                            │
│  2. extract_and_store() called with messages        │
│         ↓                                            │
│  3. LLM EXTRACTION (GPT-4o-mini)                    │
│     • Analyze conversation context                  │
│     • Extract entities (confidence ≥ 0.7)          │
│     • Extract relationships between entities        │
│         ↓                                            │
│  4. ENTITY STORAGE (Firestore)                      │
│     • Create/Update 5-50 entity documents          │
│     • Track edge statistics on each entity         │
│         ↓                                            │
│  5. EDGE STORAGE (Firestore)                        │
│     • Create/Update relationship edges             │
│     • Calculate moving average weights             │
│         ↓                                            │
│  6. OBSERVATION LOG (Immutable)                     │
│     • Record what was observed this conversation   │
│         ↓                                            │
│  7. SUMMARY UPDATE (Aggregate stats)                │
│     • Count entities by type                        │
│     • Top topics, skills, interests                │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### System Components

#### 1. Knowledge Graph Service (`knowledge_graph_service.py`)
**Location**: `/home/ec2-user/backend/knowledge_graph_service.py` (1,046 lines)

Main service for entity extraction and graph management.

**Key Methods**:
- `extract_and_store()` - Main extraction pipeline
- `get_summary()` - Retrieve aggregate statistics
- `get_entities()` - Query entities with filtering

#### 2. Graph Query Service (`graph_query_service.py`)
**Location**: `/home/ec2-user/backend/graph_query_service.py` (537 lines)

Graph algorithms and traversal operations.

**Key Methods**:
- `get_related_entities()` - BFS traversal
- `find_interest_clusters()` - Cluster detection
- `get_prerequisite_chain()` - Learning pathway traversal
- `find_learning_path()` - Shortest path finding

#### 3. Integration (`app.py`)
**Location**: `/home/ec2-user/backend/app.py`

REST API endpoints for accessing the knowledge graph.

---

## Data Model

### Firestore Schema

**Important Note:** Knowledge graph data (entities, edges, observations) is stored under `/users/{userId}/children/{childId}/`, while conversations are stored at `/users/{userId}/conversations/`. This separation allows knowledge to be child-specific while conversations can reference any child via a `childId` field.

```
/users/{userId}
  └── /children/{childId}
        ├── /entities/{entityId}
        │     ├── Core Fields
        │     │   ├── id: string (e.g., "topic_dinosaurs")
        │     │   ├── type: string (topic|skill|interest|concept|personality_trait)
        │     │   ├── name: string (e.g., "Dinosaurs")
        │     │   └── aliases: string[] (alternative names)
        │     │
        │     ├── Temporal Tracking
        │     │   ├── firstMentionedAt: timestamp
        │     │   ├── lastMentionedAt: timestamp
        │     │   ├── mentionCount: number (total mentions)
        │     │   └── conversationCount: number (distinct conversations)
        │     │
        │     ├── Strength & Confidence
        │     │   ├── strength: number (0-1, normalized by frequency)
        │     │   └── confidence: number (0-1, extraction confidence)
        │     │
        │     ├── Type-Specific Attributes
        │     │   ├── attributes.category: string
        │     │   ├── attributes.subcategory: string
        │     │   ├── attributes.level: string (for skills)
        │     │   ├── attributes.intensity: string (for interests)
        │     │   └── ... (varies by entity type)
        │     │
        │     ├── Relationship Data
        │     │   ├── relatedEntities: object[] (top connections)
        │     │   ├── edgeStats.totalEdges: number
        │     │   ├── edgeStats.incomingEdges: number
        │     │   ├── edgeStats.outgoingEdges: number
        │     │   ├── edgeStats.edgeTypeCounts: object
        │     │   └── edgeStats.topConnections: object[]
        │     │
        │     ├── Developmental Tracking
        │     │   ├── developmentalMilestones: object[]
        │     │   ├── emotionalMoments: object[]
        │     │   └── recentObservations: object[] (last 5)
        │     │
        │     └── Graph Metrics
        │         ├── clusterId: string
        │         ├── clusterLabel: string
        │         ├── centrality: number (importance score)
        │         └── lastGraphUpdateAt: timestamp
        │
        ├── /edges/{edgeId}
        │     ├── Core Fields
        │     │   ├── id: string (auto-generated)
        │     │   ├── edgeType: string (temporal_cooccurrence|learning_pathway|emotional_association)
        │     │   ├── sourceEntityId: string
        │     │   ├── sourceEntityType: string
        │     │   ├── sourceEntityName: string
        │     │   ├── targetEntityId: string
        │     │   ├── targetEntityType: string
        │     │   └── targetEntityName: string
        │     │
        │     ├── Weight & Confidence
        │     │   ├── weight: number (moving average of confidence scores)
        │     │   ├── confidence: number (latest extraction confidence)
        │     │   └── observationCount: number (times observed)
        │     │
        │     ├── Temporal Data
        │     │   ├── firstObservedAt: timestamp
        │     │   ├── lastObservedAt: timestamp
        │     │   └── conversationIds: string[] (last 10)
        │     │
        │     ├── Evidence
        │     │   └── evidenceSnippets: string[] (last 3 conversation excerpts)
        │     │
        │     ├── Type-Specific Attributes
        │     │   ├── attributes.cooccurrenceFrequency: number (for temporal)
        │     │   ├── attributes.timeProximity: string (for temporal)
        │     │   ├── attributes.prerequisite: boolean (for learning_pathway)
        │     │   ├── attributes.difficulty: string (for learning_pathway)
        │     │   ├── attributes.emotion: string (for emotional_association)
        │     │   └── attributes.intensity: string (for emotional_association)
        │     │
        │     └── Status
        │         ├── status: string (active|inactive)
        │         ├── createdAt: timestamp
        │         └── updatedAt: timestamp
        │
        ├── /observations/{observationId}
        │     ├── id: string (auto-generated)
        │     ├── conversationId: string
        │     ├── timestamp: timestamp
        │     ├── entities: object[] (all entities observed)
        │     ├── conversationType: string
        │     ├── messageCount: number
        │     ├── extractedAt: timestamp
        │     └── extractionVersion: string
        │
        └── /knowledgeGraph/
              ├── summary
              │     ├── stats.totalEntities: number
              │     ├── stats.totalTopics: number
              │     ├── stats.totalSkills: number
              │     ├── stats.totalInterests: number
              │     ├── stats.totalConcepts: number
              │     ├── stats.totalPersonalityTraits: number
              │     ├── topTopics: object[] (top 10)
              │     ├── topSkills: object[] (top 10)
              │     ├── topInterests: object[] (top 10)
              │     ├── learningProfile: object
              │     └── lastUpdatedAt: timestamp
              │
              └── graphMetadata
                    ├── totalNodes: number
                    ├── totalEdges: number
                    ├── edgeTypeCounts: object
                    ├── graphDensity: number
                    ├── averageNodeDegree: number
                    ├── clusters: object[]
                    ├── topCentralNodes: object[]
                    └── lastUpdatedAt: timestamp
```

---

## Entity Types & Taxonomy

### 1. TOPICS

Subjects and domains discussed in conversations.

**Categories**:
- `science_nature` - Natural world, animals, plants, weather
- `mathematics` - Numbers, counting, shapes, patterns
- `language_literacy` - Reading, writing, storytelling
- `arts_creativity` - Music, art, dance, crafts
- `social_emotional` - Feelings, friendships, family
- `everyday_life` - Daily routines, places, objects

**Example Entities**:
```json
{
  "id": "topic_dinosaurs",
  "type": "topic",
  "name": "Dinosaurs",
  "attributes": {
    "category": "science_nature",
    "subcategory": "prehistoric_life"
  },
  "strength": 0.85,
  "mentionCount": 12,
  "conversationCount": 4
}
```

### 2. SKILLS

Demonstrated abilities and developmental milestones.

**Categories**:
- `cognitive` - Problem-solving, memory, reasoning
- `language_communication` - Speaking, listening, vocabulary
- `literacy_numeracy` - Reading, writing, counting, math
- `social_emotional` - Empathy, self-regulation, cooperation
- `creative_thinking` - Imagination, innovation, artistic expression
- `executive_function` - Planning, focus, self-control

**Skill Levels**:
- `emerging` - Just starting to develop
- `developing` - Actively practicing
- `proficient` - Consistently demonstrated
- `advanced` - Above age-level expectation

**Example Entities**:
```json
{
  "id": "skill_counting_to_20",
  "type": "skill",
  "name": "Counting to 20",
  "attributes": {
    "category": "literacy_numeracy",
    "subcategory": "number_sense",
    "level": "proficient"
  },
  "developmentalMilestones": [
    {
      "achieved": true,
      "timestamp": "2024-01-15T10:30:00Z",
      "context": "Successfully counted dinosaur toys"
    }
  ]
}
```

### 3. INTERESTS

Areas of enthusiasm and sustained engagement.

**Categories**:
- `science_exploration` - Nature, experiments, discovery
- `creative` - Art, music, building, crafting
- `physical_active` - Sports, movement, outdoor activities
- `intellectual` - Puzzles, reading, learning
- `social_interactive` - Playing with others, teamwork
- `fantasy_imagination` - Pretend play, storytelling

**Intensity Levels**:
- `casual` - Occasional interest
- `moderate` - Regular engagement
- `strong` - Frequent enthusiasm
- `passionate` - Deep, sustained fascination

**Example Entities**:
```json
{
  "id": "interest_space_exploration",
  "type": "interest",
  "name": "Space Exploration",
  "attributes": {
    "category": "science_exploration",
    "subcategory": "astronomy",
    "intensity": "passionate"
  },
  "emotionalMoments": [
    {
      "emotion": "excitement",
      "intensity": "high",
      "timestamp": "2024-02-10T14:20:00Z",
      "context": "Asked 15 questions about planets"
    }
  ]
}
```

### 4. CONCEPTS

Abstract ideas and cognitive understanding.

**Categories**:
- `cognitive_development` - Cause-effect, classification, logic
- `time_sequence` - Past/present/future, order, duration
- `spatial_reasoning` - Size, distance, position, direction
- `social_emotional_concepts` - Fairness, kindness, sharing
- `abstract_thinking` - Hypotheticals, imagination, symbolism
- `moral_reasoning` - Right/wrong, consequences, empathy

**Example Entities**:
```json
{
  "id": "concept_extinction",
  "type": "concept",
  "name": "Extinction",
  "attributes": {
    "category": "cognitive_development",
    "subcategory": "cause_and_effect"
  },
  "recentObservations": [
    {
      "conversationId": "conv_123",
      "timestamp": "2024-01-20T09:15:00Z",
      "context": "Understood that dinosaurs died out long ago"
    }
  ]
}
```

### 5. PERSONALITY_TRAITS

Character attributes and behavioral tendencies.

**Categories**:
- `emotional_intelligence` - Self-awareness, empathy, regulation
- `cognitive_traits` - Curiosity, persistence, creativity
- `social_behavioral` - Cooperation, leadership, independence
- `temperament` - Energy level, adaptability, mood
- `learning_style` - Visual, auditory, kinesthetic preferences

**Example Entities**:
```json
{
  "id": "personality_trait_curious",
  "type": "personality_trait",
  "name": "Curious",
  "attributes": {
    "category": "cognitive_traits",
    "subcategory": "intellectual_curiosity"
  },
  "strength": 0.92,
  "recentObservations": [
    {
      "conversationId": "conv_456",
      "timestamp": "2024-02-05T11:30:00Z",
      "context": "Asked 'why' questions about how dinosaurs became extinct"
    }
  ]
}
```

---

## Edge Types & Relationships

### 1. TEMPORAL_COOCCURRENCE

Entities that appear together in conversations, indicating conceptual relationships.

**Characteristics**:
- Bidirectional (symmetric relationship)
- Weight-based (frequency of co-occurrence)
- Tracks conversation context

**Attributes**:
```json
{
  "edgeType": "temporal_cooccurrence",
  "sourceEntityId": "topic_dinosaurs",
  "targetEntityId": "concept_extinction",
  "weight": 0.78,
  "observationCount": 5,
  "attributes": {
    "cooccurrenceFrequency": "high",
    "timeProximity": "same_conversation"
  },
  "evidenceSnippets": [
    "We talked about how dinosaurs became extinct millions of years ago",
    "Child asked why dinosaurs aren't around anymore"
  ]
}
```

### 2. LEARNING_PATHWAY

Prerequisite skills and learning progressions.

**Characteristics**:
- Directional (source enables target)
- Represents skill dependencies
- Tracks mastery requirements

**Attributes**:
```json
{
  "edgeType": "learning_pathway",
  "sourceEntityId": "skill_counting_to_10",
  "targetEntityId": "skill_counting_to_20",
  "weight": 0.85,
  "attributes": {
    "prerequisite": true,
    "difficulty": "moderate",
    "masteryRequired": 0.7
  }
}
```

### 3. EMOTIONAL_ASSOCIATION

Emotions connected to topics or interests.

**Characteristics**:
- Directional (emotion → topic/interest)
- Tracks emotional engagement
- Measures intensity and valence

**Attributes**:
```json
{
  "edgeType": "emotional_association",
  "sourceEntityId": "personality_trait_excited",
  "targetEntityId": "interest_space_exploration",
  "weight": 0.90,
  "attributes": {
    "emotion": "excitement",
    "intensity": "high",
    "valence": "positive"
  }
}
```

---

## Graph Algorithms

### 1. Related Entities (BFS Traversal)

**Method**: `get_related_entities(user_id, child_id, entity_id, max_depth=2, edge_types=None, min_weight=0.0)`

**Algorithm**: Breadth-First Search (BFS)

**Purpose**: Find all entities connected to a starting entity within a certain depth.

**Use Cases**:
- Discovering related concepts for conversation context
- Building topic clusters for recommendations
- Understanding knowledge connections

**Example**:
```python
# Find entities related to "Dinosaurs" within 2 steps
related = graph_query_service.get_related_entities(
    user_id="user_123",
    child_id="child_456",
    entity_id="topic_dinosaurs",
    max_depth=2,
    edge_types=["temporal_cooccurrence"],
    min_weight=0.5
)

# Returns: ["concept_extinction", "topic_fossils", "skill_asking_why_questions"]
```

**Implementation Details**:
- Maintains visited set to prevent cycles
- Tracks depth for each entity
- Filters by edge types and minimum weight
- Returns entities sorted by connection strength

---

### 2. Entity Neighbors

**Method**: `get_entity_neighbors(user_id, child_id, entity_id, edge_type=None, direction="both")`

**Purpose**: Get immediate neighbors (1-hop connections) of an entity.

**Parameters**:
- `direction`: "outgoing", "incoming", or "both"
- `edge_type`: Filter by specific relationship type

**Use Cases**:
- Finding direct prerequisites for a skill
- Identifying co-occurring topics
- Listing emotional associations

**Example**:
```python
# Find all skills that require "Counting to 10" as a prerequisite
neighbors = graph_query_service.get_entity_neighbors(
    user_id="user_123",
    child_id="child_456",
    entity_id="skill_counting_to_10",
    edge_type="learning_pathway",
    direction="outgoing"
)
```

---

### 3. Interest Clusters (DFS + Connected Components)

**Method**: `find_interest_clusters(user_id, child_id, min_cluster_size=2)`

**Algorithm**: Depth-First Search (DFS) for connected component detection

**Purpose**: Discover groups of related interests that form thematic clusters.

**Use Cases**:
- Identifying dominant interest themes
- Personalizing content recommendations
- Understanding engagement patterns

**Example**:
```python
# Find interest clusters
clusters = graph_query_service.find_interest_clusters(
    user_id="user_123",
    child_id="child_456",
    min_cluster_size=3
)

# Returns:
# [
#   {
#     "clusterId": "cluster_science",
#     "label": "Science Exploration",
#     "entities": ["interest_space", "interest_dinosaurs", "interest_experiments"],
#     "size": 3
#   }
# ]
```

**Implementation Details**:
- Uses DFS to traverse interest networks
- Groups strongly connected interests
- Labels clusters based on category
- Filters out small clusters

---

### 4. Context Subgraph Extraction

**Method**: `extract_context_subgraph(user_id, child_id, entity_ids, max_depth=1)`

**Purpose**: Extract a relevant subgraph around specified entities for LLM context.

**Use Cases**:
- Providing conversation context to Luna
- Generating personalized learning content
- Understanding knowledge areas

**Example**:
```python
# Extract context around recent topics
subgraph = graph_query_service.extract_context_subgraph(
    user_id="user_123",
    child_id="child_456",
    entity_ids=["topic_dinosaurs", "interest_science"],
    max_depth=1
)

# Returns nodes and edges for the subgraph
```

---

### 5. Prerequisite Chain

**Method**: `get_prerequisite_chain(user_id, child_id, skill_entity_id)`

**Purpose**: Get ordered list of prerequisite skills by following learning pathways.

**Use Cases**:
- Identifying skill gaps
- Planning learning sequences
- Assessing developmental readiness

**Example**:
```python
# Find prerequisites for "Addition with carrying"
chain = graph_query_service.get_prerequisite_chain(
    user_id="user_123",
    child_id="child_456",
    skill_entity_id="skill_addition_carrying"
)

# Returns: [
#   "skill_counting_to_20",
#   "skill_basic_addition",
#   "skill_place_value",
#   "skill_addition_carrying"
# ]
```

---

### 6. Learning Path Finding

**Method**: `find_learning_path(user_id, child_id, start_skill_id, target_skill_id)`

**Algorithm**: Shortest path using BFS on learning_pathway edges

**Purpose**: Find the shortest learning progression between two skills.

**Use Cases**:
- Creating personalized learning plans
- Identifying skill dependencies
- Sequencing educational content

**Example**:
```python
# Find path from current skill to target skill
path = graph_query_service.find_learning_path(
    user_id="user_123",
    child_id="child_456",
    start_skill_id="skill_counting_to_10",
    target_skill_id="skill_multiplication"
)

# Returns: [
#   "skill_counting_to_10",
#   "skill_counting_to_20",
#   "skill_skip_counting",
#   "skill_repeated_addition",
#   "skill_multiplication"
# ]
```

---

## API Reference

### REST Endpoints

All endpoints are prefixed with `/api/knowledge-graph`

#### 1. Get Summary

**Endpoint**: `GET /api/knowledge-graph/summary`

**Description**: Retrieve aggregate statistics about a child's knowledge graph.

**Query Parameters**:
- `user_id` (required): User ID
- `child_id` (required): Child ID

**Response**:
```json
{
  "stats": {
    "totalEntities": 127,
    "totalTopics": 45,
    "totalSkills": 32,
    "totalInterests": 18,
    "totalConcepts": 25,
    "totalPersonalityTraits": 7
  },
  "topTopics": [
    {
      "id": "topic_dinosaurs",
      "name": "Dinosaurs",
      "strength": 0.85,
      "conversationCount": 12
    }
  ],
  "topSkills": [...],
  "topInterests": [...],
  "learningProfile": {
    "dominantCategories": ["science_nature", "mathematics"],
    "emergingSkills": 8,
    "proficientSkills": 15
  },
  "lastUpdatedAt": "2024-03-15T10:30:00Z"
}
```

---

#### 2. Query Entities

**Endpoint**: `GET /api/knowledge-graph/entities`

**Description**: Query entities with filtering and sorting.

**Query Parameters**:
- `user_id` (required): User ID
- `child_id` (required): Child ID
- `type` (optional): Filter by entity type (topic|skill|interest|concept|personality_trait)
- `category` (optional): Filter by category
- `limit` (optional): Maximum number of results (default: 50)
- `orderBy` (optional): Sort field (strength|mentionCount|lastMentionedAt)

**Response**:
```json
{
  "entities": [
    {
      "id": "topic_dinosaurs",
      "type": "topic",
      "name": "Dinosaurs",
      "attributes": {
        "category": "science_nature",
        "subcategory": "prehistoric_life"
      },
      "strength": 0.85,
      "mentionCount": 12,
      "conversationCount": 4,
      "firstMentionedAt": "2024-01-10T09:00:00Z",
      "lastMentionedAt": "2024-03-12T14:30:00Z",
      "edgeStats": {
        "totalEdges": 8,
        "topConnections": [
          {"entityId": "concept_extinction", "weight": 0.78}
        ]
      }
    }
  ],
  "total": 45
}
```

---

#### 3. Get Visualization Data

**Endpoint**: `GET /api/knowledge-graph/visualization`

**Description**: Get graph data formatted for visualization (nodes and edges).

**Query Parameters**:
- `user_id` (required): User ID
- `child_id` (required): Child ID
- `entity_types` (optional): Comma-separated entity types to include
- `min_weight` (optional): Minimum edge weight (default: 0.3)
- `max_nodes` (optional): Maximum nodes to return (default: 100)

**Response**:
```json
{
  "nodes": [
    {
      "id": "topic_dinosaurs",
      "label": "Dinosaurs",
      "type": "topic",
      "category": "science_nature",
      "strength": 0.85,
      "centrality": 0.72
    }
  ],
  "edges": [
    {
      "id": "edge_123",
      "source": "topic_dinosaurs",
      "target": "concept_extinction",
      "type": "temporal_cooccurrence",
      "weight": 0.78
    }
  ],
  "clusters": [
    {
      "id": "cluster_science",
      "label": "Science Exploration",
      "nodeIds": ["topic_dinosaurs", "interest_space", "concept_gravity"]
    }
  ]
}
```

---

#### 4. Get Related Entities

**Endpoint**: `GET /api/knowledge-graph/{entityId}/related`

**Description**: Find entities related to a specific entity using BFS traversal.

**Path Parameters**:
- `entityId`: Entity ID to start from

**Query Parameters**:
- `user_id` (required): User ID
- `child_id` (required): Child ID
- `max_depth` (optional): Maximum traversal depth (default: 2)
- `edge_types` (optional): Comma-separated edge types
- `min_weight` (optional): Minimum edge weight (default: 0.0)

**Response**:
```json
{
  "entityId": "topic_dinosaurs",
  "relatedEntities": [
    {
      "id": "concept_extinction",
      "name": "Extinction",
      "type": "concept",
      "depth": 1,
      "connectionStrength": 0.78
    },
    {
      "id": "topic_fossils",
      "name": "Fossils",
      "type": "topic",
      "depth": 2,
      "connectionStrength": 0.65
    }
  ]
}
```

---

#### 5. Find Interest Clusters

**Endpoint**: `GET /api/knowledge-graph/clusters`

**Description**: Discover clusters of related interests.

**Query Parameters**:
- `user_id` (required): User ID
- `child_id` (required): Child ID
- `min_cluster_size` (optional): Minimum entities per cluster (default: 2)

**Response**:
```json
{
  "clusters": [
    {
      "clusterId": "cluster_science",
      "label": "Science Exploration",
      "entities": [
        {
          "id": "interest_space",
          "name": "Space Exploration"
        },
        {
          "id": "interest_dinosaurs",
          "name": "Dinosaurs"
        },
        {
          "id": "interest_experiments",
          "name": "Science Experiments"
        }
      ],
      "size": 3,
      "dominantCategory": "science_exploration"
    }
  ]
}
```

---

### Python Service Methods

#### KnowledgeGraphService

**Location**: `knowledge_graph_service.py`

##### extract_and_store()

```python
def extract_and_store(
    self,
    user_id: str,
    conversation_id: str,
    child_id: str,
    messages: List[Dict]
) -> Dict:
    """
    Extract entities and relationships from a conversation and store them.

    Args:
        user_id: User ID
        conversation_id: Conversation ID
        child_id: Child ID
        messages: List of conversation messages

    Returns:
        Dictionary with extraction results:
        {
            "entities_extracted": 12,
            "edges_created": 8,
            "observation_id": "obs_123"
        }
    """
```

**Usage**:
```python
kg_service = KnowledgeGraphService()
result = kg_service.extract_and_store(
    user_id="user_123",
    conversation_id="conv_456",
    child_id="child_789",
    messages=[
        {"role": "user", "content": "Tell me about dinosaurs!"},
        {"role": "assistant", "content": "Dinosaurs were amazing creatures..."}
    ]
)
```

---

##### get_summary()

```python
def get_summary(self, user_id: str, child_id: str) -> Dict:
    """
    Get aggregate knowledge graph statistics.

    Args:
        user_id: User ID
        child_id: Child ID

    Returns:
        Dictionary with summary statistics
    """
```

---

##### get_entities()

```python
def get_entities(
    self,
    user_id: str,
    child_id: str,
    entity_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    order_by: str = "strength"
) -> List[Dict]:
    """
    Query entities with filtering and sorting.

    Args:
        user_id: User ID
        child_id: Child ID
        entity_type: Filter by type (optional)
        category: Filter by category (optional)
        limit: Maximum results
        order_by: Sort field (strength|mentionCount|lastMentionedAt)

    Returns:
        List of entity dictionaries
    """
```

---

#### GraphQueryService

**Location**: `graph_query_service.py`

##### get_related_entities()

```python
def get_related_entities(
    self,
    user_id: str,
    child_id: str,
    entity_id: str,
    max_depth: int = 2,
    edge_types: Optional[List[str]] = None,
    min_weight: float = 0.0
) -> List[Dict]:
    """
    Find entities related to a starting entity using BFS.

    Args:
        user_id: User ID
        child_id: Child ID
        entity_id: Starting entity ID
        max_depth: Maximum traversal depth
        edge_types: Filter by edge types
        min_weight: Minimum edge weight

    Returns:
        List of related entities with connection details
    """
```

---

##### find_interest_clusters()

```python
def find_interest_clusters(
    self,
    user_id: str,
    child_id: str,
    min_cluster_size: int = 2
) -> List[Dict]:
    """
    Detect clusters of related interests using DFS.

    Args:
        user_id: User ID
        child_id: Child ID
        min_cluster_size: Minimum entities per cluster

    Returns:
        List of cluster objects
    """
```

---

##### get_prerequisite_chain()

```python
def get_prerequisite_chain(
    self,
    user_id: str,
    child_id: str,
    skill_entity_id: str
) -> List[str]:
    """
    Get ordered list of prerequisite skills.

    Args:
        user_id: User ID
        child_id: Child ID
        skill_entity_id: Target skill entity ID

    Returns:
        Ordered list of skill entity IDs (prerequisites first)
    """
```

---

##### find_learning_path()

```python
def find_learning_path(
    self,
    user_id: str,
    child_id: str,
    start_skill_id: str,
    target_skill_id: str
) -> List[str]:
    """
    Find shortest learning path between two skills.

    Args:
        user_id: User ID
        child_id: Child ID
        start_skill_id: Starting skill entity ID
        target_skill_id: Target skill entity ID

    Returns:
        Ordered list of skill IDs forming the path
    """
```

---

## Integration Guide

### 1. Post-Conversation Extraction

**When**: After a conversation with Luna ends

**How**: Call `extract_and_store()` with the conversation messages

**Example Integration** (in `app.py`):

```python
from knowledge_graph_service import KnowledgeGraphService

kg_service = KnowledgeGraphService()

@app.route('/api/conversations/<conversation_id>/complete', methods=['POST'])
def complete_conversation(conversation_id):
    # Get conversation data
    conversation = get_conversation(conversation_id)

    # Extract knowledge graph entities
    try:
        result = kg_service.extract_and_store(
            user_id=conversation['user_id'],
            conversation_id=conversation_id,
            child_id=conversation['child_id'],
            messages=conversation['messages']
        )

        print(f"Extracted {result['entities_extracted']} entities")
        print(f"Created {result['edges_created']} edges")

    except Exception as e:
        print(f"Knowledge graph extraction failed: {e}")
        # Don't block conversation completion on KG failure

    return {"status": "completed"}
```

---

### 2. Conversation Context Enrichment

**When**: Before starting a new conversation

**How**: Query relevant entities to provide context to Luna

**Example**:

```python
from graph_query_service import GraphQueryService

graph_service = GraphQueryService()

@app.route('/api/conversations/start', methods=['POST'])
def start_conversation():
    data = request.json
    user_id = data['user_id']
    child_id = data['child_id']

    # Get recent topics
    recent_topics = kg_service.get_entities(
        user_id=user_id,
        child_id=child_id,
        entity_type="topic",
        limit=5,
        order_by="lastMentionedAt"
    )

    # Get top interests
    top_interests = kg_service.get_entities(
        user_id=user_id,
        child_id=child_id,
        entity_type="interest",
        limit=3,
        order_by="strength"
    )

    # Build context for Luna
    context = {
        "recent_topics": [t['name'] for t in recent_topics],
        "interests": [i['name'] for i in top_interests]
    }

    # Include in system prompt or conversation metadata
    return {
        "conversation_id": "conv_new",
        "context": context
    }
```

---

### 3. Parent Dashboard

**When**: User views their child's learning profile

**How**: Display knowledge graph insights

**Example**:

```python
@app.route('/api/dashboard/child/<child_id>', methods=['GET'])
def get_child_dashboard(child_id):
    user_id = request.args.get('user_id')

    # Get summary
    summary = kg_service.get_summary(user_id, child_id)

    # Find interest clusters
    clusters = graph_service.find_interest_clusters(
        user_id, child_id, min_cluster_size=2
    )

    # Get emerging skills
    emerging_skills = kg_service.get_entities(
        user_id=user_id,
        child_id=child_id,
        entity_type="skill",
        category="emerging",
        limit=10
    )

    return {
        "summary": summary,
        "interest_clusters": clusters,
        "emerging_skills": emerging_skills
    }
```

---

### 4. Personalized Recommendations

**When**: Suggesting next activities or topics

**How**: Use graph traversal to find related content

**Example**:

```python
@app.route('/api/recommendations/<child_id>', methods=['GET'])
def get_recommendations(child_id):
    user_id = request.args.get('user_id')

    # Get top interests
    interests = kg_service.get_entities(
        user_id, child_id, entity_type="interest", limit=3
    )

    recommendations = []
    for interest in interests:
        # Find related topics not yet explored
        related = graph_service.get_related_entities(
            user_id=user_id,
            child_id=child_id,
            entity_id=interest['id'],
            max_depth=2,
            edge_types=["temporal_cooccurrence"]
        )

        # Filter to unexplored topics
        unexplored = [
            r for r in related
            if r['type'] == 'topic' and r['mentionCount'] < 2
        ]

        recommendations.extend(unexplored)

    return {"recommendations": recommendations[:10]}
```

---

## Testing

### Test Script

**Location**: `/home/ec2-user/backend/test_knowledge_graph.py`

**Purpose**: End-to-end testing of knowledge graph extraction and querying

**Run**:
```bash
python test_knowledge_graph.py
```

**What It Tests**:
1. Entity extraction from sample conversation
2. Observation logging
3. Summary generation
4. Entity querying
5. Data cleanup

**Sample Test Conversation**:
```python
messages = [
    {
        "role": "user",
        "content": "I love dinosaurs! My favorite is T-Rex. Can you count with me?"
    },
    {
        "role": "assistant",
        "content": "That's wonderful! T-Rex is amazing. Let's count: 1, 2, 3..."
    },
    {
        "role": "user",
        "content": "1, 2, 3, 4, 5... up to 20! Why did dinosaurs disappear?"
    }
]
```

**Expected Extractions**:
- **Topics**: Dinosaurs, T-Rex, Counting
- **Skills**: Counting to 20, Asking Why Questions
- **Interests**: Dinosaurs, Science Exploration
- **Concepts**: Extinction
- **Personality Traits**: Curious

---

### Manual Testing

#### 1. Test Entity Extraction

```bash
curl -X POST http://localhost:5000/api/test/extract \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "child_id": "test_child",
    "conversation_id": "test_conv_1",
    "messages": [
      {"role": "user", "content": "Let'\''s talk about space!"},
      {"role": "assistant", "content": "Space is fascinating! What do you want to know?"}
    ]
  }'
```

#### 2. Test Summary Retrieval

```bash
curl "http://localhost:5000/api/knowledge-graph/summary?user_id=test_user&child_id=test_child"
```

#### 3. Test Entity Query

```bash
curl "http://localhost:5000/api/knowledge-graph/entities?user_id=test_user&child_id=test_child&type=topic&limit=10"
```

#### 4. Test Related Entities

```bash
curl "http://localhost:5000/api/knowledge-graph/topic_dinosaurs/related?user_id=test_user&child_id=test_child&max_depth=2"
```

---

## Performance & Optimization

### Token Cost Analysis

**LLM**: GPT-4o-mini

**Cost per Extraction**:
- Input tokens: ~2,500-4,000 (conversation + prompt + taxonomy)
- Output tokens: ~500-1,500 (JSON entities + relationships)
- **Estimated cost**: $0.0002-0.0006 per conversation

**Monthly Cost Estimate**:
- 1,000 conversations/month = $0.20-$0.60/month per child
- 10,000 conversations/month = $2.00-$6.00/month per child

---

### Firestore Operations

**Reads per Extraction**:
- 1 child profile read
- ~5-15 entity existence checks
- Total: ~6-16 reads

**Writes per Extraction**:
- ~5-15 entity writes (create or update)
- ~8-25 edge writes
- 1 observation write
- ~50+ reads for summary update (iterates all entities)
- Total: ~14-41 writes, ~50+ reads for summary

**Optimization Opportunities**:
1. **Batch Entity Checks**: Reduce existence checks with in-memory caching
2. **Incremental Summaries**: Use counters instead of full iteration
3. **Lazy Edge Creation**: Only create edges above weight threshold
4. **Async Processing**: Process extraction in background queue

---

### Latency Profile

**End-to-End Extraction**:
- LLM call: 1-3 seconds
- Entity processing: 1-2 seconds
- Edge processing: 1-2 seconds
- Summary update: 0.5-1 second
- **Total**: 3-8 seconds

**Optimization Strategies**:
1. **Async Extraction**: Don't block conversation completion
2. **Parallel Writes**: Batch Firestore operations
3. **Selective Updates**: Only update changed entities
4. **Summary Caching**: Update summary every N extractions

---

### Confidence Threshold

**Current**: 0.7 minimum confidence

**Impact**:
- Filters out ~30-40% of low-quality extractions
- Reduces false positives
- Decreases Firestore writes

**Tuning**:
- Lower threshold (0.5): More entities, more noise
- Higher threshold (0.8): Fewer entities, higher precision

---

### Moving Average Weights

**Purpose**: Smooth edge weights over multiple observations

**Formula**:
```
new_weight = (old_weight * observation_count + new_confidence) / (observation_count + 1)
```

**Benefits**:
- Reduces impact of outlier extractions
- Stabilizes relationship strengths over time
- Prevents weight oscillation

---

### Scaling Considerations

**Current Limits**:
- ~200 entities per child (after 50+ conversations)
- ~500 edges per child
- ~100 observations per child

**At Scale (1000 conversations)**:
- ~500-1000 entities
- ~2000-5000 edges
- ~1000 observations

**Potential Bottlenecks**:
1. Summary generation (iterates all entities)
2. Cluster detection (graph traversal)
3. Edge queries (dual query for bidirectional edges)

**Solutions**:
1. Materialized summaries with incremental updates
2. Pre-computed clusters stored in graphMetadata
3. Denormalized edge data on entities

---

## Migration

### Schema Migration Script

**Location**: `/home/ec2-user/backend/scripts/migrate_to_graph_schema.py`

**Purpose**: Add graph-specific fields to existing entities

**Run**:
```bash
# Dry run (preview changes)
python scripts/migrate_to_graph_schema.py --dry-run

# Migrate specific child
python scripts/migrate_to_graph_schema.py --child-id child_123

# Migrate all children for a user
python scripts/migrate_to_graph_schema.py --user-id user_456

# Migrate all (production use with caution!)
python scripts/migrate_to_graph_schema.py
```

**What It Adds**:

1. **edgeStats** to all entities:
   ```python
   {
     "totalEdges": 0,
     "incomingEdges": 0,
     "outgoingEdges": 0,
     "edgeTypeCounts": {},
     "topConnections": []
   }
   ```

2. **Graph metrics**:
   ```python
   {
     "clusterId": null,
     "clusterLabel": null,
     "centrality": 0.0,
     "lastGraphUpdateAt": null
   }
   ```

3. **graphMetadata** document:
   ```python
   {
     "totalNodes": 0,
     "totalEdges": 0,
     "edgeTypeCounts": {},
     "graphDensity": 0.0,
     "averageNodeDegree": 0.0,
     "clusters": [],
     "topCentralNodes": []
   }
   ```

---

### Backfilling Observations

If you have historical conversations without observations:

```python
from knowledge_graph_service import KnowledgeGraphService

kg_service = KnowledgeGraphService()

# Get historical conversations
conversations = get_all_conversations(user_id, child_id)

for conv in conversations:
    # Re-extract entities
    kg_service.extract_and_store(
        user_id=user_id,
        conversation_id=conv['id'],
        child_id=child_id,
        messages=conv['messages']
    )

    print(f"Processed conversation {conv['id']}")
```

---

## Future Enhancements

### Planned Features

- [ ] **Alias Matching**: Deduplicate entities with different names (e.g., "T-Rex" → "Tyrannosaurus Rex")
- [ ] **Sentiment Analysis**: Track emotional valence for all entities
- [ ] **Incremental Summary Updates**: Use counters instead of full iteration
- [ ] **Multi-language Support**: Extract entities from non-English conversations
- [ ] **Learning Style Detection**: Identify visual/auditory/kinesthetic preferences
- [ ] **Content Recommendations**: Suggest books, videos, activities based on graph
- [ ] **Parent Dashboard Visualizations**: Interactive graph visualizations
- [ ] **Privacy Controls**: Allow parents to blacklist sensitive topics
- [ ] **Export & Reporting**: Generate PDF/CSV reports of learning progress
- [ ] **Collaborative Filtering**: Compare learning profiles across children (anonymized)

### Research Directions

- **Graph Neural Networks**: Predict next interests or skill acquisitions
- **Temporal Analysis**: Track how interests evolve over time
- **Knowledge Gaps**: Identify missing concepts or prerequisite skills
- **Optimal Learning Paths**: Use reinforcement learning to recommend sequences
- **Conversation Quality**: Correlate graph growth with engagement metrics

---

## Appendix

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `knowledge_graph_service.py` | 1,046 | Entity extraction and storage |
| `graph_query_service.py` | 537 | Graph algorithms and traversal |
| `test_knowledge_graph.py` | 100+ | End-to-end testing |
| `scripts/migrate_to_graph_schema.py` | 150+ | Schema migration |
| `app.py` | - | REST API endpoints |

### Configuration

**Environment Variables**:
```bash
# OpenAI API key for GPT-4o-mini
OPENAI_API_KEY=sk-...

# Firestore credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional: Confidence threshold
KG_MIN_CONFIDENCE=0.7

# Optional: Max messages to analyze
KG_MAX_MESSAGES=30
```

### Dependencies

```
openai>=1.0.0
google-cloud-firestore>=2.11.0
python-dateutil>=2.8.0
```

### Support

For questions or issues:
1. Check the test script for usage examples
2. Review code comments in service files
3. Examine Firestore schema in production
4. Contact: [Your team contact info]

---

**Last Updated**: 2024-03-15
**Version**: 1.0
**Status**: Production-ready
