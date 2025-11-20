from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from inventory.models import (
    UnidadMedida,
    Proveedor,
    Insumo,
    Almacen,
    StockInsumo,
    Plato,
    RecetaInsumo,
)

User = get_user_model()


class UnidadMedidaModelTests(TestCase):
    def test_crear_unidad_medida(self):
        unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.assertEqual(str(unidad), "Gramo (g)")
        self.assertTrue(unidad.es_base)
        self.assertEqual(unidad.factor_base, Decimal("1"))

    def test_nombre_y_abreviatura_son_unicos(self):
        UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        with self.assertRaises(IntegrityError):
            UnidadMedida.objects.create(
                nombre="Gramo",
                abreviatura="g",
                es_base=False,
                factor_base=Decimal("1"),
            )


class ProveedorModelTests(TestCase):
    def test_crear_proveedor_basico(self):
        proveedor = Proveedor.objects.create(
            nombre="Proveedor Uno",
            email="proveedor@ejemplo.com",
            telefono="123456789",
        )
        self.assertEqual(str(proveedor), "Proveedor Uno")
        self.assertTrue(proveedor.activo)


class InsumoModelTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor Principal",
        )

    def test_crear_insumo_basico(self):
        insumo = Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
            proveedor_principal=self.proveedor,
            stock_minimo=Decimal("5.000"),
            stock_maximo=Decimal("50.000"),
            costo_promedio=Decimal("100.50"),
        )
        self.assertEqual(str(insumo), "Harina")
        self.assertTrue(insumo.activo)
        self.assertEqual(insumo.unidad, self.unidad)
        self.assertEqual(insumo.proveedor_principal, self.proveedor)

    def test_nombre_insumo_es_unico(self):
        Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
        )
        with self.assertRaises(IntegrityError):
            Insumo.objects.create(
                nombre="Harina",
                unidad=self.unidad,
            )


class AlmacenModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="responsable",
            password="test1234",
        )

    def test_crear_almacen(self):
        almacen = Almacen.objects.create(
            nombre="Bodega Principal",
            ubicacion="Local Centro",
            responsable=self.user,
        )
        self.assertIn("Bodega Principal", str(almacen))
        self.assertTrue(almacen.activo)

    def test_nombre_y_ubicacion_unicos(self):
        Almacen.objects.create(
            nombre="Bodega Principal",
            ubicacion="Local Centro",
        )
        with self.assertRaises(IntegrityError):
            Almacen.objects.create(
                nombre="Bodega Principal",
                ubicacion="Local Centro",
            )


class StockInsumoModelTests(TestCase):
    def setUp(self):
        unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.insumo = Insumo.objects.create(
            nombre="Azúcar",
            unidad=unidad,
        )
        self.almacen = Almacen.objects.create(
            nombre="Bodega Secos",
            ubicacion="Local Centro",
        )

    def test_crear_stock_insumo(self):
        stock = StockInsumo.objects.create(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad_actual=Decimal("10.000"),
            costo_promedio=Decimal("50.1234"),
        )
        self.assertEqual(stock.cantidad_actual, Decimal("10.000"))
        self.assertEqual(stock.insumo, self.insumo)
        self.assertEqual(stock.almacen, self.almacen)

    def test_unicidad_insumo_almacen(self):
        StockInsumo.objects.create(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad_actual=Decimal("5.000"),
        )
        with self.assertRaises(IntegrityError):
            StockInsumo.objects.create(
                insumo=self.insumo,
                almacen=self.almacen,
                cantidad_actual=Decimal("3.000"),
            )


class PlatoYRecetaModelTests(TestCase):
    def setUp(self):
        unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.insumo = Insumo.objects.create(
            nombre="Queso",
            unidad=unidad,
            costo_promedio=Decimal("10.00"),
        )
        self.plato = Plato.objects.create(
            nombre="Pizza Margarita",
            descripcion="Pizza clásica",
            precio_venta=Decimal("8000.00"),
            categoria="Principal",
        )

    def test_crear_plato(self):
        self.assertEqual(str(self.plato), "Pizza Margarita")
        self.assertTrue(self.plato.activo)

    def test_crear_receta_insumo(self):
        receta_insumo = RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo,
            cantidad=Decimal("100.000"),
        )
        self.assertEqual(receta_insumo.plato, self.plato)
        self.assertEqual(receta_insumo.insumo, self.insumo)
        self.assertEqual(receta_insumo.cantidad, Decimal("100.000"))

    def test_unicidad_plato_insumo_en_receta(self):
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo,
            cantidad=Decimal("100.000"),
        )
        with self.assertRaises(IntegrityError):
            RecetaInsumo.objects.create(
                plato=self.plato,
                insumo=self.insumo,
                cantidad=Decimal("50.000"),
            )
