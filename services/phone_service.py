import re

COUNTRY_CODES = [
    {'code': '+1', 'country': 'USA / Canada', 'flag': '🇺🇸'},
    {'code': '+44', 'country': 'United Kingdom', 'flag': '🇬🇧'},
    {'code': '+91', 'country': 'India', 'flag': '🇮🇳'},
    {'code': '+61', 'country': 'Australia', 'flag': '🇦🇺'},
    {'code': '+49', 'country': 'Germany', 'flag': '🇩🇪'},
    {'code': '+33', 'country': 'France', 'flag': '🇫🇷'},
    {'code': '+81', 'country': 'Japan', 'flag': '🇯🇵'},
    {'code': '+65', 'country': 'Singapore', 'flag': '🇸🇬'},
    {'code': '+971', 'country': 'UAE', 'flag': '🇦🇪'},
    {'code': '+41', 'country': 'Switzerland', 'flag': '🇨🇭'}
]

class PhoneService:
    @staticmethod
    def get_supported_country_codes():
        return COUNTRY_CODES

    @staticmethod
    def validate_phone(phone_str):
        """
        Validates phone number format with country code support.
        Returns: (is_valid: bool, cleaned_or_formatted: str, error_message: str or None)
        """
        if not phone_str or not str(phone_str).strip():
            return False, "", "Phone number cannot be empty."

        clean = str(phone_str).strip()

        # Check basic allowable characters: digits, +, spaces, hyphens, parentheses, dots
        if not re.match(r'^[0-9+\s\-().]+$', clean):
            return False, clean, "Phone number contains invalid characters. Only digits, +, spaces, hyphens and parentheses are permitted."

        digits_only = re.sub(r'\D', '', clean)
        if len(digits_only) < 7:
            return False, clean, "Phone number is too short (minimum 7 digits required)."
        if len(digits_only) > 15:
            return False, clean, "Phone number exceeds maximum length (maximum 15 digits according to ITU-T E.164)."

        return True, clean, None

    @staticmethod
    def format_phone(country_code, local_number):
        """Combines country code and local number cleanly."""
        code = str(country_code).strip()
        num = str(local_number).strip()
        if not code.startswith('+'):
            code = '+' + code
        return f"{code} {num}".strip()

    @staticmethod
    def split_country_code(phone_str):
        """
        Splits a full phone number into (country_code, local_number).
        Defaults to '+1' if unknown or not prefixed.
        """
        if not phone_str:
            return '+1', ''

        clean = str(phone_str).strip()
        for cc in sorted(COUNTRY_CODES, key=lambda x: len(x['code']), reverse=True):
            if clean.startswith(cc['code']):
                local = clean[len(cc['code']):].strip()
                return cc['code'], local

        if clean.startswith('+'):
            match = re.match(r'^(\+\d{1,4})\s*(.*)$', clean)
            if match:
                return match.group(1), match.group(2)

        return '+1', clean

    @staticmethod
    def mask_phone(phone_str, mask_char='*'):
        """
        Masks the middle portion of a phone number to preserve patient/clinician privacy.
        Example: '+1 (555) 019-2834' -> '+1 (555) ***-**34'
        """
        if not phone_str:
            return '--'

        raw = str(phone_str).strip()
        digits = re.findall(r'\d', raw)
        if len(digits) <= 4:
            return raw

        # Keep first 3 digits and last 2 digits, mask the rest
        digit_count = len(digits)
        unmasked_front = min(3, digit_count // 3)
        unmasked_back = min(2, digit_count // 3)

        masked_chars = []
        seen_digits = 0
        for char in raw:
            if char.isdigit():
                seen_digits += 1
                if seen_digits <= unmasked_front or seen_digits > (digit_count - unmasked_back):
                    masked_chars.append(char)
                else:
                    masked_chars.append(mask_char)
            else:
                masked_chars.append(char)

        return "".join(masked_chars)
