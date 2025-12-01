from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from inventory.models import (
    UnidadMedida,
    Almacen,
    Insumo,
    StockInsumo,
    RecetaInsumo,
    Plato,
    MovimientoInventario,
)
from inventory.services.inventory import (
    calcular_diferencias_conteo,
    aplicar_ajustes_conteo,
    registrar_consumo_receta,
    registrar_merma,
    MovimientoInventarioError,
)

User = get_user_model()

class ConteoInventarioMVPTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_conteo",
            password="password123",
        )
        self.unidad = UnidadMedida.objects.create(
            nombre="Unidad",
            abreviatura="u",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.almacen = Almacen.objects.create(
            nombre="Bodega",
            ubicacion="Local Centro",
            responsable=self.user,
        )
        self.insumo1 = Insumo.objects.create(
            nombre="Tomates",
            unidad=self.unidad,
            stock_minimo=Decimal("0"),
            costo_promedio=Decimal("100.0000"),
        )
        self.insumo2 = Insumo.objects.create(
            nombre="Cebollas",
            unidad=self.unidad,
            stock_minimo=Decimal("0"),
            costo_promedio=Decimal("50.0000"),
        )

        StockInsumo.objects.create(
            insumo=self.insumo1,
            almacen=self.almacen,
            cantidad_actual=Decimal("10.000"),
            costo_promedio=Decimal("100.0000"),
        )
        StockInsumo.objects.create(
            insumo=self.insumo2,
            almacen=self.almacen,
            cantidad_actual=Decimal("20.000"),
            costo_promedio=Decimal("50.0000"),
        )

    def test_calcular_diferencias_conteo(self):
        conteos = [
            {"insumo_id": self.insumo1.id, "cantidad_contada": "11.000"},  # +1
            {"insumo_id": self.insumo2.id, "cantidad_contada": "18.000"},  # -2
        ]

        resultados = calcular_diferencias_conteo(
            almacen=self.almacen,
            conteos=conteos,
            tolerancia_unidades=Decimal("1.000"),  # 1 unidad
        )

        self.assertEqual(len(resultados), 2)

        r1 = next(r for r in resultados if r.insumo == self.insumo1)
        r2 = next(r for r in resultados if r.insumo == self.insumo2)

        self.assertEqual(r1.diferencia, Decimal("1.000"))
        self.assertFalse(r1.fuera_tolerancia)  # igual a tolerancia

        self.assertEqual(r2.diferencia, Decimal("-2.000"))
        self.assertTrue(r2.fuera_tolerancia)  # supera tolerancia

    def test_aplicar_ajustes_conteo_crea_ajuste_solo_fuera_tolerancia(self):
        conteos = [
            {"insumo_id": self.insumo1.id, "cantidad_contada": "11.000"},  # +1
            {"insumo_id": self.insumo2.id, "cantidad_contada": "18.000"},  # -2
        ]

        resultados, movimientos = aplicar_ajustes_conteo(
            almacen=self.almacen,
            conteos=conteos,
            usuario=self.user,
            tolerancia_unidades=Decimal("1.000"),
            aplicar_solo_fuera_tolerancia=True,
        )

        # Solo debe ajustar el insumo2 (diferencia -2)
        self.assertEqual(len(movimientos), 1)
        mov = movimientos[0]
        self.assertEqual(mov.insumo, self.insumo2)
        self.assertEqual(mov.cantidad, Decimal("-2.000"))

        # Verificamos que el stock se actualizó
        stock1 = StockInsumo.objects.get(insumo=self.insumo1, almacen=self.almacen)
        stock2 = StockInsumo.objects.get(insumo=self.insumo2, almacen=self.almacen)

        self.assertEqual(stock1.cantidad_actual, Decimal("10.000"))  # sin cambios
        self.assertEqual(stock2.cantidad_actual, Decimal("18.000"))  # 20 - 2


class ConsumoRecetaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_consumo",
            password="password123",
        )
        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.almacen = Almacen.objects.create(
            nombre="Cocina",
            ubicacion="Local Centro",
            responsable=self.user,
        )

        self.insumo1 = Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
            costo_promedio=Decimal("0.0100"),  # $0.01 por gramo
        )
        self.insumo2 = Insumo.objects.create(
            nombre="Queso",
            unidad=self.unidad,
            costo_promedio=Decimal("0.0500"),  # $0.05 por gramo
        )

        StockInsumo.objects.create(
            insumo=self.insumo1,
            almacen=self.almacen,
            cantidad_actual=Decimal("1000.0000"),
            costo_promedio=Decimal("0.0100"),
        )
        StockInsumo.objects.create(
            insumo=self.insumo2,
            almacen=self.almacen,
            cantidad_actual=Decimal("500.0000"),
            costo_promedio=Decimal("0.0500"),
        )

        self.plato = Plato.objects.create(
            nombre="Pan de queso",
            descripcion="Pan relleno de queso",
            precio_venta=Decimal("1000.00"),
            categoria="Panadería",
            activo=True,
        )

        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo1,
            cantidad=Decimal("100.0000"),  # 100 g de harina por pan
        )
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo2,
            cantidad=Decimal("20.0000"),  # 20 g de queso por pan
        )

    def test_consumo_receta_descuenta_stock(self):
        # Consumimos 3 panes
        movimientos = registrar_consumo_receta(
            plato=self.plato,
            almacen=self.almacen,
            cantidad_platos=Decimal("3"),
            usuario=self.user,
        )

        self.assertEqual(len(movimientos), 2)  # harina + queso

        stock_harina = StockInsumo.objects.get(insumo=self.insumo1, almacen=self.almacen)
        stock_queso = StockInsumo.objects.get(insumo=self.insumo2, almacen=self.almacen)

        # Harina: 1000 - (3 * 100) = 700
        self.assertEqual(stock_harina.cantidad_actual, Decimal("700.0000"))
        # Queso: 500 - (3 * 20) = 440
        self.assertEqual(stock_queso.cantidad_actual, Decimal("440.0000"))

        for mov in movimientos:
            self.assertEqual(mov.tipo, MovimientoInventario.TIPO_SALIDA_CONSUMO_RECETA)
            self.assertLess(mov.cantidad, 0)  # salidas negativas

    def test_consumo_receta_sin_stock_suficiente_falla(self):
        with self.assertRaises(MovimientoInventarioError):
            registrar_consumo_receta(
                plato=self.plato,
                almacen=self.almacen,
                cantidad_platos=Decimal("1000"),  # claramente demasiado
                usuario=self.user,
            )


class MermaInventarioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_merma",
            password="password123",
        )
        self.unidad = UnidadMedida.objects.create(
            nombre="Unidad",
            abreviatura="u",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.almacen = Almacen.objects.create(
            nombre="Bodega",
            ubicacion="Local Centro",
            responsable=self.user,
        )
        self.insumo = Insumo.objects.create(
            nombre="Huevos",
            unidad=self.unidad,
            costo_promedio=Decimal("100.0000"),
        )
        StockInsumo.objects.create(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad_actual=Decimal("30.000"),
            costo_promedio=Decimal("100.0000"),
        )

    def test_merma_descuenta_stock(self):
        mov = registrar_merma(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("-3.000"),  # se rompieron 3
            usuario=self.user,
            motivo="Huevos rotos",
            referencia="MERMA-001",
        )

        stock = StockInsumo.objects.get(insumo=self.insumo, almacen=self.almacen)
        self.assertEqual(stock.cantidad_actual, Decimal("27.000"))
        self.assertEqual(mov.tipo, MovimientoInventario.TIPO_SALIDA_MERMA)
        self.assertEqual(mov.cantidad, Decimal("-3.000"))

    def test_merma_no_permite_dejar_stock_negativo(self):
        with self.assertRaises(MovimientoInventarioError):
            registrar_merma(
                insumo=self.insumo,
                almacen=self.almacen,
                cantidad=Decimal("-100.000"),
                usuario=self.user,
                motivo="Error brutal",
            )

