from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UnidadMedidaViewSet,
    ProveedorViewSet,
    InsumoViewSet,
    CategoriaInsumoViewSet,
    AlmacenViewSet,
    StockInsumoViewSet,
    PlatoViewSet,
    RecetaInsumoViewSet,
)

router = DefaultRouter()
router.register(r"unidades-medida", UnidadMedidaViewSet, basename="unidad-medida")
router.register(r"proveedores", ProveedorViewSet, basename="proveedor")
router.register(r"insumos", InsumoViewSet, basename="insumo")
router.register(r"almacenes", AlmacenViewSet, basename="almacen")
router.register(r"stocks-insumo", StockInsumoViewSet, basename="stock-insumo")
router.register(r"platos", PlatoViewSet, basename="plato")
router.register(r"recetas-insumo", RecetaInsumoViewSet, basename="receta-insumo")
router.register(r"categorias-insumo", CategoriaInsumoViewSet, basename="categoria-insumo")


urlpatterns = [
    path("", include(router.urls)),
]
