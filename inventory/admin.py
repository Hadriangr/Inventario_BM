from django.contrib import admin

from .models import (
    UnidadMedida,
    Proveedor,
    Insumo,
    CategoriaInsumo,    
    Almacen,
    StockInsumo,
    Plato,
    RecetaInsumo,
)


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

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
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
    autocomplete_fields = ("unidad", "proveedor_principal")


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
        "updated_at",
    )
    list_filter = ("almacen", "insumo")
    search_fields = ("insumo__nombre", "almacen__nombre")
    autocomplete_fields = ("insumo", "almacen")


@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio_venta", "activo")
    list_filter = ("activo", "categoria")
    search_fields = ("nombre", "descripcion")


@admin.register(RecetaInsumo)
class RecetaInsumoAdmin(admin.ModelAdmin):
    list_display = ("plato", "insumo", "cantidad", "created_at")
    list_filter = ("plato", "insumo")
    search_fields = ("plato__nombre", "insumo__nombre")
    autocomplete_fields = ("plato", "insumo")

