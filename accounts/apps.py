from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import flexyride_corporate  # noqa: F401 - triggers InclusionAdminNode patch

