# inventory/services/recetas.py

from decimal import Decimal

from django.utils import timezone

from inventory.models import Plato, RecetaInsumo


def calcular_costo_receta(*, plato: Plato, guardar: bool = False) -> Decimal:
    """
    Calcula el costo total de la receta de un plato sumando:
        costo_promedio_insumo * cantidad_por_plato

    - Usa el costo_promedio actual de cada insumo.
    - Ignora líneas sin cantidad o con cantidad <= 0.
    - Si guardar=True, actualiza plato.costo_receta en la base de datos.

    Retorna el costo total (Decimal).
    """
    receta = (
        RecetaInsumo.objects.select_related("insumo")
        .filter(plato=plato)
    )

    total = Decimal("0")

    for linea in receta:
        if not linea.cantidad or linea.cantidad <= 0:
            continue

        insumo = linea.insumo
        costo_insumo = insumo.costo_promedio or Decimal("0")
        total += linea.cantidad * costo_insumo

    # Redondeamos a 4 decimales
    total = total.quantize(Decimal("0.0001"))

    if guardar:
        plato.costo_receta = total
        # Si tu modelo Plato tiene TimeStampedModel con updated_at:
        plato.updated_at = timezone.now()
        plato.save(update_fields=["costo_receta", "updated_at"])

    return total