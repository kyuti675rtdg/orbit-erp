"""Approval inbox: review, approve, reject or return requests.

The inbox is a role-aware lens over req.Request:
- pending: requests submitted and awaiting this user's decision
- mine: requests this user submitted
- history: requests this user has acted on
Decisions are executed through the shared request workflow so the
activity history stays in one place.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core import dashboards as D
from core.modules import build_sidebar
from core.views import company_access_required

from req import hooks as req_hooks
from req.models import Request, RequestEvent
from req.views import _detail_ctx


def _el(company, url_name, **kw):
    from django.urls import reverse
    k = {"company_slug": company.slug}
    k.update(kw)
    return reverse(url_name, kwargs=k)


def _pending_qs(request):
    """Requests awaiting this user's decision."""
    c = request.company
    qs = (Request.objects.filter(company=c, status="submitted")
          .select_related("requester", "current_approver"))
    if request.membership.role in req_hooks.APPROVER_ROLES:
        return qs
    return qs.filter(current_approver=request.user)


@company_access_required
def dashboard(request, company_slug):
    c = request.company
    me = request.user
    pending = _pending_qs(request)
    my_drafts = Request.objects.filter(
        company=c, requester=me, status__in=["draft", "returned"])
    my_waiting = Request.objects.filter(
        company=c, requester=me, status="submitted")
    month_start = timezone.now().date().replace(day=1)
    decided = RequestEvent.objects.filter(
        company=c, actor=me, action__in=["approved", "rejected", "returned"],
        created_at__date__gte=month_start)

    kpis = [
        D.kpi("Pending My Approval", f"{pending.count()}", "inbox", "orange",
              sub="needs your decision"),
        D.kpi("My Drafts", f"{my_drafts.count()}", "file", "blue",
              sub="not yet submitted"),
        D.kpi("My Requests Waiting", f"{my_waiting.count()}", "clock", "purple",
              sub="with approvers"),
        D.kpi("Decided by Me (Month)", f"{decided.count()}", "check", "green",
              sub="approved / rejected / returned"),
    ]
    oldest = pending.order_by("created_at")[:8]
    recent_mine = (Request.objects.filter(company=c, requester=me)
                   .order_by("-created_at")[:8])
    cfg = {
        "title": "Inbox", "subtitle": "Review and decide on requests",
        "kpis": kpis,
        "tables": [
            {"title": "Oldest Pending First", "headers": ["Ref", "Title", "Requester", "Priority"],
             "rows": [[r.ref_no, r.title, r.requester.username,
                       r.get_priority_display()] for r in oldest],
             "link": _el(c, "inbox_pending"), "link_label": "All pending"},
            {"title": "My Recent Submissions", "headers": ["Ref", "Title", "Status"],
             "rows": [[r.ref_no, r.title, r.get_status_display()] for r in recent_mine],
             "link": _el(c, "inbox_mine"), "link_label": "My submissions"},
        ],
        "actions": [
            {"label": "Review Pending", "icon": "inbox", "url": _el(c, "inbox_pending")},
            {"label": "New Request", "icon": "plus", "url": _el(c, "req_create")},
        ],
    }
    return D.render_module_dashboard(request, c, cfg)


@company_access_required
def pending(request, company_slug):
    c = request.company
    qs = _pending_qs(request).order_by("-priority", "created_at")
    ftype = request.GET.get("type", "")
    if ftype:
        qs = qs.filter(request_type=ftype)
    rows = qs[:100]
    ctx = {"company": c, "membership": request.membership, "rows": rows,
           "ftype": ftype, "type_choices": Request.TYPE_CHOICES,
           "sidebar": build_sidebar(request)}
    return render(request, "inbox/pending.html", ctx)


@company_access_required
def mine(request, company_slug):
    c = request.company
    rows = (Request.objects.filter(company=request.company, requester=request.user)
            .select_related("current_approver").order_by("-created_at")[:100])
    ctx = {"company": c, "membership": request.membership, "rows": rows,
           "sidebar": build_sidebar(request)}
    return render(request, "inbox/mine.html", ctx)


@company_access_required
def history(request, company_slug):
    c = request.company
    acted_ids = (RequestEvent.objects.filter(company=c, actor=request.user)
                 .values_list("request_id", flat=True))
    rows = (Request.objects.filter(company=c, pk__in=acted_ids)
            .select_related("requester").order_by("-updated_at")[:100])
    ctx = {"company": c, "membership": request.membership, "rows": rows,
           "sidebar": build_sidebar(request)}
    return render(request, "inbox/history.html", ctx)


@company_access_required
def item_detail(request, company_slug, pk):
    """Inbox view of a request — same detail page & workflow actions."""
    c = request.company
    req = get_object_or_404(Request.objects.select_related(
        "requester", "current_approver", "decided_by"), company=c, pk=pk)
    allowed = (req.requester_id == request.user.id
               or request.membership.role in req_hooks.APPROVER_ROLES
               or req.current_approver_id == request.user.id)
    if not allowed:
        messages.error(request, "This request is not in your inbox.")
        return redirect(_el(c, "inbox_pending"))
    ctx = _detail_ctx(request, req)
    ctx["back_url"] = _el(c, "inbox_pending")
    return render(request, "req/request_detail.html", ctx)
