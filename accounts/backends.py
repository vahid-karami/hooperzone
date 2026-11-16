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

        # Phone and username are each unique, but one person's username or email can equal
        # another's phone. Check every match (own phone first) instead of whichever row the
        # database returns first, or a look-alike account would lock the real owner out.
        matches = list(
            UserModel.objects.filter(
                Q(username__iexact=identifier)
                | Q(phone__iexact=identifier)
                | Q(email__iexact=identifier)
            ).order_by("id")[:10]
        )
        if not matches:
            UserModel().set_password(password)  # same work as a real check: don't reveal who exists
            return None
        matches.sort(key=lambda u: (u.phone != identifier, (u.username or "").lower() != identifier.lower()))
        for user in matches:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
