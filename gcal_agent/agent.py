"""
cloud_root — The Orchestrator
Root agent that analyzes user intent and routes to the appropriate sub-agent.
Routes to mapping_agent for AWS/Azure translation, billing_agent for GCP cost calculation.
"""

from google.adk.agents import Agent
from gcal_agent.subagents.mapping_agent.mapping_agent import mapping_agent
from gcal_agent.subagents.billing_agent.billing_agent import billing_agent
from gcal_agent.instructions import ROOT_INSTRUCTION

agent = Agent(
    name="cloud_root",
    model="gemini-2.0-flash",
    description="Root orchestrator agent for the GCP Blueprint AI.",
    instruction=ROOT_INSTRUCTION,
    sub_agents=[mapping_agent, billing_agent],
)

root_agent = agent
