from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import UnidadMedida, Proveedor, Insumo

User = get_user_model()


class UnidadMedidaAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.list_url = reverse("unidad-medida-list")
        self.detail_url_name = "unidad-medida-detail"

        # Creamos una unidad base para tener datos en el listado
        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )

    def test_list_unidades_medida(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        # Chequeo simple del contenido
        nombres = [u["nombre"] for u in response.data]
        self.assertIn("Gramo", nombres)

    def test_create_unidad_medida_requires_authentication(self):
        payload = {
            "nombre": "Kilogramo",
            "abreviatura": "kg",
            "es_base": False,
            "factor_base": "1000",
        }
        response = self.client.post(self.list_url, payload, format="json")
        # Dependiendo de la config puede ser 401 o 403, aceptamos ambos
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_unidad_medida_success(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "nombre": "Mililitro",
            "abreviatura": "ml",
            "es_base": False,
            "factor_base": "1",
        }
        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nombre"], "Mililitro")
        self.assertTrue(UnidadMedida.objects.filter(nombre="Mililitro").exists())


class InsumoAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.list_url = reverse("insumo-list")
        self.detail_url_name = "insumo-detail"

        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor Test",
            email="proveedor@test.com",
        )

        self.insumo = Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
            proveedor_principal=self.proveedor,
            stock_minimo=Decimal("5.000"),
            stock_maximo=Decimal("50.000"),
            costo_promedio=Decimal("100.50"),
        )

    def test_list_insumos(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        nombres = [i["nombre"] for i in response.data]
        self.assertIn("Harina", nombres)

    def test_create_insumo_requires_authentication(self):
        payload = {
            "nombre": "Azúcar",
            "unidad": self.unidad.id,
            "proveedor_principal": self.proveedor.id,
            "stock_minimo": "1.000",
            "stock_maximo": "10.000",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_insumo_success(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "nombre": "Azúcar",
            "unidad": self.unidad.id,
            "proveedor_principal": self.proveedor.id,
            "stock_minimo": "1.000",
            "stock_maximo": "10.000",
        }
        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nombre"], "Azúcar")
        self.assertTrue(Insumo.objects.filter(nombre="Azúcar").exists())

    def test_create_insumo_rejects_negative_stock_minimo(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "nombre": "Aceite",
            "unidad": self.unidad.id,
            "proveedor_principal": self.proveedor.id,
            "stock_minimo": "-1.000",
            "stock_maximo": "10.000",
        }
        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stock_minimo", response.data)

    def test_retrieve_insumo_detail(self):
        url = reverse(self.detail_url_name, args=[self.insumo.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.insumo.id)
        self.assertEqual(response.data["nombre"], "Harina")
        # chequeamos que venga el detalle de unidad
        self.assertIn("unidad_detalle", response.data)
        self.assertEqual(response.data["unidad_detalle"]["abreviatura"], "g")
