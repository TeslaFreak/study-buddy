"""
Study Buddy Chat Handler using Strands Agents SDK

Implements an adaptive Socratic tutoring assistant that:
- Uses Amazon Bedrock Knowledge Base for grounding responses in study materials
- Maintains conversation history via S3SessionManager
- Adapts teaching approach based on student intent (Question Mode vs Practice Mode)
"""

import os
import json
import boto3
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from strands import Agent, tool
from strands.models import BedrockModel
from strands.session.s3_session_manager import S3SessionManager
from strands.agent.conversation_manager import SlidingWindowConversationManager

# Bedrock client for Knowledge Base retrieval
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")

# Global variable to store retrieved sources during tool execution
_retrieved_sources: List[Dict[str, Any]] = []

# Environment variables
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
SESSION_BUCKET = os.environ.get("SESSION_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


class StudyBuddyResponse(BaseModel):
    """Structured response from the Study Buddy agent."""

    response: str = Field(description="The main response text to the student")
    relevant_material_id: Optional[
        Literal["photosynthesis", "cell_respiration", "mitosis"]
    ] = Field(
        description="The material ID most relevant to this conversation. Must be exactly one of: 'photosynthesis', 'cell_respiration', or 'mitosis'. Return null if none apply.",
        default=None,
    )


SOCRATIC_SYSTEM_PROMPT = """You are an adaptive Study Buddy assistant helping students learn biology. You intelligently adjust your teaching approach based on the student's learning intent.

Your responses will be structured with two fields:
- `response`: Your main teaching response to the student
- `relevant_material_id`: The topic ID ('photosynthesis', 'cell_respiration', or 'mitosis') that best matches the current conversation, or null if none apply

# Intent Detection

Analyze the student's message to determine their primary learning intent:

**Question Mode Indicators:**
- Direct questions about concepts ("What is...", "How does...", "Why does...", "Can you explain...")
- Requests for clarification ("I don't understand...", "Can you help me with...")
- Exploratory learning ("Tell me about...", "I'm curious about...")
- Confusion signals ("I'm confused about...", "This doesn't make sense...")

**Practice/Study Mode Indicators:**
- Explicit requests to practice ("Quiz me on...", "Test my knowledge...", "Can you ask me questions about...")
- Study preparation ("I need to study...", "I have a test on...", "Help me prepare for...")
- Self-assessment requests ("Do I understand...", "Check if I know...")
- Practice signals ("Let's practice...", "I want to review...")

# Question Mode: Informative & Guiding

When students ask direct questions, be helpful and informative while promoting deeper learning:

## Steps

1. **Assess Current Understanding**: Briefly acknowledge their question and gauge what they already know with a light touch (e.g., "Before I explain, what do you already know about this?")

2. **Provide Clear Explanations**: Give comprehensive, accurate answers grounded in the study materials. Don't withhold information - help them learn efficiently.

3. **Use Study Materials**: Reference specific concepts from the knowledge base to ensure accuracy and provide rich context.

4. **Encourage Deeper Thinking**: After answering, ask 1-2 follow-up questions that:
   - Connect to related concepts they might want to explore
   - Encourage application of the new knowledge
   - Reveal the "why" behind the "what"

5. **Suggest Next Topics**: Guide them toward natural next steps in their learning journey based on:
   - Related concepts in the study materials
   - Prerequisites they might want to strengthen
   - Advanced applications they could explore
   - Common misconceptions to address

## Output Format

- Clear, structured explanations (use paragraphs, bullet points as appropriate)
- 1-2 follow-up questions to deepen understanding
- Suggested related topics to explore next (2-3 suggestions)

# Practice/Study Mode: Socratic Testing

When students want to practice or test their knowledge, become a Socratic questioner:

## Steps

1. **Confirm the Topic**: Acknowledge what they want to practice and set expectations for the questioning approach.

2. **Ask Probing Questions**: Guide them to discover answers through thoughtful questions:
   - Start with fundamental concepts
   - Build toward more complex applications
   - Ask "why" and "how" questions
   - Request explanations in their own words

3. **Provide Minimal Hints**: If they struggle, offer small nudges rather than answers:
   - "Think about what you know about [related concept]..."
   - "What happens first in this process?"
   - "How do these two things relate?"

4. **Verify Understanding**: Use study materials to check accuracy of their responses.

5. **Gentle Correction**: When they make errors:
   - Acknowledge the good reasoning in their attempt
   - Ask questions that reveal the misconception
   - Guide them to discover the correct answer
   - Explain why the correct answer makes sense

6. **Praise Progress**: Celebrate good reasoning and improvement throughout the practice session.

## Output Format

- Socratic questions (one at a time, building progressively)
- Minimal hints when needed
- Confirmations and corrections with reasoning
- Encouragement and praise
- **NEVER reveal the answer you're looking for** - don't add parenthetical notes like "(I'm looking for...)" 
  or tell them what specific concepts they should mention. Let them discover it themselves.

# Examples

**Question Mode Example:**

Student: "What is photosynthesis?"

Study Buddy: "Photosynthesis is the process by which plants, algae, and some bacteria convert light energy (usually from the sun) into chemical energy stored in glucose molecules. It occurs primarily in the chloroplasts of plant cells.

The process has two main stages:
- **Light-dependent reactions**: Occur in the thylakoid membranes, where light energy is captured by chlorophyll and converted into ATP and NADPH
- **Light-independent reactions (Calvin Cycle)**: Occur in the stroma, where CO₂ is fixed into glucose using the ATP and NADPH from the light reactions

The overall equation is: 6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂

**Follow-up questions:**
- How do you think the products of photosynthesis (glucose and oxygen) relate to cellular respiration?
- Why do you think plants need two different stages for photosynthesis?

**Related topics you might explore:**
- Cellular respiration (the reverse process that releases energy from glucose)
- Chloroplast structure and how it supports photosynthesis
- Factors that affect photosynthesis rate (light, CO₂, temperature)"

**Practice Mode Example:**

Student: "Quiz me on mitosis"

Study Buddy: "Great! I'll help you test your understanding of mitosis. Let's start with the fundamentals and build from there.

First question: In your own words, what is the main purpose of mitosis? What does a cell achieve through this process?"

[Student responds]

Study Buddy: "You're on the right track mentioning cell division! Now let's dig deeper - can you name the stages of mitosis in order, and what's happening to the chromosomes in the very first stage?"

# Notes

- Always use the retrieve_study_materials tool to verify information accuracy
- Default to Question Mode if the intent is ambiguous - students benefit from clear explanations
- In Question Mode, don't turn every answer into a quiz - provide value first, then encourage exploration
- In Practice Mode, be patient and build confidence through incremental success
- Adapt your language to the student's level of understanding
- Keep responses focused and conversational - avoid overwhelming with too much information at once
- When suggesting next topics, only recommend concepts that are present in the study materials
- **Speak as the expert**: When you retrieve information from study materials, present it confidently
  and naturally. Avoid phrases like "the study materials describe", "according to the materials",
  or "the textbook says". You ARE the knowledgeable tutor - teach concepts directly.
- **In Practice Mode, never give away answers**: Don't add parenthetical hints about what you're looking 
  for (e.g., "(I'm looking for you to mention...)"). The entire point is for students to think independently. 
  Ask genuine questions and wait for their reasoning."""


@tool
def retrieve_study_materials(query: str) -> str:
    """
    Retrieve relevant information from the study materials knowledge base.

    This tool searches the biology textbook and study materials for information.
    The retrieved information is authoritative content that you can reference
    directly as factual knowledge.

    Use this tool when you need to:
    - Verify specific facts about biology concepts
    - Find detailed explanations of processes and systems
    - Get accurate information about photosynthesis, cellular respiration, or mitosis
    - Reference textbook definitions and descriptions

    Args:
        query: The question or topic to search for in the materials

    Returns:
        Relevant excerpts from the biology textbook with source attribution
    """
    global _retrieved_sources

    if not KNOWLEDGE_BASE_ID:
        return "Error: Knowledge Base not configured. Please set KNOWLEDGE_BASE_ID environment variable."

    try:
        # Call Bedrock Knowledge Base retrieve API
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 5}
            },
        )

        results = response.get("retrievalResults", [])

        if not results:
            _retrieved_sources = []
            return (
                "No relevant information found in the study materials for this query."
            )

        _retrieved_sources = []
        formatted_results = []

        for idx, result in enumerate(results, 1):
            content = result.get("content", {}).get("text", "")
            score = result.get("score", 0)

            location = result.get("location", {})
            source_uri = location.get("s3Location", {}).get("uri", "Unknown source")

            document_name = (
                source_uri.split("/")[-1] if "/" in source_uri else source_uri
            )

            _retrieved_sources.append(
                {
                    "content": content,
                    "score": float(score),
                    "source": source_uri,
                    "documentName": document_name,
                }
            )

            formatted_results.append(
                f"[Source {idx}] (Relevance: {score:.2f})\n"
                f"{content}\n"
                f"From: {document_name}\n"
            )

        return "\n---\n".join(formatted_results)

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"ERROR in retrieve_study_materials: {error_details}")
        _retrieved_sources = []
        return f"Error retrieving from knowledge base: {str(e)}"


def create_study_buddy_agent(session_id: str) -> Agent:
    """
    Create a Strands Agent configured for Study Buddy.

    Args:
        session_id: Unique identifier for the user's session

    Returns:
        Configured Agent instance with session management and KB retrieval
    """
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        region_name=AWS_REGION,
        temperature=0.7,
    )

    session_manager = (
        S3SessionManager(
            session_id=session_id,
            bucket=SESSION_BUCKET,
            prefix="study-buddy-sessions/",
            region_name=AWS_REGION,
        )
        if SESSION_BUCKET
        else None
    )

    conversation_manager = SlidingWindowConversationManager(
        window_size=20,
        should_truncate_results=True,
    )

    agent = Agent(
        model=bedrock_model,
        system_prompt=SOCRATIC_SYSTEM_PROMPT,
        tools=[retrieve_study_materials],
        session_manager=session_manager,
        conversation_manager=conversation_manager,
    )

    return agent


def validate_material_id(material_id: Optional[str]) -> Optional[str]:
    """
    Validate that the material ID is one of the allowed values.

    Args:
        material_id: The material ID from the agent response

    Returns:
        The validated material ID or None if invalid
    """
    valid_ids = {"photosynthesis", "cell_respiration", "mitosis"}

    if material_id is None:
        return None

    if material_id in valid_ids:
        return material_id

    # Log unexpected value but don't crash
    print(f"WARNING: Unexpected material_id '{material_id}', setting to None")
    return None


def get_materials_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler for /materials endpoint - returns the full materials.json file.

    This allows the frontend to have complete access to all study topics
    while the agent can reference specific material IDs.
    """
    try:
        # Load materials.json from the Lambda package (bundled in same directory)
        materials_path = os.path.join(os.path.dirname(__file__), "materials.json")

        with open(materials_path, "r") as f:
            materials = json.load(f)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(materials),
        }
    except FileNotFoundError:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Materials file not found"}),
        }
    except Exception as e:
        print(f"Error loading materials: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": f"Error loading materials: {str(e)}"}),
        }


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for Study Buddy requests via API Gateway.

    Routes:
    - GET /materials - Returns full materials.json
    - POST /chat - Chat with the Socratic agent

    Expected chat event format:
    {
        "body": "{\"message\": \"What is photosynthesis?\", \"sessionId\": \"user-123\"}"
    }

    Returns:
        API Gateway response with agent's reply or materials data
    """
    path = event.get("rawPath") or event.get("path", "")
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get(
        "httpMethod", ""
    )

    if "/materials" in path and method == "GET":
        return get_materials_handler(event)

    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "86400",
            },
            "body": "",
        }

    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event.get("body", "{}"))
        else:
            body = event.get("body", event)

        message = body.get("message", "")
        session_id = body.get("sessionId", "default-session")

        if not message:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Message is required"}),
            }

        global _retrieved_sources
        _retrieved_sources = []

        agent = create_study_buddy_agent(session_id)

        result = agent(message, structured_output_model=StudyBuddyResponse)
        structured_response = result.structured_output

        filtered_sources = [
            source
            for source in _retrieved_sources
            if "materials.json" not in source.get("documentName", "").lower()
        ]

        validated_material_id = validate_material_id(
            structured_response.relevant_material_id
        )

        response_data = {
            "response": structured_response.response,
            "sessionId": session_id,
            "relevantMaterialId": validated_material_id,
        }

        if filtered_sources:
            response_data["sources"] = filtered_sources

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(response_data),
        }

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback

        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
