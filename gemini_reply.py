
import os
import json
from google import genai
from firestore_service import firestore_service
from logging_config import get_logger

# Configure Gemini API
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
logger = get_logger(__name__)

CHARACTER_PROMPT = (
    "You are Luna, a magical friendly companion who loves kids! You're playful, curious, and encouraging. "
    "Use simple, age-appropriate language and speak in complete, friendly sentences. "
    "Be conversational and warm, like a caring friend having a chat. "
    "Your aim is to engage children in creative and educational conversations that spark their curiosity. "
    "Respond with 2-5 complete sentences (30-100 words). Keep responses natural and engaging without special formatting or emojis."
)

# Simple in-memory session storage
CONVERSATIONS = {}

# Session metadata for Firestore integration
SESSION_METADATA = {}

def clear_session_history(session_id):
    """
    Clear conversation history for a session

    Args:
        session_id: Session ID to clear history for
    """
    if session_id in CONVERSATIONS:
        del CONVERSATIONS[session_id]
        logger.info(f"Cleared conversation history for session {session_id}")


def get_session_message_count(session_id):
    """
    Get message count for a session

    Args:
        session_id: Session ID

    Returns:
        int: Number of messages in session history
    """
    return len(CONVERSATIONS.get(session_id, []))


def get_gpt_reply(user_text, session_id="default", user_id=None, conversation_id=None, child_id=None):
    """
    Generate reply using Google Gemini (named get_gpt_reply for compatibility)

    Args:
        user_text: User's message
        session_id: Session identifier
        user_id: Parent user ID
        conversation_id: Conversation ID for Firestore
        child_id: Child ID for knowledge graph context

    Returns:
        str: Luna's reply
    """
    try:
        logger.info(f"Gemini request | Session: {session_id} | Message: {user_text}")

        # Get conversation history for this session
        if session_id not in CONVERSATIONS:
            CONVERSATIONS[session_id] = []

        history = CONVERSATIONS[session_id]

        # Fetch child knowledge context if available (graph-based)
        knowledge_context = ""
        if child_id and user_id:
            knowledge_context = _build_knowledge_context(user_id, child_id, user_text)

        # Build enhanced system prompt
        enhanced_prompt = CHARACTER_PROMPT
        if knowledge_context:
            enhanced_prompt += knowledge_context

        # Build conversation history for the new API
        contents = []

        # Add previous conversation context (last 6 messages = 3 turns)
        for msg in history[-6:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        # Add current message
        contents.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })

        logger.debug(f"Using {len(contents)-1} previous messages for context")

        # Generate response using new API
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',  # Latest fast model
            contents=contents,
            config={
                'temperature': 0.9,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 1024,
                'system_instruction': enhanced_prompt,
            }
        )

        reply = response.text.strip()

        # Save conversation turn to memory
        CONVERSATIONS[session_id].append({"role": "user", "content": user_text})
        CONVERSATIONS[session_id].append({"role": "assistant", "content": reply})

        # Keep only last 10 messages (5 turns) to manage memory
        if len(CONVERSATIONS[session_id]) > 10:
            CONVERSATIONS[session_id] = CONVERSATIONS[session_id][-10:]

        # Save to Firestore if metadata is provided
        if user_id and conversation_id:
            try:
                # Save child message to array
                logger.info(f"Saving child message to Firestore | Conversation: {conversation_id} | User: {user_id}")
                success_child = firestore_service.add_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    sender="child",
                    content=user_text
                )
                if success_child:
                    logger.info(f"Child message saved successfully | Conversation: {conversation_id}")
                else:
                    logger.error(f"Failed to save child message | Conversation: {conversation_id}")

                # Save toy message to array
                logger.info(f"Saving toy message to Firestore | Conversation: {conversation_id} | User: {user_id}")
                success_toy = firestore_service.add_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    sender="toy",
                    content=reply
                )
                if success_toy:
                    logger.info(f"Toy message saved successfully | Conversation: {conversation_id}")
                else:
                    logger.error(f"Failed to save toy message | Conversation: {conversation_id}")

            except Exception as e:
                logger.error(f"Failed to save messages to Firestore | Conversation: {conversation_id} | Error: {str(e)}", exc_info=True)
                # Continue execution even if Firestore fails

        logger.info(f"Gemini reply generated | Session: {session_id} | Reply: {reply[:100]}{'...' if len(reply) > 100 else ''}")
        logger.debug(f"Session {session_id} now has {len(CONVERSATIONS[session_id])} messages")

        return reply

    except Exception as e:
        logger.error(f"Gemini request failed | Session: {session_id} | Error: {str(e)}", exc_info=True)
        return "Hi! I'm Luna! Sorry, I had a little hiccup. Can you try again?"


def _build_knowledge_context(user_id, child_id, current_message=""):
    """
    Build graph-based knowledge context for Gemini system prompt

    Uses graph traversal to find related entities, interest clusters,
    learning progressions, and emotional connections.

    Args:
        user_id: Parent user ID
        child_id: Child ID
        current_message: Current user message for entity detection

    Returns:
        str: Knowledge context string or empty string if no data
    """
    try:
        from knowledge_graph_service import knowledge_graph_service
        from graph_query_service import GraphQueryService
        from firebase_config import db

        graph_service = GraphQueryService(db)
        context_parts = []
        context_parts.append("\n\nCHILD PROFILE:")

        # 1. Detect mentioned entities in current message
        mentioned_entities = _detect_mentioned_entities(user_id, child_id, current_message, knowledge_graph_service)

        # 2. Get related entities via graph traversal
        if mentioned_entities:
            related = _build_related_entities_context(user_id, child_id, mentioned_entities, graph_service)
            if related:
                mentioned_names = ', '.join([e['name'] for e in mentioned_entities[:2]])
                context_parts.append(f"- Currently discussing: {mentioned_names}")

                if related.get('topics'):
                    context_parts.append(f"- Related topics: {related['topics']}")

                if related.get('concepts'):
                    context_parts.append(f"- Related concepts: {related['concepts']}")

        # 3. Interest clusters
        try:
            clusters = graph_service.find_interest_clusters(user_id, child_id, min_cluster_size=2)
            if clusters:
                largest = max(clusters, key=lambda c: c['size'])
                cluster_names = ', '.join([e['name'] for e in largest['entities'][:5]])
                context_parts.append(f"- Interest area: {largest['label']} ({cluster_names})")
        except Exception as e:
            logger.debug(f"[KG] Cluster detection skipped: {e}")

        # 4. Skills with learning progressions
        try:
            skills_result = knowledge_graph_service.get_entities(
                user_id, child_id,
                {"type": "skill", "orderBy": "strength", "limit": 3}
            )

            if skills_result.get('entities'):
                skill_context = []
                for skill in skills_result['entities'][:3]:
                    mastery = skill.get('attributes', {}).get('masteryLevel', 'emerging')

                    # Get prerequisites
                    prereqs = graph_service.get_prerequisite_chain(user_id, child_id, skill['id'], max_depth=1)

                    if prereqs:
                        skill_context.append(f"{skill['name']} ({mastery}, builds on {prereqs[0]['name']})")
                    else:
                        skill_context.append(f"{skill['name']} ({mastery})")

                if skill_context:
                    context_parts.append(f"- Skills: {', '.join(skill_context)}")
        except Exception as e:
            logger.debug(f"[KG] Skills context skipped: {e}")

        # 5. Recent milestones
        milestones = _build_milestone_context(user_id, child_id, knowledge_graph_service)
        if milestones:
            context_parts.append(f"- Recent achievements: {milestones}")

        # 6. Emotional connections
        if mentioned_entities:
            emotions = _build_emotional_context(user_id, child_id, mentioned_entities, graph_service)
            if emotions:
                context_parts.append(f"- Emotional connections: {emotions}")

        # Fallback to summary if no graph context
        if len(context_parts) <= 1:  # Only header
            summary = knowledge_graph_service.get_summary(user_id, child_id)
            if summary:
                if summary.get('topInterests'):
                    interests = [i['name'] for i in summary['topInterests'][:3]]
                    context_parts.append(f"- Loves: {', '.join(interests)}")

                if summary.get('topTopics'):
                    topics = [t['name'] for t in summary['topTopics'][:3]]
                    context_parts.append(f"- Recently discussed: {', '.join(topics)}")

        # Add guidance
        context_parts.append("\nPersonalize responses based on their interests, skills, and emotional connections.")
        context_parts.append("Reference related topics naturally. Build on their interest areas.")

        context = "\n".join(context_parts)
        logger.debug(f"[KG] Built graph-based knowledge context: {len(context)} chars")

        return context

    except Exception as e:
        logger.error(f"[KG] Failed to build knowledge context: {e}", exc_info=True)
        return ""


def _detect_mentioned_entities(user_id, child_id, message, kg_service):
    """Simple keyword matching against entity names"""
    try:
        if not message:
            return []

        message_lower = message.lower()

        # Get all entities
        all_entities = []
        for entity_type in ['topic', 'interest', 'skill', 'concept']:
            result = kg_service.get_entities(user_id, child_id, {"type": entity_type, "limit": 50})
            if result.get('entities'):
                all_entities.extend(result['entities'])

        # Find mentions
        mentioned = []
        for entity in all_entities:
            name_lower = entity['name'].lower()
            if name_lower in message_lower:
                mentioned.append(entity)

        logger.debug(f"[KG] Detected {len(mentioned)} entities in message")
        return mentioned[:5]  # Limit to 5

    except Exception as e:
        logger.debug(f"[KG] Entity detection failed: {e}")
        return []


def _build_related_entities_context(user_id, child_id, mentioned_entities, graph_service):
    """Get related topics/concepts via graph traversal"""
    try:
        seed_ids = [e['id'] for e in mentioned_entities[:3]]

        # Extract subgraph
        subgraph = graph_service.extract_context_subgraph(
            user_id, child_id, seed_ids, max_entities=10, depth=1
        )

        if not subgraph.get('entities'):
            return None

        # Group by type
        topics = []
        concepts = []

        for entity in subgraph['entities']:
            if entity.get('isSeed'):
                continue  # Skip seeds

            if entity['type'] == 'topic':
                topics.append(entity['name'])
            elif entity['type'] == 'concept':
                concepts.append(entity['name'])

        result = {}
        if topics:
            result['topics'] = ', '.join(topics[:3])
        if concepts:
            result['concepts'] = ', '.join(concepts[:2])

        return result if result else None

    except Exception as e:
        logger.debug(f"[KG] Related entities context failed: {e}")
        return None


def _build_emotional_context(user_id, child_id, mentioned_entities, graph_service):
    """Get emotional_association edges from mentioned entities"""
    try:
        from firebase_config import db

        emotions = []

        for entity in mentioned_entities[:3]:
            # Get emotional_association edges
            edges_ref = db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("edges")

            # Edges where this entity is the target (emotion → entity)
            edge_docs = list(edges_ref.where("edgeType", "==", "emotional_association")\
                                      .where("targetEntityId", "==", entity['id'])\
                                      .where("weight", ">=", 0.7).stream())

            for edge_doc in edge_docs:
                edge = edge_doc.to_dict()
                attrs = edge.get('attributes', {})
                emotion = attrs.get('emotion', 'interest')
                emotions.append(f"{emotion} about {entity['name']}")

        if emotions:
            return ', '.join(emotions[:3])

        return None

    except Exception as e:
        logger.debug(f"[KG] Emotional context failed: {e}")
        return None


def _build_milestone_context(user_id, child_id, kg_service):
    """Get recent developmental milestones"""
    try:
        # Get skills with milestones
        skills_result = kg_service.get_entities(
            user_id, child_id,
            {"type": "skill", "orderBy": "lastMentionedAt", "limit": 10}
        )

        if not skills_result.get('entities'):
            return None

        milestones = []

        for skill in skills_result['entities'][:10]:
            skill_milestones = skill.get('developmentalMilestones', [])
            if skill_milestones:
                # Get most recent milestone
                latest = max(skill_milestones, key=lambda m: m.get('achievedAt', ''))
                milestones.append({
                    'milestone': latest.get('milestone', skill['name']),
                    'achievedAt': latest.get('achievedAt')
                })

        if not milestones:
            return None

        # Sort by date and take top 2
        milestones.sort(key=lambda m: m.get('achievedAt', ''), reverse=True)
        milestone_names = [m['milestone'] for m in milestones[:2]]

        return ', '.join(milestone_names)

    except Exception as e:
        logger.debug(f"[KG] Milestone context failed: {e}")
        return None
