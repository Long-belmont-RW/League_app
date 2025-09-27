from django.apps import AppConfig


class LeagueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'league'

    def ready(self):
        # This imports the signals so they are registered when Django starts.
        import league.signals
