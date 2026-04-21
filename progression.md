# Progression Tracker — GCP Blueprint AI

Multi-agent system using Google ADK for conversational GCP cost estimation.

## Milestones

| # | Milestone | Status | Timestamp |
|---|---|---|---|
| 1 | Project Setup (uv init + dependencies) | ✅ Complete | 2026-04-21 13:10 IST |
| 2 | Agent Scaffolding (cloud_root, mapping_agent, billing_agent) | ✅ Complete | 2026-04-21 13:12 IST |
| 3 | Tool Integration (Billing Catalog API + Google Search) | ✅ Complete | 2026-04-21 13:12 IST |
| 4 | Configuration (.env + requirements.txt) | ✅ Complete | 2026-04-21 13:11 IST |
| 5 | ADK Web Server Launch | ✅ Complete | 2026-04-21 13:32 IST |
| 6 | Agent Graph Verification | ✅ Complete | 2026-04-21 13:34 IST |
| 7 | Live Testing (with real credentials) | ✅ Complete | 2026-04-21 |
| 8 | Directory Restructure & Centralization | ✅ Complete | 2026-04-21 |
| 9 | Intelligence & Precision Upgrade | ✅ Complete | 2026-04-21 |

## Architecture

```
gcal_agent
├── agent.py (Orchestrator: cloud_root)
├── instructions.py (Centralized prompts)
├── tools.py (Catalog API v2beta + Fuzzy Match)
└── subagents/
    ├── mapping_agent/
    │   └── mapping_agent.py (AWS/Azure → GCP Translator)
    └── billing_agent/
        └── billing_agent.py (GCP Cost Calculator)
```

## Bug Fixes

| Issue | Fix | Date |
|---|---|---|
| `GoogleSearchTool` import not found | Changed to `from google.adk.tools import google_search` | 2026-04-21 |
| ADK Loader 'subagents' Error | Renamed sub-agent `agent.py` to unique names to fix discovery | 2026-04-21 |
| `invalid_scope` OAuth Error | Switched to explicit Service Account loading + `load_dotenv()` | 2026-04-21 |
| Tool Mixing Restriction | Removed `google_search` to allow stable function calling | 2026-04-21 |
| SKU Discovery Cap | Implemented Regional Filtering + Fuzzy SKU matching | 2026-04-21 |

## Notes

- **Phase 1-4**: All code and configuration files created. Agents use Gemini 2.5 Flash via Vertex AI.
- **Phase 5**: ADK web server starts clean. All 3 agents discovered via `/list-apps`. Agent graph builds via `/dev/build_graph/cloud_root`.
- **Next Step**: Update `.env` with real GCP project ID and service account key, then test conversations.

## Deep Architectural Knowledge (Learnings & Patterns)

1. **API Selection (v1 vs v2beta):** 
   - **`v1` is Superior for AI Agents**: The `v1` Catalog API delivers a monolithic payload containing standard descriptions, regions, AND exact `pricingInfo` tiers in a single HTTP request. 
   - **`v2beta` is for backend syncs**: The `v2beta` update intentionally stripped `pricingInfo` out of the SKUs list, forcing an N+1 secondary callback to `v2beta/{sku}/price`. This introduces severe latency and causes LLM timeouts, mapping `v1` natively as the only acceptable pattern for real-time generative agents.

2. **Preventing 429 RESOURCE_EXHAUSTED (Token Quotas):**
   - Huge monolithic services (like Compute Engine) have >15,000 SKUs. Making an API filter for a broad keyword (like "Linux") will return pages of useless matched hardware models and exhaust the underlying Vertex AI context token limits.
   - **Mitigation:** Implement strict Python-side short-circuit guards early in the tool execution (e.g., throwing a `needs_input` if `sku_keyword` belongs to an arbitrary broad stopword map). This protects the endpoint silently without complex ADK routing setups.

3. **HTTP Pagination Nuances:**
   - GCP Base64 pagination tokens strictly include trailing `=` or `+` chars. These universally MUST be properly wrapped with `urllib.parse.quote()` before string interpolation, otherwise, local dev queries throw `400 Bad Request` exceptions natively.

4. **Solving LLM Hallucination WITHOUT Hardcoding:**
   - Hardcoding global GCP regions locally creates a deeply brittle stack constraint over time. Creating dynamic "Agent Web Search Skills" adds pointless latency.
   - **Chain of Thought (CoT):** The ultimate solution is to modify the tool instruction prompt requiring the LLM to process and "print out" exactly why a city maps to an ID right in the text console BEFORE pulling the custom tool context. It immediately engages better memory pathways and halts standard hallucination (e.g. mapping Delhi to Mumbai `asia-south1` incorrectly).

5. **Predefined vs Custom Pricing:**
   - In standard GCP billing terminology, predefined instance shapes (like `e2-medium`) correlate to strictly generic string SKUs (like `E2 Instance Core`). 
   - The LLM's natural fallback is to erroneously pick `Custom Instance` SKU models which have higher rates. This must be corrected with a strict instruction rule explicitly banning the inclusion of the word "Custom" for standard requests.
