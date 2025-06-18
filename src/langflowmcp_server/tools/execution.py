import logging
from typing import Any, Dict, Optional, List

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from ..langflow_models import LangflowApiException, RunFlowRequest, RunFlowResponse
from ..app import get_session_langflow_client

logger = logging.getLogger(__name__)

class RunFlowPayload(BaseModel):
    flow_id: str = Field(..., description="The ID of the flow to run.")
    input_value: str = Field(..., description="The input message or data for the flow.")
    session_id: Optional[str] = Field(None, description="An optional session ID to maintain conversation history.")
    output_type: str = Field("chat", description="The desired output type ('chat', 'any', 'debug').")
    tweaks: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="A dictionary of tweaks to apply to the flow components.")

async def run_langflow_flow_impl(ctx: Context, payload: RunFlowPayload) -> RunFlowResponse:
    """Executes a Langflow flow synchronously and returns the final result."""
    logger.info(f"Tool 'run_langflow_flow' called for flow_id: {payload.flow_id}")
    try:
        client = await get_session_langflow_client(ctx)
        request_data = RunFlowRequest(
            input_value=payload.input_value,
            session_id=payload.session_id,
            output_type=payload.output_type,
            tweaks=payload.tweaks,
        )
        response = await client.run_flow(payload.flow_id, request_data)
        return RunFlowResponse.model_validate(response)
    except LangflowApiException as e:
        raise ToolError(f"Failed to run flow: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in run_langflow_flow_impl")
        raise ToolError(f"An unexpected error occurred: {e}")

def register_execution_tools(app: FastMCP):
    logger.info("Registering Execution tools...")
    app.tool(name="run_langflow_flow")(run_langflow_flow_impl)