import phonenumbers
import pycountry
from phonenumbers import NumberParseException

class CountryDetector:
    @staticmethod
    def detect_country(phone_number: str) -> str:
        """ Detects and returns the country name using phone number.
            Detection happens in granular level using region codes
            because some country codes are used by multiple countires.
        """
        try:
            parsed = phonenumbers.parse(phone_number)
            if not phonenumbers.is_valid_number(parsed):
                return "Invalid"

            region_code = phonenumbers.region_code_for_number(parsed)
            country = pycountry.countries.get(alpha2=region_code)
            return country or "Invalid"

        except NumberParseException:
            return "Invalid"
