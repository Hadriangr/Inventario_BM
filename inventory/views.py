from rest_framework import viewsets, permissions

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


class RecetaInsumoViewSet(viewsets.ModelViewSet):
    queryset = RecetaInsumo.objects.all().select_related("plato", "insumo", "insumo__unidad")
    serializer_class = RecetaInsumoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
