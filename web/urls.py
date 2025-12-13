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
    conteos_list,
    conteos_create,
    conteos_detail,
    conteo_cerrar,
    api_conteo_preview,
    conteo_solicitar_aprobacion,
    conteo_aprobar,
    
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

    # Conteos de inventario
    path("conteos/", conteos_list, name="conteos_list"),
    path("conteos/nuevo/", conteos_create, name="conteos_create"),
    path("conteos/<int:pk>/", conteos_detail, name="conteos_detail"),
    path("conteos/<int:pk>/cerrar/", conteo_cerrar, name="conteos_cerrar"),
    path("api/conteos/preview/", api_conteo_preview, name="api_conteo_preview"),
    path("conteos/<int:pk>/solicitar-aprobacion/", conteo_solicitar_aprobacion, name="conteo_solicitar_aprobacion"),
    path("conteos/<int:pk>/aprobar/", conteo_aprobar, name="conteo_aprobar"),




]

