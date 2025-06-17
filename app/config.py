import os

class KommoConfig():
    def __init__(
        self,
        base_url,
        subdomain,
        access_token,
        target_pipeline,
        field_ids
    ):
        self.base_url = base_url
        self.subdomain: str = subdomain
        self.access_token: str = access_token
        self.target_pipeline_id = target_pipeline
        self.field_ids = field_ids

class GoogleAdsConfig():
    def __init__(
        self, 
        is_enabled,
        developer_token,
        login_customer_id,
        client_customer_id,
        json_key_file_path,
        use_proto_plus,
        conversion_action_ids
    ):
        self.is_enabled = is_enabled
        self.developer_token = developer_token
        self.login_customer_id = login_customer_id
        self.client_customer_id = client_customer_id
        self.json_key_file_path = json_key_file_path
        self.use_proto_plus = use_proto_plus
        self.conversion_action_ids = conversion_action_ids
    
    def get_config_dict(self):
        return {
            "developer_token": self.developer_token,
            "login_customer_id": self.login_customer_id,
            "json_key_file_path": self.json_key_file_path,
            "use_proto_plus": self.use_proto_plus
        }

def load_config():
    """ Loads config objects using env variables.

        Returns Tuple[KommoConfig, GoogleAdsConfig]: KommoConfig and GoogleAdsConfig objects.

        Raises: 
            ValueError: If environment variables are missing.
    """
    kommo_config = KommoConfig(
        os.getenv("KOMMO_BASE_URL"),
        os.getenv("KOMMO_SUBDOMAIN"),
        os.getenv("KOMMO_ACCESS_TOKEN"),
        os.getenv("KOMMO_TARGET_PIPELINE_ID"),
        field_ids={
            "source": int(os.getenv("KOMMO_SOURCE_FIELD_ID")),
            "gclid": int(os.getenv("KOMMO_GCLID_FIELD_ID")),
            "gbraid": int(os.getenv("KOMMO_GBRAID_FIELD_ID")),
            "page_path": int(os.getenv("KOMMO_PAGEPATH_FIELD_ID")),
            "conversion_value": int(os.getenv("KOMMO_CONVERSION_VALUE_FIELD_ID")),
            "currency_code": int(os.getenv("KOMMO_CURRENCY_CODE_FIELD_ID")),
            "conversion_time": int(os.getenv("KOMMO_CONVERSION_TIME_FIELD_ID")),
            "phone": int(os.getenv("KOMMO_PHONE_FIELD_ID")),
            "email": int(os.getenv("KOMMO_EMAIL_FIELD_ID")),
        },
    )

    google_ads_config = GoogleAdsConfig(
        os.getenv("GOOGLE_ADS_IS_ENABLED") == "True",
        os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        os.getenv("GOOGLE_ADS_CLIENT_CUSTOMER_ID"),
        os.getenv("GOOGLE_ADS_JSON_KEY_FILE_PATH"),
        os.getenv("GOOGLE_ADS_USE_PROTO_PLUS"),
        conversion_action_ids={
            "kommo_message_received": os.getenv("GOOGLE_ADS_MESSAGE_RECEIVED_CONVERSION_ACTION_ID"),
            "appointment_made": os.getenv("GOOGLE_ADS_APPOINTMENT_MADE_CONVERSION_ACTION_ID"),
            "converted_lead": os.getenv("GOOGLE_ADS_CONVERTED_LEAD_CONVERSION_ACTION_ID")
        }
    )

    return kommo_config, google_ads_config
