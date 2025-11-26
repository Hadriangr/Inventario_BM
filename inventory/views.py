from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response


from .models import (
    UnidadMedida,
    Proveedor,
    CategoriaInsumo, 
    Insumo,
    Almacen,
    StockInsumo,
    Plato,
    RecetaInsumo,
)
from .serializers import (
    UnidadMedidaSerializer,
    ProveedorSerializer,
    CategoriaInsumoSerializer,
    InsumoSerializer,
    AlmacenSerializer,
    StockInsumoSerializer,
    PlatoSerializer,
    RecetaInsumoSerializer,
)


class IsAuthenticatedOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """
    Por ahora usamos la clase estándar de DRF.
    Más adelante podemos definir permisos por rol/almacén.
    """
    pass


class UnidadMedidaViewSet(viewsets.ModelViewSet):
    queryset = UnidadMedida.objects.all()
    serializer_class = UnidadMedidaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.all().select_related("unidad", "proveedor_principal")
    serializer_class = InsumoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CategoriaInsumoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaInsumo.objects.all()
    serializer_class = CategoriaInsumoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class AlmacenViewSet(viewsets.ModelViewSet):
    queryset = Almacen.objects.all().select_related("responsable")
    serializer_class = AlmacenSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class StockInsumoViewSet(viewsets.ModelViewSet):
    queryset = (
        StockInsumo.objects.all()
        .select_related("insumo", "almacen", "insumo__unidad", "insumo__proveedor_principal")
    )
    serializer_class = StockInsumoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class PlatoViewSet(viewsets.ModelViewSet):
    queryset = Plato.objects.all()
    serializer_class = PlatoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=["get"], url_path="indicadores")
    def indicadores(self, request, pk=None):
        plato = self.get_object()
        data = {
            "id": plato.id,
            "nombre": plato.nombre,
            "costo_receta": str(plato.costo_receta),
            "precio_venta": str(plato.precio_venta) if plato.precio_venta is not None else None,
            "food_cost_porcentaje": (
                str(plato.food_cost_porcentaje) if plato.food_cost_porcentaje is not None else None
            ),
            "margen_bruto": (
                str(plato.margen_bruto) if plato.margen_bruto is not None else None
            ),
            "margen_bruto_porcentaje": (
                str(plato.margen_bruto_porcentaje) if plato.margen_bruto_porcentaje is not None else None
            ),
        }
        return Response(data)

    
    @action(detail=True, methods=["post"], url_path="calcular-costo")
    def calcular_costo(self, request, pk=None):
        """
        Recalcula el costo de la receta del plato y lo devuelve.
        POST /api/platos/<id>/calcular-costo/
        """
        plato = self.get_object()
        costo = calcular_costo_receta(plato=plato, guardar=True)
        return Response({"plato": plato.id, "costo_receta": str(costo)})


class RecetaInsumoViewSet(viewsets.ModelViewSet):
    queryset = RecetaInsumo.objects.all().select_related("plato", "insumo", "insumo__unidad")
    serializer_class = RecetaInsumoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
