

from django.contrib import admin
from .utils_roles import usuario_ve_todos_los_almacenes


class SoloAlmacenesUsuarioMixin(admin.ModelAdmin):
    """
    Limita el acceso a almacenes según reglas configurables.
    Si un usuario tiene un rol con acceso total, ve todos los almacenes.
    Si no, ve solo los almacenes a los que esté asignado individualmente.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if usuario_ve_todos_los_almacenes(request.user):
            return qs
        return qs.filter(
            almacen__in=request.user.almacenes_asignados.all()
        ).distinct()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "almacen" and not usuario_ve_todos_los_almacenes(request.user):
            kwargs["queryset"] = request.user.almacenes_asignados.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
