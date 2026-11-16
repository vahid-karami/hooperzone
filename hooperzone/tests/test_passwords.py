"""Customer passwords follow Django's password rules, not just a minimum length."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import serializers
from rest_framework.test import APIClient

from accounts.passwords import check_password_rules

User = get_user_model()

WEAK = [
    ("12345678", "password_entirely_numeric"),
    ("09121234567", "password_entirely_numeric"),
    ("password", "password_too_common"),
    ("qwertyuiop", "password_too_common"),
    ("short1a", "password_too_short"),
]


class TestRules:
    @pytest.mark.parametrize("password, code", WEAK)
    def test_weak_passwords_are_refused_with_their_rule_code(self, password, code):
        with pytest.raises(serializers.ValidationError) as error:
            check_password_rules(password)
        assert code in error.value.detail["password_codes"]
        assert len(error.value.detail["password"]) == len(error.value.detail["password_codes"])

    def test_password_that_copies_the_username_or_name_is_refused(self):
        for attrs in ({"username": "sara_ahmadi"}, {"first_name": "Sara", "last_name": "ahmadi99x"}):
            with pytest.raises(serializers.ValidationError) as error:
                check_password_rules("ahmadi99x" if "last_name" in attrs else "sara_ahmadi", **attrs)
            assert error.value.detail["password_codes"] == ["password_too_similar"]

    @pytest.mark.parametrize("password", ["securepass123", "کلمه‌عبور۱۲۳", "blue-Kettle-41", "zanoo band 7"])
    def test_ordinary_passwords_pass(self, password):
        check_password_rules(password, username="09121234567", first_name="Sara")
