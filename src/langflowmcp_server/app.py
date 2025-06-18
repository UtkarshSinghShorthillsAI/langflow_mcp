import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

import anyio
import dotenv
from fastmcp import FastMCP
from pydantic import ValidationError

from .langflow_api_client import LangflowApiClient, LangflowApiException, LangflowAuthException
from .langflow_models import LangflowClientCreds

# --- Environment & Logging Setup ---
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_path):
    dotenv.load_dotenv(dotenv_path=env_path)
    logging.info(f"--- Loaded environment variables from: {env_path} ---")
else:
    logging.warning(f"--- .env file not found at {env_path} ---")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s %(levelname)-8s %(name)s | %(message)s',
    stream=sys.stderr,
    force=True
)
logger = logging.getLogger("langflowmcp_server.app")

# --- Session Management ---
active_langflow_api_clients: Dict[str, LangflowApiClient] = {}
_client_creation_locks: Dict[str, asyncio.Lock] = {}
_global_lock = asyncio.Lock()

async def _get_lock(session_id: str) -> asyncio.Lock:
    async with _global_lock:
        return _client_creation_locks.setdefault(session_id, asyncio.Lock())

async def get_session_langflow_client(ctx: Any) -> LangflowApiClient:
    session_object = getattr(ctx, 'session', None)
    if not session_object:
        raise LangflowApiException(0, "Server error: Could not access session object from context.")
    session_id = str(id(session_object))

    if session_id in active_langflow_api_clients:
        return active_langflow_api_clients[session_id]

    creation_lock = await _get_lock(session_id)
    async with creation_lock:
        if session_id in active_langflow_api_clients:
            return active_langflow_api_clients[session_id]

        logger.info(f"Creating new LangflowApiClient for session {session_id}.")
        
        initialize_params = getattr(session_object, '_client_params', None)
        raw_meta = getattr(initialize_params, '_meta', None) if initialize_params else None
        
        creds_dict: Optional[Dict[str, Any]] = None
        creds_source = "environment"

        if isinstance(raw_meta, dict) and "langflow_credentials" in raw_meta:
            creds_dict = raw_meta["langflow_credentials"]
            creds_source = "_meta.langflow_credentials"
        else:
            api_key = os.getenv("LANGFLOW_API_KEY")
            if api_key:
                creds_dict = {"api_key": api_key}

        if not creds_dict:
            raise LangflowAuthException("Langflow API key not supplied via _meta or env vars (LANGFLOW_API_KEY).")

        base_url = creds_dict.get("url") or os.getenv("LANGFLOW_BASE_URL")
        if not base_url:
            raise LangflowApiException(0, "LANGFLOW_BASE_URL not configured on server or provided in _meta.")

        try:
            creds = LangflowClientCreds.model_validate(creds_dict)
            api_client = await LangflowApiClient.create(base_url=base_url, api_key=creds.api_key)
            active_langflow_api_clients[session_id] = api_client
            logger.info(f"LangflowApiClient created successfully for session {session_id} using credentials from {creds_source}.")
            return api_client
        except ValidationError as e:
            raise LangflowAuthException(f"Invalid Langflow credentials structure: {e}")
        except (LangflowAuthException, LangflowApiException) as e:
            logger.error(f"Failed to create LangflowApiClient for session {session_id}: {e}")
            async with _global_lock:
                _client_creation_locks.pop(session_id, None)
            raise

@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[None]:
    logger.info("LangflowMCP Server application starting...")
    yield
    logger.info("LangflowMCP Server application shutting down...")
    clients_to_close = list(active_langflow_api_clients.values())
    active_langflow_api_clients.clear()
    _client_creation_locks.clear()
    async with anyio.create_task_group() as tg:
        for client in clients_to_close:
            tg.start_soon(client.close)
    logger.info("Global lifespan cleanup finished.")

# --- FastMCP Application ---
mcp_app = FastMCP(
    name="LangflowMCP Server",
    instructions="This server exposes tools to interact with the Langflow API, allowing for programmatic management and execution of flows.",
    dependencies=["httpx", "pydantic"],
    lifespan=app_lifespan,
)

def register_tools() -> None:
    """Imports tool modules and calls their registration functions."""
    logger.info("Attempting to register Langflow tools...")
    try:
        # Correctly import the existing tool modules
        from .tools import execution, flows, projects, utility, files, monitoring
        
        # Call the registration function from each imported module
        execution.register_execution_tools(mcp_app)
        flows.register_flow_tools(mcp_app)
        projects.register_project_tools(mcp_app)
        utility.register_utility_tools(mcp_app)
        files.register_file_tools(mcp_app)
        monitoring.register_monitoring_tools(mcp_app)
        
        logger.info("All Langflow tool modules registered successfully.")
    except ImportError as exc:
        logger.error("Tool registration failed during import: %s", exc)
    except Exception as exc:
        logger.exception("Unexpected error during tool registration: %s", exc)

# Exported for CLI entry-point in pyproject.toml
mcp_app_for_cli = mcp_app

if __name__ == "__main__":
    register_tools()
    logger.info("Starting LangflowMCP Server (stdio transport)...")
    mcp_app.run()