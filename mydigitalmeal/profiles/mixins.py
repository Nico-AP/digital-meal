from django.contrib.auth.mixins import AccessMixin

from mydigitalmeal.profiles.models import MDMProfile


class LoginAndProfileRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated and has an MDMProfile."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        profile, _ = MDMProfile.objects.get_or_create(user=request.user)
        request.mdm_profile = profile

        # TODO: If profile is newly created, redirect to donation step/entry
        # point after the authentication step. Otherwise, figure out where to
        # route user to

        return super().dispatch(request, *args, **kwargs)
