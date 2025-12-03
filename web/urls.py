from django.urls import path
from web.views import (
    ProveedorListView,
    ProveedorCreateView,
    ProveedorUpdateView,
    InsumoListView,
    InsumoCreateView,
    InsumoUpdateView,
    EntradaCompraListView,
    EntradaCompraCreateView,
    PlatoListView,
    PlatoCreateView,
    PlatoUpdateView,
    plato_recalcular_costo,
    ProveedorDeleteView,
    InsumoDeleteView,
    EntradaCompraDeleteView,
    PlatoDeleteView,
    plato_receta_edit,
)

app_name = "web"

urlpatterns = [
    path("proveedores/", ProveedorListView.as_view(), name="proveedores_list"),
    path("proveedores/nuevo/", ProveedorCreateView.as_view(), name="proveedores_create"),
    path(
        "proveedores/<int:pk>/editar/",
        ProveedorUpdateView.as_view(),
        name="proveedores_update",
    ),
    path("proveedores/<int:pk>/eliminar/", ProveedorDeleteView.as_view(), name="proveedores_delete"),


        path("insumos/", InsumoListView.as_view(), name="insumos_list"),
    path("insumos/nuevo/", InsumoCreateView.as_view(), name="insumos_create"),
    path(
        "insumos/<int:pk>/editar/",
        InsumoUpdateView.as_view(),
        name="insumos_update",
    ),
    path("insumos/<int:pk>/eliminar/", InsumoDeleteView.as_view(), name="insumos_delete"),


    
    path("compras/", EntradaCompraListView.as_view(), name="compras_list"),
    path("compras/nueva/", EntradaCompraCreateView.as_view(), name="compras_create"),
    path("compras/<int:pk>/eliminar/", EntradaCompraDeleteView.as_view(), name="compras_delete"),


    path("platos/", PlatoListView.as_view(), name="platos_list"),
    path("platos/nuevo/", PlatoCreateView.as_view(), name="platos_create"),
    path("platos/<int:pk>/editar/", PlatoUpdateView.as_view(), name="platos_update"),
    path("platos/<int:pk>/recalcular/", plato_recalcular_costo, name="platos_recalcular"),
    path("platos/<int:pk>/receta/", plato_receta_edit, name="platos_receta"),
    path("platos/<int:pk>/eliminar/", PlatoDeleteView.as_view(), name="platos_delete"),


]

