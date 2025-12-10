from django.contrib.auth import get_user_model

User = get_user_model()


def es_supervisor(user: User) -> bool:
    """
    Devuelve True si el usuario es superusuario o pertenece a los grupos
    que consideramos supervisores de inventario.
    """
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.groups.filter(
        name__in=["SupervisorInventario", "Administrador"]
    ).exists()
