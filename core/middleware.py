from django.utils.deprecation import MiddlewareMixin

from .models import Company, Membership


class ActiveCompanyMiddleware(MiddlewareMixin):
    """Attaches request.company / request.membership from the session.

    Company-scoped views resolve the company from the URL; this middleware
    makes the *selected* company available everywhere (topbar switcher, hub).
    """

    def process_request(self, request):
        request.company = None
        request.membership = None
        if not request.user.is_authenticated:
            return
        company_id = request.session.get("active_company_id")
        if company_id:
            try:
                membership = (
                    Membership.objects.select_related("company", "user")
                    .get(user=request.user, company_id=company_id, is_active=True, company__is_active=True)
                )
                request.membership = membership
                request.company = membership.company
            except Membership.DoesNotExist:
                request.session.pop("active_company_id", None)
