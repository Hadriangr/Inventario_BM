
from django import forms
from inventory.models import Proveedor, Insumo,EntradaCompra,Plato, RecetaInsumo
from django.forms import inlineformset_factory


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
