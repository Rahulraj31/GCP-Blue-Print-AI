# Mapping Agent

This is a specialized ADK sub-agent responsible for translating other cloud providers' services into GCP equivalents.

## Features
- **Internal Architect Knowledge**: Uses prompt engineering to deduce correct mappings leveraging the native LLM knowledge.
- **Vision Integration**: Accepts architecture diagram uploads and parses them to identify components to map.
- **Web Search Fallback**: If an obscure service is presented, it searches the GCP service comparison documentation.
