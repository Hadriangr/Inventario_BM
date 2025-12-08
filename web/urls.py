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
    MenuPlanListView,
    MenuPlanRequerimientosView,
    menu_plan_create,
    menu_plan_update,
)

app_name = "web"

urlpatterns = [
    # Proveedores
    path("proveedores/", ProveedorListView.as_view(), name="proveedores_list"),
    path("proveedores/nuevo/", ProveedorCreateView.as_view(), name="proveedores_create"),
    path(
        "proveedores/<int:pk>/editar/",
        ProveedorUpdateView.as_view(),
        name="proveedores_update",
    ),
    path("proveedores/<int:pk>/eliminar/", ProveedorDeleteView.as_view(), name="proveedores_delete"),

    # Insumos
    path("insumos/", InsumoListView.as_view(), name="insumos_list"),
    path("insumos/nuevo/", InsumoCreateView.as_view(), name="insumos_create"),
    path(
        "insumos/<int:pk>/editar/",
        InsumoUpdateView.as_view(),
        name="insumos_update",
    ),
    path("insumos/<int:pk>/eliminar/", InsumoDeleteView.as_view(), name="insumos_delete"),


    # Compras
    path("compras/", EntradaCompraListView.as_view(), name="compras_list"),
    path("compras/nueva/", EntradaCompraCreateView.as_view(), name="compras_create"),
    path("compras/<int:pk>/eliminar/", EntradaCompraDeleteView.as_view(), name="compras_delete"),

    # Platos
    path("platos/", PlatoListView.as_view(), name="platos_list"),
    path("platos/nuevo/", PlatoCreateView.as_view(), name="platos_create"),
    path("platos/<int:pk>/editar/", PlatoUpdateView.as_view(), name="platos_update"),
    path("platos/<int:pk>/recalcular/", plato_recalcular_costo, name="platos_recalcular"),
    path("platos/<int:pk>/receta/", plato_receta_edit, name="platos_receta"),
    path("platos/<int:pk>/eliminar/", PlatoDeleteView.as_view(), name="platos_delete"),

    # Planes de menú
    path("planes/", MenuPlanListView.as_view(), name="planes_list"),
    path("planes/<int:pk>/requerimientos/", MenuPlanRequerimientosView.as_view(), name="planes_requerimientos"),

        # Planes de menú
    path("planes/", MenuPlanListView.as_view(), name="planes_list"),
    path("planes/nuevo/", menu_plan_create, name="planes_create"),
    path("planes/<int:pk>/editar/", menu_plan_update, name="planes_update"),
    path("planes/<int:pk>/requerimientos/", MenuPlanRequerimientosView.as_view(), name="planes_requerimientos"),



]

