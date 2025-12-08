from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import date

from inventory.models import (
    UnidadMedida,
    Insumo,
    Plato,
    RecetaInsumo,
    MenuPlan,
    MenuPlanItem,
    Almacen,
    StockInsumo,
)
from inventory.services.planificacion import calcular_requerimientos_plan


class CalcularRequerimientosPlanTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.almacen = Almacen.objects.create(
            nombre="Bodega Principal",
            ubicacion="Local",
        )

        # Insumos
        self.harina = Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
        )
        self.queso = Insumo.objects.create(
            nombre="Queso rallado",
            unidad=self.unidad,
        )

        # Plato 1
        self.plato = Plato.objects.create(
            nombre="Pizza",
            precio_venta=Decimal("10000.00"),
        )
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.harina,
            cantidad=Decimal("100"),  # 100g por porción
        )
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.queso,
            cantidad=Decimal("50"),   # 50g por porción
        )

        # Plan de menú
        self.plan = MenuPlan.objects.create(
            nombre="Plan semana",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            almacen=self.almacen,
        )
        MenuPlanItem.objects.create(
            plan=self.plan,
            fecha=date.today(),
            servicio="almuerzo",
            plato=self.plato,
            porciones_planificadas=Decimal("10"),  # 10 pizzas
        )

    def test_requerimientos_sin_stock(self):
        reqs = calcular_requerimientos_plan(plan=self.plan, incluir_stock=False)

        # Esperamos: Harina 100*10 = 1000g, Queso 50*10 = 500g
        datos = {r["insumo"].nombre: r for r in reqs}
        self.assertEqual(datos["Harina"]["cantidad_necesaria"], Decimal("1000"))
        self.assertEqual(datos["Queso rallado"]["cantidad_necesaria"], Decimal("500"))

    def test_requerimientos_con_stock(self):
        # Cargamos stock parcial
        StockInsumo.objects.create(
            insumo=self.harina,
            almacen=self.almacen,
            cantidad_actual=Decimal("600"),
            costo_promedio=Decimal("0"),
        )
        StockInsumo.objects.create(
            insumo=self.queso,
            almacen=self.almacen,
            cantidad_actual=Decimal("100"),
            costo_promedio=Decimal("0"),
        )

        reqs = calcular_requerimientos_plan(plan=self.plan, incluir_stock=True)

        datos = {r["insumo"].nombre: r for r in reqs}

        self.assertEqual(datos["Harina"]["stock_disponible"], Decimal("600"))
        self.assertEqual(datos["Harina"]["faltante"], Decimal("400"))  # 1000 - 600

        self.assertEqual(datos["Queso rallado"]["stock_disponible"], Decimal("100"))
        self.assertEqual(datos["Queso rallado"]["faltante"], Decimal("400"))  # 500 - 100
