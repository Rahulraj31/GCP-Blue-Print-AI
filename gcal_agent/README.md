# GCAL Agent (Cloud Root Orchestrator)

This directory contains the root orchestration agent for the GCP Cloud Calculator.

## Overview

The `cloud_root` agent serves as the entry point for user interactions. It parses natural language to understand user intent and delegates the task to the appropriate specialist agent (either the `mapping_agent` or the `billing_agent`).

## Directory Structure

- **`agent.py`**: Defines the `cloud_root` agent and its delegating logic.
- **`instructions.py`**: Contains the centralized instruction sets for all agents.
- **`tools.py`**: Contains tools used by the agents (e.g., getting GCP pricing).
- **`subagents/`**: Directory containing the specialized sub-agents.
