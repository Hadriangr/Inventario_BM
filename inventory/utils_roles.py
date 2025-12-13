
from typing import List

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

from .models_roles import RolEspecial

User = get_user_model()

# Nombre del grupo base de inventario
GRUPO_INVENTARIO_BASE = "InventarioBase"


def obtener_roles_usuario(user: "User") -> List["RolEspecial"]:
    if not user.is_authenticated:
        return []
    return list(RolEspecial.objects.filter(grupo__in=user.groups.all()))


def usuario_es_supervisor(user: "User") -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return any(r.es_supervisor_inventario for r in obtener_roles_usuario(user))


def usuario_ve_todos_los_almacenes(user: "User") -> bool:
    """
    Devuelve True si el usuario puede ver TODOS los almacenes, por alguna de estas razones:
    - Es superusuario.
    - Alguno de sus grupos tiene RolEspecial.acceso_todos_los_almacenes = True.
    - Pertenece al grupo 'InventarioBase' (fallback para simplificar la operación).
    """

    if not user.is_authenticated:
        return False

    # 1) Superusuario siempre ve todo
    if user.is_superuser:
        return True

    # 2) Revisamos roles especiales configurados en el admin
    roles = obtener_roles_usuario(user)
    if any(r.acceso_todos_los_almacenes for r in roles):
        return True

    # 3) Fallback: cualquier usuario del grupo InventarioBase ve todos los almacenes
    if user.groups.filter(name=GRUPO_INVENTARIO_BASE).exists():
        return True

    return False


def usuario_puede_cerrar_conteos(user: "User") -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    roles = obtener_roles_usuario(user)
    return any(r.puede_cerrar_conteos or r.es_supervisor_inventario for r in roles)


def usuario_puede_aplicar_ajustes(user: "User") -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    roles = obtener_roles_usuario(user)
    return any(r.puede_aplicar_ajustes or r.es_supervisor_inventario for r in roles)
