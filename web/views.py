from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView,DeleteView, DetailView
from decimal import Decimal
from django.db.models import Q, Sum
from inventory.models import Proveedor, Insumo, StockInsumo,EntradaCompra,Plato, MenuPlan
from inventory.services.recetas import calcular_costo_receta
from web.forms import ProveedorForm, InsumoForm, EntradaCompraForm,PlatoForm, RecetaInsumoFormSet, MenuPlanForm,MenuPlanItemFormSet, ConteoInventario,ConteoInventarioItemFormSet, ConteoInventarioForm
from datetime import date
from django.shortcuts import redirect, get_object_or_404
from inventory.services.planificacion import calcular_requerimientos_plan
from inventory.models import ConteoInventario, EstadoConteo
from inventory.services.conteo import conciliar_conteo
from inventory.utils_roles import (
    usuario_ve_todos_los_almacenes,
    usuario_puede_cerrar_conteos,
    usuario_es_supervisor,
)
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.utils import timezone



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

@login_required
def conteos_list(request):
    """
    Lista de conteos de inventario visibles para el usuario.
    Si el usuario no ve todos los almacenes, filtramos por sus almacenes asignados.
    """
    qs = ConteoInventario.objects.all()

    if not usuario_ve_todos_los_almacenes(request.user):
        qs = qs.filter(almacen__in=request.user.almacenes_asignados.all())

    qs = qs.select_related("almacen", "responsable").order_by("-fecha", "-creado_en")

    context = {
        "conteos": qs,
    }
    return render(request, "web/conteos_list.html", context)


@login_required
def conteos_create(request):
    """
    Crear un nuevo conteo de inventario (estado BORRADOR).
    Encabezado + líneas (formset).
    Después de guardar, ejecutamos conciliar_conteo para rellenar
    cantidad_sistema / diferencia / dentro_tolerancia.
    """
    if request.method == "POST":
        form = ConteoInventarioForm(request.POST, user=request.user)
        if form.is_valid():
            conteo = form.save(commit=False)
            conteo.responsable = request.user
            conteo.estado = EstadoConteo.BORRADOR
            conteo.save()

            formset = ConteoInventarioItemFormSet(request.POST, instance=conteo)

            if formset.is_valid():
                formset.save()
                # Calculamos diferencias inmediatamente
                conciliar_conteo(conteo, aplicar_ajustes=False, usuario=request.user)
                messages.success(request, "Conteo de inventario creado y conciliado.")
                return redirect("web:conteos_detail", pk=conteo.pk)
        else:
            formset = ConteoInventarioItemFormSet(request.POST)
    else:
        form = ConteoInventarioForm(user=request.user, initial={"fecha": date.today()})
        formset = ConteoInventarioItemFormSet()

    context = {
        "form": form,
        "formset": formset,
        "titulo": "Nuevo conteo de inventario",
    }
    return render(request, "web/conteos_form.html", context)


@login_required
def conteos_detail(request, pk):
    """
    Detalle del conteo: encabezado + líneas con:
    - cantidad_contada
    - cantidad_sistema
    - diferencia
    - dentro_tolerancia
    Además, mostramos botones para:
    - Editar (si está en BORRADOR)
    - Cerrar conteo (POST a conteo_cerrar)
    """
    conteo = get_object_or_404(ConteoInventario, pk=pk)

    # Seguridad: solo ver conteos de sus almacenes (si aplica)
    if not usuario_ve_todos_los_almacenes(request.user):
        if conteo.almacen not in request.user.almacenes_asignados.all():
            raise Http404("No tienes acceso a este conteo.")

    items = conteo.items.select_related("insumo").order_by("insumo__nombre")

    context = {
        "conteo": conteo,
        "items": items,
        "es_supervisor": usuario_es_supervisor(request.user),
    }
    return render(request, "web/conteos_detail.html", context)


@login_required
def conteo_cerrar(request, pk):
    """
    Acción para cerrar un conteo (pasar de BORRADOR a CERRADO).
    - Respeta las mismas reglas que en el admin:
      * Si hay diferencias críticas, solo un supervisor puede cerrarlo.
      * Si lo cierra un supervisor con diferencias críticas, se llena aprobado_por / aprobado_en.
    """
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido.")

    conteo = get_object_or_404(ConteoInventario, pk=pk)

    # Seguridad básica por almacén
    if not usuario_ve_todos_los_almacenes(request.user):
        if conteo.almacen not in request.user.almacenes_asignados.all():
            raise Http404("No tienes acceso a este conteo.")

    if not conteo.es_editable:
        messages.error(request, "Este conteo ya no es editable.")
        return redirect("web:conteos_detail", pk=conteo.pk)

    # ¿El usuario tiene permiso funcional para cerrar?
    if not usuario_puede_cerrar_conteos(request.user):
        messages.error(request, "No tienes permisos para cerrar conteos de inventario.")
        return redirect("web:conteos_detail", pk=conteo.pk)

    # Reconciliamos antes de cerrar, para asegurarnos que diferencias y tolerancias están al día
    conciliar_conteo(conteo, aplicar_ajustes=False, usuario=request.user)

    # Si hay diferencias críticas y el usuario NO es supervisor → no permitimos cerrar
    if conteo.tiene_diferencias_criticas and not usuario_es_supervisor(request.user):
        messages.error(
            request,
            "El conteo tiene diferencias críticas. Debe ser cerrado por un supervisor.",
        )
        return redirect("web:conteos_detail", pk=conteo.pk)

    # Si llegamos aquí, cerramos el conteo
    from django.utils import timezone

    conteo.estado = EstadoConteo.CERRADO

    # Si hay diferencias críticas y quien cierra es supervisor, lo marcamos como aprobado
    if conteo.tiene_diferencias_criticas and usuario_es_supervisor(request.user):
        conteo.aprobado_por = request.user
        conteo.aprobado_en = timezone.now()

    conteo.save()

    messages.success(request, "El conteo fue cerrado correctamente.")
    return redirect("web:conteos_detail", pk=conteo.pk)

@require_GET
@login_required
def api_conteo_preview(request):
    """
    Devuelve cantidad_sistema y diferencia para un insumo en un almacén dado,
    considerando la tolerancia ingresada (porcentaje y/o unidades).

    GET params:
      - almacen_id
      - insumo_id
      - cantidad_contada
      - tolerancia_porcentaje (opcional)
      - tolerancia_unidades (opcional)
    """
    from decimal import Decimal, InvalidOperation
    from inventory.models import StockInsumo, Almacen, Insumo

    almacen_id = request.GET.get("almacen_id")
    insumo_id = request.GET.get("insumo_id")
    cantidad_contada_str = request.GET.get("cantidad_contada")

    tol_pct_str = request.GET.get("tolerancia_porcentaje", "")
    tol_units_str = request.GET.get("tolerancia_unidades", "")

    if not almacen_id or not insumo_id or cantidad_contada_str is None:
        return JsonResponse({"ok": False, "error": "Faltan parámetros."}, status=400)

    # Seguridad por almacenes (misma lógica que venimos usando)
    almacen = Almacen.objects.filter(pk=almacen_id, activo=True).first()
    if not almacen:
        return JsonResponse({"ok": False, "error": "Almacén inválido."}, status=404)

    if not usuario_ve_todos_los_almacenes(request.user):
        if not almacen.usuarios.filter(pk=request.user.pk).exists():
            return JsonResponse({"ok": False, "error": "Sin acceso a este almacén."}, status=403)

    insumo = Insumo.objects.filter(pk=insumo_id, activo=True).first()
    if not insumo:
        return JsonResponse({"ok": False, "error": "Insumo inválido."}, status=404)

    try:
        cantidad_contada = Decimal(cantidad_contada_str)
    except (InvalidOperation, TypeError):
        return JsonResponse({"ok": False, "error": "cantidad_contada inválida."}, status=400)

    # cantidad sistema
    stock = StockInsumo.objects.filter(almacen=almacen, insumo=insumo).first()
    cantidad_sistema = stock.cantidad_actual if stock else Decimal("0")
    diferencia = cantidad_contada - cantidad_sistema

    # tolerancias
    tol_pct = None
    tol_units = None

    if tol_pct_str not in ("", None):
        try:
            tol_pct = Decimal(tol_pct_str)
        except InvalidOperation:
            tol_pct = None

    if tol_units_str not in ("", None):
        try:
            tol_units = Decimal(tol_units_str)
        except InvalidOperation:
            tol_units = None

    abs_diff = abs(diferencia)
    unidad = ""
    if getattr(insumo, "unidad", None) and getattr(insumo.unidad, "abreviatura", None):
        unidad = insumo.unidad.abreviatura
    elif getattr(insumo, "unidad", None) and getattr(insumo.unidad, "nombre", None):
        unidad = insumo.unidad.nombre
    dentro = True
    # si hay tolerancia por unidades definida, se usa
    if tol_units is not None:
        dentro = abs_diff <= tol_units

    # si hay tolerancia porcentaje definida, se evalúa también
    if tol_pct is not None:
        base = cantidad_sistema if cantidad_sistema != 0 else Decimal("1")
        pct_diff = (abs_diff / base) * Decimal("100")
        dentro = dentro and (pct_diff <= tol_pct)

    # “crítica” si está fuera de tolerancia
    critica = not dentro

    return JsonResponse({
        "ok": True,
        "cantidad_sistema": str(cantidad_sistema),
        "diferencia": str(diferencia),
        "dentro_tolerancia": dentro,
        "critica": critica,
        "unidad": unidad,
    })

@login_required
def conteo_solicitar_aprobacion(request, pk):
    """
    Operador: pasa BORRADOR -> PENDIENTE_APROBACION.
    Solo se permite si está en BORRADOR.
    """
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido.")

    conteo = get_object_or_404(ConteoInventario, pk=pk)

    # Seguridad por almacén
    if not usuario_ve_todos_los_almacenes(request.user):
        if conteo.almacen not in request.user.almacenes_asignados.all():
            raise Http404("No tienes acceso a este conteo.")

    if conteo.estado != EstadoConteo.BORRADOR:
        messages.error(request, "Solo puedes solicitar aprobación desde BORRADOR.")
        return redirect("web:conteos_detail", pk=conteo.pk)

    # Reconciliamos antes de enviar a aprobación (para dejar diferencias guardadas)
    conciliar_conteo(conteo, aplicar_ajustes=False, usuario=request.user)

    conteo.estado = EstadoConteo.PENDIENTE
    conteo.save(update_fields=["estado"])

    messages.success(request, "Conteo enviado a aprobación de supervisor.")
    return redirect("web:conteos_detail", pk=conteo.pk)


@login_required
def conteo_aprobar(request, pk):
    """
    Supervisor: pasa PENDIENTE_APROBACION -> CERRADO.
    Registra aprobado_por y aprobado_en.
    Permite agregar una nota (opcional) y la guarda en conteo.comentarios.
    """
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido.")

    if not usuario_es_supervisor(request.user):
        return HttpResponseForbidden("Solo un supervisor puede aprobar.")

    conteo = get_object_or_404(ConteoInventario, pk=pk)

    # Seguridad por almacén
    if not usuario_ve_todos_los_almacenes(request.user):
        if conteo.almacen not in request.user.almacenes_asignados.all():
            raise Http404("No tienes acceso a este conteo.")

    if conteo.estado != EstadoConteo.PENDIENTE:
        messages.error(
            request,
            "Este conteo no está pendiente de aprobación."
        )
        return redirect("web:conteos_detail", pk=conteo.pk)


    # Reconciliar antes de cerrar (por seguridad)
    conciliar_conteo(conteo, aplicar_ajustes=False, usuario=request.user)

    # Nota supervisor (opcional)
    nota = (request.POST.get("nota_supervisor") or "").strip()
    if nota:
        conteo.comentarios = (conteo.comentarios or "").rstrip() + nota

        # 1) Pasar a CERRADO y registrar aprobación
    conteo.estado = EstadoConteo.CERRADO
    conteo.aprobado_por = request.user
    conteo.aprobado_en = timezone.now()
    conteo.save(update_fields=["estado", "aprobado_por", "aprobado_en", "comentarios"])

    # 2) Recargar desde BD para asegurar que el servicio vea estado=CERRADO
    conteo.refresh_from_db(fields=["estado"])

    # 3) Aplicar ajustes automáticamente (el servicio exige CERRADO)
    conciliar_conteo(conteo, aplicar_ajustes=True, usuario=request.user)

    # 4) Marcar como AJUSTADO (estado final)
    conteo.estado = EstadoConteo.AJUSTADO
    conteo.save(update_fields=["estado"])

    messages.success(request, "Conteo aprobado, cerrado y ajustes aplicados correctamente.")
    return redirect("web:conteos_detail", pk=conteo.pk)
