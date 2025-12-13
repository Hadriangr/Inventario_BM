from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal, InvalidOperation
from django.utils import timezone

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
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores" 
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
    unidad_compra = models.ForeignKey(
    UnidadMedida,
    on_delete=models.PROTECT,
    related_name="insumos_compra",
    null=True,
    blank=True,
    help_text="Unidad en que se compra este insumo (ej: saco, litro, bandeja).",
    )

    factor_conversion = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text=(
            "Cantidad de unidad de consumo incluida en 1 unidad de compra. "
            "Ej: saco 25kg → consumo en gramos → 25,000."
        ),
    )

    costo_promedio = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text="Costo promedio ponderado por unidad.",
    )

    def clean(self):
        if self.unidad_compra and not self.factor_conversion:
            raise ValidationError("Debe especificar factor_conversion cuando existe unidad_compra.")

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

    usuarios = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="almacenes_asignados",
        blank=True,
        help_text="Usuarios que pueden operar este almacén.",
    )

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

    @property
    def valor_total(self):
        """
        Valor total del stock de este insumo en este almacén.
        cantidad_actual * costo_promedio
        """
        cantidad = self.cantidad_actual or Decimal("0")
        costo = self.costo_promedio or Decimal("0")
        return cantidad * costo
    @property
    def bajo_minimo(self) -> bool:
        """
        True si este stock está por debajo del stock mínimo definido en el Insumo.
        """
        stock_minimo = self.insumo.stock_minimo or Decimal("0")
        if stock_minimo <= 0:
            return False
        return (self.cantidad_actual or Decimal("0")) < stock_minimo

    @property
    def sobre_maximo(self) -> bool:
        """
        True si este stock está por encima del stock máximo definido en el Insumo.
        """
        stock_maximo = self.insumo.stock_maximo
        if stock_maximo is None or stock_maximo <= 0:
            return False
        return (self.cantidad_actual or Decimal("0")) > stock_maximo

    @property
    def nivel_alerta(self) -> str:
        """
        Devuelve:
        - 'bajo_minimo'
        - 'sobre_maximo'
        - 'ok'
        En el futuro se podría extender a 'sin_stock' o 'sin_configuracion'.
        """
        if self.bajo_minimo:
            return "bajo_minimo"
        if self.sobre_maximo:
            return "sobre_maximo"
        return "ok"


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
    categoria = models.ForeignKey(
        "CategoriaPlato",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="platos",
        help_text="Tipo de plato (ej: entrada, principal, postre, menú ejecutivo).",
    )
    activo = models.BooleanField(default=True)

    costo_receta = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text="Costo total de la receta para una porción/unidad del plato.",
    )
    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
    
    @property
    def food_cost_porcentaje(self) -> Decimal | None:
        """
        Retorna el % de food cost:
            (costo_receta / precio_venta) * 100
        o None si no hay precio_venta.
        """
        if not self.precio_venta or self.precio_venta <= 0:
            return None
        try:
            valor = (self.costo_receta / self.precio_venta) * Decimal("100")
            return valor.quantize(Decimal("0.01"))
        except (InvalidOperation, ZeroDivisionError):
            return None

    @property
    def margen_bruto(self) -> Decimal | None:
        """
        Retorna el margen bruto en moneda:
            precio_venta - costo_receta
        o None si no hay precio_venta.
        """
        if self.precio_venta is None:
            return None
        return (self.precio_venta - self.costo_receta).quantize(Decimal("0.0001"))

    @property
    def margen_bruto_porcentaje(self) -> Decimal | None:
        """
        Retorna el margen bruto en %:
            (margen_bruto / precio_venta) * 100
        o None si no hay precio_venta.
        """
        if not self.precio_venta or self.precio_venta <= 0:
            return None
        margen = self.margen_bruto
        if margen is None:
            return None
        try:
            valor = (margen / self.precio_venta) * Decimal("100")
            return valor.quantize(Decimal("0.01"))
        except (InvalidOperation, ZeroDivisionError):
            return None


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
        decimal_places=4,
        help_text="Cantidad necesaria por unidad de plato, en unidad del insumo.",
    )

    class Meta:
        verbose_name = "Ingrediente de receta"
        verbose_name_plural = "Ingredientes de receta"
        ordering = ["plato", "insumo"]
        unique_together = ("plato", "insumo")

    def __str__(self):
        return f"{self.cantidad} {self.insumo.unidad.abreviatura} de {self.insumo} para {self.plato}"

class MovimientoInventario(TimeStampedModel):
    """
    Representa un movimiento de inventario para un insumo en un almacén.
    Ejemplos:
    - Entrada por compra
    - Ajuste positivo/negativo
    - (Más adelante) Salida por venta, producción, merma, etc.
    """

    TIPO_ENTRADA_COMPRA = "ENTRADA_COMPRA"
    TIPO_ENTRADA_AJUSTE = "ENTRADA_AJUSTE"
    TIPO_SALIDA_AJUSTE = "SALIDA_AJUSTE"
    TIPO_ENTRADA_TRASPASO = "ENTRADA_TRASPASO"
    TIPO_SALIDA_TRASPASO = "SALIDA_TRASPASO"

    TIPO_SALIDA_CONSUMO_RECETA = "SALIDA_CONSUMO_RECETA"
    TIPO_SALIDA_MERMA = "SALIDA_MERMA"

    TIPO_CHOICES = [
        (TIPO_ENTRADA_COMPRA, "Entrada por compra"),
        (TIPO_ENTRADA_AJUSTE, "Entrada por ajuste"),
        (TIPO_SALIDA_AJUSTE, "Salida por ajuste"),
        (TIPO_ENTRADA_TRASPASO, "Entrada por traspaso"),
        (TIPO_SALIDA_TRASPASO, "Salida por traspaso"),
        (TIPO_SALIDA_CONSUMO_RECETA, "Salida por consumo de receta"),
        (TIPO_SALIDA_MERMA, "Salida por merma"),



    ]

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
    )

    cantidad = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        help_text="Cantidad del movimiento. Positiva para entrada, negativa para salida.",
    )

    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text=(
            "Costo unitario asociado al movimiento. "
            "Obligatorio para entradas de compra. Puede ser nulo en ciertos ajustes/salidas."
        ),
    )

    costo_total = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        help_text="Costo total del movimiento (cantidad * costo_unitario) cuando aplica.",
    )

    fecha_movimiento = models.DateTimeField(
        help_text="Fecha efectiva del movimiento (puede diferir de la creación del registro).",
    )

    motivo = models.TextField(
        blank=True,
        help_text="Descripción o motivo del movimiento (ej: ajuste inventario, corrección, etc.).",
    )
    referencia = models.CharField(
        max_length=100,
        blank=True,
        help_text="Referencia externa, número de documento, factura, etc.",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
        help_text="Usuario que registró el movimiento.",
    )

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        ordering = ["-fecha_movimiento", "-created_at"]

    def __str__(self):
        return f"{self.tipo} - {self.insumo} @ {self.almacen} ({self.cantidad})"

    def save(self, *args, **kwargs):
        """
        De momento solo nos aseguramos de calcular costo_total si hay costo_unitario.
        La lógica de actualizar stock y costo promedio la manejaremos en un servicio separado,
        para tener tests claros y evitar efectos colaterales en save().
        """
        if self.costo_unitario is not None and self.cantidad is not None:
            self.costo_total = (self.cantidad * self.costo_unitario).quantize(Decimal("0.0001"))
        super().save(*args, **kwargs)

class LoteInsumo(TimeStampedModel):
    """
    Lote de un insumo en un almacén, con fecha de vencimiento.
    La cantidad y el costo_unitario están en la misma unidad de consumo del insumo.
    """

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="lotes",
    )
    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name="lotes",
    )
    numero_lote = models.CharField(
        max_length=100,
        blank=True,
        help_text="Identificador de lote entregado por proveedor o interno.",
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento del lote (si aplica).",
    )
    cantidad_actual = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        help_text="Cantidad disponible de este lote en unidad de consumo.",
    )
    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text="Costo unitario en unidad de consumo para este lote.",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Permite desactivar lotes antiguos o cerrados.",
    )

    class Meta:
        verbose_name = "Lote de insumo"
        verbose_name_plural = "Lotes de insumos"
        ordering = ["fecha_vencimiento", "numero_lote"]
        unique_together = ("insumo", "almacen", "numero_lote", "fecha_vencimiento")

    def __str__(self):
        base = f"{self.insumo} @ {self.almacen}"
        if self.numero_lote:
            base += f" [Lote {self.numero_lote}]"
        if self.fecha_vencimiento:
            base += f" vence {self.fecha_vencimiento}"
        return base

    @property
    def valor_total(self) -> Decimal:
        cantidad = self.cantidad_actual or Decimal("0")
        costo = self.costo_unitario or Decimal("0")
        return cantidad * costo

    @property
    def esta_vencido(self) -> bool:
        if not self.fecha_vencimiento:
            return False
        return self.fecha_vencimiento < date.today()

    def por_vencer_en(self, dias: int = 7) -> bool:
        """
        True si el lote vence dentro de los próximos `dias` días (incluyendo hoy).
        """
        if not self.fecha_vencimiento:
            return False
        hoy = date.today()
        limite = hoy.fromordinal(hoy.toordinal() + dias)
        return hoy <= self.fecha_vencimiento <= limite

class CategoriaPlato(TimeStampedModel):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoría de plato"
        verbose_name_plural = "Categorías de plato"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class EntradaCompra(TimeStampedModel):
    """
    Documento de compra simple (una línea = un insumo).
    Al guardarse y procesarse, genera la entrada de inventario
    usando registrar_entrada_compra.
    """

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="entradas_compra",
    )
    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name="entradas_compra",
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="entradas_compra",
    )

    fecha_documento = models.DateField(
        help_text="Fecha de la factura / guía de compra.",
    )
    numero_documento = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de factura/boleta/guía.",
    )

    numero_lote = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Número de lote del proveedor"
    )

    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento declarada para este lote"
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Cantidad comprada en unidad de consumo del insumo.",
    )
    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Costo unitario en moneda local (por unidad de consumo).",
    )

    referencia = models.CharField(
        max_length=100,
        blank=True,
        help_text="Referencia interna opcional (OC, nota, etc.).",
    )
    observaciones = models.TextField(blank=True)

    # Control de procesamiento
    procesada = models.BooleanField(
        default=False,
        editable=False,
        help_text="Indica si ya se generó la entrada de inventario.",
    )
    movimiento = models.ForeignKey(
        "MovimientoInventario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entradas_compra",
        editable=False,
    )

    class Meta:
        verbose_name = "Entrada de compra"
        verbose_name_plural = "Entradas de compra"
        ordering = ["-fecha_documento", "-created_at"]

    def __str__(self):
        return f"Compra {self.id} - {self.proveedor} - {self.insumo}"

    def procesar(self, usuario=None, fecha_movimiento=None):
        """
        Genera la entrada de inventario (si aún no está procesada)
        usando el servicio registrar_entrada_compra.
        """
        from inventory.services.inventory import registrar_entrada_compra

        if self.procesada:
            return self.movimiento

        if fecha_movimiento is None:
            fecha_movimiento = timezone.now()

        motivo = self.observaciones or f"Compra de {self.insumo.nombre}"
        referencia = self.referencia or self.numero_documento or f"COMP-{self.pk}"

        mov = registrar_entrada_compra(
            insumo=self.insumo,
            almacen=self.almacen,
            cantidad=self.cantidad,
            costo_unitario=self.costo_unitario,
            usuario=usuario,
            motivo=motivo,
            referencia=referencia,
            fecha_movimiento=fecha_movimiento,
            numero_lote=self.numero_lote,
            fecha_vencimiento=self.fecha_vencimiento,
        )

        self.movimiento = mov
        self.procesada = True
        self.save(update_fields=["movimiento", "procesada", "updated_at"])

        return mov


class MenuPlan(TimeStampedModel):
    """
    Representa un plan de menú para un rango de fechas (ej: 2 semanas).
    Puede ser por sede/almacén.
    """

    ESTADO_CHOICES = [
        ("borrador", "Borrador"),
        ("confirmado", "Confirmado"),
    ]

    nombre = models.CharField(max_length=200)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name="planes_menu",
        null=True,
        blank=True,
        help_text="Almacén o sede para el cual se planifica el menú.",
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="borrador",
    )

    notas = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_inicio", "-id"]

    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicio} → {self.fecha_fin})"


class MenuPlanItem(TimeStampedModel):
    """
    Línea del plan: un plato programado en una fecha + servicio del día.
    """
    plan = models.ForeignKey(
        MenuPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )

    fecha = models.DateField()

    categoria_plato = models.ForeignKey(
        CategoriaPlato,
        on_delete=models.PROTECT,
        related_name="items_menu",
        help_text="Categoría del plato en este plan (ej: Principal, Ensalada, Postre).",
    )

    plato = models.ForeignKey(
        Plato,
        on_delete=models.PROTECT,
        related_name="planes_menu",
    )

    porciones_planificadas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Número de platos estimados para este día/servicio.",
    )

    notas = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["fecha", "plato__nombre"]

    def __str__(self):
        return (
            f"{self.fecha} - {self.categoria_plato} - "
            f"{self.plato} ({self.porciones_planificadas} porciones)"
        )
    
class EstadoConteo(models.TextChoices):
    BORRADOR = "borrador", "Borrador"
    CERRADO = "cerrado", "Cerrado"
    AJUSTADO = "ajustado", "Ajustes aplicados"  # cuando ya se generaron ajustes de stock
    PENDIENTE = "pendiente_aprobacion", "Pendiente de aprobación"


class ConteoInventario(models.Model):
    """
    Cabecera de un conteo físico de inventario.
    Ej: Conteo del almacén principal el 10-12-2025, tolerancia 2%.
    """

    fecha = models.DateField()
    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name="conteos",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conteos_inventario",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoConteo.choices,
        default=EstadoConteo.BORRADOR,
    )

    # Tolerancia en porcentaje (ej: 2.00 = 2%)
    tolerancia_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tolerancia en % para considerar las diferencias aceptables.",
    )


    # (opcional) tolerancia absoluta en unidades. Si la usas, la aplicaremos en el servicio.
    tolerancia_unidades = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Tolerancia absoluta en unidades (opcional).",
    )

    comentarios = models.TextField(blank=True)

    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="conteos_aprobados",
    )

    aprobado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-creado_en"]
        verbose_name = "Conteo de inventario"
        verbose_name_plural = "Conteos de inventario"

    def __str__(self):
        return f"Conteo #{self.id} - {self.almacen} - {self.fecha} ({self.estado})"

    @property
    def es_editable(self) -> bool:
        """Solo permite editar items cuando está en borrador."""
        return self.estado == EstadoConteo.BORRADOR
    
    @property
    def tiene_diferencias_criticas(self) -> bool:
        """
        Por ahora consideramos 'crítico' cualquier item fuera de tolerancia.
        Si luego quieres un umbral extra, lo agregamos.
        """
        return self.items.filter(dentro_tolerancia=False).exists()
    
    def puede_aplicar_ajustes(self) -> bool:
        """
        Solo permitimos aplicar ajustes cuando el conteo está cerrado
        y aún no se ha ajustado.
        """
        return self.estado == EstadoConteo.CERRADO



class ConteoInventarioItem(models.Model):
    """
    Detalle del conteo, por insumo.
    """

    conteo = models.ForeignKey(
        ConteoInventario,
        on_delete=models.CASCADE,
        related_name="items",
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="conteos_items",
    )

    # Cantidad contada físicamente por el usuario
    cantidad_contada = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    # Snapshot del sistema al momento de cerrar/conciliar el conteo
    cantidad_sistema = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Cantidad de sistema al momento de conciliar (snapshot).",
    )

    # Diferencia = cantidad_contada - cantidad_sistema
    diferencia = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    dentro_tolerancia = models.BooleanField(
        default=False,
        help_text="Indica si la diferencia está dentro de la tolerancia definida.",
    )

    comentarios = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        verbose_name = "Ítem de conteo de inventario"
        verbose_name_plural = "Ítems de conteo de inventario"
        unique_together = ("conteo", "insumo")

    def __str__(self):
        return f"{self.insumo} - Conteo #{self.conteo_id}"