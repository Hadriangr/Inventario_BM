from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView,DeleteView, DetailView
from decimal import Decimal
from django.db.models import Q, Sum
from inventory.models import Proveedor, Insumo, StockInsumo,EntradaCompra,Plato, MenuPlan
from inventory.services.recetas import calcular_costo_receta
from web.forms import ProveedorForm, InsumoForm, EntradaCompraForm,PlatoForm, RecetaInsumoFormSet, MenuPlanForm,MenuPlanItemFormSet
from django.shortcuts import redirect, get_object_or_404
from inventory.services.planificacion import calcular_requerimientos_plan



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


class InsumoListView(ListView):
    model = Insumo
    template_name = "web/insumos_list.html"
    context_object_name = "insumos"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("unidad", "categoria", "proveedor_principal")
        )

        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(categoria__nombre__icontains=q)
                | Q(proveedor_principal__nombre__icontains=q)
            )

        qs = qs.order_by("nombre")

        insumo_ids = list(qs.values_list("id", flat=True))
        if not insumo_ids:
            return qs

  
        stocks = (
            StockInsumo.objects.filter(insumo_id__in=insumo_ids)
            .values("insumo_id")
            .annotate(total=Sum("cantidad_actual"))
        )
        mapa_stock = {
            s["insumo_id"]: (s["total"] or Decimal("0")) for s in stocks
        }

        UMBRAL_PORCENTAJE = Decimal("0.10")  # 10%

        for insumo in qs:
            cantidad = mapa_stock.get(insumo.id, Decimal("0"))
            insumo.total_stock = cantidad

            minimo = insumo.stock_minimo or Decimal("0")
            maximo = insumo.stock_maximo  # puede ser None

            nivel = "verde"

            # ROJO: fuera de rango
            if (minimo and cantidad < minimo) or (
                maximo is not None and cantidad > maximo
            ):
                nivel = "rojo"
            else:
                # AMARILLO: cerca del mínimo o del máximo (si existe)
                cerca_min = False
                cerca_max = False

                if minimo and cantidad >= minimo:
                    # distancia relativa al mínimo
                    diff_min = (cantidad - minimo) / minimo if minimo > 0 else 0
                    if diff_min <= UMBRAL_PORCENTAJE:
                        cerca_min = True

                if maximo is not None and cantidad <= maximo:
                    diff_max = (maximo - cantidad) / maximo if maximo > 0 else 0
                    if diff_max <= UMBRAL_PORCENTAJE:
                        cerca_max = True

                if cerca_min or cerca_max:
                    nivel = "amarillo"

            insumo.nivel_alerta_global = nivel

        return qs


class InsumoCreateView(CreateView):
    model = Insumo
    form_class = InsumoForm
    template_name = "web/insumos_form.html"
    success_url = reverse_lazy("web:insumos_list")


class InsumoUpdateView(UpdateView):
    model = Insumo
    form_class = InsumoForm
    template_name = "web/insumos_form.html"
    success_url = reverse_lazy("web:insumos_list")


class EntradaCompraListView(ListView):
    model = EntradaCompra
    template_name = "web/compras_list.html"
    context_object_name = "compras"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("proveedor", "almacen", "insumo")
        )
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(insumo__nombre__icontains=q)
                | Q(proveedor__nombre__icontains=q)
                | Q(numero_documento__icontains=q)
                | Q(referencia__icontains=q)
            )
        return qs.order_by("-fecha_documento", "-created_at")


class EntradaCompraCreateView(CreateView):
    model = EntradaCompra
    form_class = EntradaCompraForm
    template_name = "web/compras_form.html"
    success_url = reverse_lazy("web:compras_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.procesar(usuario=self.request.user if self.request.user.is_authenticated else None)
        return response


class PlatoListView(ListView):
    model = Plato
    template_name = "web/platos_list.html"
    context_object_name = "platos"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("categoria")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs.order_by("nombre")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # agregamos cálculo de porcentaje + margen
        for plato in ctx["platos"]:
            try:
                ctx_obj = plato.food_cost_porcentaje  # propiedad del modelo
            except:
                pass
        return ctx


class PlatoCreateView(CreateView):
    model = Plato
    form_class = PlatoForm
    template_name = "web/platos_form.html"
    success_url = reverse_lazy("web:platos_list")


class PlatoUpdateView(UpdateView):
    model = Plato
    form_class = PlatoForm
    template_name = "web/platos_form.html"
    success_url = reverse_lazy("web:platos_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        # recalcular costo de receta después de editar
        calcular_costo_receta(plato=self.object, guardar=True)
        return response


def plato_recalcular_costo(request, pk):
    """
    Recalcula el costo de receta de un plato y vuelve al listado.
    Se ejecuta con un GET simple desde el link en la tabla.
    """
    plato = get_object_or_404(Plato, pk=pk)
    calcular_costo_receta(plato=plato, guardar=True)
    return redirect("web:platos_list")


class ProveedorDeleteView(DeleteView):
    model = Proveedor
    template_name = "web/proveedores_confirm_delete.html"
    success_url = reverse_lazy("web:proveedores_list")


class InsumoDeleteView(DeleteView):
    model = Insumo
    template_name = "web/insumos_confirm_delete.html"
    success_url = reverse_lazy("web:insumos_list")


class EntradaCompraDeleteView(DeleteView):
    model = EntradaCompra
    template_name = "web/compras_confirm_delete.html"
    success_url = reverse_lazy("web:compras_list")


class PlatoDeleteView(DeleteView):
    model = Plato
    template_name = "web/platos_confirm_delete.html"
    success_url = reverse_lazy("web:platos_list")


def plato_receta_edit(request, pk):
    """
    Permite gestionar la receta (lista de insumos + cantidades) de un plato.
    Usa un inline formset sobre RecetaInsumo.
    """
    plato = get_object_or_404(Plato, pk=pk)

    if request.method == "POST":
        formset = RecetaInsumoFormSet(request.POST, instance=plato)
        if formset.is_valid():
            formset.save()
            # Recalcular costo de receta después de guardar
            calcular_costo_receta(plato=plato, guardar=True)
            return redirect("web:platos_list")
    else:
        formset = RecetaInsumoFormSet(instance=plato)

    return render(
        request,
        "web/platos_receta_form.html",
        {
            "plato": plato,
            "formset": formset,
        },
    )

class MenuPlanListView(ListView):
    model = MenuPlan
    template_name = "web/planes_list.html"
    context_object_name = "planes"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("almacen")
        return qs.order_by("-fecha_inicio", "-id")


class MenuPlanRequerimientosView(DetailView):
    model = MenuPlan
    template_name = "web/planes_requerimientos.html"
    context_object_name = "plan"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        plan = self.object
        # Usamos el almacen del plan; podríamos permitir override con GET más adelante.
        requerimientos = calcular_requerimientos_plan(
            plan=plan,
            incluir_stock=True,
            almacen=plan.almacen,
        )

        ctx["requerimientos"] = requerimientos
        ctx["almacen"] = plan.almacen
        return ctx
    
def menu_plan_create(request):
    """
    Crear un nuevo plan de menú + sus items (día/plato/porciones).
    """
    if request.method == "POST":
        form = MenuPlanForm(request.POST)
        formset = MenuPlanItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            plan = form.save()
            formset.instance = plan
            formset.save()
            return redirect("web:planes_list")
    else:
        form = MenuPlanForm()
        formset = MenuPlanItemFormSet()

    return render(
        request,
        "web/planes_form.html",
        {
            "form": form,
            "formset": formset,
            "plan": None,
        },
    )


def menu_plan_update(request, pk):
    """
    Editar un plan existente + sus items.
    """
    plan = get_object_or_404(MenuPlan, pk=pk)

    if request.method == "POST":
        form = MenuPlanForm(request.POST, instance=plan)
        formset = MenuPlanItemFormSet(request.POST, instance=plan)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("web:planes_list")
    else:
        form = MenuPlanForm(instance=plan)
        formset = MenuPlanItemFormSet(instance=plan)

    return render(
        request,
        "web/planes_form.html",
        {
            "form": form,
            "formset": formset,
            "plan": plan,
        },
    )
