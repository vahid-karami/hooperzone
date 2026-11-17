"""Password rules for customers: the validators in settings.AUTH_PASSWORD_VALIDATORS.

Django only runs these in its own forms (admin, createsuperuser). The API sets passwords
itself, so every endpoint that does must call `check_password_rules` first.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers


def check_password_rules(password, user=None, **attrs):
    """Raise a DRF error if `password` breaks a rule.

    `user` is the account the password is for; for a new account pass what the form holds
    (username, first_name, last_name, email) so a password that copies them is refused.
    The error carries the rule codes next to the English messages, so the storefront can
    show its own Persian text: {"password": [...], "password_codes": ["password_too_common"]}.
    """
    if user is None:
        user = get_user_model()(**{k: v for k, v in attrs.items() if v})
    try:
        validate_password(password, user=user)
    except ValidationError as e:
        raise serializers.ValidationError({
            "password": list(e.messages),
            "password_codes": [error.code for error in e.error_list],
        }) from e
