from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce


from inventory.models import StockInsumo, Almacen,Insumo,ConteoInventario,ConteoInventarioItem,EstadoConteo  # ajusta si está en otra app


def obtener_stock_sistema(almacen: Almacen, insumo: Insumo) -> Decimal:
    """
    Devuelve la cantidad actual en sistema para un insumo en un almacén.

    IMPORTANTE:
    - Ajusta el nombre del campo en StockInsumo si no se llama 'cantidad_actual'.
    """

    qs = StockInsumo.objects.filter(
        almacen=almacen,
        insumo=insumo,
    )

    total = qs.aggregate(
        total=Coalesce(Sum("cantidad_actual"), Decimal("0"))
    )["total"]

    return total or Decimal("0")


@transaction.atomic
def conciliar_conteo(conteo: ConteoInventario, aplicar_ajustes: bool = False, usuario=None):
    """
    - Lee el stock actual en sistema.
    - Calcula cantidad_sistema, diferencia y dentro_tolerancia por ítem.
    - Si aplicar_ajustes=True, crea ajustes de inventario para los ítems fuera de tolerancia.

    NOTA:
    - No cambia el estado del conteo. Eso se maneja desde el admin o las vistas.
    """

    if aplicar_ajustes and not conteo.puede_aplicar_ajustes():
        raise ValueError(
            "No se pueden aplicar ajustes: el conteo debe estar en estado CERRADO."
        )
    
    # Import diferido para evitar dependencias circulares si las hay
    try:
        from inventory.services import registrar_ajuste_inventario
    except ImportError:
        registrar_ajuste_inventario = None

    tolerancia_pct = conteo.tolerancia_porcentaje or Decimal("0")
    tol_abs = conteo.tolerancia_unidades

    for item in conteo.items.select_related("insumo"):
        cantidad_sistema = obtener_stock_sistema(conteo.almacen, item.insumo)
        cantidad_contada = item.cantidad_contada

        diferencia = cantidad_contada - cantidad_sistema

        # Porcentaje de diferencia respecto al sistema
        if cantidad_sistema and cantidad_sistema != 0:
            porcentaje_diff = (abs(diferencia) / cantidad_sistema) * Decimal("100")
        else:
            porcentaje_diff = None

        dentro_tolerancia = False

        # 1) Tolerancia absoluta en unidades (si está definida)
        if tol_abs is not None:
            if abs(diferencia) <= tol_abs:
                dentro_tolerancia = True

        # 2) Si no está dentro por unidades, evaluamos por porcentaje
        if not dentro_tolerancia and porcentaje_diff is not None:
            if porcentaje_diff <= tolerancia_pct:
                dentro_tolerancia = True

        # Guardamos snapshot en el ítem
        item.cantidad_sistema = cantidad_sistema
        item.diferencia = diferencia
        item.dentro_tolerancia = dentro_tolerancia
        item.save(
            update_fields=["cantidad_sistema", "diferencia", "dentro_tolerancia"]
        )

        # Ajustes de inventario (opcional)
        if aplicar_ajustes and not dentro_tolerancia and diferencia != 0:
            if registrar_ajuste_inventario is None:
                raise RuntimeError(
                    "registrar_ajuste_inventario no está disponible. "
                    "Importa correctamente inventory.services."
                )

            # diferencia = contada - sistema
            # Si > 0 => faltaba stock en sistema, hacemos ajuste de ENTRADA
            # Si < 0 => sobraba stock en sistema, hacemos ajuste de SALIDA

            registrar_ajuste_inventario(
                almacen=conteo.almacen,
                insumo=item.insumo,
                cantidad=diferencia,  # positiva o negativa
                motivo="ajuste_por_conteo_fisico",
                usuario=usuario,
                referencia=conteo,
            )
 


