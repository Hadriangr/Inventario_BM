from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from inventory.models import UnidadMedida, Insumo, Plato, RecetaInsumo


class RecetasAPITests(APITestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(
            nombre="Gramo",
            abreviatura="g",
            es_base=True,
            factor_base=Decimal("1"),
        )
        self.insumo = Insumo.objects.create(
            nombre="Harina",
            unidad=self.unidad,
            stock_minimo=Decimal("0"),
        )
        self.plato = Plato.objects.create(
            nombre="Pan casero",
            precio_venta=Decimal("1000.00"),
            categoria="Panadería",
        )

        self.receta_url = reverse("receta-insumo-list")
        self.plato_receta_url = reverse("plato-receta", args=[self.plato.id])

    def test_no_permite_insumo_duplicado_en_receta(self):
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo,
            cantidad=Decimal("100.00"),
        )

        payload = {
            "plato": self.plato.id,
            "insumo": self.insumo.id,
            "cantidad": "50.00",
        }
        response = self.client.post(self.receta_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("insumo", response.data)

    def test_obtener_receta_completa_de_plato(self):
        RecetaInsumo.objects.create(
            plato=self.plato,
            insumo=self.insumo,
            cantidad=Decimal("100.00"),
        )

        response = self.client.get(self.plato_receta_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.plato.id)
        self.assertEqual(len(response.data["receta"]), 1)
        self.assertEqual(response.data["receta"][0]["insumo"], self.insumo.id)
