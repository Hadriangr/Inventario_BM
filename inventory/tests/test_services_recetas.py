from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from inventory.models import UnidadMedida, Insumo, Plato, RecetaInsumo
from inventory.services.inventory import calcular_costo_receta


class CalculoCostoRecetaTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.insumo1 = Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
            costo_promedio=Decimal("0.0100"),  # $0.01 por gramo
        )
        self.insumo2 = Insumo.objects.create(
            nombre="Levadura",
            unidad=self.unidad,
            costo_promedio=Decimal("0.0500"),  # $0.05 por gramo
        )

        self.plato = Plato.objects.create(
            nombre="Pan casero",
            descripcion="Pan básico",
            precio_venta=Decimal("1000.00"),
            categoria="Panadería",
        )

    def test_costo_receta_simple(self):
        # Harina: 500 g * 0.01 = 5.00
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo1,
            cantidad=Decimal("500.0000"),
        )
        # Levadura: 10 g * 0.05 = 0.50
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo2,
            cantidad=Decimal("10.0000"),
        )

        costo = calcular_costo_receta(plato=self.plato, guardar=True)

        # Costo esperado: 5.50
        self.assertEqual(costo, Decimal("5.5000"))

        self.plato.refresh_from_db()
        self.assertEqual(self.plato.costo_receta, Decimal("5.5000"))

    def test_plato_sin_receta_tiene_costo_cero(self):
        costo = calcular_costo_receta(plato=self.plato, guardar=True)
        self.assertEqual(costo, Decimal("0.0000"))
        self.plato.refresh_from_db()
        self.assertEqual(self.plato.costo_receta, Decimal("0.0000"))

class IndicadoresPlatoTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.insumo = Insumo.objects.create(
            nombre="Queso",
            unidad=self.unidad,
            costo_promedio=Decimal("0.0200"),  # $0.02 por gramo
        )

        self.plato = Plato.objects.create(
            nombre="Pizza",
            descripcion="Pizza sencilla",
            precio_venta=Decimal("5000.00"),
            categoria="Pizzería",
        )

        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo,
            cantidad=Decimal("100.0000"),  # 100 g -> 2.00
        )

        # calculamos costo_receta
        calcular_costo_receta(plato=self.plato, guardar=True)
        self.plato.refresh_from_db()

    def test_indicadores_plato(self):
        # costo_receta: 100 g * 0.02 = 2.00
        self.assertEqual(self.plato.costo_receta, Decimal("2.0000"))

        # food cost % = (2 / 5000) * 100 = 0.04%
        self.assertEqual(self.plato.food_cost_porcentaje, Decimal("0.04"))

        # margen bruto = 5000 - 2 = 4998
        self.assertEqual(self.plato.margen_bruto, Decimal("4998.0000"))

        # margen bruto % ≈ (4998 / 5000) * 100 ≈ 99.96%
        self.assertEqual(self.plato.margen_bruto_porcentaje, Decimal("99.96"))

