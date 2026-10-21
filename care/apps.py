from django.apps import AppConfig

class CareConfig(AppConfig):
    name = "care"
    def ready(self):
        from . import signals
