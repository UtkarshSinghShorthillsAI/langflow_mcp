import logging
import uuid
import copy
import json
from typing import Any, Dict, Optional, Tuple

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import Field, ValidationError

from ..langflow_models import LangflowApiException, UpdateFlowRequest, FlowData, FlowModel
from ..app import get_session_langflow_client
from .. import globals

logger = logging.getLogger(__name__)

# --- Internal Helper Functions ---

def _get_active_flow(ctx: Context) -> Tuple[str, Dict[str, Any]]:
    """
    Retrieves the active flow ID and its data from the session.
    Raises a ToolError if no flow is active.
    """
    flow_id = getattr(ctx.session, "active_flow_id", None)
    flow_data = getattr(ctx.session, "active_flow_data", None)
    if not flow_id or flow_data is None:
        raise ToolError("No active flow set. Please call 'set_active_flow' first.")
    return flow_id, flow_data


# --- First, enhance the _save_flow_to_langflow helper to create a debug file ---

async def _save_flow_to_langflow(ctx: Context, flow_id: str, flow_data_dict: Dict):
    """Saves the provided flow data dictionary to the specified flow_id in Langflow."""
    # --- DEBUG: Write the exact JSON being sent to a file ---
    try:
        debug_path = os.path.join(os.path.dirname(__file__), "..", "debug_payload_to_save.json")
        with open(debug_path, 'w') as f:
            json.dump(flow_data_dict, f, indent=2)
        logger.info(f"--- Wrote final payload to {debug_path} before saving. ---")
    except Exception as e:
        logger.error(f"Failed to write debug payload file: {e}")

    try:
        flow_data_model = FlowData.model_validate(flow_data_dict)
        update_request = UpdateFlowRequest(data=flow_data_model)
        
        client = await get_session_langflow_client(ctx)
        await client.update_flow(flow_id, update_request)
        logger.info(f"Successfully saved updated data to flow {flow_id}.")
    except ValidationError as e:
        logger.error(f"Validation error before saving flow: {e}")
        raise ToolError(f"Internal error: The generated flow data is invalid. Details: {e}")
    except LangflowApiException as e:
        logger.error(f"API error while saving flow {flow_id}: {e}")
        raise ToolError(f"Failed to save flow to Langflow: {e.message}")



# --- MCP Tools ---

async def add_node_impl(
    ctx: Context,
    component_name: str = Field(..., description="The exact name of the component, e.g., 'OpenAIModel'."),
    template_values: Optional[Dict[str, Any]] = Field(None, description="A dictionary of values to set in the component's template, e.g., {'model_name': 'gpt-4o-mini'}."),
    position: Optional[Dict[str, int]] = Field(None, description="The x and y coordinates for the node's position.")
) -> Dict[str, str]:
    """
    Adds a new component node to the active flow and immediately saves the change.
    Returns the unique ID of the newly created node.
    """
    flow_id, flow_data = _get_active_flow(ctx)
    
    component_template = globals.COMPONENT_CACHE.get(component_name)
            
    if not component_template:
        raise ToolError(f"Component '{component_name}' not found.")

    # 1. Create a deep copy to avoid modifying the global cache.
    full_node_definition = copy.deepcopy(component_template)

    # 2. Apply user modifications to the template inside our copy.
    if template_values:
        for key, value in template_values.items():
            if key in full_node_definition.get("template", {}):
                full_node_definition["template"][key]["value"] = value
            else:
                logger.warning(f"Key '{key}' not found in template for '{component_name}'.")

    node_id = f"{component_name}-{str(uuid.uuid4())[:8]}"
    node_position = position or {"x": 0, "y": 0}

    # 3. Build the final `data` object, matching the manual ground truth structure.
    #    It should be a clean object with only the necessary top-level keys.
    final_node_data = {
        "id": node_id,
        "type": component_name,
        "showNode": True,  # This key is present in the manual export.
        "node": full_node_definition  # The entire component definition is nested here.
    }

    # 4. Build the final, top-level node object for the flow.
    new_node = {
        "id": node_id,
        "type": "genericNode",
        "position": node_position,
        "data": final_node_data,
        "measured": {"height": 234, "width": 320} # Add default UI state keys
    }
    
    flow_data["nodes"].append(new_node)
    
    await _save_flow_to_langflow(ctx, flow_id, flow_data)
    
    return {"status": "success", "message": f"Node '{component_name}' added successfully.", "node_id": node_id}

async def set_active_flow_impl(
    ctx: Context, 
    flow_id: str = Field(..., description="The unique ID of the flow to be edited.")
) -> str:
    """
    Fetches a flow from Langflow and sets it as the active flow for editing in the current session.
    This must be called before using 'add_node' or 'add_edge'.
    """
    logger.info(f"Setting active flow for editing: {flow_id}")
    try:
        client = await get_session_langflow_client(ctx)
        response = await client.get_flow(flow_id)
        flow = FlowModel.model_validate(response)
        
        ctx.session.active_flow_id = flow.id
        if flow.data:
            ctx.session.active_flow_data = flow.data.model_dump()
        else:
            ctx.session.active_flow_data = {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
        
        # --- DEBUG: Write the active flow's data to a file for inspection ---
        try:
            debug_path = os.path.join(os.path.dirname(__file__), "..", "debug_active_flow.json")
            with open(debug_path, 'w') as f:
                json.dump(ctx.session.active_flow_data, f, indent=2)
            logger.info(f"--- Wrote current active flow data to {debug_path} ---")
        except Exception as e:
            logger.error(f"Failed to write debug active flow file: {e}")
            
        return f"Success. Flow '{flow.name}' is now the active flow for editing."
    except LangflowApiException as e:
        raise ToolError(f"Failed to fetch or set active flow: {e.message}")
    
async def add_edge_impl():
    return "hello"

def register_builder_tools(app: FastMCP):
    """Registers the flow-building tools."""
    logger.info("Registering Flow Builder tools...")
    app.tool(name="set_active_flow")(set_active_flow_impl)
    app.tool(name="add_node")(add_node_impl)
    app.tool(name="add_edge")(add_edge_impl)