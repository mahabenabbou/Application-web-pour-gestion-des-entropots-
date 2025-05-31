from django.apps import AppConfig


class PfaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pfa'
    verbose_name = 'Gestion des Stocks'
    
    def ready(self):
        """
        Importe les signaux quand l'application est prête
        Cette méthode est appelée automatiquement par Django
        """
        try:
            import pfa.signals  # Remplacez par le nom de votre app
        except ImportError:
            pass