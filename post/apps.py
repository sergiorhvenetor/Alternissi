from django.apps import AppConfig


class PostConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'post'
    verbose_name = 'Gestión de Tienda' # Nombre más descriptivo para el admin

    def ready(self):
        # Importar señales aquí para que se registren cuando la app esté lista
        import post.signals