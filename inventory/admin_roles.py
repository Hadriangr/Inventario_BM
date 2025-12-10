

from django.contrib import admin
from .models_roles import RolEspecial

@admin.register(RolEspecial)
class RolEspecialAdmin(admin.ModelAdmin):
    list_display = (
        "grupo",
        "es_supervisor_inventario",
        "acceso_todos_los_almacenes",
        "puede_cerrar_conteos",
        "puede_aplicar_ajustes",
    )
    list_filter = (
        "es_supervisor_inventario",
        "acceso_todos_los_almacenes",
    )
    search_fields = ("grupo__name",)
