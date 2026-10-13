"""Shared generic CRUD engine: list / detail / create / update / delete.

Every industry app (fleet, imports, exports, manufacturing, rentals, shared)
registers an ENTITIES dict and gets full working CRUD. App config travels as
extra URL kwargs::

    path("<slug:entity>/", crud.crud_list,
         {"entities": ENTITIES, "url_ns": "imports",
          "sidebar_fn": get_sidebar, "template_dir": "crud"},
         name="imports_entity_list"),

URLs are pre-reversed into a ``urls`` dict so templates stay app-agnostic.
"""
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models as dj_models
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.views import company_access_required, editor_required


def resolve(obj, accessor):
    """Resolve 'a__b' style accessor to a display value."""
    cur = obj
    for part in accessor.split("__"):
        cur = getattr(cur, part, None)
        if cur is None:
            return "—"
        if callable(cur) and not isinstance(cur, dj_models.Manager):
            try:
                cur = cur()
            except TypeError:
                return "—"
    return cur if cur not in ("", None) else "—"


def display_value(obj, field_name):
    """Human-friendly value for a model field (choices aware)."""
    try:
        field = obj._meta.get_field(field_name)
    except Exception:
        return resolve(obj, field_name)
    if field.choices:
        return getattr(obj, f"get_{field_name}_display")()
    val = getattr(obj, field_name, None)
    if isinstance(val, bool):
        return "Yes" if val else "No"
    if val in ("", None):
        return "—"
    from decimal import Decimal
    if isinstance(val, int):
        return f"{val:,}"
    if isinstance(val, Decimal):
        return f"{val:,}"
    return val


def scope_fk_fields(form, company):
    for name, field in form.fields.items():
        try:
            model_field = form._meta.model._meta.get_field(name)
        except Exception:
            continue
        if isinstance(model_field, dj_models.ForeignKey):
            rel = model_field.related_model
            if any(f.name == "company" for f in rel._meta.get_fields()):
                field.queryset = rel.objects.filter(company=company)


def entity_form_class(cfg, company):
    model = cfg["model"]
    fields = cfg["form_fields"]

    def _form_init(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        scope_fk_fields(self, company)
        for fname, f in self.fields.items():
            try:
                mf = model._meta.get_field(fname)
            except Exception:
                continue
            if isinstance(mf, dj_models.DateTimeField):
                f.widget = forms.DateTimeInput(attrs={"type": "datetime-local"})
            elif isinstance(mf, dj_models.DateField):
                f.widget = forms.DateInput(attrs={"type": "date"})
            elif isinstance(mf, dj_models.TextField):
                f.widget.attrs.update({"rows": 3})
            if isinstance(f.widget, (forms.TextInput, forms.NumberInput, forms.Select,
                                     forms.DateInput, forms.DateTimeInput, forms.Textarea,
                                     forms.EmailInput)):
                f.widget.attrs.setdefault("class", "input")

    Meta = type("Meta", (), {"model": model, "fields": fields})
    return type("_EntityForm", (forms.ModelForm,), {"Meta": Meta, "__init__": _form_init})


def _cfg_or_404(entities, entity):
    cfg = entities.get(entity)
    if not cfg:
        raise Http404("Unknown entity")
    return cfg


def _base_urls(url_ns, company_slug, entity):
    kw = {"company_slug": company_slug, "entity": entity}
    return {
        "list": reverse(f"{url_ns}_entity_list", kwargs=kw),
        "create": reverse(f"{url_ns}_entity_create", kwargs=kw),
    }


def _obj_urls(url_ns, company_slug, entity, pk):
    kw = {"company_slug": company_slug, "entity": entity, "pk": pk}
    return {
        "detail": reverse(f"{url_ns}_entity_detail", kwargs=kw),
        "update": reverse(f"{url_ns}_entity_update", kwargs=kw),
        "delete": reverse(f"{url_ns}_entity_delete", kwargs=kw),
    }


def _ctx(request, sidebar_fn):
    return {"sidebar": sidebar_fn(request)} if sidebar_fn else {}


@company_access_required
def crud_list(request, company_slug, entity, *, entities, url_ns, sidebar_fn=None,
              template_dir="crud", module_name=""):
    cfg = _cfg_or_404(entities, entity)
    company = request.company
    model = cfg["model"]
    order = "-created_at" if any(f.name == "created_at" for f in model._meta.get_fields()) else "-id"
    qs = model.objects.filter(company=company).order_by(order)
    q = request.GET.get("q", "").strip()
    if q and cfg.get("search"):
        cond = Q()
        for f in cfg["search"]:
            cond |= Q(**{f"{f}__icontains": q})
        qs = qs.filter(cond)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    rows = []
    for obj in page.object_list:
        rows.append({
            "obj": obj,
            "cells": [display_value(obj, a) for _, a in cfg["list_display"]],
            "url": reverse(f"{url_ns}_entity_detail",
                           kwargs={"company_slug": company.slug, "entity": entity, "pk": obj.pk}),
        })
    ctx = {
        "company": company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "headers": [h for h, _ in cfg["list_display"]],
        "rows": rows, "page": page, "q": q,
        "urls": _base_urls(url_ns, company.slug, entity),
        "module_name": module_name,
        "readonly": cfg.get("readonly", False),
    }
    ctx.update(_ctx(request, sidebar_fn))
    return render(request, f"{template_dir}/entity_list.html", ctx)


@company_access_required
def crud_detail(request, company_slug, entity, pk, *, entities, url_ns,
                sidebar_fn=None, template_dir="crud", module_name="", custom_detail=None,
                detail_panel=None):
    cfg = _cfg_or_404(entities, entity)
    company = request.company
    obj = get_object_or_404(cfg["model"], company=company, pk=pk)
    if custom_detail and entity in custom_detail:
        return custom_detail[entity](request, company_slug, obj)
    fields = []
    for f in cfg["model"]._meta.get_fields():
        if f.name in ("id", "company", "created_at", "updated_at") or f.auto_created:
            continue
        if isinstance(f, (dj_models.ForeignKey, dj_models.CharField, dj_models.TextField,
                          dj_models.IntegerField, dj_models.DecimalField, dj_models.FloatField,
                          dj_models.DateField, dj_models.DateTimeField, dj_models.BooleanField,
                          dj_models.PositiveIntegerField, dj_models.JSONField,
                          dj_models.FileField)):
            fields.append((f.verbose_name.title(), display_value(obj, f.name)))
    related = []
    for title, rel_name, cols in cfg.get("detail_related", []):
        manager = getattr(obj, rel_name, None)
        items = list(manager.all()[:8]) if manager is not None else []
        related.append({"title": title, "headers": [h for h, _ in cols],
                        "rows": [[display_value(i, a) for _, a in cols] for i in items],
                        "count": manager.count() if manager is not None else 0})
    panel = detail_panel(entity, obj, request) if detail_panel else None
    urls = _base_urls(url_ns, company.slug, entity)
    urls.update(_obj_urls(url_ns, company.slug, entity, pk))
    ctx = {
        "company": company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "obj": obj, "fields": fields, "related": related,
        "urls": urls, "detail_panel": panel,
        "module_name": module_name,
        "readonly": cfg.get("readonly", False),
    }
    ctx.update(_ctx(request, sidebar_fn))
    return render(request, f"{template_dir}/entity_detail.html", ctx)


def _audit(request, action, obj):
    """Write an audit trail entry; never breaks the main flow."""
    try:
        from shared.models import AuditLog
        AuditLog.objects.create(
            company=request.company, user=request.user, action=action,
            model_name=obj._meta.model_name, object_repr=str(obj)[:200],
        )
    except Exception:
        pass


def _finance_denied(request, entities, entity, url_ns):
    cfg = _cfg_or_404(entities, entity)
    if cfg.get("finance") and request.membership.role not in settings.FINANCE_ROLES | settings.EDITOR_ROLES:
        messages.error(request, "Your role does not permit this action.")
        return redirect(f"{url_ns}_entity_list",
                        company_slug=request.company.slug, entity=entity)
    return None


@company_access_required
@editor_required
def crud_create(request, company_slug, entity, *, entities, url_ns, sidebar_fn=None,
                template_dir="crud", module_name=""):
    denied = _finance_denied(request, entities, entity, url_ns)
    if denied:
        return denied
    cfg = _cfg_or_404(entities, entity)
    Form = entity_form_class(cfg, request.company)
    form = Form(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.company = request.company
        if hasattr(obj, "created_by") and not getattr(obj, "created_by_id", None):
            obj.created_by = request.user
        obj.save()
        form.save_m2m()
        _audit(request, "created", obj)
        messages.success(request, f"{cfg['singular']} created.")
        return redirect(f"{url_ns}_entity_detail",
                        company_slug=request.company.slug, entity=entity, pk=obj.pk)
    ctx = {
        "company": request.company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "form": form, "mode": "Create",
        "urls": _base_urls(url_ns, request.company.slug, entity),
        "module_name": module_name,
    }
    ctx.update(_ctx(request, sidebar_fn))
    return render(request, f"{template_dir}/entity_form.html", ctx)


@company_access_required
@editor_required
def crud_update(request, company_slug, entity, pk, *, entities, url_ns,
                sidebar_fn=None, template_dir="crud", module_name=""):
    denied = _finance_denied(request, entities, entity, url_ns)
    if denied:
        return denied
    cfg = _cfg_or_404(entities, entity)
    obj = get_object_or_404(cfg["model"], company=request.company, pk=pk)
    Form = entity_form_class(cfg, request.company)
    form = Form(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        _audit(request, "updated", obj)
        messages.success(request, f"{cfg['singular']} updated.")
        return redirect(f"{url_ns}_entity_detail",
                        company_slug=request.company.slug, entity=entity, pk=obj.pk)
    urls = _base_urls(url_ns, request.company.slug, entity)
    urls.update(_obj_urls(url_ns, request.company.slug, entity, pk))
    ctx = {
        "company": request.company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "form": form, "mode": "Edit", "urls": urls,
        "module_name": module_name,
    }
    ctx.update(_ctx(request, sidebar_fn))
    return render(request, f"{template_dir}/entity_form.html", ctx)


@company_access_required
@editor_required
def crud_delete(request, company_slug, entity, pk, *, entities, url_ns,
                sidebar_fn=None, template_dir="crud", module_name=""):
    denied = _finance_denied(request, entities, entity, url_ns)
    if denied:
        return denied
    cfg = _cfg_or_404(entities, entity)
    obj = get_object_or_404(cfg["model"], company=request.company, pk=pk)
    if request.method == "POST":
        _audit(request, "deleted", obj)
        obj.delete()
        messages.success(request, f"{cfg['singular']} deleted.")
        return redirect(f"{url_ns}_entity_list",
                        company_slug=request.company.slug, entity=entity)
    urls = _base_urls(url_ns, request.company.slug, entity)
    urls.update(_obj_urls(url_ns, request.company.slug, entity, pk))
    ctx = {
        "company": request.company, "membership": request.membership, "cfg": cfg,
        "entity": entity, "obj": obj, "urls": urls,
        "module_name": module_name,
    }
    ctx.update(_ctx(request, sidebar_fn))
    return render(request, f"{template_dir}/entity_confirm_delete.html", ctx)


def crud_urls(url_ns, entities, sidebar_fn, template_dir="crud", module_name=""):
    """URL patterns list for an app's generic entities."""
    from django.urls import path
    kw = {"entities": entities, "url_ns": url_ns,
          "sidebar_fn": sidebar_fn, "template_dir": template_dir,
          "module_name": module_name}
    return [
        path("<slug:entity>/", crud_list, kw, name=f"{url_ns}_entity_list"),
        path("<slug:entity>/new/", crud_create, kw, name=f"{url_ns}_entity_create"),
        path("<slug:entity>/<int:pk>/", crud_detail, kw, name=f"{url_ns}_entity_detail"),
        path("<slug:entity>/<int:pk>/edit/", crud_update, kw, name=f"{url_ns}_entity_update"),
        path("<slug:entity>/<int:pk>/delete/", crud_delete, kw, name=f"{url_ns}_entity_delete"),
    ]
