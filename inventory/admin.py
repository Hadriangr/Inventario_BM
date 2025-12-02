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
)

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


