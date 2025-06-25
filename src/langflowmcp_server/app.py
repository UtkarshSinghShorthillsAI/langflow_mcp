import asyncio
import logging
import os
import sys
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

import anyio
import dotenv
from fastmcp import FastMCP
from pydantic import ValidationError

from .langflow_api_client import LangflowApiClient, LangflowApiException, LangflowAuthException
from .langflow_models import LangflowClientCreds
from . import globals

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


async def fetch_and_cache_components():
    """
    Fetches all components from the Langflow API, saves debug files, 
    and builds a flat cache for fast lookups.
    """
    logger.info("Attempting to fetch all components from Langflow API...")
    
    base_url = os.getenv("LANGFLOW_BASE_URL")
    api_key = os.getenv("LANGFLOW_API_KEY")

    if not base_url or not api_key:
        logger.error("LANGFLOW_BASE_URL and LANGFLOW_API_KEY must be set to fetch components. Builder tools will be unavailable.")
        return

    client = None
    try:
        # Create a temporary, short-lived client for this startup task.
        client = await LangflowApiClient.create(base_url=base_url, api_key=api_key)
        
        # 1. Fetch the component data from the API
        components_response = await client.get_all_components()

        # 2. Save the RAW NESTED response for debugging
        # The raw response is a dictionary of categories, e.g., {"agents": {...}, "inputs": {...}}
        nested_components_dict = components_response
        raw_debug_path = os.path.join(os.path.dirname(__file__), "debug_components_from_api.json")
        try:
            with open(raw_debug_path, 'w') as f:
                json.dump(nested_components_dict, f, indent=2)
            logger.info(f"--- Wrote RAW nested component data to {raw_debug_path} ---")
        except Exception as e:
            logger.error(f"Failed to write raw debug components file: {e}")

        # 3. Build the flat hash map for efficient searching
        flat_cache = {}
        for category_name, components_in_category in nested_components_dict.items():
            for component_name, component_template in components_in_category.items():
                if component_name in flat_cache:
                    logger.warning(f"Duplicate component name '{component_name}' found in category '{category_name}'. It will be overwritten.")
                flat_cache[component_name] = component_template
        
        # 4. Populate the global variable with the flattened map
        globals.COMPONENT_CACHE = flat_cache
        
        # 5. Save the FLATTENED cache for debugging
        flat_debug_path = os.path.join(os.path.dirname(__file__), "debug_flattened_cache.json")
        try:
            with open(flat_debug_path, 'w') as f:
                json.dump(globals.COMPONENT_CACHE, f, indent=2)
            logger.info(f"--- Wrote FLATTENED component cache to {flat_debug_path} ---")
        except Exception as e:
            logger.error(f"Failed to write flattened debug file: {e}")

        total_components = len(globals.COMPONENT_CACHE)
        logger.info(f"--- Successfully built and cached a flat map of {total_components} components. ---")
        if not total_components > 0:
            logger.warning("Warning: Component cache is empty. The Langflow API might have returned no components.")

    except (LangflowAuthException, LangflowApiException) as e:
        logger.error(f"Failed to fetch components from Langflow API: {e}. Builder tools will be unavailable.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred while fetching components: {e}")
    finally:
        if client:
            await client.close()

@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[None]:
    logger.info("LangflowMCP Server application starting...")
    await fetch_and_cache_components()  # Fetch and cache on startup
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
        from .tools import execution, flows, projects, utility, files, monitoring, builder
        
        # Call the registration function from each imported module
        execution.register_execution_tools(mcp_app)
        flows.register_flow_tools(mcp_app)
        projects.register_project_tools(mcp_app)
        utility.register_utility_tools(mcp_app)
        files.register_file_tools(mcp_app)
        monitoring.register_monitoring_tools(mcp_app)
        builder.register_builder_tools(mcp_app)
        
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