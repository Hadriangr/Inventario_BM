# web/views/proveedores.py
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from inventory.models import Proveedor
from web.forms import ProveedorForm


class ProveedorListView(ListView):
    model = Proveedor
    template_name = "web/proveedores_list.html"
    context_object_name = "proveedores"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs.order_by("nombre")


class ProveedorCreateView(CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = "web/proveedores_form.html"
    success_url = reverse_lazy("web:proveedores_list")


class ProveedorUpdateView(UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = "web/proveedores_form.html"
    success_url = reverse_lazy("web:proveedores_list")
