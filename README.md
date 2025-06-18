# Langflow MCP Server

MCP Server for interacting with the Langflow API via a natural language interface.

## Overview

This server exposes Langflow functionalities as "tools" that can be understood and invoked by a Large Language Model (LLM) through an MCP Client. It allows for programmatic interaction with flows, projects, components, and more.

## Project Structure

- **`src/langflowmcp_server/app.py`**: The main FastMCP application entry point. Manages server lifecycle and session handling.
- **`src/langflowmcp_server/langflow_api_client.py`**: A dedicated client for all communication with the Langflow REST API.
- **`src/langflowmcp_server/langflow_models.py`**: Pydantic models for all Langflow API data structures.
- **`src/langflowmcp_server/tools/`**: Directory containing the tool implementations, organized by functionality (e.g., `flows.py`, `execution.py`).

## Setup

1.  Clone the repository.
2.  Ensure Python 3.10+ and `uv` are installed.
3.  Create a virtual environment:
    ```bash
    uv venv
    source .venv/bin/activate
    ```
4.  Install dependencies:
    ```bash
    uv pip install -e .
    ```
5.  Set up your Langflow connection details in a `.env` file (see `.env.example`). You will need your Langflow URL and an API key.

## Running the Server

You can run the server directly for stdio-based communication:
```bash
python -m src.langflowmcp_server.app