import logging
from typing import Dict, Any

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from ..langflow_models import LangflowApiException, VersionResponse, ConfigResponse
from ..app import get_session_langflow_client

logger = logging.getLogger(__name__)

async def get_langflow_version_impl(ctx: Context) -> VersionResponse:
    """Retrieves the version of the Langflow API."""
    logger.info("Tool 'get_langflow_version' called.")
    try:
        client = await get_session_langflow_client(ctx)
        response = await client.get_version()
        return VersionResponse.model_validate(response)
    except LangflowApiException as e:
        raise ToolError(f"Failed to get version: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in get_langflow_version_impl")
        raise ToolError(f"An unexpected error occurred: {e}")

async def get_langflow_config_impl(ctx: Context) -> ConfigResponse:
    """Retrieves the server configuration of the Langflow instance."""
    logger.info("Tool 'get_langflow_config' called.")
    try:
        client = await get_session_langflow_client(ctx)
        response = await client.get_config()
        return ConfigResponse.model_validate(response)
    except LangflowApiException as e:
        raise ToolError(f"Failed to get config: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in get_langflow_config_impl")
        raise ToolError(f"An unexpected error occurred: {e}")

async def get_all_langflow_components_impl(ctx: Context) -> Dict[str, Any]:
    """Retrieves a dictionary of all registered Langflow components."""
    logger.info("Tool 'get_all_langflow_components' called.")
    try:
        client = await get_session_langflow_client(ctx)
        return await client.get_all_components()
    except LangflowApiException as e:
        raise ToolError(f"Failed to get components: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in get_all_langflow_components_impl")
        raise ToolError(f"An unexpected error occurred: {e}")

def register_utility_tools(app: FastMCP):
    logger.info("Registering Utility tools...")
    app.tool(name="get_langflow_version")(get_langflow_version_impl)
    app.tool(name="get_langflow_config")(get_langflow_config_impl)
    app.tool(name="get_all_langflow_components")(get_all_langflow_components_impl)