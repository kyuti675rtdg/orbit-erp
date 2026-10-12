from .models import Membership


def active_company(request):
    """Expose the selected company + membership + user's companies to all templates."""
    companies = []
    if request.user.is_authenticated:
        companies = (
            Membership.objects.select_related("company")
            .filter(user=request.user, is_active=True, company__is_active=True)
            .order_by("company__name")
        )
    return {
        "active_company": getattr(request, "company", None),
        "active_membership": getattr(request, "membership", None),
        "my_companies": companies,
    }
