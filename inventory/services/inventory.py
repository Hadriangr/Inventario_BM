from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.db.models import Q, F
from datetime import date, timedelta
from inventory.models import Plato, RecetaInsumo

from inventory.models import (
    Insumo,
    Almacen,
    StockInsumo,
    MovimientoInventario,
    LoteInsumo,
)


class MovimientoInventarioError(Exception):
    """Errores de dominio al registrar movimientos de inventario."""
    pass


@transaction.atomic
def registrar_entrada_compra(
    *,
    insumo: Insumo,
    almacen: Almacen,
    cantidad: Decimal,
    costo_unitario: Decimal,
    usuario=None,
    motivo: str = "",
    referencia: str = "",
    fecha_movimiento=None,
    numero_lote: str | None = None,
    fecha_vencimiento: date | None = None,
) -> MovimientoInventario:
    """
    Registra una entrada de inventario por COMPRA con costo promedio ponderado.

    - Crea/actualiza el registro de StockInsumo.
    - Recalcula el costo_promedio del StockInsumo.
    - Actualiza el costo_promedio del Insumo (a nivel global).
    - Crea un MovimientoInventario asociado.

    Regla de costo promedio ponderado:
        nuevo_costo = (qty_ant * costo_ant + qty_nueva * costo_unitario) / (qty_ant + qty_nueva)
    """
    # Convertir costo de compra → costo por unidad de consumo
    if insumo.unidad_compra and insumo.factor_conversion:
        costo_unitario = costo_unitario / insumo.factor_conversion

    if cantidad <= 0:
        raise MovimientoInventarioError("La cantidad de una entrada de compra debe ser > 0.")

    if costo_unitario <= 0:
        raise MovimientoInventarioError("El costo unitario debe ser > 0.")

    if fecha_movimiento is None:
        fecha_movimiento = timezone.now()

    # Obtenemos (o creamos) el stock para este insumo+almacén
    stock, _created = StockInsumo.objects.select_for_update().get_or_create(
        insumo=insumo,
        almacen=almacen,
        defaults={
            "cantidad_actual": Decimal("0"),
            "costo_promedio": Decimal("0"),
        },
    )

    qty_ant = stock.cantidad_actual or Decimal("0")
    costo_ant = stock.costo_promedio or Decimal("0")

    # Cálculo de nuevo stock
    qty_nueva = qty_ant + cantidad

    # Cálculo de nuevo costo promedio ponderado
    if qty_ant <= 0:
        # Si no había stock previo, el costo promedio pasa a ser el costo_unitario
        nuevo_costo = costo_unitario
    else:
        valor_ant = qty_ant * costo_ant
        valor_nuevo = cantidad * costo_unitario
        nuevo_costo = (valor_ant + valor_nuevo) / qty_nueva

    # Actualizamos el stock
    stock.cantidad_actual = qty_nueva
    stock.costo_promedio = nuevo_costo.quantize(Decimal("0.0001"))
    stock.save()

# Actualizamos el costo_promedio global del insumo
    _actualizar_costo_promedio_insumo(insumo)

    # Registramos el movimiento
    movimiento = MovimientoInventario.objects.create(
        insumo=insumo,
        almacen=almacen,
        tipo=MovimientoInventario.TIPO_ENTRADA_COMPRA,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        fecha_movimiento=fecha_movimiento,
        motivo=motivo,
        referencia=referencia,
        usuario=usuario,
    )

    # Si se especifican datos de lote/vencimiento, actualizamos/creamos lote
    if numero_lote or fecha_vencimiento:
        lote, created = LoteInsumo.objects.select_for_update().get_or_create(
            insumo=insumo,
            almacen=almacen,
            numero_lote=numero_lote or "",
            fecha_vencimiento=fecha_vencimiento,
            defaults={
                "cantidad_actual": Decimal("0"),
                "costo_unitario": costo_unitario,
                "activo": True,
            },
        )
        lote.cantidad_actual = (lote.cantidad_actual or Decimal("0")) + cantidad
        # Para el MVP dejamos costo_unitario como el último costo registrado
        lote.costo_unitario = costo_unitario
        lote.save()
    return movimiento

def obtener_lotes_por_vencer(*, dias: int = 7, almacen: Almacen | None = None):
    """
    Retorna lotes activos cuya fecha de vencimiento esté entre hoy y hoy+días.
    Solo lotes con cantidad_actual > 0.
    """
    hoy = date.today()
    limite = hoy + timedelta(days=dias)

    qs = LoteInsumo.objects.select_related("insumo", "almacen").filter(
        activo=True,
        cantidad_actual__gt=0,
        fecha_vencimiento__isnull=False,
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=limite,
    )
    if almacen is not None:
        qs = qs.filter(almacen=almacen)
    return qs


def obtener_lotes_vencidos(*, almacen: Almacen | None = None):
    """
    Retorna lotes ya vencidos con cantidad_actual > 0.
    """
    hoy = date.today()
    qs = LoteInsumo.objects.select_related("insumo", "almacen").filter(
        activo=True,
        cantidad_actual__gt=0,
        fecha_vencimiento__isnull=False,
        fecha_vencimiento__lt=hoy,
    )
    if almacen is not None:
        qs = qs.filter(almacen=almacen)
    return qs


def obtener_stocks_bajo_minimo(*, almacen: Almacen | None = None, solo_activos: bool = True):
    """
    Retorna un queryset de StockInsumo que están por debajo del stock mínimo.
    Opcionalmente filtrado por almacén y solo activos.
    """
    qs = StockInsumo.objects.select_related("insumo", "almacen")

    if solo_activos:
        qs = qs.filter(insumo__activo=True, almacen__activo=True)

    qs = qs.filter(
        insumo__stock_minimo__gt=0,
        cantidad_actual__lt=F("insumo__stock_minimo"),
    )

    if almacen is not None:
        qs = qs.filter(almacen=almacen)

    return qs


def obtener_stocks_sobre_maximo(*, almacen: Almacen | None = None, solo_activos: bool = True):
    """
    Retorna un queryset de StockInsumo que están por encima del stock máximo.
    Opcionalmente filtrado por almacén y solo activos.
    """
    qs = StockInsumo.objects.select_related("insumo", "almacen")

    if solo_activos:
        qs = qs.filter(insumo__activo=True, almacen__activo=True)

    qs = qs.filter(
        insumo__stock_maximo__isnull=False,
        insumo__stock_maximo__gt=0,
        cantidad_actual__gt=F("insumo__stock_maximo"),
    )

    if almacen is not None:
        qs = qs.filter(almacen=almacen)
    return qs


@transaction.atomic
def registrar_ajuste_inventario(
    *,
    insumo: Insumo,
    almacen: Almacen,
    cantidad: Decimal,
    usuario=None,
    motivo: str,
    referencia: str = "",
    fecha_movimiento=None,
    tipo: str | None = None,
) -> MovimientoInventario:
    """
    Registra un AJUSTE de inventario (positivo o negativo).

    - cantidad > 0 → entrada por ajuste
    - cantidad < 0 → salida por ajuste
    - NO modifica el costo_promedio del stock ni del insumo.
    - Motivo obligatorio.
    - No permite que el stock quede negativo.
    """
    if cantidad == 0:
        raise MovimientoInventarioError("La cantidad del ajuste no puede ser 0.")

    if not motivo or not motivo.strip():
        raise MovimientoInventarioError("El motivo del ajuste es obligatorio.")

    if fecha_movimiento is None:
        fecha_movimiento = timezone.now()

    # Determinar el tipo si no lo pasan explícito
    if tipo is None:
        if cantidad > 0:
            tipo = MovimientoInventario.TIPO_ENTRADA_AJUSTE
        else:
            tipo = MovimientoInventario.TIPO_SALIDA_AJUSTE
    else:
        if tipo not in {
            MovimientoInventario.TIPO_ENTRADA_AJUSTE,
            MovimientoInventario.TIPO_SALIDA_AJUSTE,
        }:
            raise MovimientoInventarioError("Tipo de ajuste inválido.")

    # Obtenemos el stock actual (o lo creamos si no existe y el ajuste es positivo)
    try:
        stock = StockInsumo.objects.select_for_update().get(
            insumo=insumo,
            almacen=almacen,
        )
    except StockInsumo.DoesNotExist:
        if cantidad < 0:
            # No hay stock y quieren ajustar en negativo
            raise MovimientoInventarioError(
                "No existe stock para este insumo en este almacén; "
                "no se puede registrar un ajuste negativo."
            )
        # Ajuste positivo sin stock previo → creamos registro
        stock = StockInsumo.objects.create(
            insumo=insumo,
            almacen=almacen,
            cantidad_actual=Decimal("0"),
            costo_promedio=insumo.costo_promedio or Decimal("0"),
        )

    cantidad_actual = stock.cantidad_actual or Decimal("0")
    costo_unitario_actual = stock.costo_promedio or Decimal("0")

    # Nuevo stock luego del ajuste
    nueva_cantidad = cantidad_actual + cantidad
    if nueva_cantidad < 0:
        raise MovimientoInventarioError(
            "El ajuste resultaría en stock negativo, operación no permitida."
        )

    # Actualizamos la cantidad, pero NO tocamos costo_promedio
    stock.cantidad_actual = nueva_cantidad
    stock.save(update_fields=["cantidad_actual", "updated_at"])

    # Registramos el movimiento.
    # Usamos el costo_unitario_actual solo para referencia contable.
    movimiento = MovimientoInventario.objects.create(
        insumo=insumo,
        almacen=almacen,
        tipo=tipo,
        cantidad=cantidad,
        costo_unitario=costo_unitario_actual if costo_unitario_actual != 0 else None,
        fecha_movimiento=fecha_movimiento,
        motivo=motivo.strip(),
        referencia=referencia,
        usuario=usuario,
    )

    return movimiento

def _actualizar_costo_promedio_insumo(insumo: Insumo) -> None:
    """
    Recalcula el costo_promedio del Insumo a nivel global,
    en base a TODOS los stocks en todos los almacenes.

    costo_promedio_insumo = sum(qty * costo) / sum(qty)
    """
    from django.db.models import Sum, F, DecimalField, ExpressionWrapper

    qs = StockInsumo.objects.filter(insumo=insumo)

    agg = qs.aggregate(
        total_cantidad=Sum("cantidad_actual"),
        total_valor=Sum(
            ExpressionWrapper(
                F("cantidad_actual") * F("costo_promedio"),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            )
        ),
    )
    total_cantidad = agg["total_cantidad"] or Decimal("0")
    total_valor = agg["total_valor"] or Decimal("0")

    if total_cantidad > 0:
        insumo.costo_promedio = (total_valor / total_cantidad).quantize(Decimal("0.0001"))
    else:
        # Si no hay stock en ningún almacén, podríamos dejar costo_promedio como está
        # o ponerlo en 0. Para este MVP lo dejamos en 0.
        insumo.costo_promedio = Decimal("0")

    insumo.save(update_fields=["costo_promedio", "updated_at"])

def calcular_costo_receta(*, plato: Plato, guardar: bool = True) -> Decimal:
    """
    Calcula el costo total de la receta de un plato, sumando:
        suma( cantidad_insumo * costo_promedio_insumo )

    - Usa la unidad de consumo del insumo.
    - Si guardar=True, actualiza plato.costo_receta en BD.
    - Devuelve el costo calculado (Decimal).
    """
    total = Decimal("0")

    receta = RecetaInsumo.objects.select_related("insumo").filter(plato=plato)

    for linea in receta:
        insumo = linea.insumo
        costo_unitario = insumo.costo_promedio or Decimal("0")
        cantidad = linea.cantidad or Decimal("0")
        total += cantidad * costo_unitario

    total = total.quantize(Decimal("0.0001"))

    if guardar:
        plato.costo_receta = total
        plato.save(update_fields=["costo_receta", "updated_at"])

    return total

@transaction.atomic
def registrar_traspaso(
    *,
    insumo: Insumo,
    almacen_origen: Almacen,
    almacen_destino: Almacen,
    cantidad: Decimal,
    usuario=None,
    motivo: str = "",
    referencia: str = "",
    fecha_movimiento=None,
) -> tuple[MovimientoInventario, MovimientoInventario]:
    """
    Registra un TRASPASO de inventario entre dos almacenes.

    - Disminuye stock en el almacén_origen (SALIDA_TRASPASO, cantidad negativa).
    - Aumenta stock en el almacén_destino (ENTRADA_TRASPASO, cantidad positiva).
    - Mantiene el costo valorado: el destino recibe el insumo al costo_promedio
      del origen, ajustando su propio costo_promedio por ponderación.

    Reglas:
    - cantidad > 0
    - origen != destino
    - No permite dejar stock negativo en origen.
    """
    if cantidad <= 0:
        raise MovimientoInventarioError("La cantidad del traspaso debe ser > 0.")

    if almacen_origen == almacen_destino:
        raise MovimientoInventarioError("El almacén de origen y destino no pueden ser el mismo.")

    if fecha_movimiento is None:
        fecha_movimiento = timezone.now()

    # --- Stock origen ---
    try:
        stock_origen = StockInsumo.objects.select_for_update().get(
            insumo=insumo,
            almacen=almacen_origen,
        )
    except StockInsumo.DoesNotExist:
        raise MovimientoInventarioError(
            "No existe stock para este insumo en el almacén de origen."
        )

    cantidad_origen = stock_origen.cantidad_actual or Decimal("0")
    if cantidad_origen < cantidad:
        raise MovimientoInventarioError(
            "No hay suficiente stock en el almacén de origen para el traspaso."
        )

    costo_origen = stock_origen.costo_promedio or Decimal("0")

    # Nuevo stock en origen
    stock_origen.cantidad_actual = cantidad_origen - cantidad
    stock_origen.save(update_fields=["cantidad_actual", "updated_at"])

    # --- Stock destino ---
    stock_destino, _created = StockInsumo.objects.select_for_update().get_or_create(
        insumo=insumo,
        almacen=almacen_destino,
        defaults={
            "cantidad_actual": Decimal("0"),
            "costo_promedio": costo_origen,
        },
    )

    cantidad_destino_ant = stock_destino.cantidad_actual or Decimal("0")
    costo_destino_ant = stock_destino.costo_promedio or Decimal("0")

    nueva_cantidad_destino = cantidad_destino_ant + cantidad

    if cantidad_destino_ant <= 0:
        nuevo_costo_destino = costo_origen
    else:
        valor_ant = cantidad_destino_ant * costo_destino_ant
        valor_nuevo = cantidad * costo_origen
        nuevo_costo_destino = (valor_ant + valor_nuevo) / nueva_cantidad_destino

    stock_destino.cantidad_actual = nueva_cantidad_destino
    stock_destino.costo_promedio = nuevo_costo_destino.quantize(Decimal("0.0001"))
    stock_destino.save(update_fields=["cantidad_actual", "costo_promedio", "updated_at"])

    # Actualizamos costo_promedio global del insumo (no cambia el valor total, solo distribución)
    _actualizar_costo_promedio_insumo(insumo)

    # --- Movimientos ---
    mov_salida = MovimientoInventario.objects.create(
        insumo=insumo,
        almacen=almacen_origen,
        tipo=MovimientoInventario.TIPO_SALIDA_TRASPASO,
        cantidad=-cantidad,  # salida → negativa
        costo_unitario=costo_origen,
        fecha_movimiento=fecha_movimiento,
        motivo=motivo or "Traspaso a almacén {}".format(almacen_destino.nombre),
        referencia=referencia,
        usuario=usuario,
    )

    mov_entrada = MovimientoInventario.objects.create(
        insumo=insumo,
        almacen=almacen_destino,
        tipo=MovimientoInventario.TIPO_ENTRADA_TRASPASO,
        cantidad=cantidad,  # entrada → positiva
        costo_unitario=costo_origen,
        fecha_movimiento=fecha_movimiento,
        motivo=motivo or "Traspaso desde almacén {}".format(almacen_origen.nombre),
        referencia=referencia,
        usuario=usuario,
    )

    return mov_salida, mov_entrada
