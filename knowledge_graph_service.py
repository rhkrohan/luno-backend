"""
Knowledge Graph Service for Child Learning Profiles

Extracts and stores knowledge entities from conversations:
- Topics (subjects discussed)
- Skills (demonstrated abilities & developmental milestones)
- Interests (enthusiasms & engagement patterns)
- Concepts (abstract understanding & cognitive development)
- Personality Traits (character attributes & emotional intelligence)
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from openai import OpenAI
import os
from google.cloud import firestore
from firestore_service import firestore_service
from logging_config import get_logger

logger = get_logger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class KnowledgeGraphService:
    """Service for extracting and managing child knowledge graphs"""

    def __init__(self, firestore_svc):
        """
        Initialize Knowledge Graph Service

        Args:
            firestore_svc: FirestoreService instance
        """
        self.fs = firestore_svc
        self.db = firestore_svc.db

    def extract_and_store(self, user_id: str, conversation_id: str, child_id: str, messages: List[Dict]):
        """
        Main extraction pipeline - called after conversation ends

        Args:
            user_id: Parent user ID
            conversation_id: Conversation ID
            child_id: Child ID
            messages: List of message dicts from conversation
        """
        try:
            logger.info(f"[KG] Starting extraction for conversation {conversation_id}")

            # Get child profile for age_level context
            child_doc = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id).get()

            if not child_doc.exists:
                logger.error(f"[KG] Child {child_id} not found")
                return

            child_data = child_doc.to_dict()
            child_age_level = child_data.get("ageLevel", "elementary")

            # Call LLM for extraction
            extracted_data = self._call_extraction_llm(messages, child_age_level)

            if not extracted_data:
                logger.warning(f"[KG] No data extracted from conversation {conversation_id}")
                return

            # Store entities and build entity name -> ID mapping
            entity_count = 0
            entities_map = {}

            for entity_type in ["topics", "skills", "interests", "concepts", "personality_traits"]:
                entities = extracted_data.get(entity_type, [])
                for entity_data in entities:
                    self._create_or_update_entity(
                        user_id, child_id, entity_data, entity_type, conversation_id
                    )
                    entity_count += 1

                    # Build mapping for edge extraction
                    name = entity_data.get('name')
                    if name:
                        # Use singular form to match entity type in edges
                        singular_type = entity_type.rstrip('s')
                        key = f"{singular_type}_{name.lower().strip()}"
                        entity_id = self._generate_entity_id(name, entity_type)
                        entities_map[key] = entity_id

            # Extract and store edges (relationships)
            relationships = extracted_data.get('relationships', [])
            if relationships:
                logger.debug(f"[KG] Found {len(relationships)} relationships to extract")
                self._extract_and_store_edges(
                    user_id, child_id, conversation_id,
                    relationships, entities_map
                )

            # Create observation document
            self._create_observation(user_id, child_id, conversation_id, extracted_data)

            # Update summary document
            self._update_summary(user_id, child_id)

            logger.info(f"[KG] Extraction complete for {conversation_id}: {entity_count} entities")

        except Exception as e:
            logger.error(f"[KG] Extraction failed for {conversation_id}: {e}", exc_info=True)

    def _call_extraction_llm(self, messages: List[Dict], child_age_level: str) -> Optional[Dict]:
        """
        Call GPT-4o-mini to extract knowledge entities

        Args:
            messages: List of conversation messages
            child_age_level: Child's age level (preschool, elementary, etc.)

        Returns:
            Dict with extracted entities or None if extraction failed
        """
        try:
            prompt = self._build_extraction_prompt(messages, child_age_level)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Low temperature for consistent extraction
                max_tokens=2000,
                timeout=30
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            extracted_data = json.loads(response_text)

            logger.debug(f"[KG] Extracted {len(extracted_data.get('topics', []))} topics, "
                        f"{len(extracted_data.get('skills', []))} skills, "
                        f"{len(extracted_data.get('interests', []))} interests")

            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"[KG] Failed to parse LLM response as JSON: {e}")
            logger.error(f"[KG] Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"[KG] LLM extraction failed: {e}", exc_info=True)
            return None

    def _build_extraction_prompt(self, messages: List[Dict], child_age_level: str) -> str:
        """
        Build comprehensive extraction prompt with enhanced taxonomy

        Args:
            messages: Conversation messages
            child_age_level: Child's age level

        Returns:
            Prompt string for LLM
        """
        # Limit to first 30 messages to control token cost
        message_context = "\n".join([
            f"{msg.get('sender', 'unknown')}: {msg.get('content', '')}"
            for msg in messages[:30]
        ])

        prompt = f"""Analyze this conversation between a child (age level: {child_age_level}) and Luna (AI companion). Extract structured knowledge to build the child's learning profile.

CONVERSATION:
{message_context}

TASK:
Extract entities with rich developmental and emotional context:

1. TOPICS - Subjects discussed
2. SKILLS - Abilities demonstrated & developmental milestones
3. INTERESTS - Enthusiasms & engagement patterns
4. CONCEPTS - Abstract understanding & cognitive development
5. PERSONALITY_TRAITS - Character attributes & emotional intelligence

TAXONOMY GUIDELINES:

TOPICS - Use these categories/subcategories:
- science_nature: prehistoric_animals, astronomy, biology, physics_chemistry, earth_science
- mathematics: numbers_counting, geometry, measurement, arithmetic
- language_literacy: reading, writing, vocabulary, storytelling
- arts_creativity: visual_arts, music, drama_performance, creative_expression
- social_emotional: emotions, relationships, empathy, conflict_resolution
- everyday_life: routines, safety, health, environment

SKILLS - Use these categories/subcategories:
- cognitive: memory, attention, reasoning, planning, categorization
- language_communication: expressive_language, receptive_language, conversation, pronunciation
- literacy_numeracy: counting, number_sense, phonics, reading_comprehension, writing
- social_emotional: emotion_recognition, emotion_regulation, empathy, cooperation, conflict_resolution
- creative_thinking: imagination, storytelling, creative_problem_solving, artistic_expression
- executive_function: working_memory, inhibitory_control, cognitive_flexibility, task_initiation

INTERESTS - Use these categories/subcategories:
- science_exploration: animals, space, nature, experiments
- creative: storytelling, art, music, pretend_play
- physical_active: sports, outdoor_play, dance_movement
- intellectual: puzzles, reading_books, numbers_patterns, questions_learning
- social_interactive: friendship, helping_caring, family
- fantasy_imagination: magical_themes, adventure, characters

CONCEPTS - Use these categories/subcategories:
- cognitive_development: cause_effect, classification, conservation, reversibility, seriation
- time_sequence: temporal_concepts, sequence, duration, daily_cycles
- spatial_reasoning: position, direction, size_comparison, perspective
- social_emotional_concepts: emotions, empathy, fairness, friendship, identity
- abstract_thinking: symbolism, analogy, hypothetical_thinking, metacognition
- moral_reasoning: right_wrong, kindness, responsibility, honesty

PERSONALITY_TRAITS - Use these categories/subcategories:
- emotional_intelligence: self_awareness, self_regulation, empathy, social_awareness
- cognitive_traits: curiosity, persistence, attention_focus, creativity, analytical_thinking
- social_behavioral: cooperation, independence, leadership, shyness_confidence, assertiveness
- temperament: energy_level, adaptability, sensitivity, mood
- learning_style: verbal_learner, visual_learner, kinesthetic_learner, social_learner, independent_learner

EXTRACTION RULES:
- Only extract if clearly evident in conversation
- Include confidence score (0.0-1.0, minimum 0.7 to extract)
- Identify developmental milestones when demonstrated
- Note emotional moments (excitement, frustration, joy, etc.)
- Track question patterns (what, why, how questions)
- Identify creative/imaginative elements

OUTPUT FORMAT (strict JSON):
{{
  "topics": [
    {{
      "name": "Dinosaurs",
      "category": "science_nature",
      "subcategory": "prehistoric_animals",
      "knowledge_level": "intermediate",
      "question_types": ["what", "why"],
      "vocabulary_growth": ["carnivore", "extinction"],
      "confidence": 0.9,
      "evidence": "Asked detailed questions about T-Rex diet and habitat"
    }}
  ],
  "skills": [
    {{
      "name": "Counting to 20",
      "skill_category": "literacy_numeracy",
      "skill_subcategory": "counting",
      "developmental_stage": "early_elementary",
      "mastery_level": "developing",
      "progression_rate": "steady",
      "confidence": 0.85,
      "evidence": "Counted 1-20 correctly with one prompt",
      "milestone": "Counts to 20 (age 5 milestone)"
    }}
  ],
  "interests": [
    {{
      "name": "Dinosaurs",
      "interest_category": "science_exploration",
      "interest_subcategory": "animals",
      "engagement_level": 0.95,
      "initiation_frequency": 0.9,
      "persistence_level": 0.9,
      "emotional_connection": "highly_positive",
      "confidence": 0.9,
      "evidence": "Very excited, asked many follow-up questions, initiated topic"
    }}
  ],
  "concepts": [
    {{
      "name": "Extinction",
      "concept_category": "cognitive_development",
      "concept_subcategory": "cause_effect",
      "abstraction_level": "semi_abstract",
      "understanding_level": 0.7,
      "cognitive_markers": {{
        "reasoning": "developing",
        "memory": "strong",
        "attention": "focused"
      }},
      "confidence": 0.8,
      "evidence": "Understood that dinosaurs lived long ago and are gone now"
    }}
  ],
  "personality_traits": [
    {{
      "name": "Curious",
      "trait_category": "cognitive_traits",
      "trait_subcategory": "curiosity",
      "intensity": 0.85,
      "consistency": 0.9,
      "development_trend": "growing",
      "confidence": 0.85,
      "evidence": "Asked many 'why' and 'how' questions throughout conversation"
    }}
  ],
  "developmental_milestones": [
    {{
      "milestone": "Understands concept of time (past vs present)",
      "domain": "cognitive",
      "age_appropriate": "5-6 years",
      "evidence": "Understood dinosaurs lived 'a long time ago'",
      "confidence": 0.8
    }}
  ],
  "emotional_moments": [
    {{
      "emotion": "excitement",
      "intensity": 0.9,
      "trigger": "Learning T-Rex was biggest carnivore",
      "social_emotional_marker": "strong_engagement",
      "evidence": "Voice got louder, asked rapid questions"
    }}
  ],
  "creative_elements": [
    {{
      "type": "imaginative_play",
      "description": "Pretended to be a dinosaur",
      "themes": ["adventure", "animals"],
      "creativity_level": 0.8,
      "evidence": "Made dinosaur sounds and movements"
    }}
  ],
  "relationships": [
    {{
      "sourceEntity": "Dinosaurs",
      "sourceType": "topic",
      "targetEntity": "Extinction",
      "targetType": "concept",
      "relationType": "learning_pathway",
      "confidence": 0.85,
      "evidence": "Child learned about extinction through dinosaur discussion",
      "attributes": {{
        "prerequisite": false,
        "difficulty": "medium"
      }}
    }}
  ]
}}

RELATIONSHIP EXTRACTION GUIDELINES:

Extract THREE types of relationships between entities:

1. TEMPORAL_COOCCURRENCE - Entities discussed together in conversation
   - When entities appear in the same conversational context
   - Indicates related concepts the child connects mentally
   - Examples: "Dinosaurs" + "T-Rex", "Space" + "Planets", "Counting" + "Numbers"
   - Attributes: {{"cooccurrenceFrequency": 0.0-1.0, "timeProximity": 0.0-1.0}}

2. LEARNING_PATHWAY - Learning progressions and concept relationships
   - When one concept leads to understanding another
   - When a skill requires prerequisite knowledge
   - Developmental progressions (earlier skill → later skill)
   - Examples: "Dinosaurs" → "Extinction" (learned through),
              "Counting" → "Addition" (prerequisite for),
              "Letters" → "Reading" (enables)
   - Attributes: {{
       "prerequisite": true/false,
       "difficulty": "easy" | "medium" | "hard",
       "masteryRequired": 0.0-1.0
     }}

3. EMOTIONAL_ASSOCIATION - Strong emotions connected to topics/interests
   - Emotions tied to specific topics, interests, or activities
   - Enthusiasm, excitement, frustration, or curiosity markers
   - Examples: "Excitement" about "Dinosaurs",
              "Frustration" with "Math",
              "Curiosity" about "Space"
   - Attributes: {{
       "emotion": "excitement" | "joy" | "curiosity" | "frustration" | "pride",
       "intensity": 0.0-1.0,
       "valence": "positive" | "negative" | "neutral"
     }}

RELATIONSHIP OUTPUT FORMAT:
{{
  "sourceEntity": "Entity name (exactly as in entities array)",
  "sourceType": "topic" | "skill" | "interest" | "concept" | "personality_trait",
  "targetEntity": "Entity name",
  "targetType": "topic" | "skill" | "interest" | "concept" | "personality_trait",
  "relationType": "temporal_cooccurrence" | "learning_pathway" | "emotional_association",
  "confidence": 0.0-1.0,
  "evidence": "Brief evidence from conversation (max 200 chars)",
  "attributes": {{...type-specific attributes as defined above...}}
}}

RELATIONSHIP RULES:
- Only extract relationships with confidence >= 0.7
- Provide specific evidence from the conversation
- Use appropriate attributes based on relationship type
- Ensure sourceEntity and targetEntity match entity names in other arrays
- Temporal cooccurrence relationships are bidirectional (order doesn't matter)
- Learning pathway relationships are directional (source enables/leads to target)
- Emotional associations should link emotions (from personality_traits or emotional_moments) to topics/interests

RESPOND ONLY WITH VALID JSON. NO EXPLANATIONS."""

        return prompt

    def _generate_entity_id(self, name: str, entity_type: str) -> str:
        """
        Generate consistent entity ID from name and type

        Args:
            name: Entity name (e.g., "Dinosaurs")
            entity_type: Entity type (topic, skill, interest, concept, personality_trait)

        Returns:
            Entity ID (e.g., "topic_dinosaurs")
        """
        # Normalize name: lowercase, remove special chars, replace spaces with underscores
        normalized = re.sub(r'[^a-z0-9\s]', '', name.lower())
        normalized = normalized.replace(' ', '_')

        # Singular form of entity_type
        type_prefix = entity_type.rstrip('s') if entity_type.endswith('s') else entity_type

        return f"{type_prefix}_{normalized}"

    def _resolve_entity_match(self, user_id: str, child_id: str, name: str, entity_type: str) -> Optional[str]:
        """
        Check if entity already exists (exact match or alias match)

        Args:
            user_id: Parent user ID
            child_id: Child ID
            name: Entity name to match
            entity_type: Entity type

        Returns:
            Existing entity ID if found, None otherwise
        """
        try:
            # Generate expected entity ID
            entity_id = self._generate_entity_id(name, entity_type)

            # Check if entity with this ID exists
            entity_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("entities").document(entity_id)

            entity_doc = entity_ref.get()

            if entity_doc.exists:
                return entity_id

            # TODO: Future enhancement - check aliases in other entities
            # For MVP, only exact ID match

            return None

        except Exception as e:
            logger.error(f"[KG] Error resolving entity match: {e}")
            return None

    def _create_or_update_entity(self, user_id: str, child_id: str, entity_data: Dict,
                                 entity_type: str, conversation_id: str):
        """
        Create new entity or update existing one

        Args:
            user_id: Parent user ID
            child_id: Child ID
            entity_data: Extracted entity data from LLM
            entity_type: Entity type (topics, skills, interests, concepts, personality_traits)
            conversation_id: Conversation ID
        """
        try:
            name = entity_data.get("name")
            if not name:
                logger.warning(f"[KG] Entity missing name: {entity_data}")
                return

            # Check minimum confidence threshold
            confidence = entity_data.get("confidence", 0)
            if confidence < 0.7:
                logger.debug(f"[KG] Skipping low-confidence entity: {name} ({confidence})")
                return

            # Generate entity ID
            entity_id = self._generate_entity_id(name, entity_type)

            # Get existing entity if it exists
            entity_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("entities").document(entity_id)

            entity_doc = entity_ref.get()

            timestamp = firestore.SERVER_TIMESTAMP
            timestamp_value = datetime.utcnow()  # For nested fields where SERVER_TIMESTAMP can't be used

            if entity_doc.exists:
                # UPDATE existing entity
                existing_data = entity_doc.to_dict()

                update_data = {
                    "lastMentionedAt": timestamp,
                    "lastConversationId": conversation_id,
                    "mentionCount": firestore.Increment(1),
                    "strength": max(existing_data.get("strength", 0), confidence),
                }

                # Update conversation count if this is a new conversation
                if conversation_id != existing_data.get("lastConversationId"):
                    update_data["conversationCount"] = firestore.Increment(1)

                # Add recent observation snippet
                observation_snippet = {
                    "conversationId": conversation_id,
                    "timestamp": timestamp_value,  # Use datetime for nested field
                    "snippet": entity_data.get("evidence", "")[:200],
                    "sentiment": "positive",  # Can be enhanced later
                }

                # Keep only last 5 observations
                recent_obs = existing_data.get("recentObservations", [])
                recent_obs.append(observation_snippet)
                update_data["recentObservations"] = recent_obs[-5:]

                entity_ref.update(update_data)
                logger.debug(f"[KG] Updated entity: {entity_id}")

            else:
                # CREATE new entity
                new_entity = {
                    "id": entity_id,
                    "type": entity_type.rstrip('s'),  # Singular form
                    "name": name,
                    "aliases": [],
                    "firstMentionedAt": timestamp_value,  # Use datetime for set() operation
                    "firstConversationId": conversation_id,
                    "lastMentionedAt": timestamp_value,  # Use datetime for set() operation
                    "lastConversationId": conversation_id,
                    "mentionCount": 1,
                    "conversationCount": 1,
                    "strength": confidence,
                    "attributes": {},
                    "relatedEntities": [],
                    "developmentalMilestones": [],
                    "emotionalMoments": [],
                    "edgeStats": {
                        "totalEdges": 0,
                        "incomingEdges": 0,
                        "outgoingEdges": 0,
                        "temporalCooccurrence": 0,
                        "learningPathway": 0,
                        "emotionalAssociation": 0,
                        "topConnections": []
                    },
                    "clusterId": None,
                    "clusterLabel": None,
                    "centrality": 0.0,
                    "lastGraphUpdateAt": timestamp_value,
                    "recentObservations": [{
                        "conversationId": conversation_id,
                        "timestamp": timestamp_value,  # Use datetime for nested field
                        "snippet": entity_data.get("evidence", "")[:200],
                        "sentiment": "positive",
                    }]
                }

                # Add type-specific attributes
                if entity_type == "topics":
                    new_entity["attributes"] = {
                        "category": entity_data.get("category", ""),
                        "subcategory": entity_data.get("subcategory", ""),
                        "knowledgeLevel": entity_data.get("knowledge_level", "beginner"),
                        "questionTypes": entity_data.get("question_types", []),
                        "vocabularyGrowth": entity_data.get("vocabulary_growth", []),
                    }
                elif entity_type == "skills":
                    new_entity["attributes"] = {
                        "skillCategory": entity_data.get("skill_category", ""),
                        "skillSubcategory": entity_data.get("skill_subcategory", ""),
                        "developmentalStage": entity_data.get("developmental_stage", ""),
                        "masteryLevel": entity_data.get("mastery_level", "emerging"),
                        "progressionRate": entity_data.get("progression_rate", "steady"),
                        "lastDemonstrated": timestamp_value,  # Use datetime for nested field
                    }
                    # Add milestone if present
                    if "milestone" in entity_data:
                        new_entity["developmentalMilestones"].append({
                            "milestone": entity_data["milestone"],
                            "achievedAt": timestamp_value,  # Use datetime for nested field
                            "conversationId": conversation_id,
                            "evidence": entity_data.get("evidence", "")
                        })
                elif entity_type == "interests":
                    new_entity["attributes"] = {
                        "interestCategory": entity_data.get("interest_category", ""),
                        "interestSubcategory": entity_data.get("interest_subcategory", ""),
                        "engagementLevel": entity_data.get("engagement_level", 0.5),
                        "initiationFrequency": entity_data.get("initiation_frequency", 0.5),
                        "persistenceLevel": entity_data.get("persistence_level", 0.5),
                        "emotionalConnection": entity_data.get("emotional_connection", "positive"),
                    }
                elif entity_type == "concepts":
                    new_entity["attributes"] = {
                        "conceptCategory": entity_data.get("concept_category", ""),
                        "conceptSubcategory": entity_data.get("concept_subcategory", ""),
                        "abstractionLevel": entity_data.get("abstraction_level", "concrete"),
                        "understandingLevel": entity_data.get("understanding_level", 0.5),
                        "cognitiveMarkers": entity_data.get("cognitive_markers", {}),
                    }
                elif entity_type == "personality_traits":
                    new_entity["attributes"] = {
                        "traitCategory": entity_data.get("trait_category", ""),
                        "traitSubcategory": entity_data.get("trait_subcategory", ""),
                        "intensity": entity_data.get("intensity", 0.5),
                        "consistency": entity_data.get("consistency", 0.5),
                        "developmentTrend": entity_data.get("development_trend", "stable"),
                    }

                entity_ref.set(new_entity)
                logger.debug(f"[KG] Created entity: {entity_id}")

        except Exception as e:
            logger.error(f"[KG] Error creating/updating entity: {e}", exc_info=True)

    def _extract_and_store_edges(self, user_id: str, child_id: str, conversation_id: str,
                                 relationships: List[Dict], entities_map: Dict[str, str]):
        """
        Extract edges from LLM relationships output

        Args:
            user_id: Parent user ID
            child_id: Child ID
            conversation_id: Conversation ID
            relationships: List of relationship dictionaries from LLM
            entities_map: Mapping of "type_name" to entity ID
        """
        try:
            logger.debug(f"[KG] Extracting {len(relationships)} relationships")

            for rel in relationships:
                # Skip low-confidence relationships
                if rel.get('confidence', 0) < 0.7:
                    logger.debug(f"[KG] Skipping low-confidence relationship: {rel.get('sourceEntity')} -> {rel.get('targetEntity')} ({rel.get('confidence')})")
                    continue

                # Resolve entity IDs from names
                source_key = f"{rel['sourceType']}_{rel['sourceEntity'].lower().strip()}"
                target_key = f"{rel['targetType']}_{rel['targetEntity'].lower().strip()}"

                source_id = entities_map.get(source_key)
                target_id = entities_map.get(target_key)

                if not source_id or not target_id:
                    logger.warning(f"[KG] Could not resolve entity IDs for relationship: {source_key} -> {target_key}")
                    continue

                # Create or update edge
                self._create_or_update_edge(
                    user_id, child_id, conversation_id,
                    source_id, rel['sourceType'], rel['sourceEntity'],
                    target_id, rel['targetType'], rel['targetEntity'],
                    rel['relationType'], rel['confidence'],
                    rel.get('evidence', ''), rel.get('attributes', {})
                )

        except Exception as e:
            logger.error(f"[KG] Error extracting edges: {e}", exc_info=True)

    def _create_or_update_edge(self, user_id: str, child_id: str, conversation_id: str,
                               source_id: str, source_type: str, source_name: str,
                               target_id: str, target_type: str, target_name: str,
                               edge_type: str, confidence: float, evidence: str,
                               attributes: Dict):
        """
        Create new edge or update existing with moving average weight

        Args:
            user_id: Parent user ID
            child_id: Child ID
            conversation_id: Conversation ID
            source_id: Source entity ID
            source_type: Source entity type
            source_name: Source entity name
            target_id: Target entity ID
            target_type: Target entity type
            target_name: Target entity name
            edge_type: Edge type (temporal_cooccurrence, learning_pathway, emotional_association)
            confidence: Confidence score (0.0-1.0)
            evidence: Evidence text from conversation
            attributes: Type-specific attributes dict
        """
        try:
            # Generate edge ID (sorted IDs for undirected temporal edges)
            if edge_type == 'temporal_cooccurrence':
                ids_sorted = sorted([source_id, target_id])
                edge_id = f"{edge_type}_{ids_sorted[0]}_{ids_sorted[1]}"
            else:
                edge_id = f"{edge_type}_{source_id}_{target_id}"

            edge_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("edges").document(edge_id)

            edge_doc = edge_ref.get()
            timestamp_value = datetime.utcnow()

            if edge_doc.exists:
                # UPDATE existing edge with moving average weight
                existing_data = edge_doc.to_dict()
                obs_count = existing_data.get('observationCount', 0)
                current_weight = existing_data.get('weight', 0)
                new_weight = (current_weight * obs_count + confidence) / (obs_count + 1)

                update_data = {
                    'weight': new_weight,
                    'lastObservedAt': timestamp_value,
                    'observationCount': firestore.Increment(1),
                    'updatedAt': timestamp_value
                }

                # Update conversation IDs (keep last 10)
                conv_ids = existing_data.get('conversationIds', [])
                if conversation_id not in conv_ids:
                    conv_ids.append(conversation_id)
                update_data['conversationIds'] = conv_ids[-10:]

                # Update evidence snippets (keep last 3)
                snippets = existing_data.get('evidenceSnippets', [])
                snippets.append({
                    'conversationId': conversation_id,
                    'timestamp': timestamp_value,
                    'snippet': evidence[:200]
                })
                update_data['evidenceSnippets'] = snippets[-3:]

                edge_ref.update(update_data)
                logger.debug(f"[KG] Updated edge: {edge_id} (new weight: {new_weight:.2f})")

            else:
                # CREATE new edge
                new_edge = {
                    'id': edge_id,
                    'edgeType': edge_type,
                    'sourceEntityId': source_id,
                    'sourceEntityType': source_type,
                    'sourceEntityName': source_name,
                    'targetEntityId': target_id,
                    'targetEntityType': target_type,
                    'targetEntityName': target_name,
                    'weight': confidence,
                    'confidence': confidence,
                    'firstObservedAt': timestamp_value,
                    'lastObservedAt': timestamp_value,
                    'observationCount': 1,
                    'conversationIds': [conversation_id],
                    'attributes': attributes,
                    'evidenceSnippets': [{
                        'conversationId': conversation_id,
                        'timestamp': timestamp_value,
                        'snippet': evidence[:200]
                    }],
                    'status': 'active',
                    'createdAt': timestamp_value,
                    'updatedAt': timestamp_value
                }

                edge_ref.set(new_edge)
                logger.debug(f"[KG] Created edge: {edge_id}")

            # Update entity edge stats
            self._update_entity_edge_stats(user_id, child_id, source_id, target_id, edge_type)

        except Exception as e:
            logger.error(f"[KG] Error creating/updating edge {edge_type} {source_id}->{target_id}: {e}", exc_info=True)

    def _update_entity_edge_stats(self, user_id: str, child_id: str,
                                  source_id: str, target_id: str, edge_type: str):
        """
        Update edge statistics on both source and target entities

        Args:
            user_id: Parent user ID
            child_id: Child ID
            source_id: Source entity ID
            target_id: Target entity ID
            edge_type: Edge type
        """
        try:
            entities_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("entities")

            # Map edge type to field name
            edge_type_field = edge_type.replace('_', '')  # temporal_cooccurrence -> temporalCooccurrence
            edge_type_field = edge_type_field[0].lower() + edge_type_field[1:]  # camelCase

            # For temporal cooccurrence, update both nodes symmetrically
            if edge_type == 'temporal_cooccurrence':
                for entity_id in [source_id, target_id]:
                    entity_ref = entities_ref.document(entity_id)
                    entity_ref.update({
                        'edgeStats.totalEdges': firestore.Increment(1),
                        f'edgeStats.{edge_type_field}': firestore.Increment(1),
                        'lastGraphUpdateAt': datetime.utcnow()
                    })
            else:
                # For directed edges, update source (outgoing) and target (incoming)
                source_ref = entities_ref.document(source_id)
                source_ref.update({
                    'edgeStats.totalEdges': firestore.Increment(1),
                    'edgeStats.outgoingEdges': firestore.Increment(1),
                    f'edgeStats.{edge_type_field}': firestore.Increment(1),
                    'lastGraphUpdateAt': datetime.utcnow()
                })

                target_ref = entities_ref.document(target_id)
                target_ref.update({
                    'edgeStats.totalEdges': firestore.Increment(1),
                    'edgeStats.incomingEdges': firestore.Increment(1),
                    f'edgeStats.{edge_type_field}': firestore.Increment(1),
                    'lastGraphUpdateAt': datetime.utcnow()
                })

            logger.debug(f"[KG] Updated edge stats for {source_id} and {target_id}")

        except Exception as e:
            logger.error(f"[KG] Error updating entity edge stats: {e}", exc_info=True)

    def _create_observation(self, user_id: str, child_id: str, conversation_id: str, extracted_data: Dict):
        """
        Create observation document (immutable log of what was observed)

        Args:
            user_id: Parent user ID
            child_id: Child ID
            conversation_id: Conversation ID
            extracted_data: Full extracted data from LLM
        """
        try:
            # Generate observation ID
            timestamp_value = datetime.utcnow()
            timestamp_str = timestamp_value.strftime("%Y%m%d_%H%M%S")
            observation_id = f"obs_{conversation_id}_{timestamp_str}"

            # Build entities list from all entity types
            observed_entities = []

            for entity_type in ["topics", "skills", "interests", "concepts", "personality_traits"]:
                entities = extracted_data.get(entity_type, [])
                for entity_data in entities:
                    name = entity_data.get("name")
                    if name and entity_data.get("confidence", 0) >= 0.7:
                        entity_id = self._generate_entity_id(name, entity_type)
                        observed_entities.append({
                            "entityId": entity_id,
                            "entityType": entity_type.rstrip('s'),
                            "entityName": name,
                            "observationType": "mentioned",  # Can be enhanced
                            "confidence": entity_data.get("confidence", 0.7),
                            "evidenceSnippet": entity_data.get("evidence", "")[:200]
                        })

            observation_doc = {
                "id": observation_id,
                "conversationId": conversation_id,
                "timestamp": timestamp_value,  # Use datetime for set() operation
                "entities": observed_entities,
                "conversationType": "conversation",  # Can get from conversation metadata
                "messageCount": len(extracted_data.get("topics", [])),  # Approximate
                "extractedAt": timestamp_value,  # Use datetime for set() operation
                "extractionVersion": "v1.0"
            }

            observation_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("observations").document(observation_id)

            observation_ref.set(observation_doc)
            logger.debug(f"[KG] Created observation: {observation_id}")

        except Exception as e:
            logger.error(f"[KG] Error creating observation: {e}", exc_info=True)

    def _update_summary(self, user_id: str, child_id: str):
        """
        Update aggregate summary document with latest stats

        Args:
            user_id: Parent user ID
            child_id: Child ID
        """
        try:
            # Query all entities for this child
            entities_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("entities")

            entities = list(entities_ref.stream())

            # Count by type
            stats = {
                "totalEntities": len(entities),
                "topicsCount": 0,
                "skillsCount": 0,
                "interestsCount": 0,
                "conceptsCount": 0,
                "traitsCount": 0,
            }

            topics = []
            skills = []
            interests = []

            for entity_doc in entities:
                entity = entity_doc.to_dict()
                entity_type = entity.get("type", "")

                if entity_type == "topic":
                    stats["topicsCount"] += 1
                    topics.append({
                        "id": entity["id"],
                        "name": entity["name"],
                        "count": entity.get("mentionCount", 1)
                    })
                elif entity_type == "skill":
                    stats["skillsCount"] += 1
                    skills.append({
                        "id": entity["id"],
                        "name": entity["name"],
                        "level": entity.get("attributes", {}).get("masteryLevel", "emerging")
                    })
                elif entity_type == "interest":
                    stats["interestsCount"] += 1
                    interests.append({
                        "id": entity["id"],
                        "name": entity["name"],
                        "strength": entity.get("strength", 0.5)
                    })
                elif entity_type == "concept":
                    stats["conceptsCount"] += 1
                elif entity_type == "personality_trait":
                    stats["traitsCount"] += 1

            # Sort and get top 5
            topics.sort(key=lambda x: x["count"], reverse=True)
            skills.sort(key=lambda x: x["name"])
            interests.sort(key=lambda x: x["strength"], reverse=True)

            summary_doc = {
                "childId": child_id,
                "lastUpdatedAt": datetime.utcnow(),  # Use datetime for set() operation
                "stats": stats,
                "topTopics": topics[:5],
                "topSkills": skills[:5],
                "topInterests": interests[:5],
                "learningProfile": {
                    "ageLevel": "elementary",  # Get from child profile
                    "curiosityScore": 0.8,  # Calculate from entity data
                    "engagementScore": 0.8,
                    "vocabularyLevel": "grade2"
                }
            }

            summary_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("knowledgeGraph").document("summary")

            summary_ref.set(summary_doc, merge=True)
            logger.debug(f"[KG] Updated summary for child {child_id}")

        except Exception as e:
            logger.error(f"[KG] Error updating summary: {e}", exc_info=True)

    def get_summary(self, user_id: str, child_id: str) -> Optional[Dict]:
        """
        Get knowledge graph summary for a child

        Args:
            user_id: Parent user ID
            child_id: Child ID

        Returns:
            Summary dict or None if not found
        """
        try:
            summary_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("knowledgeGraph").document("summary")

            summary_doc = summary_ref.get()

            if not summary_doc.exists:
                return None

            return summary_doc.to_dict()

        except Exception as e:
            logger.error(f"[KG] Error getting summary: {e}", exc_info=True)
            return None

    def get_entities(self, user_id: str, child_id: str, filters: Dict) -> List[Dict]:
        """
        Query entities with filters

        Args:
            user_id: Parent user ID
            child_id: Child ID
            filters: Dict with optional keys: type, limit, orderBy

        Returns:
            List of entity dicts
        """
        try:
            entities_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("entities")

            query = entities_ref

            # Filter by type
            if filters.get("type"):
                query = query.where("type", "==", filters["type"])

            # Order by field
            order_by = filters.get("orderBy", "strength")
            query = query.order_by(order_by, direction=firestore.Query.DESCENDING)

            # Limit results
            limit = filters.get("limit", 50)
            query = query.limit(limit)

            # Execute query
            entities = []
            for doc in query.stream():
                entity = doc.to_dict()
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"[KG] Error querying entities: {e}", exc_info=True)
            return []


# Global instance
knowledge_graph_service = KnowledgeGraphService(firestore_service)
