
import hashlib
import logging
import re
import threading

from config import GoogleAdsConfig
from datetime import datetime, timedelta, timezone
from enum import Enum
from google.ads.googleads.client import GoogleAdsClient

# logger 
logger = logging.getLogger(__name__)

class GoogleAdsService:
    """ Services for interacting with Google Ads API to upload offline conversions.
    """
    class ConversionType(Enum):
        """ Supported offline conversion types used in Google Ads

        Keys map to specific conversion actions configured in
        Google Ads UI. Enum values are used to retrive the 
        corresponding conversion_action_id from the config.
        """
        MESSAGE_RECEIVED = ("kommo_message_received", 5)
        APPOINTMENT_MADE = ("appointment_made", 40)
        CONVERTED_LEAD = ("converted_lead", 500)

        def __init__(self, ads_conversion_name, default_conversion_value):
            self._conversion_name = ads_conversion_name
            self._default_conversion_value = default_conversion_value

        @property
        def conversion_name(self):
            return self._conversion_name

        @property
        def default_conversion_value(self):
            return self._default_conversion_value

    def __init__(self, config: GoogleAdsConfig):
        """ Initializes the GoogleAdsService using the passed config.

        Args:
            config (GoogleAdsConfig): Google Ads configuration object.
        """
        self.config = config
        self._client = None
        self._lock = threading.Lock()
    
    def _get_client(self):
        """ Creates a Google Ads Client constructed by config dict.
        """

        # lazy singleton pattern
        # double check is added because of critical section
        if not self._client:
            with self._lock:
                if not self._client:
                    self._client =  GoogleAdsClient.load_from_dict(
                        self.config.get_config_dict()
                    )
        return self._client

    def upload_offline_conversion(self, raw_lead, conversion_type):
        """ Uploads an offline conversion to Google Ads using the specified conversion type.

        Args: 
            raw_lead(dict): a dict that contains lead details such as email, phone, gclid, etc.
            conversion_type(ConversionType): an enum that indicates the corresponding conversion action

        Returns:
            MutateClickConversionResponse: Response from Google Ads API.

        Raises:
            GoogleAdsException: If the click conversion upload fails due to a Google Ads API error.
        """
        logger.info("Received raw lead %s", raw_lead)
        try:

            client = self._get_client()

            client_customer_id = self.config.client_customer_id
            conversion_action_id = self.config.conversion_action_ids.get(conversion_type.conversion_name)

            click_conversion = self._create_click_conversion(client, raw_lead, conversion_type) 
            self._add_user_identifiers(client, raw_lead, click_conversion)
           
            conversion_action_service = client.get_service("ConversionActionService")
            click_conversion.conversion_action = (
                conversion_action_service.conversion_action_path(
                    client_customer_id, conversion_action_id
                )
            )
            
            conversion_upload_service = client.get_service("ConversionUploadService")
            
            res = conversion_upload_service.upload_click_conversions(
                customer_id=client_customer_id,
                conversions=[click_conversion],
                partial_failure=True
            )
            logger.info("Google Ads response: %s", res)
            return res
        except Exception as e:
            logger.info("exception occured %s", e)

    def _create_click_conversion(self, client, raw_lead, conversion_type):
        """ Creates a Google Ads API ClickConversion object from raw lead data.

            Args: 
                client(GoogleAdsClient): A GoogleAdsAPI client.
                raw_lead(dict): a dict that contains lead details such as email, phone, gclid, etc.

            Returns:
                A ClickConversion object that is populated with lead data.
            """
        click_conversion = client.get_type("ClickConversion")
        click_conversion.conversion_date_time = self._format_time(
            raw_lead.get("conversion_date_time", datetime.now(timezone.utc).timestamp()))
        click_conversion.conversion_value = float(raw_lead.get("conversion_value", conversion_type.default_conversion_value))
        click_conversion.currency_code = raw_lead.get("currency_code", "USD")
 
        if raw_lead.get("order_id"):
            click_conversion.order_id = raw_lead["order_id"]

        # Ads API does not allow multiple click identifiers
        # Store gbraid if gclid is not present, since gclid has 
        # more data point
        if raw_lead.get("gclid"):
            click_conversion.gclid = raw_lead["gclid"]
        elif raw_lead.get("gbraid"):
            click_conversion.gbraid= raw_lead["gbraid"]

        click_conversion.consent.ad_user_data = client.enums.ConsentStatusEnum.GRANTED
        click_conversion.consent.ad_personalization = client.enums.ConsentStatusEnum.GRANTED

        return click_conversion

    def _add_user_identifiers(self, client, raw_lead, click_conversion):
        """ Adds UserIdentifier objects to ClickConversion object.
            
            Args:
                raw_lead(dict): a dict that contains lead details such as email, phone, gclid, etc.
                client(GoogleAdsClient): A GoogleAdsAPI client.
                click_conversion(ClickConversion): A Google Ads ClickConversion object.
        """
        if raw_lead.get("email"):
            email_identifier = client.get_type("UserIdentifier")
            email_identifier.hashed_email = self._normalize_and_hash_email_address(
                raw_lead["email"].lower()
            )
            email_identifier.user_identifier_source = client.enums.UserIdentifierSourceEnum.FIRST_PARTY
            click_conversion.user_identifiers.append(email_identifier)

        if raw_lead.get("phone"):
            phone_identifier = client.get_type("UserIdentifier")
            phone_identifier.hashed_phone_number = self._normalize_and_hash(
                raw_lead["phone"]
            )
            phone_identifier.user_identifier_source = client.enums.UserIdentifierSourceEnum.FIRST_PARTY
            click_conversion.user_identifiers.append(phone_identifier)
 
    def _normalize_and_hash_email_address(self, email_address):
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
            if re.match(r"^(gmail|googlemail)\.com$", email_parts[1]):
                email_parts[0] = email_parts[0].replace(".", "")
                normalized_email = "@".join(email_parts)

        return self._normalize_and_hash(normalized_email)

    def _normalize_and_hash(self, s):
        """Normalizes and hashes a string with SHA-256.

        Private customer data must be hashed during upload, as described at:
        https://support.google.com/google-ads/answer/7474263

        Args:
            s: The string to perform this operation on.

        Returns:
            A normalized (lowercase, removed whitespace) and SHA-256 hashed string.
        """
        return hashlib.sha256(s.strip().lower().encode()).hexdigest()
    
    def _format_time(self, utc_timestamp):
        """ Formats the time as it is specified in Google Ads API.
            
            Args:
                utc_timestamp(float): Unix timestamp

            Returns: 
                Formatted datetime string. 
                (e.g.): yyyy-mm-dd hh:mm:ss+|-hh:mm, 2019-01-01 12:32:45-08:00
        """
        # convert timestamp to datetime in UTC
        datetime_utc = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)

        # convert to GMT+3 time for consistency
        gmt_plus_3 = timezone(timedelta(hours=3))
        time = datetime_utc.astimezone(gmt_plus_3)
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S%z")

        return formatted_time[:-2] + ":" + formatted_time[-2:]
