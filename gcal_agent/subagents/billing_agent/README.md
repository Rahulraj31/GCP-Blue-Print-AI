# Billing Agent

This is a specialized ADK sub-agent responsible for gathering real-time standard price estimates.

## Features
- **Catalog Navigation**: Given a GCP service name (like "Compute Engine"), it retrieves the matching SKUs and prices.
- **Filtering**: Specifically queries the v2beta2 `https://cloudbilling.googleapis.com/v2beta/skus` endpoint.
- **Price Calculation**: Converts rates, tiers, and limits into a human-readable Bill of Materials structure.
