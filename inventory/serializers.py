from rest_framework import serializers

from .models import (
    UnidadMedida,
    Proveedor,
    CategoriaInsumo,
    Insumo,
    Almacen,
    StockInsumo,
    Plato,
    RecetaInsumo,
)


class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = [
            "id",
            "nombre",
            "abreviatura",
            "es_base",
            "factor_base",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            "id",
            "nombre",
            "email",
            "telefono",
            "direccion",
            "activo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class CategoriaInsumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaInsumo
        fields = [
            "id",
            "nombre",
            "descripcion",
            "activo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InsumoSerializer(serializers.ModelSerializer):
    unidad_detalle = UnidadMedidaSerializer(source="unidad", read_only=True)
    proveedor_principal_detalle = ProveedorSerializer(
        source="proveedor_principal",
        read_only=True,
    )
    categoria_detalle = CategoriaInsumoSerializer(   
        source="categoria",
        read_only=True,
    )

    class Meta:
        model = Insumo
        fields = [
            "id",
            "nombre",

            #UoM de consumo
            "unidad",
            "unidad_detalle",

            #UoM de compra
            "unidad_compra",
            "factor_conversion",
            "costo_unitario_consumo",

            "proveedor_principal",
            "proveedor_principal_detalle",
            "categoria",          
            "categoria_detalle",  
            "activo",
            "stock_minimo",
            "stock_maximo",
            "costo_promedio",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "costo_promedio", "created_at", "updated_at","costo_unitario_consumo"]

    def validate_stock_minimo(self, value):
        if value < 0:
            raise serializers.ValidationError("El stock mínimo no puede ser negativo.")
        return value

    def validate_stock_maximo(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("El stock máximo no puede ser negativo.")
        return value
    
    unidad_compra = serializers.PrimaryKeyRelatedField(
        queryset=UnidadMedida.objects.all(),
        required=False,
        allow_null=True,
    )

    factor_conversion = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        required=False,
        allow_null=True,
    )
    costo_unitario_consumo = serializers.SerializerMethodField()

    def get_costo_unitario_consumo(self, obj):
        if obj.factor_conversion and obj.factor_conversion > 0:
            return obj.costo_promedio
        return None
    def validate_factor_conversion(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("El factor de conversión debe ser mayor que 0.")
        return value

    def validate(self, attrs):
        unidad_compra = attrs.get("unidad_compra", getattr(self.instance, "unidad_compra", None))
        factor_conversion = attrs.get("factor_conversion", getattr(self.instance, "factor_conversion", None))

        if unidad_compra and not factor_conversion:
            raise serializers.ValidationError({
                "factor_conversion": "Debes especificar un factor de conversión cuando hay unidad de compra."
            })

        return attrs




class AlmacenSerializer(serializers.ModelSerializer):
    """
    De momento solo exponemos el ID del responsable.
    Más adelante podemos anidar el usuario si hace falta.
    """

    class Meta:
        model = Almacen
        fields = [
            "id",
            "nombre",
            "ubicacion",
            "responsable",
            "activo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockInsumoSerializer(serializers.ModelSerializer):
    """
    Maneja el stock de un insumo en un almacén.
    - `insumo` y `almacen` como IDs.
    - `insumo_detalle` y `almacen_detalle` solo lectura para inspección.
    """

    insumo_detalle = InsumoSerializer(source="insumo", read_only=True)
    almacen_detalle = AlmacenSerializer(source="almacen", read_only=True)
    valor_total = serializers.SerializerMethodField()
    bajo_minimo = serializers.SerializerMethodField()    
    sobre_maximo = serializers.SerializerMethodField()   
    nivel_alerta = serializers.SerializerMethodField()

    class Meta:
        model = StockInsumo
        fields = [
            "id",
            "insumo",
            "insumo_detalle",
            "almacen",
            "almacen_detalle",
            "cantidad_actual",
            "costo_promedio",
            "valor_total",
            "bajo_minimo",
            "sobre_maximo",
            "nivel_alerta",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "valor_total",
                            "bajo_minimo", "sobre_maximo", "nivel_alerta"]

    def get_valor_total(self, obj):
        return obj.valor_total

    def get_bajo_minimo(self, obj):
        return obj.bajo_minimo

    def get_sobre_maximo(self, obj):
        return obj.sobre_maximo

    def get_nivel_alerta(self, obj):
        return obj.nivel_alerta

    def validate_cantidad_actual(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "La cantidad actual no puede ser negativa."
            )
        return value


class PlatoSerializer(serializers.ModelSerializer):
    """
    Por ahora el plato no incluye la receta anidada.
    Más adelante podemos crear un serializer 'detallado' que incluya RecetaInsumo.
    """

    class Meta:
        model = Plato
        fields = [
            "id",
            "nombre",
            "descripcion",
            "precio_venta",
            "categoria",
            "activo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RecetaInsumoSerializer(serializers.ModelSerializer):
    """
    - `plato` e `insumo` como IDs para escritura.
    - `plato_detalle` e `insumo_detalle` para lectura.
    """

    plato_detalle = PlatoSerializer(source="plato", read_only=True)
    insumo_detalle = InsumoSerializer(source="insumo", read_only=True)

    class Meta:
        model = RecetaInsumo
        fields = [
            "id",
            "plato",
            "plato_detalle",
            "insumo",
            "insumo_detalle",
            "cantidad",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a cero."
            )
        return value
