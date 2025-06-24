import logging
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import Field, ValidationError

from ..langflow_models import LangflowApiException, FlowModel, CreateFlowRequest, UpdateFlowRequest, AllFlowsResponse, GenericSuccessMessage, FlowsListResponse
from ..app import get_session_langflow_client

logger = logging.getLogger(__name__)

async def list_langflow_flows_impl(
    ctx: Context,
    remove_example_flows: bool = Field(True, description="If True, example flows are excluded from the results."),
    components_only: bool = Field(False, description="If True, only flows that are components are returned."),
    get_all: bool = Field(True, description="If True, fetches all flows, ignoring pagination."),
    folder_id: Optional[str] = Field(None, description="The unique ID of a folder (project) to filter flows by."),
    header_flows: bool = Field(False, description="If True, returns only the headers of the flows, not the full data."),
    page: int = Field(1, description="The page number to retrieve when pagination is active (get_all=False)."),
    size: int = Field(50, description="The number of items per page when pagination is active (get_all=False).")
) -> FlowsListResponse:
    """Lists available flows in LangFlow, with optional filtering and pagination."""
    logger.info(f"Tool 'list_langflow_flows' called with params: folder_id={folder_id}, get_all={get_all}")
    try:
        client = await get_session_langflow_client(ctx)
        response_data = await client.list_flows(
            remove_example_flows=remove_example_flows,
            components_only=components_only,
            get_all=get_all,
            folder_id=folder_id,
            header_flows=header_flows,
            page=page,
            size=size
        )

        if isinstance(response_data, list):
            # API returned a direct list (get_all=True or header_flows=True)
            return FlowsListResponse(
                total_count=len(response_data),
                flows=response_data
            )
        elif isinstance(response_data, dict) and "items" in response_data:
            # API returned a paginated response object
            return FlowsListResponse(
                total_count=response_data.get("total", 0),
                flows=response_data.get("items", []),
                page=response_data.get("page"),
                size=response_data.get("size"),
                pages=response_data.get("pages"),
            )
        else:
            logger.warning(f"Unexpected response format from list_flows: {type(response_data)}")
            return FlowsListResponse(total_count=0, flows=[])

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