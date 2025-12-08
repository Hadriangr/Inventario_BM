
from collections import defaultdict
from decimal import Decimal

from inventory.models import (
    MenuPlan,
    MenuPlanItem,
    RecetaInsumo,
    StockInsumo,
    Insumo,
    Almacen,
)


def calcular_requerimientos_plan(
    *,
    plan: MenuPlan,
    incluir_stock: bool = False,
    almacen: Almacen | None = None,
):
    """
    Calcula los requerimientos de insumos para un plan de menú.

    - Recorre todos los MenuPlanItem del plan.
    - Para cada plato, toma su receta (RecetaInsumo).
    - Requerimiento por línea = cantidad_receta * porciones_planificadas.
    - Suma por Insumo.

    Si incluir_stock=True y se indica un almacén (o el plan tiene uno asociado),
    también devuelve stock disponible y faltante.

    Retorna una lista de diccionarios con:
        {
            "insumo": <Insumo>,
            "unidad": <UnidadMedida>,
            "cantidad_necesaria": Decimal,
            "stock_disponible": Decimal | None,
            "faltante": Decimal | None,
        }
    """

    if almacen is None:
        almacen = plan.almacen  # puede seguir siendo None

    # 1) Acumular requerimientos por insumo
    requerimientos_por_insumo: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

    items = plan.items.select_related("plato")

    for item in items:
        receta_qs = RecetaInsumo.objects.select_related("insumo").filter(plato=item.plato)

        for linea in receta_qs:
            if not linea.cantidad or linea.cantidad <= 0:
                continue

            insumo = linea.insumo
            total_para_item = (linea.cantidad * item.porciones_planificadas)
            requerimientos_por_insumo[insumo.id] += total_para_item

    # 2) Si se pide incluir stock, obtener stock actual por insumo+almacén
    stock_por_insumo: dict[int, Decimal] = {}

    if incluir_stock and almacen is not None:
        stocks = StockInsumo.objects.filter(
            almacen=almacen,
            insumo_id__in=requerimientos_por_insumo.keys(),
        )
        for s in stocks:
            stock_por_insumo[s.insumo_id] = s.cantidad_actual or Decimal("0")

    # 3) Armar resultado ordenado por nombre de insumo
    insumos = Insumo.objects.filter(id__in=requerimientos_por_insumo.keys()).select_related("unidad")
    insumo_map = {i.id: i for i in insumos}

    resultado = []

    for insumo_id, cantidad_necesaria in requerimientos_por_insumo.items():
        insumo = insumo_map[insumo_id]
        unidad = insumo.unidad

        stock_disp = None
        faltante = None

        if incluir_stock and almacen is not None:
            stock_disp = stock_por_insumo.get(insumo_id, Decimal("0"))
            faltante = cantidad_necesaria - stock_disp
            if faltante < 0:
                faltante = Decimal("0")

        resultado.append(
            {
                "insumo": insumo,
                "unidad": unidad,
                "cantidad_necesaria": cantidad_necesaria,
                "stock_disponible": stock_disp,
                "faltante": faltante,
            }
        )

    # Ordenar por nombre de insumo para que sea más legible
    resultado.sort(key=lambda r: r["insumo"].nombre)

    return resultado
