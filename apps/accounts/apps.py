from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        import config  # noqa: F401 - triggers InclusionAdminNode patch

