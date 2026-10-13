"""Requests module views: submit, track, and decide on ERP requests."""
from django import forms
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core import dashboards as D
from core.crud import _audit
from core.modules import build_sidebar
from core.views import company_access_required

from . import hooks
from .models import Request

APPROVER_ROLES = ["owner", "admin", "manager"]


class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ["request_type", "title", "description", "amount",
                  "needed_by", "start_date", "end_date", "priority"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "needed_by": forms.DateInput(attrs={"type": "date"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


def _el(company, url_name, **kw):
    from django.urls import reverse
    k = {"company_slug": company.slug}
    k.update(kw)
    return reverse(url_name, kwargs=k)


def _can_decide(request, req):
    return hooks.can_decide(request.membership, req)


def _is_approver(request):
    return request.membership.role in APPROVER_ROLES


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    me = request.user
    my_open = Request.objects.filter(company=c, requester=me).exclude(
        status__in=["approved", "rejected", "cancelled"])
    awaiting = Request.objects.filter(company=c, status="submitted")
    if not _is_approver(request):
        awaiting = awaiting.filter(current_approver=me)
    month_start = timezone.now().date().replace(day=1)
    decided_month = Request.objects.filter(
        company=c, decided_at__date__gte=month_start,
        status__in=["approved", "rejected"])

    kpis = [
        D.kpi("My Open Requests", f"{my_open.count()}", "inbox", "orange",
              sub="draft / submitted / returned"),
        D.kpi("Awaiting My Approval" if not _is_approver(request) else "Awaiting Approval",
              f"{awaiting.count()}", "check", "blue", sub="needs a decision"),
        D.kpi("Decided This Month", f"{decided_month.count()}", "clipboard", "green",
              sub="approved + rejected"),
        D.kpi("Total Requests", f"{Request.objects.filter(company=c).count()}",
              "layers", "purple", sub="all time"),
    ]
    my_recent = (Request.objects.filter(company=c, requester=me)
                 .order_by("-created_at")[:8])
    pending = awaiting.order_by("-priority", "-created_at")[:8]
    cfg = {
        "title": "Requests", "subtitle": "Submit and track every business request",
        "kpis": kpis,
        "tables": [
            {"title": "Awaiting Approval", "headers": ["Ref", "Title", "Type", "Requester"],
             "rows": [[r.ref_no, r.title, r.get_request_type_display(),
                       r.requester.username] for r in pending],
             "link": _el(c, "inbox_pending"), "link_label": "Open inbox"},
            {"title": "My Recent Requests", "headers": ["Ref", "Title", "Status", "Updated"],
             "rows": [[r.ref_no, r.title, r.get_status_display(),
                       r.updated_at.strftime("%b %d")] for r in my_recent],
             "link": _el(c, "req_list") + "?tab=mine", "link_label": "My requests"},
        ],
        "actions": [
            {"label": "New Request", "icon": "plus", "url": _el(c, "req_create")},
            {"label": "Approval Inbox", "icon": "inbox", "url": _el(c, "inbox_dashboard")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)


@company_access_required
def request_list(request, company_slug):
    c = request.company
    tab = request.GET.get("tab", "mine")
    q = Request.objects.filter(company=c).select_related("requester", "current_approver")
    if tab == "all":
        if not _is_approver(request):
            tab = "mine"
        else:
            pass
    if tab == "mine" or not _is_approver(request):
        q = q.filter(requester=request.user)
        tab = "mine"
    ftype = request.GET.get("type", "")
    fstatus = request.GET.get("status", "")
    if ftype:
        q = q.filter(request_type=ftype)
    if fstatus:
        q = q.filter(status=fstatus)
    q = q.order_by("-created_at")
    rows = q[:100]
    ctx = {
        "company": c, "membership": request.membership, "tab": tab,
        "ftype": ftype, "fstatus": fstatus, "rows": rows,
        "type_choices": Request.TYPE_CHOICES, "status_choices": Request.STATUS_CHOICES,
        "is_approver": _is_approver(request),
        "sidebar": build_sidebar(request),
    }
    return render(request, "req/request_list.html", ctx)


@company_access_required
def request_create(request, company_slug):
    c = request.company
    form = RequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        req = form.save(commit=False)
        req.company = c
        req.requester = request.user
        req.save()
        hooks.log_event(c, req, request.user, "created", "Request created as draft.")
        _audit(request, "created", req)
        if request.POST.get("do") == "submit":
            req.status = "submitted"
            req.save(update_fields=["status"])
            hooks.on_submitted(c, req, request.user)
            messages.success(request, f"{req.ref_no} submitted for approval.")
        else:
            messages.success(request, f"{req.ref_no} saved as draft.")
        return redirect(_el(c, "req_detail", pk=req.pk))
    ctx = {"company": c, "membership": request.membership, "form": form,
           "sidebar": build_sidebar(request)}
    return render(request, "req/request_form.html", ctx)


def _detail_ctx(request, req):
    c = request.company
    events = req.events.select_related("actor").all()
    can_edit = req.status in ("draft", "returned") and (
        req.requester_id == request.user.id or request.membership.role in ("owner", "admin"))
    can_submit = req.status in ("draft", "returned") and (
        req.requester_id == request.user.id or request.membership.role in ("owner", "admin"))
    can_decide = req.status == "submitted" and _can_decide(request, req)
    can_cancel = req.status in ("draft", "submitted", "returned") and (
        req.requester_id == request.user.id or request.membership.role in ("owner", "admin"))
    return {
        "company": c, "membership": request.membership, "req": req, "events": events,
        "can_edit": can_edit, "can_submit": can_submit, "can_decide": can_decide,
        "can_cancel": can_cancel, "sidebar": build_sidebar(request),
    }


@company_access_required
def request_detail(request, company_slug, pk):
    c = request.company
    req = get_object_or_404(Request.objects.select_related(
        "requester", "current_approver", "decided_by"), company=c, pk=pk)
    if not _is_approver(request) and req.requester_id != request.user.id:
        messages.error(request, "You can only view your own requests.")
        return redirect(_el(c, "req_list"))
    return render(request, "req/request_detail.html", _detail_ctx(request, req))


@company_access_required
def request_update(request, company_slug, pk):
    c = request.company
    req = get_object_or_404(Request, company=c, pk=pk)
    if req.status not in ("draft", "returned") or not (
            req.requester_id == request.user.id or request.membership.role in ("owner", "admin")):
        messages.error(request, "This request can no longer be edited.")
        return redirect(_el(c, "req_detail", pk=pk))
    form = RequestForm(request.POST or None, instance=req)
    if request.method == "POST" and form.is_valid():
        form.save()
        _audit(request, "updated", req)
        messages.success(request, "Request updated.")
        return redirect(_el(c, "req_detail", pk=pk))
    ctx = {"company": c, "membership": request.membership, "form": form,
           "req": req, "sidebar": build_sidebar(request)}
    return render(request, "req/request_form.html", ctx)


@company_access_required
@require_POST
def request_delete(request, company_slug, pk):
    c = request.company
    req = get_object_or_404(Request, company=c, pk=pk)
    if req.status != "draft" or not (
            req.requester_id == request.user.id or request.membership.role in ("owner", "admin")):
        messages.error(request, "Only drafts can be deleted.")
        return redirect(_el(c, "req_detail", pk=pk))
    _audit(request, "deleted", req)
    req.delete()
    messages.success(request, "Draft deleted.")
    return redirect(_el(c, "req_list"))


@company_access_required
@require_POST
def request_action(request, company_slug, pk, action):
    c = request.company
    req = get_object_or_404(Request, company=c, pk=pk)
    note = (request.POST.get("note") or "").strip()
    me = request.user

    if action == "submit":
        if req.status not in ("draft", "returned") or not (
                req.requester_id == me.id or request.membership.role in ("owner", "admin")):
            messages.error(request, "Cannot submit this request.")
        else:
            req.status = "submitted"
            req.review_notes = ""
            req.save(update_fields=["status", "review_notes"])
            hooks.on_submitted(c, req, me)
            _audit(request, "submitted", req)
            messages.success(request, f"{req.ref_no} submitted for approval.")
    elif action in ("approve", "reject"):
        if req.status != "submitted" or not _can_decide(request, req):
            messages.error(request, "You cannot decide on this request.")
        else:
            req.status = "approved" if action == "approve" else "rejected"
            req.review_notes = note
            req.save(update_fields=["status", "review_notes"])
            hooks.on_decided(c, req, me, req.status)
            _audit(request, action, req)
            messages.success(request, f"{req.ref_no} {req.status}.")
    elif action == "return":
        if req.status != "submitted" or not _can_decide(request, req):
            messages.error(request, "You cannot return this request.")
        elif not note:
            messages.error(request, "Please explain what needs to change.")
        else:
            req.status = "returned"
            req.review_notes = note
            req.save(update_fields=["status", "review_notes"])
            hooks.on_returned(c, req, me)
            _audit(request, "returned", req)
            messages.success(request, f"{req.ref_no} returned for changes.")
    elif action == "cancel":
        if req.status not in ("draft", "submitted", "returned") or not (
                req.requester_id == me.id or request.membership.role in ("owner", "admin")):
            messages.error(request, "Cannot cancel this request.")
        else:
            req.status = "cancelled"
            req.save(update_fields=["status"])
            hooks.on_cancelled(c, req, me)
            _audit(request, "cancelled", req)
            messages.success(request, f"{req.ref_no} cancelled.")
    elif action == "comment":
        if not note:
            messages.error(request, "Comment cannot be empty.")
        elif not (_is_approver(request) or req.requester_id == me.id):
            messages.error(request, "You cannot comment on this request.")
        else:
            hooks.log_event(c, req, me, "comment", note)
            messages.success(request, "Comment added.")
    else:
        messages.error(request, "Unknown action.")
    return redirect(_el(c, "req_detail", pk=pk))


@company_access_required
def request_history(request, company_slug):
    """Activity history across all requests (approvers see all; others see own)."""
    from .models import RequestEvent
    c = request.company
    ev = RequestEvent.objects.filter(company=c).select_related("request", "actor")
    if not _is_approver(request):
        ev = ev.filter(Q(request__requester=request.user) | Q(actor=request.user))
    ev = ev.order_by("-created_at")[:150]
    ctx = {"company": c, "membership": request.membership, "events": ev,
           "sidebar": build_sidebar(request)}
    return render(request, "req/request_history.html", ctx)
