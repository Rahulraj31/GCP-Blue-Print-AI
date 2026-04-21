"""
mapping_agent — The Translator
Handles 1:1 mapping from AWS/Azure services to GCP equivalents.
Uses Google Search + Gemini's native knowledge for accurate mappings.
Supports multimodal input (architecture diagrams) via Gemini vision.
"""

from google.adk.agents import Agent
from google.adk.tools import google_search
from gcal_agent.instructions import MAPPING_INSTRUCTION

mapping_agent = Agent(
    name="mapping_agent",
    model="gemini-2.5-flash",
    description=(
        "Use this agent when the user mentions AWS or Azure services, "
        "uploads an architecture diagram, or asks to convert/migrate "
        "non-GCP cloud resources to GCP equivalents."
    ),
    instruction=MAPPING_INSTRUCTION,
    #tools=[google_search],
)
