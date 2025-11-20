from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TimeStampedModel(models.Model):
    """
    Modelo base abstracto con timestamps estándar.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UnidadMedida(TimeStampedModel):
    """
    Ejemplos:
    - nombre: "Gramo", abreviatura: "g", es_base=True, factor_base=1
    - nombre: "Kilogramo", abreviatura: "kg", es_base=False, factor_base=1000
      (si la unidad base del sistema es "g")
    """
    nombre = models.CharField(max_length=50, unique=True)
    abreviatura = models.CharField(max_length=10, unique=True)
    es_base = models.BooleanField(
        default=False,
        help_text="Marca si esta unidad es una de las unidades base del sistema."
    )
    factor_base = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text=(
            "Factor para convertir a la unidad base del sistema. "
            "Ej: si la base es 'g', 1 kg = 1000 g → factor_base = 1000."
        ),
    )

    class Meta:
        verbose_name = "Unidad de medida"
        verbose_name_plural = "Unidades de medida"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.abreviatura})"


class Proveedor(TimeStampedModel):
    nombre = models.CharField(max_length=100, unique=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Insumo(TimeStampedModel):
    """
    Catálogo de insumos (ingredientes). El stock se maneja en StockInsumo
    por almacén, no aquí.
    """
    nombre = models.CharField(max_length=100, unique=True)
    unidad = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        related_name="insumos",
    )
    categoria = models.ForeignKey(
        "CategoriaInsumo",
        on_delete=models.SET_NULL,
        related_name="insumos",
        null=True,
        blank=True,
        help_text="Categoría general del insumo (ej: Carnes, Abarrotes, etc.).",
    )
    proveedor_principal = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        related_name="insumos",
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)

    stock_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Cantidad mínima recomendada en unidad del insumo.",
    )
    stock_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Cantidad máxima recomendada en unidad del insumo.",
    )

    costo_promedio = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text="Costo promedio ponderado por unidad.",
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

class CategoriaInsumo(TimeStampedModel):
    """
    Agrupa insumos en categorías (ej: Panes y masas, Carnes y pescados, etc.)
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría de insumo"
        verbose_name_plural = "Categorías de insumo"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Almacen(TimeStampedModel):
    """
    Representa un almacén físico (bodega, cámara, cocina, sucursal, etc.).
    """
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, blank=True)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="almacenes_responsables",
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        unique_together = ("nombre", "ubicacion")
        ordering = ["nombre"]

    def __str__(self):
        if self.ubicacion:
            return f"{self.nombre} - {self.ubicacion}"
        return self.nombre


class StockInsumo(TimeStampedModel):
    """
    Stock de un insumo en un almacén específico.
    A futuro, cuando agreguemos lotes, este modelo se podrá ajustar o derivar.
    """
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    cantidad_actual = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        help_text="Cantidad disponible en este almacén, en unidad del insumo.",
    )
    costo_promedio = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text=(
            "Costo promedio ponderado por unidad para este insumo "
            "en este almacén (puede diferir del costo promedio global del insumo)."
        ),
    )

    class Meta:
        verbose_name = "Stock de insumo"
        verbose_name_plural = "Stocks de insumos"
        unique_together = ("insumo", "almacen")

    def __str__(self):
        return f"{self.insumo} @ {self.almacen}: {self.cantidad_actual}"


class Plato(TimeStampedModel):
    """
    Producto del menú (plato) que se vende.
    El costo se calculará a partir de RecetaInsumo y los costos de Insumo.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Precio de venta al público.",
    )
    categoria = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ej: entrada, principal, postre...",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class RecetaInsumo(TimeStampedModel):
    """
    Línea de receta: cuánto de un insumo se necesita para preparar un plato.
    La unidad es la del insumo.
    """
    plato = models.ForeignKey(
        Plato,
        on_delete=models.CASCADE,
        related_name="receta_insumos",
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="recetas",
    )
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Cantidad necesaria por unidad de plato, en unidad del insumo.",
    )

    class Meta:
        verbose_name = "Ingrediente de receta"
        verbose_name_plural = "Ingredientes de receta"
        unique_together = ("plato", "insumo")

    def __str__(self):
        return f"{self.cantidad} {self.insumo.unidad.abreviatura} de {self.insumo} para {self.plato}"
