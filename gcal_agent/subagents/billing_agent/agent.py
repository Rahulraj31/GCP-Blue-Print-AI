"""
billing_agent — The Calculator
Queries real-time pricing from the GCP Cloud Billing Catalog API.
Asks clarifying questions when data is incomplete (e.g., missing region).
"""

from google.adk.agents import Agent
from gcal_agent.tools import get_gcp_pricing
from gcal_agent.instructions import BILLING_INSTRUCTION

billing_agent = Agent(
    name="billing_agent",
    model="gemini-2.5-flash",
    description=(
        "Use this agent when specific GCP services have been identified and the user "
        "wants to know pricing, costs, or needs a Bill of Materials (BOM). "
        "This agent queries real-time GCP pricing data."
    ),
    instruction=BILLING_INSTRUCTION,
    tools=[get_gcp_pricing],
)
