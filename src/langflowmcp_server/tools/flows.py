import logging
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import Field, ValidationError

from ..langflow_models import LangflowApiException, FlowModel, CreateFlowRequest, UpdateFlowRequest, AllFlowsResponse, GenericSuccessMessage
from ..app import get_session_langflow_client

logger = logging.getLogger(__name__)

async def list_langflow_flows_impl(ctx: Context) -> AllFlowsResponse:
    """Lists all available flows in Langflow."""
    logger.info("Tool 'list_langflow_flows' called.")
    try:
        client = await get_session_langflow_client(ctx)
        response = await client.list_flows()
        structured_response = {
            "count": len(response),
            "flows": response
        }
        return AllFlowsResponse.model_validate(structured_response)
        return response
    except LangflowApiException as e:
        raise ToolError(f"Failed to list flows: {e.message}")
    except ValidationError as e:
        logger.error(f"Pydantic validation failed for flows list: {e}")
        raise ToolError(f"Data from Langflow API for flows is malformed: {e}")

async def create_langflow_flow_impl(ctx: Context, name: str, description: Optional[str] = None, project_id: Optional[str] = None) -> FlowModel:
    """Creates a new, empty flow in Langflow, optionally assigning it to a project."""
    logger.info(f"Tool 'create_langflow_flow' called with name: {name}")
    try:
        client = await get_session_langflow_client(ctx)
        request_data = CreateFlowRequest(name=name, description=description, project_id=project_id)
        response = await client.create_flow(request_data)
        return FlowModel.model_validate(response)
    except LangflowApiException as e:
        raise ToolError(f"Failed to create flow: {e.message}")

async def get_langflow_flow_details_impl(ctx: Context, flow_id: str = Field(..., description="The ID of the flow to retrieve.")) -> Optional[FlowModel]:
    """Retrieves the details of a specific Langflow flow by its ID."""
    logger.info(f"Tool 'get_langflow_flow_details' called for flow_id: {flow_id}")
    try:
        client = await get_session_langflow_client(ctx)
        response = await client.get_flow(flow_id)
        return FlowModel.model_validate(response)
    except LangflowApiException as e:
        if e.status_code == 404: return None
        raise ToolError(f"Failed to get flow details: {e.message}")

async def update_langflow_flow_impl(ctx: Context, flow_id: str, name: Optional[str] = None, description: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> FlowModel:
    """Updates an existing flow in Langflow."""
    logger.info(f"Tool 'update_langflow_flow' called for flow_id: {flow_id}")
    try:
        client = await get_session_langflow_client(ctx)
        request_data = UpdateFlowRequest(name=name, description=description, data=data)
        response = await client.update_flow(flow_id, request_data)
        return FlowModel.model_validate(response)
    except LangflowApiException as e:
        raise ToolError(f"Failed to update flow: {e.message}")

async def delete_langflow_flow_impl(ctx: Context, flow_id: str = Field(..., description="The ID of the flow to delete.")) -> GenericSuccessMessage:
    """Deletes a flow from Langflow."""
    logger.info(f"Tool 'delete_langflow_flow' called for flow_id: {flow_id}")
    try:
        client = await get_session_langflow_client(ctx)
        return await client.delete_flow(flow_id)
    except LangflowApiException as e:
        raise ToolError(f"Failed to delete flow: {e.message}")

def register_flow_tools(app: FastMCP):
    logger.info("Registering Flow tools...")
    app.tool(name="list_langflow_flows")(list_langflow_flows_impl)
    app.tool(name="create_langflow_flow")(create_langflow_flow_impl)
    app.tool(name="get_langflow_flow_details")(get_langflow_flow_details_impl)
    app.tool(name="update_langflow_flow")(update_langflow_flow_impl)
    app.tool(name="delete_langflow_flow")(delete_langflow_flow_impl)