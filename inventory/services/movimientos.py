from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from inventory.models import MovimientoInventario, StockInsumo


@transaction.atomic
def registrar_ajuste_inventario(
    *,
    almacen,
    insumo,
    cantidad,
    motivo,
    usuario,
    referencia=None,
):
    """
    Registra un ajuste de inventario (positivo o negativo)
    y actualiza el StockInsumo.
    """

    cantidad = Decimal(cantidad)

    # Obtener o crear stock
    stock, _ = StockInsumo.objects.select_for_update().get_or_create(
        almacen=almacen,
        insumo=insumo,
        defaults={"cantidad_actual": Decimal("0")},
    )

    # Determinar tipo de movimiento según signo
    if cantidad > 0:
        tipo_movimiento = MovimientoInventario.TIPO_ENTRADA_AJUSTE
    else:
        tipo_movimiento = MovimientoInventario.TIPO_SALIDA_AJUSTE

    # Crear movimiento
    movimiento = MovimientoInventario.objects.create(
        tipo=tipo_movimiento,
        almacen=almacen,
        insumo=insumo,
        cantidad=abs(cantidad),
        motivo=motivo,
        usuario=usuario,
        referencia=str(referencia) if referencia else "",
        fecha_movimiento=timezone.now(), 
    )

    # Ajustar stock
    stock.cantidad_actual += cantidad
    stock.save(update_fields=["cantidad_actual"])

    return movimiento