import logging
import re
import sys
import hashlib

from google.ads.googleads.client import GoogleAdsClient
from config import GoogleAdsConfig


class GoogleAdsService:
    def __init__(self, config: GoogleAdsConfig):
        self.config = config
    
    def _get_client(self):
        return GoogleAdsClient.load_from_dict(self.config.get_config_dict())

    def upload_offline_conversion(self, raw_lead, conversion_type):
        client = self._get_client()
        client_customer_id = self.config.client_customer_id
        conversion_action_id = self.config.conversion_action_ids.get(conversion_type)

        click_conversion = client.get_type("ClickConversion") 

        if raw_lead.get("email"):
            email_identifier = client.get_type("UserIdentifier")
            email_identifier.hashed_email = self.normalize_and_hash_email_address(
                raw_lead["email"]
            )
            click_conversion.user_identifiers.append(email_identifier)
        if raw_lead.get("phone"):
            phone_identifier = client.get_type("UserIdentifier")
            phone_identifier.hashed_phone_number = self.normalize_and_hash(
                raw_lead["phone"]
            )
            click_conversion.user_identifiers.append(phone_identifier)
        
        conversion_action_service = client.get_service("ConversionActionService")
        click_conversion.conversion_action = (
            conversion_action_service.conversion_action_path(
                client_customer_id, conversion_action_id
            )
        )

        click_conversion.conversion_date_time = raw_lead["conversion_date_time"]
        click_conversion.conversion_value = raw_lead.get("conversion_value", 1)
        click_conversion.currency_code = raw_lead.get("currency_code", "USD")
        
        if raw_lead.get("order_id"):
            click_conversion.order_id = raw_lead["order_id"]
        if raw_lead.get("gclid"):
            click_conversion.gclid = raw_lead["gclid"]
        if raw_lead["ad_user_data_consent"]:
            click_conversion.consent.ad_user_data = client.enums.ConsentStatusEnum[
                raw_lead["ad_user_data_consent"]
            ]

        conversion_upload_service = client.get_service("ConversionUploadService")
        return conversion_upload_service.upload_click_conversions(
            customer_id=client_customer_id,
            conversions=[click_conversion]
            partial_failure=True
        )


    def normalize_and_hash_email_address(self, email_address):
        """Returns the result of normalizing and hashing an email address.

        For this use case, Google Ads requires removal of any '.' characters
        preceding "gmail.com" or "googlemail.com"

        Args:
            email_address: An email address to normalize.

        Returns:
            A normalized (lowercase, removed whitespace) and SHA-265 hashed string.
        """
        normalized_email = email_address.strip().lower()
        email_parts = normalized_email.split("@")

        # Check that there are at least two segments
        if len(email_parts) > 1:
            # Checks whether the domain of the email address is either "gmail.com"
            # or "googlemail.com". If this regex does not match then this statement
            # will evaluate to None.
            if re.match(r"^(gmail|googlemail)\.com$", email_parts[1]):
                # Removes any '.' characters from the portion of the email address
                # before the domain if the domain is gmail.com or googlemail.com.
                email_parts[0] = email_parts[0].replace(".", "")
                normalized_email = "@".join(email_parts)

        return self.normalize_and_hash(normalized_email)


    def normalize_and_hash(self, s):
        """Normalizes and hashes a string with SHA-256.

        Private customer data must be hashed during upload, as described at:
        https://support.google.com/google-ads/answer/7474263

        Args:
            s: The string to perform this operation on.

        Returns:
            A normalized (lowercase, removed whitespace) and SHA-256 hashed string.
        """
        return hashlib.sha256(s.strip().lower().encode()).hexdigest()
