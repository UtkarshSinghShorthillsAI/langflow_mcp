from pydantic import BaseModel, Field, HttpUrl
from typing import Any, Dict, List, Optional, Union

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
    node: Dict[str, Any]
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
    webhook: bool
    endpoint_name: Optional[str] = None
    locked: bool = False
    user_id: str
    project_id: Optional[str] = None

class CreateFlowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    data: Optional[FlowData] = None
    project_id: Optional[str] = None

class UpdateFlowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    data: Optional[FlowData] = None
    project_id: Optional[str] = None

class AllFlowsResponse(BaseModel):
    count: int
    flows: List[FlowModel]

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