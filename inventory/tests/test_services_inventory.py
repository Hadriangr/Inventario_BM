from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from inventory.models import (
    UnidadMedida,
    Almacen,
    Insumo,
    StockInsumo,
    LoteInsumo,
    MovimientoInventario,
)
from inventory.services.inventory import (
    registrar_entrada_compra,
    registrar_ajuste_inventario,
    registrar_traspaso,
    obtener_stocks_bajo_minimo,
    obtener_stocks_sobre_maximo,
    obtener_lotes_por_vencer,
    obtener_lotes_vencidos,
    MovimientoInventarioError,
)

User = get_user_model()


class RegistrarEntradaCompraTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_test",
            password="password123",
        )

        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.insumo = Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
            stock_minimo=Decimal("5.000"),
            stock_maximo=Decimal("50.000"),
            costo_promedio=Decimal("0"),
        )

        self.almacen = Almacen.objects.create(
            nombre="Bodega Principal",
            ubicacion="Local Centro",
            responsable=self.user,
        )

    def test_registrar_entrada_compra_crea_stock_si_no_existe(self):
        self.assertFalse(
            StockInsumo.objects.filter(insumo=self.insumo, almacen=self.almacen).exists()
        )

        movimiento = registrar_entrada_compra(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("10.000"),
            costo_unitario=Decimal("100.00"),
            usuario=self.user,
            motivo="Compra inicial",
            referencia="FAC-001",
            fecha_movimiento=timezone.now(),
        )

        stock = StockInsumo.objects.get(insumo=self.insumo, almacen=self.almacen)

        self.assertEqual(movimiento.cantidad, Decimal("10.000"))
        self.assertEqual(stock.cantidad_actual, Decimal("10.000"))
        self.assertEqual(stock.costo_promedio, Decimal("100.0000"))
        self.assertEqual(self.insumo.costo_promedio, Decimal("100.0000"))

    def test_registrar_entrada_compra_actualiza_costo_promedio_ponderado(self):
        # Stock inicial: 10 unidades a 100
        registrar_entrada_compra(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("10.000"),
            costo_unitario=Decimal("100.00"),
            usuario=self.user,
            motivo="Compra 1",
            referencia="FAC-001",
            fecha_movimiento=timezone.now(),
        )

        stock = StockInsumo.objects.get(insumo=self.insumo, almacen=self.almacen)
        self.assertEqual(stock.cantidad_actual, Decimal("10.000"))
        self.assertEqual(stock.costo_promedio, Decimal("100.0000"))

        # Nueva entrada: 20 unidades a 200
        registrar_entrada_compra(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("20.000"),
            costo_unitario=Decimal("200.00"),
            usuario=self.user,
            motivo="Compra 2",
            referencia="FAC-002",
            fecha_movimiento=timezone.now(),
        )

        stock.refresh_from_db()
        self.insumo.refresh_from_db()

        # Cálculo esperado:
        # qty_ant = 10, costo_ant = 100 → valor_ant = 1000
        # qty_nueva = 20, costo_unit = 200 → valor_nueva = 4000
        # total_qty = 30 → costo_promedio = (1000 + 4000) / 30 = 5000 / 30 = 166.666...
        # redondeado a 4 decimales → 166.6667
        self.assertEqual(stock.cantidad_actual, Decimal("30.000"))
        self.assertEqual(stock.costo_promedio, Decimal("166.6667"))
        self.assertEqual(self.insumo.costo_promedio, Decimal("166.6667"))

    def test_registrar_entrada_compra_rechaza_cantidad_no_positiva(self):
        with self.assertRaises(MovimientoInventarioError):
            registrar_entrada_compra(
                insumo=self.insumo,
                almacen=self.almacen,
                cantidad=Decimal("0"),
                costo_unitario=Decimal("100.00"),
                usuario=self.user,
            )

    def test_registrar_entrada_compra_rechaza_costo_no_positivo(self):
        with self.assertRaises(MovimientoInventarioError):
            registrar_entrada_compra(
                insumo=self.insumo,
                almacen=self.almacen,
                cantidad=Decimal("5.000"),
                costo_unitario=Decimal("0"),
                usuario=self.user,
            )


class RegistrarAjusteInventarioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_ajuste",
            password="password123",
        )

        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.insumo = Insumo.objects.create(
            nombre="Azúcar",
            unidad=self.unidad,
            costo_promedio=Decimal("100.0000"),
        )

        self.almacen = Almacen.objects.create(
            nombre="Bodega Azúcar",
            ubicacion="Local Centro",
            responsable=self.user,
        )

    def test_ajuste_positivo_crea_stock_si_no_existe(self):
        self.assertFalse(
            StockInsumo.objects.filter(insumo=self.insumo, almacen=self.almacen).exists()
        )

        movimiento = registrar_ajuste_inventario(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("5.000"),
            usuario=self.user,
            motivo="Conteo inicial",
            referencia="AJ-001",
        )

        stock = StockInsumo.objects.get(insumo=self.insumo, almacen=self.almacen)

        self.assertEqual(movimiento.cantidad, Decimal("5.000"))
        self.assertEqual(stock.cantidad_actual, Decimal("5.000"))
        # No tocamos costo_promedio del insumo ni del stock
        self.assertEqual(self.insumo.costo_promedio, Decimal("100.0000"))
        self.assertEqual(stock.costo_promedio, Decimal("100.0000"))

    def test_ajuste_negativo_disminuye_stock(self):
        # Primero generamos stock con una compra
        registrar_entrada_compra(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("20.000"),
            costo_unitario=Decimal("100.00"),
            usuario=self.user,
            motivo="Compra inicial",
            referencia="FAC-100",
            fecha_movimiento=timezone.now(),
        )

        stock = StockInsumo.objects.get(insumo=self.insumo, almacen=self.almacen)
        self.assertEqual(stock.cantidad_actual, Decimal("20.000"))

        movimiento = registrar_ajuste_inventario(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("-5.000"),
            usuario=self.user,
            motivo="Ajuste por pérdida",
            referencia="AJ-002",
        )

        stock.refresh_from_db()
        self.insumo.refresh_from_db()

        self.assertEqual(movimiento.cantidad, Decimal("-5.000"))
        self.assertEqual(stock.cantidad_actual, Decimal("15.000"))
        # costo_promedio no cambia
        self.assertEqual(stock.costo_promedio, Decimal("100.0000"))
        self.assertEqual(self.insumo.costo_promedio, Decimal("100.0000"))

    def test_ajuste_negativo_no_permite_stock_negativo(self):
        StockInsumo.objects.create(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad_actual=Decimal("2.000"),
            costo_promedio=Decimal("100.0000"),
        )

        with self.assertRaises(MovimientoInventarioError):
            registrar_ajuste_inventario(
                insumo=self.insumo,
                almacen=self.almacen,
                cantidad=Decimal("-5.000"),
                usuario=self.user,
                motivo="Intento de ajuste inválido",
                referencia="AJ-003",
            )

    def test_motivo_es_obligatorio(self):
        with self.assertRaises(MovimientoInventarioError):
            registrar_ajuste_inventario(
                insumo=self.insumo,
                almacen=self.almacen,
                cantidad=Decimal("5.000"),
                usuario=self.user,
                motivo="   ",
                referencia="AJ-004",
            )


class AlertasStockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_alertas",
            password="password123",
        )

        self.unidad = UnidadMedida.objects.create(
            nombre="Unidad",
            abreviatura="u",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.almacen = Almacen.objects.create(
            nombre="Bodega Central",
            ubicacion="Local Centro",
            responsable=self.user,
        )

        # Insumo bajo mínimo
        self.insumo_bajo = Insumo.objects.create(
            nombre="Insumo Bajo",
            unidad=self.unidad,
            stock_minimo=Decimal("10.000"),
            stock_maximo=Decimal("100.000"),
            costo_promedio=Decimal("50.0000"),
        )
        StockInsumo.objects.create(
            insumo=self.insumo_bajo,
            almacen=self.almacen,
            cantidad_actual=Decimal("5.000"),
            costo_promedio=Decimal("50.0000"),
        )

        # Insumo sobre máximo
        self.insumo_sobre = Insumo.objects.create(
            nombre="Insumo Sobre",
            unidad=self.unidad,
            stock_minimo=Decimal("10.000"),
            stock_maximo=Decimal("20.000"),
            costo_promedio=Decimal("30.0000"),
        )
        StockInsumo.objects.create(
            insumo=self.insumo_sobre,
            almacen=self.almacen,
            cantidad_actual=Decimal("25.000"),
            costo_promedio=Decimal("30.0000"),
        )

        # Insumo en rango OK
        self.insumo_ok = Insumo.objects.create(
            nombre="Insumo OK",
            unidad=self.unidad,
            stock_minimo=Decimal("10.000"),
            stock_maximo=Decimal("30.000"),
            costo_promedio=Decimal("10.0000"),
        )
        StockInsumo.objects.create(
            insumo=self.insumo_ok,
            almacen=self.almacen,
            cantidad_actual=Decimal("20.000"),
            costo_promedio=Decimal("10.0000"),
        )

    def test_propiedades_bajo_minimo_y_sobre_maximo(self):
        stock_bajo = StockInsumo.objects.get(insumo=self.insumo_bajo, almacen=self.almacen)
        stock_sobre = StockInsumo.objects.get(insumo=self.insumo_sobre, almacen=self.almacen)
        stock_ok = StockInsumo.objects.get(insumo=self.insumo_ok, almacen=self.almacen)

        self.assertTrue(stock_bajo.bajo_minimo)
        self.assertFalse(stock_bajo.sobre_maximo)
        self.assertEqual(stock_bajo.nivel_alerta, "bajo_minimo")

        self.assertFalse(stock_sobre.bajo_minimo)
        self.assertTrue(stock_sobre.sobre_maximo)
        self.assertEqual(stock_sobre.nivel_alerta, "sobre_maximo")

        self.assertFalse(stock_ok.bajo_minimo)
        self.assertFalse(stock_ok.sobre_maximo)
        self.assertEqual(stock_ok.nivel_alerta, "ok")

    def test_obtener_stocks_bajo_minimo(self):
        qs = obtener_stocks_bajo_minimo()
        nombres = {s.insumo.nombre for s in qs}
        self.assertIn("Insumo Bajo", nombres)
        self.assertNotIn("Insumo Sobre", nombres)
        self.assertNotIn("Insumo OK", nombres)

    def test_obtener_stocks_sobre_maximo(self):
        qs = obtener_stocks_sobre_maximo()
        nombres = {s.insumo.nombre for s in qs}
        self.assertIn("Insumo Sobre", nombres)
        self.assertNotIn("Insumo Bajo", nombres)
        self.assertNotIn("Insumo OK", nombres)


class LotesInventarioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_lotes",
            password="password123",
        )

        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.insumo = Insumo.objects.create(
            nombre="Jamón",
            unidad=self.unidad,
            stock_minimo=Decimal("0"),
            costo_promedio=Decimal("0"),
        )

        self.almacen = Almacen.objects.create(
            nombre="Cámara Fría",
            ubicacion="Local Centro",
            responsable=self.user,
        )

    def test_crear_lote_en_entrada_compra(self):
        hoy = date.today()
        vencimiento = hoy + timedelta(days=10)

        registrar_entrada_compra(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=Decimal("5.000"),
            costo_unitario=Decimal("1000.00"),
            usuario=self.user,
            motivo="Compra perecible",
            referencia="FAC-LOTE-001",
            fecha_movimiento=timezone.now(),
            numero_lote="L001",
            fecha_vencimiento=vencimiento,
        )

        lote = LoteInsumo.objects.get(
            insumo=self.insumo,
            almacen=self.almacen,
            numero_lote="L001",
            fecha_vencimiento=vencimiento,
        )

        self.assertEqual(lote.cantidad_actual, Decimal("5.000"))
        self.assertEqual(lote.costo_unitario, Decimal("1000.0000"))
        self.assertFalse(lote.esta_vencido)
        self.assertTrue(lote.por_vencer_en(15))

    def test_lotes_por_vencer_y_vencidos(self):
        hoy = date.today()
        vencido = hoy - timedelta(days=1)
        por_vencer = hoy + timedelta(days=3)
        futuro_lejano = hoy + timedelta(days=30)

        LoteInsumo.objects.create(
            insumo=self.insumo,
            almacen=self.almacen,
            numero_lote="VENCIDO",
            fecha_vencimiento=vencido,
            cantidad_actual=Decimal("2.000"),
            costo_unitario=Decimal("500.00"),
        )
        LoteInsumo.objects.create(
            insumo=self.insumo,
            almacen=self.almacen,
            numero_lote="PROX",
            fecha_vencimiento=por_vencer,
            cantidad_actual=Decimal("3.000"),
            costo_unitario=Decimal("600.00"),
        )
        LoteInsumo.objects.create(
            insumo=self.insumo,
            almacen=self.almacen,
            numero_lote="LEJOS",
            fecha_vencimiento=futuro_lejano,
            cantidad_actual=Decimal("4.000"),
            costo_unitario=Decimal("700.00"),
        )

        por_vencer_qs = obtener_lotes_por_vencer(dias=7, almacen=self.almacen)
        nombres_por_vencer = {l.numero_lote for l in por_vencer_qs}
        self.assertIn("PROX", nombres_por_vencer)
        self.assertNotIn("VENCIDO", nombres_por_vencer)
        self.assertNotIn("LEJOS", nombres_por_vencer)

        vencidos_qs = obtener_lotes_vencidos(almacen=self.almacen)
        nombres_vencidos = {l.numero_lote for l in vencidos_qs}
        self.assertIn("VENCIDO", nombres_vencidos)
        self.assertNotIn("PROX", nombres_vencidos)
        self.assertNotIn("LEJOS", nombres_vencidos)


class TraspasoInventarioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user_traspaso",
            password="password123",
        )

        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

        self.insumo = Insumo.objects.create(
            nombre="Queso rallado",
            unidad=self.unidad,
            costo_promedio=Decimal("0"),
        )

        self.almacen_origen = Almacen.objects.create(
            nombre="Bodega Principal",
            ubicacion="Local Centro",
            responsable=self.user,
        )
        self.almacen_destino = Almacen.objects.create(
            nombre="Cocina",
            ubicacion="Local Centro",
            responsable=self.user,
        )

        # Cargamos stock inicial en origen vía compra
        registrar_entrada_compra(
            insumo=self.insumo,
            almacen=self.almacen_origen,
            cantidad=Decimal("10.000"),
            costo_unitario=Decimal("100.00"),
            usuario=self.user,
            motivo="Compra inicial",
            referencia="FAC-TR-001",
            fecha_movimiento=timezone.now(),
        )
        self.insumo.refresh_from_db()

    def test_traspaso_simple_disminuye_origen_y_aumenta_destino(self):
        mov_salida, mov_entrada = registrar_traspaso(
            insumo=self.insumo,
            almacen_origen=self.almacen_origen,
            almacen_destino=self.almacen_destino,
            cantidad=Decimal("4.000"),
            usuario=self.user,
            motivo="Traspaso a cocina",
            referencia="TR-001",
        )

        stock_origen = StockInsumo.objects.get(
            insumo=self.insumo, almacen=self.almacen_origen
        )
        stock_destino = StockInsumo.objects.get(
            insumo=self.insumo, almacen=self.almacen_destino
        )

        self.assertEqual(stock_origen.cantidad_actual, Decimal("6.000"))
        self.assertEqual(stock_destino.cantidad_actual, Decimal("4.000"))

        self.assertEqual(stock_origen.costo_promedio, Decimal("100.0000"))
        self.assertEqual(stock_destino.costo_promedio, Decimal("100.0000"))

        self.assertEqual(mov_salida.tipo, MovimientoInventario.TIPO_SALIDA_TRASPASO)
        self.assertEqual(mov_salida.cantidad, Decimal("-4.000"))

        self.assertEqual(mov_entrada.tipo, MovimientoInventario.TIPO_ENTRADA_TRASPASO)
        self.assertEqual(mov_entrada.cantidad, Decimal("4.000"))

    def test_traspaso_no_permite_mismo_almacen(self):
        with self.assertRaises(MovimientoInventarioError):
            registrar_traspaso(
                insumo=self.insumo,
                almacen_origen=self.almacen_origen,
                almacen_destino=self.almacen_origen,
                cantidad=Decimal("1.000"),
                usuario=self.user,
            )

    def test_traspaso_no_permite_stock_insuficiente(self):
        with self.assertRaises(MovimientoInventarioError):
            registrar_traspaso(
                insumo=self.insumo,
                almacen_origen=self.almacen_origen,
                almacen_destino=self.almacen_destino,
                cantidad=Decimal("50.000"),
                usuario=self.user,
            )
