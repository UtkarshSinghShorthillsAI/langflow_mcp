import logging
from typing import List, Optional

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from ..langflow_models import LangflowApiException, ProjectModel, CreateProjectRequest, UpdateProjectRequest
from ..app import get_session_langflow_client

logger = logging.getLogger(__name__)

async def list_langflow_projects_impl(ctx: Context) -> List[ProjectModel]:
    """Lists all available projects in Langflow."""
    logger.info("Tool 'list_langflow_projects' called.")
    try:
        client = await get_session_langflow_client(ctx)
        response = await client.list_projects()
        return [ProjectModel.model_validate(p) for p in response]
    except LangflowApiException as e:
        raise ToolError(f"Failed to list projects: {e.message}")

async def create_langflow_project_impl(ctx: Context, name: str, description: Optional[str] = None) -> ProjectModel:
    """Creates a new project in Langflow."""
    logger.info(f"Tool 'create_langflow_project' called with name: {name}")
    try:
        client = await get_session_langflow_client(ctx)
        request_data = CreateProjectRequest(name=name, description=description)
        response = await client.create_project(request_data)
        return ProjectModel.model_validate(response)
    except LangflowApiException as e:
        raise ToolError(f"Failed to create project: {e.message}")

async def update_langflow_project_impl(ctx: Context, project_id: str, name: Optional[str] = None, description: Optional[str] = None) -> ProjectModel:
    """Updates an existing project in Langflow."""
    logger.info(f"Tool 'update_langflow_project' called for project_id: {project_id}")
    try:
        client = await get_session_langflow_client(ctx)
        request_data = UpdateProjectRequest(name=name, description=description)
        response = await client.update_project(project_id, request_data)
        return ProjectModel.model_validate(response)
    except LangflowApiException as e:
        raise ToolError(f"Failed to update project: {e.message}")

async def delete_langflow_project_impl(ctx: Context, project_id: str = Field(..., description="The ID of the project to delete.")):
    """Deletes a project from Langflow."""
    logger.info(f"Tool 'delete_langflow_project' called for project_id: {project_id}")
    try:
        client = await get_session_langflow_client(ctx)
        await client.delete_project(project_id)
        return {"status": "success", "message": f"Project {project_id} deleted."}
    except LangflowApiException as e:
        raise ToolError(f"Failed to delete project: {e.message}")

def register_project_tools(app: FastMCP):
    logger.info("Registering Project tools...")
    app.tool(name="list_langflow_projects")(list_langflow_projects_impl)
    app.tool(name="create_langflow_project")(create_langflow_project_impl)
    app.tool(name="update_langflow_project")(update_langflow_project_impl)
    app.tool(name="delete_langflow_project")(delete_langflow_project_impl)