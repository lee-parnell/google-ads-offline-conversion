import requests
import logging

from typing import Any
from config import KommoConfig


logger = logging.getLogger(__name__)


class KommoService:
    def __init__(self, config: KommoConfig):
        self.config = config

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "accept": "application/json",
        }

    def _build_url(self, endpoint, api_version="v4"):
        base_url = self.config.base_url.format(
            subdomain=self.config.subdomain
        ).replace("v4", f"{api_version}")

        return base_url + endpoint

    def _request(self, method, endpoint, params=None, json=None):
        url = self._build_url(endpoint)

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                headers=self._headers,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Request to %s failed. Exception: %s", url, e)
            raise RuntimeError(
                f"{method.upper()} request to {endpoint} failed"
            ) from e

    def _get_contact_field_ids(self):
        return {
            self.config.field_ids.get("phone"),
            self.config.field_ids.get("email"),
        }

    def _get_lead_field_ids(self):
        return {
            self.config.field_ids.get("gclid"),
            self.config.field_ids.get("gbraid"),
            self.config.field_ids.get("conversion_value"),
            self.config.field_ids.get("currency_code"),
            self.config.field_ids.get("conversion_time"),
        }

    def _create_order_id(self, lead_id):
        return {"order_id": f"order_{lead_id}"}

    def _get_contact_data(self, contact_id):
        """Returns phone and email values of contact.

        Args:
            contact_id(int): Kommo contact id associated with the lead.

        Returns:
            Dictionary that contains email and phone values
        """

        contact_data = {}
        contact_field_ids = self._get_contact_field_ids()

        contact = self._request("GET", f"/contacts/{contact_id}")

        for field in contact.get("custom_fields_values", []):
            field_id = field.get("field_id")
            if field_id in contact_field_ids:
                contact_data[field["field_name"].lower()] = field.get("values")[
                    0
                ]["value"]
        return contact_data

    def _get_lead_ids_by_pipeline(
        self, pipeline_id, stage_id, starts_at, ends_at
    ):
        """Returns a filtered list based on pipeline id that contains lead ids.

        Args:
            pipeline_id(int): Kommo pipeline stage id.
            starts_at(int): Unix timestamp that denotes task starting time.
            ends_at(int): Unix timestamp that denotes task ending time.

        Returns:
            A list that contains lead ids.
        """

        params = {
            "filter[statuses][0][pipeline_id]": pipeline_id,
            "filter[statuses][0][status_id]": stage_id,
            "filter[closest_task_at][from]": starts_at,
            "filter[closest_task_at][to]": ends_at,
        }

        raw_filtered_leads = self._request("GET", "/leads", params=params)

        return list(
            map(
                lambda lead: lead["id"],
                raw_filtered_leads["_embedded"]["leads"],
            )
        )

    def run_salesbot_on_leads(self, salesbot_id, lead_ids):
        """Executes salesbot on each lead.

        Args:
            salesbot_id(int): Kommo salesbot id.
            lead_ids(list): A list that contains Kommo lead ids.
        """
        url = self._build_url(endpoint="/salesbot/run", api_version="v2")

        body = [
            {
                "bot_id": salesbot_id,
                "entity_id": id,
                "entity_type": 2,  # denotes lead entity type in Kommo
            }
            for id in lead_ids
        ]

        requests.post(url=url, json=body, headers=self._headers)

    def construct_raw_lead(self, lead_id):
        """Returns a dict that contains lead info.

        Args:
            lead_id(int): Kommo lead id.

        Returns:
            A dictionary that contains lead details such as email, phone, gclid, etc.
        """
        contact_data = self.get_contact_info(lead_id)
        order_id = self._create_order_id(lead_id)

        lead_data = {}
        raw_lead = self.get_lead_by_id(lead_id=lead_id)
        lead_field_ids = self._get_lead_field_ids()

        for field in raw_lead.get("custom_fields_values", {}):
            if field.get("field_id") in lead_field_ids:
                lead_data[field.get("field_name")] = field["values"][0]["value"]

        return {**lead_data, **contact_data, **order_id}

    def get_lead_by_id(self, lead_id):
        params = {"with": "contacts"}

        return self._request("GET", f"/leads/{lead_id}", params=params)

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
        params = {"with": "contacts"}

        return self._request("GET", f"/leads/unsorted/{lead_id}", params=params)

    def get_contact_info(self, lead_id):
        """Retrives email and phone values using the lead id.

        Args:
            lead_id(int): Kommo lead id.

        Returns:
            Dictionary that contains email and phone values
        """

        lead_info = self.get_lead_by_id(lead_id=lead_id)
        contact_id = lead_info["_embedded"]["contacts"][0]["id"]

        return self._get_contact_data(contact_id=contact_id)

    def get_latest_incoming_lead_id(self):
        leads = self.get_incoming_leads()

        return int(
            leads["_embedded"]["unsorted"][0]["_embedded"]["leads"][0]["id"]
        )

    def update_lead(
        self, lead_id, source, gclid=None, gbraid=None, page_path="/"
    ):
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
                "field_id": self.config.field_ids["gbraid"],
                "values": [{"value": gbraid}],
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
