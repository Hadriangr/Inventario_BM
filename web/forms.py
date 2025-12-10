
from django import forms
from inventory.models import Proveedor, Insumo,EntradaCompra,Plato, RecetaInsumo,MenuPlan,MenuPlanItem,ConteoInventario,ConteoInventarioItem, Almacen
from django.forms import inlineformset_factory, BaseInlineFormSet
from inventory.utils_roles import usuario_ve_todos_los_almacenes



class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "telefono", "email", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = [
            "nombre",
            "unidad",
            "categoria",
            "proveedor_principal",
            "activo",
            "stock_minimo",
            "stock_maximo",
            "unidad_compra",
            "factor_conversion",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "unidad": forms.Select(attrs={"class": "form-select"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "proveedor_principal": forms.Select(attrs={"class": "form-select"}),
            "stock_minimo": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "stock_maximo": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "unidad_compra": forms.Select(attrs={"class": "form-select"}),
            "factor_conversion": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
        }

class EntradaCompraForm(forms.ModelForm):
    class Meta:
        model = EntradaCompra
        fields = [
            "proveedor",
            "almacen",
            "insumo",
            "fecha_documento",
            "numero_documento",
            "numero_lote",
            "fecha_vencimiento",
            "cantidad",
            "costo_unitario",
            "referencia",
            "observaciones",
        ]
        widgets = {
            "proveedor": forms.Select(attrs={"class": "form-select"}),
            "almacen": forms.Select(attrs={"class": "form-select"}),
            "insumo": forms.Select(attrs={"class": "form-select"}),
            "fecha_documento": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "numero_lote": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "numero_documento": forms.TextInput(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "costo_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class PlatoForm(forms.ModelForm):
    class Meta:
        model = Plato
        fields = [
            "nombre",
            "descripcion",
            "precio_venta",
            "categoria",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "precio_venta": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class RecetaInsumoForm(forms.ModelForm):
    class Meta:
        model = RecetaInsumo
        fields = ["insumo", "cantidad"]
        widgets = {
            "insumo": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
        }


RecetaInsumoFormSet = inlineformset_factory(
    Plato,
    RecetaInsumo,
    form=RecetaInsumoForm,
    extra=3,          
    can_delete=True, 
)

class MenuPlanForm(forms.ModelForm):
    class Meta:
        model = MenuPlan
        fields = ["nombre", "fecha_inicio", "fecha_fin", "almacen", "estado", "notas"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "almacen": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class MenuPlanItemForm(forms.ModelForm):
    class Meta:
        model = MenuPlanItem
        fields = ["fecha", "categoria_plato", "plato", "porciones_planificadas", "notas"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "categoria_plato": forms.Select(attrs={"class": "form-select"}),
            "plato": forms.Select(attrs={"class": "form-select"}),
            "porciones_planificadas": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notas": forms.TextInput(attrs={"class": "form-control"}),
        }


MenuPlanItemFormSet = inlineformset_factory(
    MenuPlan,
    MenuPlanItem,
    form=MenuPlanItemForm,
    extra=3,          # filas vacías para agregar nuevos ítems
    can_delete=True,  # permite marcar líneas para eliminar
)


class ConteoInventarioForm(forms.ModelForm):
    """
    Formulario para el encabezado del conteo.
    Filtramos almacenes según los permisos del usuario.
    """

    class Meta:
        model = ConteoInventario
        fields = [
            "fecha",
            "almacen",
            "tolerancia_porcentaje",
            "tolerancia_unidades",
            "comentarios",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Fecha por defecto: hoy
        if not self.instance.pk and "fecha" not in self.initial:
            from datetime import date
            self.initial["fecha"] = date.today()

        # Limitar almacenes según permisos del usuario
        if user is not None:
            if usuario_ve_todos_los_almacenes(user):
                qs = Almacen.objects.filter(activo=True)
            else:
                qs = Almacen.objects.filter(activo=True, usuarios=user)
            self.fields["almacen"].queryset = qs


class ConteoInventarioItemForm(forms.ModelForm):
    """
    Ítem del conteo: insumo + cantidad contada.
    No exponemos cantidad_sistema ni diferencia: eso lo calcula el servicio.
    """

    class Meta:
        model = ConteoInventarioItem
        fields = ["insumo", "cantidad_contada", "comentarios"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo insumos activos
        self.fields["insumo"].queryset = Insumo.objects.filter(activo=True).order_by("nombre")


ConteoInventarioItemFormSet = inlineformset_factory(
    ConteoInventario,
    ConteoInventarioItem,
    form=ConteoInventarioItemForm,
    extra=5,           # puedes ajustar la cantidad de filas vacías
    can_delete=True,   # para permitir eliminar líneas
)