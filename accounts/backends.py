from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class PhoneOrUsernameBackend(ModelBackend):
    """
    Authenticate against username, phone, or email.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = kwargs.get("phone") or username or kwargs.get("username")
        if not identifier or not password:
            return None

        try:
            user = UserModel.objects.filter(
                Q(username__iexact=identifier)
                | Q(phone__iexact=identifier)
                | Q(email__iexact=identifier)
            ).first()
        except UserModel.DoesNotExist:
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
