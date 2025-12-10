from django.db import models
from django.contrib.auth.models import Group

class RolEspecial(models.Model):
    """
    Configura los permisos funcionales asociados a un *grupo*.
    Permite que todo sea administrable desde el Django Admin.
    """

    grupo = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name="rol_especial",
        help_text="Seleccione el grupo al que desea asignar permisos especiales.",
    )

    # ---- Permisos funcionales ----

    es_supervisor_inventario = models.BooleanField(
        default=False,
        help_text="Puede aprobar conteos con diferencias críticas y aplicar ajustes.",
    )

    acceso_todos_los_almacenes = models.BooleanField(
        default=False,
        help_text="Puede ver y operar todos los almacenes sin necesidad de estar asignado en ellos.",
    )

    puede_cerrar_conteos = models.BooleanField(
        default=False,
        help_text="Puede cerrar conteos de inventario (sin necesidad de ser supervisor).",
    )

    puede_aplicar_ajustes = models.BooleanField(
        default=False,
        help_text="Puede ejecutar la acción de 'Aplicar ajustes de inventario' en los conteos.",
    )

    # Campos extra que podrían servir en el futuro
    puede_ver_costos = models.BooleanField(default=False)
    puede_editar_costos = models.BooleanField(default=False)
    puede_gestionar_insumos = models.BooleanField(default=False)
    puede_gestionar_recetas = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Rol especial"
        verbose_name_plural = "Roles especiales"

    def __str__(self):
        return f"Permisos especiales de grupo: {self.grupo.name}"