from django.contrib import admin
from django import forms

from .models import (
    UnidadMedida,
    Proveedor,
    Insumo,
    CategoriaInsumo,    
    Almacen,
    StockInsumo,
    Plato,
    RecetaInsumo,
    LoteInsumo,
    MovimientoInventario,
    CategoriaPlato,
    Plato,
    EntradaCompra,
    MenuPlan,
    MenuPlanItem,
    ConteoInventario,
    ConteoInventarioItem,
    EstadoConteo,
)

from .admin_mixin import SoloAlmacenesUsuarioMixin
from .services.conteo import conciliar_conteo
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib import messages
from .utils_roles import (
    usuario_puede_cerrar_conteos,
    usuario_puede_aplicar_ajustes,
    usuario_es_supervisor,
)
from django.contrib.auth import get_user_model
User = get_user_model()





admin.site.site_header = "Administración de Inventario BM"
admin.site.site_title = "Inventario BM"



def aplicar_ajustes_conteo(modeladmin, request, queryset):
    """
    Acción admin: aplica ajustes de inventario según roles configurados.
    """

    if not usuario_puede_aplicar_ajustes(request.user):
        messages.error(
            request,
            "No tiene permiso para aplicar ajustes de inventario."
        )
        return

    exitosos = 0
    saltados = 0

    for conteo in queryset:
        if conteo.estado != EstadoConteo.CERRADO:
            saltados += 1
            continue

        conciliar_conteo(conteo, aplicar_ajustes=True, usuario=request.user)

        conteo.estado = EstadoConteo.AJUSTADO
        conteo.save(update_fields=["estado"])
        exitosos += 1

    if exitosos:
        messages.success(request, f"{exitosos} conteos ajustados correctamente.")

    if saltados:
        messages.warning(request, f"{saltados} conteos omitidos (no estaban cerrados).")



@admin.register(LoteInsumo)
class LoteInsumoAdmin(admin.ModelAdmin):
    list_display = (
        "insumo",
        "almacen",
        "numero_lote",
        "fecha_vencimiento",
        "cantidad_actual",
        "costo_unitario",
        "activo",
    )
    list_filter = (
        "almacen",
        "insumo",
        "activo",
        "fecha_vencimiento",
    )
    search_fields = (
        "insumo__nombre",
        "almacen__nombre",
        "numero_lote",
    )
    autocomplete_fields = ("insumo", "almacen")


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "abreviatura", "es_base", "factor_base", "created_at")
    list_filter = ("es_base",)
    search_fields = ("nombre", "abreviatura")


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "telefono", "activo", "created_at")
    list_filter = ("activo",)
    search_fields = ("nombre", "email", "telefono")

@admin.register(CategoriaInsumo)
class CategoriaInsumoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "created_at")
    list_filter = ("activo",)
    search_fields = ("nombre",)


class InsumoAdminForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = "__all__"
        labels = {
            "unidad": "Unidad de consumo",
            "unidad_compra": "Unidad de compra",
            "factor_conversion": "Factor de conversión",   
        }


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    form = InsumoAdminForm   
    readonly_fields = ("costo_promedio", "created_at", "updated_at")

    list_display = (
        "nombre",
        "categoria",
        "unidad",
        "proveedor_principal",
        "activo",
        "stock_minimo",
        "stock_maximo",
        "costo_promedio",
    )
    list_filter = ("activo", "unidad", "proveedor_principal")
    search_fields = ("nombre",)
    autocomplete_fields = ("unidad", "proveedor_principal", "unidad_compra")

@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "responsable", "activo", "created_at")
    list_filter = ("activo",)
    search_fields = ("nombre", "ubicacion")
    autocomplete_fields = ("responsable",)


@admin.register(StockInsumo)
class StockInsumoAdmin(admin.ModelAdmin):
    list_display = (
        "insumo",
        "almacen",
        "cantidad_actual",
        "costo_promedio",
        "valor_total",
        "updated_at",
    )
    list_filter = ("almacen", "insumo")
    search_fields = ("insumo__nombre", "almacen__nombre")
    autocomplete_fields = ("insumo", "almacen")

    readonly_fields = ("costo_promedio", "created_at", "updated_at")

    def valor_total(self, obj):
        return obj.valor_total


@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio_venta", "activo")
    list_filter = ("activo", "categoria")
    search_fields = ("nombre", "descripcion")
    autocomplete_fields = ("categoria",)


@admin.register(RecetaInsumo)
class RecetaInsumoAdmin(admin.ModelAdmin):
    list_display = ("plato", "insumo", "cantidad", "created_at")
    list_filter = ("plato", "insumo")
    search_fields = ("plato__nombre", "insumo__nombre")
    autocomplete_fields = ("plato", "insumo")


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "tipo",
        "insumo",
        "almacen",
        "cantidad",
        "costo_unitario",
        "costo_total",
        "fecha_movimiento",
        "usuario",
    )
    list_filter = (
        "tipo",
        "almacen",
        "insumo",
        "usuario",
        "fecha_movimiento",
    )
    search_fields = (
        "insumo__nombre",
        "almacen__nombre",
        "motivo",
        "referencia",
    )
    autocomplete_fields = ("insumo", "almacen", "usuario")

    readonly_fields = (
        "costo_total",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (None, {
            "fields": (
                "tipo",
                "insumo",
                "almacen",
                "cantidad",
                "costo_unitario",
                "costo_total",
                "fecha_movimiento",
            )
        }),
        ("Información adicional", {
            "classes": ("collapse",),
            "fields": (
                "motivo",
                "referencia",
                "usuario",
                "created_at",
                "updated_at",
            )
        }),
    )


@admin.register(CategoriaPlato)
class CategoriaPlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", )
    search_fields = ("nombre", )


class EntradaCompraAdminForm(forms.ModelForm):
    class Meta:
        model = EntradaCompra
        fields = "__all__"
        labels = {
            "costo_unitario": "Costo unitario (unidad de consumo)",
        }


@admin.register(EntradaCompra)
class EntradaCompraAdmin(admin.ModelAdmin):
    form = EntradaCompraAdminForm

    list_display = (
        "id",
        "fecha_documento",
        "proveedor",
        "almacen",
        "insumo",
        "cantidad",
        "costo_unitario",
        "procesada",
    )
    list_filter = ("proveedor", "almacen", "procesada", "fecha_documento")
    search_fields = ("numero_documento", "referencia", "observaciones")
    autocomplete_fields = ("proveedor", "almacen", "insumo")
    readonly_fields = ("procesada", "movimiento", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        # Primero guardamos la compra en la BD
        super().save_model(request, obj, form, change)
        # Luego, si aún no está procesada, generamos la entrada de inventario
        if not obj.procesada:
            obj.procesar(usuario=request.user)


class MenuPlanItemInline(admin.TabularInline):
    model = MenuPlanItem
    extra = 3


@admin.register(MenuPlan)
class MenuPlanAdmin(admin.ModelAdmin):
    list_display = ("nombre", "fecha_inicio", "fecha_fin", "almacen", "estado")
    search_fields = ("nombre",)
    list_filter = ("estado", "almacen")
    inlines = [MenuPlanItemInline]


@admin.register(MenuPlanItem)
class MenuPlanItemAdmin(admin.ModelAdmin):
    list_display = ("plan", "fecha", "categoria_plato", "plato", "porciones_planificadas")
    list_filter = ("categoria_plato", "fecha", "plan")
    search_fields = ("plato__nombre", "plan__nombre")


class MenuPlanItemInline(admin.TabularInline):
    model = MenuPlanItem
    extra = 3
    autocomplete_fields = ("plato", "categoria_plato")


class ConteoInventarioItemInline(admin.TabularInline):
    model = ConteoInventarioItem
    extra = 1

    readonly_fields = ("cantidad_sistema", "diferencia", "dentro_tolerancia")

    def has_change_permission(self, request, obj=None):
        # Solo se pueden editar ítems si el conteo está en BORRADOR
        if obj is not None and not obj.es_editable:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not obj.es_editable:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(ConteoInventario)
class ConteoInventarioAdmin(SoloAlmacenesUsuarioMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "fecha",
        "almacen",
        "responsable",
        "estado",
        "tolerancia_porcentaje",
        "tiene_diferencias_criticas",
        "aprobado_por",
        "creado_en",
    )
    list_filter = ("estado", "almacen", "fecha", "responsable")
    search_fields = ("id", "almacen__nombre", "responsable__username")
    date_hierarchy = "fecha"
    inlines = [ConteoInventarioItemInline]

    readonly_fields = ("creado_en", "actualizado_en", "aprobado_por", "aprobado_en")
    actions = [aplicar_ajustes_conteo]
    def get_readonly_fields(self, request, obj=None):
        base = list(self.readonly_fields)
        if obj is not None and not obj.es_editable:
            # Cuando no está en borrador, no permitimos cambiar cabecera crítica
            base += [
                "fecha",
                "almacen",
                "responsable",
                "tolerancia_porcentaje",
                "tolerancia_unidades",
            ]
        return base
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """
        Oculta el estado AJUSTADO en el formulario: solo debe setearse por acción admin.
        """
        field = super().formfield_for_choice_field(db_field, request, **kwargs)

        if db_field.name == "estado":
            # Siempre ocultamos AJUSTADO del formulario
            field.choices = [
                (value, label)
                for value, label in field.choices
                if value != EstadoConteo.AJUSTADO
            ]
        return field

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        obj = form.instance
        estado_anterior = getattr(obj, "_estado_anterior", None)

        # 1) Conciliar siempre (para que se vean diferencias al guardar)
        if obj.estado != EstadoConteo.AJUSTADO:
            conciliar_conteo(obj, aplicar_ajustes=False, usuario=request.user)

        # 2) Prohibir que alguien setee AJUSTADO manualmente
        if obj.estado == EstadoConteo.AJUSTADO:
            # Solo permitimos AJUSTADO si el usuario puede aplicar ajustes
            if not usuario_puede_aplicar_ajustes(request.user):
                # Revertimos al estado anterior y bloqueamos
                obj.estado = estado_anterior or EstadoConteo.BORRADOR
                obj.save(update_fields=["estado"])
                raise ValidationError(
                    "No tienes permisos para marcar un conteo como 'Ajustado'. "
                    "Los ajustes solo pueden aplicarse por un supervisor/autorizado."
                )

            # Además, por regla de negocio: solo se puede ajustar si estaba CERRADO
            if estado_anterior != EstadoConteo.CERRADO:
                obj.estado = estado_anterior or EstadoConteo.BORRADOR
                obj.save(update_fields=["estado"])
                raise ValidationError("Solo se puede ajustar un conteo que esté en estado 'Cerrado'.")

        # 3) Validación SIEMPRE que el estado quede en CERRADO
        if obj.estado == EstadoConteo.CERRADO:
            # Reconciliar por seguridad antes de validar (por si cambiaron ítems)
            conciliar_conteo(obj, aplicar_ajustes=False, usuario=request.user)

            # Si hay diferencias críticas y NO es supervisor -> bloquear SIEMPRE
            if obj.tiene_diferencias_criticas and not usuario_es_supervisor(request.user):
                obj.estado = EstadoConteo.BORRADOR
                obj.save(update_fields=["estado"])
                raise ValidationError(
                    "Este conteo tiene diferencias críticas. "
                    "Debe ser cerrado y aprobado por un supervisor."
                )

            # Si hay diferencias críticas y SÍ es supervisor -> registrar aprobación
            if obj.tiene_diferencias_criticas and usuario_es_supervisor(request.user):
                obj.aprobado_por = request.user
                obj.aprobado_en = timezone.now()
                obj.save(update_fields=["aprobado_por", "aprobado_en"])


