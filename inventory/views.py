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
    ConteoInventarioRequestSerializer,
    ResultadoConteoSerializer,
)
from .services.inventory import (
    calcular_costo_receta,
    aplicar_ajustes_conteo,
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

class AlmacenViewSet(viewsets.ModelViewSet):
    queryset = Almacen.objects.all()
    serializer_class = AlmacenSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=["post"], url_path="conteo/previsualizar")
    def previsualizar_conteo(self, request, pk=None):
        """
        Recibe un conteo físico y devuelve diferencias vs sistema SIN aplicar ajustes.
        POST /api/almacenes/<id>/conteo/previsualizar/
        """
        almacen = self.get_object()
        serializer = ConteoInventarioRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        conteos = data["conteos"]
        tolerancia_unidades = data.get("tolerancia_unidades")
        tolerancia_porcentaje = data.get("tolerancia_porcentaje")

        resultados = calcular_diferencias_conteo(
            almacen=almacen,
            conteos=conteos,
            tolerancia_unidades=tolerancia_unidades,
            tolerancia_porcentaje=tolerancia_porcentaje,
        )

        # Serializamos la lista de resultados
        output = [ResultadoConteoSerializer.from_resultado(r).data for r in resultados]
        return Response({"almacen": almacen.id, "resultados": output})

    @action(detail=True, methods=["post"], url_path="conteo/aplicar")
    def aplicar_conteo(self, request, pk=None):
        """
        Recibe un conteo físico, calcula diferencias y APLICA ajustes donde corresponda.
        POST /api/almacenes/<id>/conteo/aplicar/
        """
        almacen = self.get_object()
        serializer = ConteoInventarioRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        conteos = data["conteos"]
        tolerancia_unidades = data.get("tolerancia_unidades")
        tolerancia_porcentaje = data.get("tolerancia_porcentaje")
        aplicar_solo_fuera_tolerancia = data.get("aplicar_solo_fuera_tolerancia", True)

        resultados, movimientos = aplicar_ajustes_conteo(
            almacen=almacen,
            conteos=conteos,
            usuario=request.user if request.user.is_authenticated else None,
            tolerancia_unidades=tolerancia_unidades,
            tolerancia_porcentaje=tolerancia_porcentaje,
            referencia=f"CONTEO-{almacen.id}",
            aplicar_solo_fuera_tolerancia=aplicar_solo_fuera_tolerancia,
        )

        resultados_serializados = [
            ResultadoConteoSerializer.from_resultado(r).data for r in resultados
        ]

        movimientos_data = [
            {
                "id": mov.id,
                "insumo_id": mov.insumo_id,
                "almacen_id": mov.almacen_id,
                "tipo": mov.tipo,
                "cantidad": str(mov.cantidad),
                "fecha_movimiento": mov.fecha_movimiento,
            }
            for mov in movimientos
        ]

        return Response(
            {
                "almacen": almacen.id,
                "resultados": resultados_serializados,
                "movimientos_generados": movimientos_data,
            }
        )

