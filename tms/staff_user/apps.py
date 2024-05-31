from django.apps import AppConfig

class StaffUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff_user'

    def ready(self):
        import staff_user.signals  # Ensure signals are imported when the app is ready

