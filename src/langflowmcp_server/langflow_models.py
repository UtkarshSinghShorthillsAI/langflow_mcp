from pydantic import BaseModel, Field, HttpUrl
from typing import Any, Dict, List, Optional, Union
from enum import Enum

# --- Enums from API Spec ---
class AccessTypeEnum(str, Enum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"


# --- Custom Exceptions ---
class LangflowAuthException(Exception): pass
class LangflowApiException(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
    def __str__(self):
        return f"Langflow API Error {self.status_code}: {self.message}"

# --- Client Credentials ---
class LangflowClientCreds(BaseModel):
    api_key: str = Field(..., description="API Key for Langflow authentication.")
    url: Optional[HttpUrl] = Field(None, description="Optional Langflow Base URL override.")

# --- Flow Execution Models ---
class RunFlowRequest(BaseModel):
    input_value: str
    session_id: Optional[str] = None
    input_type: str = "chat"
    output_type: str = "chat"
    output_component: Optional[str] = None
    tweaks: Optional[Dict[str, Dict[str, Any]]] = None

class RunFlowResponse(BaseModel):
    session_id: str
    outputs: List[Dict[str, Any]]

class StreamEvent(BaseModel):
    event: str
    data: Dict[str, Any]

# --- Project Models ---
class ProjectModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = Field(None, alias="parent_id")

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None

# --- Flow Data Structure Models ---
class FlowNodeData(BaseModel):
    data: Dict[str, Any]
    id: str
    type: str

class FlowEdge(BaseModel):
    source: str
    target: str
    sourceHandle: str
    targetHandle: str
    id: str

class FlowData(BaseModel):
    nodes: List[FlowNodeData]
    edges: List[FlowEdge]
    viewport: Dict[str, Any]

# --- Flow Models ---
class FlowModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    data: Optional[FlowData] = None
    is_component: bool = False
    updated_at: str
    webhook: bool = False
    endpoint_name: Optional[str] = None
    locked: bool = False
    user_id: Optional[str] = None
    folder_id: Optional[str] = None  # Renamed from project_id to match API response

    # New fields to match the API response from the image
    icon: Optional[str] = None
    icon_bg_color: Optional[str] = None
    gradient: Optional[str] = None
    tags: Optional[List[Any]] = None  # Using List[Any] as the tag structure is not fully visible
    mcp_enabled: bool = False
    action_name: Optional[str] = None
    action_description: Optional[str] = None
    access_type: AccessTypeEnum = AccessTypeEnum.PRIVATE

class CreateFlowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    data: Optional[FlowData] = None
    folder_id: Optional[str] = None # Renamed for consistency

class UpdateFlowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    data: Optional[FlowData] = None
    folder_id: Optional[str] = None # Renamed for consistency

class AllFlowsResponse(BaseModel):
    count: int
    flows: List[FlowModel]

class FlowsListResponse(BaseModel):
    """A structured response for listing flows, including pagination details."""
    total_count: int = Field(description="The total number of flows matching the criteria.")
    flows: List[FlowModel] = Field(description="The list of flows retrieved.")
    page: Optional[int] = Field(None, description="The current page number, if paginated.")
    size: Optional[int] = Field(None, description="The number of items per page, if paginated.")
    pages: Optional[int] = Field(None, description="The total number of pages, if paginated.")

# --- Utility Models ---
class VersionResponse(BaseModel):
    version: str

class ConfigResponse(BaseModel):
    feature_flags: Dict[str, bool]
    frontend_timeout: int
    auto_saving: bool
    auto_saving_interval: int
    max_file_size_upload: int

class GenericSuccessMessage(BaseModel):
    message: str