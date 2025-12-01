from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.db.models import Q, F
from datetime import date, timedelta
from inventory.models import Plato, RecetaInsumo
from dataclasses import dataclass


from inventory.models import (
    Insumo,
    Almacen,
    StockInsumo,
    MovimientoInventario,
    LoteInsumo,
    Plato,
    RecetaInsumo,
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


@dataclass
class ResultadoConteoInventario:
    insumo: Insumo
    cantidad_sistema: Decimal
    cantidad_contada: Decimal
    diferencia: Decimal
    fuera_tolerancia: bool

@dataclass
class ResultadoConteoInventario:
    insumo: Insumo
    cantidad_sistema: Decimal
    cantidad_contada: Decimal
    diferencia: Decimal
    fuera_tolerancia: bool

def calcular_diferencias_conteo(
    *,
    almacen: Almacen,
    conteos: list[dict],
    tolerancia_unidades: Decimal | None = None,
    tolerancia_porcentaje: Decimal | None = None,
) -> list[ResultadoConteoInventario]:
    """
    Calcula diferencias entre el stock del sistema y un conteo físico.

    Parámetros:
    - almacen: almacén donde se hizo el conteo.
    - conteos: lista de dicts con al menos:
        {
            "insumo_id": <int>,
            "cantidad_contada": <Decimal | str | float>
        }
      (idealmente vendrán desde el frontend en JSON).
    - tolerancia_unidades: diferencia absoluta permitida (ej: 1.000).
    - tolerancia_porcentaje: diferencia relativa permitida (ej: 0.02 = 2%).

    Retorna una lista de ResultadoConteoInventario.
    """

    # Mapeo insumo_id -> cantidad_contada
    mapa_contados: dict[int, Decimal] = {}
    for item in conteos:
        insumo_id = int(item["insumo_id"])
        cantidad = Decimal(str(item["cantidad_contada"]))
        mapa_contados[insumo_id] = cantidad

    # Cargar stocks del almacén para todos esos insumos
    insumos_ids = list(mapa_contados.keys())
    stocks = (
        StockInsumo.objects.select_related("insumo")
        .filter(almacen=almacen, insumo_id__in=insumos_ids)
    )

    stocks_por_insumo: dict[int, StockInsumo] = {s.insumo_id: s for s in stocks}

    resultados: list[ResultadoConteoInventario] = []

    for insumo_id, cantidad_contada in mapa_contados.items():
        stock = stocks_por_insumo.get(insumo_id)
        if stock is None:
            # Si no hay StockInsumo, el sistema asume 0
            cantidad_sistema = Decimal("0")
            insumo = Insumo.objects.get(pk=insumo_id)
        else:
            cantidad_sistema = stock.cantidad_actual or Decimal("0")
            insumo = stock.insumo

        diferencia = cantidad_contada - cantidad_sistema

        # Evaluar tolerancia
        fuera_tolerancia = False
        diff_abs = abs(diferencia)

        if tolerancia_unidades is not None and diff_abs > tolerancia_unidades:
            fuera_tolerancia = True

        if tolerancia_porcentaje is not None:
            base = max(cantidad_sistema, Decimal("1"))  # evitar div/0
            diff_rel = diff_abs / base  # ej: 0.05 = 5%
            if diff_rel > tolerancia_porcentaje:
                fuera_tolerancia = True

        # Si no se definió ninguna tolerancia,
        # marcamos fuera_tolerancia solo si hay diferencia ≠ 0.
        if tolerancia_unidades is None and tolerancia_porcentaje is None:
            fuera_tolerancia = (diferencia != 0)

        resultados.append(
            ResultadoConteoInventario(
                insumo=insumo,
                cantidad_sistema=cantidad_sistema,
                cantidad_contada=cantidad_contada,
                diferencia=diferencia,
                fuera_tolerancia=fuera_tolerancia,
            )
        )

    return resultados

@transaction.atomic
def aplicar_ajustes_conteo(
    *,
    almacen: Almacen,
    conteos: list[dict],
    usuario=None,
    tolerancia_unidades: Decimal | None = None,
    tolerancia_porcentaje: Decimal | None = None,
    referencia: str = "",
    aplicar_solo_fuera_tolerancia: bool = True,
) -> tuple[list[ResultadoConteoInventario], list[MovimientoInventario]]:
    """
    Aplica ajustes de inventario en base a un conteo físico.

    - Calcula diferencias vs stock del sistema.
    - Genera ajustes (entrada/salida) usando registrar_ajuste_inventario
      solo cuando corresponda.

    Retorna:
    - lista de resultados (dif/sistema/contado/flag)
    - lista de movimientos de ajuste creados
    """

    resultados = calcular_diferencias_conteo(
        almacen=almacen,
        conteos=conteos,
        tolerancia_unidades=tolerancia_unidades,
        tolerancia_porcentaje=tolerancia_porcentaje,
    )

    movimientos: list[MovimientoInventario] = []
    hoy = timezone.now().date()
    referencia_base = referencia or f"CONTEO-{hoy.isoformat()}"

    for idx, res in enumerate(resultados, start=1):
        if res.diferencia == 0:
            continue

        if aplicar_solo_fuera_tolerancia and not res.fuera_tolerancia:
            continue

        motivo = f"Ajuste por conteo físico ({hoy.isoformat()})"
        ref_linea = f"{referencia_base}-L{idx}"

        mov = registrar_ajuste_inventario(
            insumo=res.insumo,
            almacen=almacen,
            cantidad=res.diferencia,  # puede ser + (entrada) o - (salida)
            usuario=usuario,
            motivo=motivo,
            referencia=ref_linea,
        )
        movimientos.append(mov)

    return resultados, movimientos


@transaction.atomic
def registrar_consumo_receta(
    *,
    plato: Plato,
    almacen: Almacen,
    cantidad_platos: Decimal,
    usuario=None,
    motivo: str = "",
    referencia: str = "",
    fecha_movimiento=None,
) -> list[MovimientoInventario]:
    """
    Registra el CONSUMO de insumos según la receta de un plato.

    - Para cada línea de receta (insumo + cantidad_por_plato):
        cantidad_total = cantidad_por_plato * cantidad_platos
    - Verifica que haya stock suficiente en el almacén.
    - Descuenta stock en StockInsumo.
    - Crea un MovimientoInventario SALIDA_CONSUMO_RECETA por insumo,
      con costo_unitario igual al costo_promedio actual del stock.

    NOTA: versión MVP sin manejo por lotes (usa solo StockInsumo).
    """

    if cantidad_platos <= 0:
        raise MovimientoInventarioError("La cantidad de platos debe ser > 0.")

    if not plato.activo:
        raise MovimientoInventarioError("No se puede consumir receta de un plato inactivo.")

    if fecha_movimiento is None:
        fecha_movimiento = timezone.now()

    receta = RecetaInsumo.objects.select_related("insumo").filter(plato=plato)

    if not receta.exists():
        raise MovimientoInventarioError("El plato no tiene receta definida.")

    # 1) Validar stock suficiente para TODOS los insumos primero
    requerimientos: dict[int, Decimal] = {}
    for linea in receta:
        cantidad_por_plato = linea.cantidad or Decimal("0")
        if cantidad_por_plato <= 0:
            continue
        cantidad_total = (cantidad_por_plato * cantidad_platos).quantize(Decimal("0.0001"))
        if cantidad_total <= 0:
            continue
        requerimientos[linea.insumo_id] = cantidad_total

    if not requerimientos:
        raise MovimientoInventarioError("La receta no tiene cantidades válidas para consumo.")

    stocks = {
        s.insumo_id: s
        for s in StockInsumo.objects.select_for_update().filter(
            almacen=almacen,
            insumo_id__in=requerimientos.keys(),
        )
    }

    # Validar stock
    for insumo_id, cantidad_req in requerimientos.items():
        stock = stocks.get(insumo_id)
        cantidad_actual = stock.cantidad_actual if stock else Decimal("0")
        if cantidad_actual < cantidad_req:
            insumo = RecetaInsumo.objects.get(plato=plato, insumo_id=insumo_id).insumo
            raise MovimientoInventarioError(
                f"No hay stock suficiente de '{insumo.nombre}' "
                f"en el almacén para consumir la receta. "
                f"Requerido {cantidad_req}, disponible {cantidad_actual}."
            )

    # 2) Aplicar salidas y crear movimientos
    movimientos: list[MovimientoInventario] = []
    motivo_base = motivo or f"Consumo receta plato '{plato.nombre}'"
    referencia_base = referencia or f"CONSUMO-{plato.id}-{fecha_movimiento.date().isoformat()}"

    for idx, linea in enumerate(receta, start=1):
        insumo = linea.insumo
        cantidad_req = requerimientos.get(insumo.id)
        if not cantidad_req:
            continue

        stock = stocks[insumo.id]
        costo_unitario = stock.costo_promedio or Decimal("0")

        # Actualizar stock
        stock.cantidad_actual = (stock.cantidad_actual - cantidad_req).quantize(Decimal("0.0001"))
        stock.save(update_fields=["cantidad_actual", "updated_at"])

        # Crear movimiento
        mov = MovimientoInventario.objects.create(
            insumo=insumo,
            almacen=almacen,
            tipo=MovimientoInventario.TIPO_SALIDA_CONSUMO_RECETA,
            cantidad=-cantidad_req,  # salida → negativa
            costo_unitario=costo_unitario,
            fecha_movimiento=fecha_movimiento,
            motivo=f"{motivo_base} (L{idx})",
            referencia=f"{referencia_base}-L{idx}",
            usuario=usuario,
        )
        movimientos.append(mov)

    return movimientos

@transaction.atomic
def registrar_merma(
    *,
    insumo: Insumo,
    almacen: Almacen,
    cantidad: Decimal,
    usuario=None,
    motivo: str,
    referencia: str = "",
    fecha_movimiento=None,
) -> MovimientoInventario:
    """
    Registra una MERMA de inventario (pérdida, daño, vencimiento, etc.).

    - La cantidad DEBE ser negativa (ej: -2.000).
    - No permite dejar stock en negativo.
    - Usa el costo_promedio actual del stock como costo_unitario.
    """

    if cantidad >= 0:
        raise MovimientoInventarioError("La cantidad de una merma debe ser negativa (< 0).")

    if not motivo or not motivo.strip():
        raise MovimientoInventarioError("El motivo de la merma es obligatorio.")

    if fecha_movimiento is None:
        fecha_movimiento = timezone.now()

    try:
        stock = StockInsumo.objects.select_for_update().get(
            insumo=insumo,
            almacen=almacen,
        )
    except StockInsumo.DoesNotExist:
        raise MovimientoInventarioError(
            "No existe stock para este insumo en el almacén para registrar merma."
        )

    cantidad_actual = stock.cantidad_actual or Decimal("0")
    nueva_cantidad = cantidad_actual + cantidad  # cantidad es negativa

    if nueva_cantidad < 0:
        raise MovimientoInventarioError(
            f"No se puede registrar merma. Stock insuficiente. "
            f"Actual: {cantidad_actual}, merma: {cantidad}."
        )

    stock.cantidad_actual = nueva_cantidad
    stock.save(update_fields=["cantidad_actual", "updated_at"])

    costo_unitario = stock.costo_promedio or Decimal("0")

    movimiento = MovimientoInventario.objects.create(
        insumo=insumo,
        almacen=almacen,
        tipo=MovimientoInventario.TIPO_SALIDA_MERMA,
        cantidad=cantidad,  # negativa
        costo_unitario=costo_unitario,
        fecha_movimiento=fecha_movimiento,
        motivo=motivo,
        referencia=referencia,
        usuario=usuario,
    )

    return movimiento



