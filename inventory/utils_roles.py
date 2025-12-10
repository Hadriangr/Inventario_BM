

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models_roles import RolEspecial


User = get_user_model()


def obtener_roles_usuario(user: User) -> list[RolEspecial]:
    """Devuelve una lista con los objetos RolEspecial asociados a los grupos del usuario."""
    if not user.is_authenticated:
        return []
    roles = RolEspecial.objects.filter(grupo__in=user.groups.all())
    return list(roles)


def usuario_es_supervisor(user: User) -> bool:
    """True si alguno de sus grupos es supervisor de inventario."""
    return any(r.es_supervisor_inventario for r in obtener_roles_usuario(user)) or user.is_superuser


def usuario_ve_todos_los_almacenes(user: User) -> bool:
    """True si un grupo le da acceso a todos los almacenes."""
    if user.is_superuser:
        return True
    return any(r.acceso_todos_los_almacenes for r in obtener_roles_usuario(user))


def usuario_puede_cerrar_conteos(user: User) -> bool:
    if user.is_superuser:
        return True
    return any(r.puede_cerrar_conteos or r.es_supervisor_inventario for r in obtener_roles_usuario(user))


def usuario_puede_aplicar_ajustes(user: User) -> bool:
    if user.is_superuser:
        return True
    return any(r.puede_aplicar_ajustes or r.es_supervisor_inventario for r in obtener_roles_usuario(user))
