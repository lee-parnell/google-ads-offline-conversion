import requests
import logging

from typing import Any
from config import KommoConfig


logger = logging.getLogger(__name__)


class KommoService:
    def __init__(self, config: KommoConfig):
        self.config = config

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "accept": "application/json",
        }

    def _build_url(self, endpoint):
        return (
            self.config.base_url.format(subdomain=self.config.subdomain)
            + endpoint
        )

    def _request(self, method, endpoint, params=None, json=None):
        url = self._build_url(endpoint)

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Request to %s failed. Exception: %s", url, e)
            raise RuntimeError(
                f"{method.upper()} request to {endpoint} failed"
            ) from e

    def get_incoming_leads(
        self, is_sorted=True, filter_pipeline=True, page=1, limit=10
    ):
        params: dict[str, Any] = {"limit": limit, "page": page}

        if is_sorted:
            params["order[created_at]"] = "desc"
        if filter_pipeline:
            params["filter[pipeline_id]"] = self.config.target_pipeline_id

        return self._request("GET", "/leads/unsorted", params=params)

    def get_incoming_lead_by_id(self, lead_id):
        return self._request("GET", f"/leads/unsorted/{lead_id}")

    def get_latest_incoming_lead_id(self):
        leads = self.get_incoming_leads()

        return int(
            leads["_embedded"]["unsorted"][0]["_embedded"]["leads"][0]["id"]
        )

    def update_lead(self, lead_id, source, gclid=None, page_path="/"):
        custom_fields_values = [
            {
                "field_id": self.config.field_ids["source"],
                "values": [{"value": source}],
            },
            {
                "field_id": self.config.field_ids["gclid"],
                "values": [{"value": gclid}],
            },
            {
                "field_id": self.config.field_ids["page_path"],
                "values": [{"value": page_path}],
            },
        ]

        return self._request(
            "PATCH",
            f"/leads/{lead_id}",
            json={"custom_fields_values": custom_fields_values},
        )
