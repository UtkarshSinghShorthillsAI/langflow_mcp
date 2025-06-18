import httpx
import logging
from typing import Any, Dict, Optional, Type, TypeVar, AsyncIterator, List

from pydantic import BaseModel, ValidationError
from .langflow_models import LangflowApiException, LangflowAuthException, GenericSuccessMessage

logger = logging.getLogger(__name__)
ResponseType = TypeVar("ResponseType", bound=BaseModel)

class LangflowApiClient:
    """An asynchronous client for the Langflow REST API."""

    def __init__(self, base_url: str, httpx_client: httpx.AsyncClient):
        self._base_url = base_url.rstrip('/')
        self._httpx_client = httpx_client

    @classmethod
    async def create(cls, base_url: str, api_key: str) -> "LangflowApiClient":
        if not api_key:
            raise LangflowAuthException("API key must be provided.")
        
        headers = {
            "accept": "application/json",
            "x-api-key": api_key,
        }
        httpx_client = httpx.AsyncClient(headers=headers, timeout=30.0)
        
        try:
            await httpx_client.get(f"{base_url.rstrip('/')}/api/v1/version")
        except httpx.RequestError as e:
            raise LangflowApiException(0, f"Failed to connect to Langflow at {base_url}: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LangflowAuthException("Authentication failed. The provided API key is invalid.") from e
            raise LangflowApiException(e.response.status_code, f"Failed to connect to Langflow: {e.response.text}") from e

        return cls(base_url, httpx_client)

    async def close(self):
        if not self._httpx_client.is_closed:
            await self._httpx_client.aclose()
            logger.debug("Langflow API HTTP client closed.")

    async def _request(self, method: str, path: str, response_model: Optional[Type[ResponseType]] = None, **kwargs):
        url = f"{self._base_url}{path}"
        try:
            response = await self._httpx_client.request(method, url, **kwargs)
            response.raise_for_status()

            if response.status_code == 204:
                return None
            
            response_json = response.json()
            if response_model:
                return response_model.model_validate(response_json)
            return response_json
        except httpx.HTTPStatusError as e:
            raise LangflowApiException(e.response.status_code, e.response.text) from e
        except (ValidationError, ValueError) as e:
            raise LangflowApiException(0, f"Failed to parse API response: {e}") from e
        except httpx.RequestError as e:
            raise LangflowApiException(0, f"HTTP request failed: {e}") from e

    # --- Project CRUD Methods ---
    async def list_projects(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/api/v1/projects/")

    async def create_project(self, data: BaseModel) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/projects/", json=data.model_dump(exclude_none=True))

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/api/v1/projects/{project_id}")

    async def update_project(self, project_id: str, data: BaseModel) -> Dict[str, Any]:
        return await self._request("PATCH", f"/api/v1/projects/{project_id}", json=data.model_dump(exclude_none=True))

    async def delete_project(self, project_id: str):
        await self._request("DELETE", f"/api/v1/projects/{project_id}")

    # --- Flow CRUD Methods ---
    async def list_flows(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/flows/")

    async def create_flow(self, data: BaseModel) -> Dict[str, Any]:
        return await self._request("POST", "/api/v1/flows/", json=data.model_dump(exclude_none=True))

    async def get_flow(self, flow_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/api/v1/flows/{flow_id}")

    async def update_flow(self, flow_id: str, data: BaseModel) -> Dict[str, Any]:
        return await self._request("PATCH", f"/api/v1/flows/{flow_id}", json=data.model_dump(exclude_none=True))

    async def delete_flow(self, flow_id: str) -> GenericSuccessMessage:
        return await self._request("DELETE", f"/api/v1/flows/{flow_id}", response_model=GenericSuccessMessage)

    # --- Execution Methods ---
    async def run_flow(self, flow_id: str, data: BaseModel) -> Dict[str, Any]:
        return await self._request("POST", f"/api/v1/run/{flow_id}", json=data.model_dump(exclude_none=True))

    # --- Utility Methods ---
    async def get_all_components(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/all")
        
    async def get_version(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/version")

    async def get_config(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/config")