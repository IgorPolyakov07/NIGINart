import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import streamlit as st
from dashboard.config import API_BASE_URL, DEFAULT_METRICS_LIMIT, DEFAULT_LOGS_LIMIT
class APIClient:
    def __init__(self, base_url: str = API_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
    def get_accounts(
        self,
        platform: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict]:
        params = {}
        if platform:
            params["platform"] = platform
        if is_active is not None:
            params["is_active"] = is_active
        response = self.client.get("/accounts", params=params)
        response.raise_for_status()
        return response.json()
    def update_account_status(self, account_id: UUID, is_active: bool) -> Dict:
        response = self.client.patch(
            f"/accounts/{account_id}",
            json={"is_active": is_active}
        )
        response.raise_for_status()
        return response.json()
    def get_metrics(
        self,
        account_id: Optional[UUID] = None,
        platform: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = DEFAULT_METRICS_LIMIT
    ) -> List[Dict]:
        params = {"limit": limit}
        if account_id:
            params["account_id"] = str(account_id)
        if platform:
            params["platform"] = platform
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        response = self.client.get("/metrics", params=params)
        response.raise_for_status()
        return response.json()
    def get_collection_logs(self, limit: int = DEFAULT_LOGS_LIMIT) -> List[Dict]:
        response = self.client.get("/logs", params={"limit": limit})
        response.raise_for_status()
        return response.json()
    def trigger_collection(self, platform: Optional[str] = None) -> Dict:
        payload = {}
        if platform:
            payload["platform"] = platform
        response = self.client.post("/collect", json=payload)
        response.raise_for_status()
        return response.json()
    def health_check(self) -> Dict:
        response = self.client.get("/health")
        response.raise_for_status()
        return response.json()
    def close(self):
        self.client.close()
@st.cache_resource
def get_api_client() -> APIClient:
    return APIClient()
