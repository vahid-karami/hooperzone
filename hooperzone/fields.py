from rest_framework import serializers

# Persian (۰-۹) and Arabic-Indic (٠-٩) digits -> ASCII.
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_digits(value):
    return value.translate(_DIGITS) if isinstance(value, str) else value


class DigitsCharField(serializers.CharField):
    """CharField that stores Persian/Arabic digits as ASCII, so "۰۹۱۲..." and "0912..." are the same phone."""

    def to_internal_value(self, data):
        return normalize_digits(super().to_internal_value(data))
