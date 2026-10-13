from django.conf import settings
from django.db import models
from django.utils.text import slugify


INDUSTRY_CHOICES = [
    ("transport", "Transportation & Fleet"),
    ("import", "Import Management"),
    ("export", "Export Management"),
    ("manufacturing", "Manufacturing"),
    ("rental", "Building & Property Rental"),
    ("coffee", "Coffee Production & Export"),
    ("other", "General Business"),
]


class CompanyOwned(models.Model):
    """Abstract base: every operational record belongs to one company."""

    company = models.ForeignKey(
        "core.Company", on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(models.Model):
    """A client company registered on the Orbit ERP platform."""

    PLAN_CHOICES = [
        ("starter", "Starter"),
        ("professional", "Professional"),
        ("enterprise", "Enterprise"),
    ]
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    industry_key = models.CharField(
        max_length=20, choices=INDUSTRY_CHOICES, default="transport",
        help_text="Determines the industry-specific modules for this company.",
    )
    country = models.CharField(max_length=80, default="Ethiopia")
    city = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    tin = models.CharField("TIN", max_length=40, blank=True)
    address = models.CharField(max_length=255, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="professional")
    brand_color = models.CharField(max_length=7, default="#ff7a18")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "company"
            slug = base
            i = 2
            while Company.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(models.Model):
    """Links a user to a company with a role (role-based access)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=settings.ROLES, default=settings.ROLE_VIEWER)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "company")
        ordering = ["company__name"]

    def __str__(self):
        return f"{self.user.username} @ {self.company.name} ({self.get_role_display()})"

    @property
    def can_edit(self):
        return self.role in settings.EDITOR_ROLES

    @property
    def can_finance(self):
        return self.role in settings.FINANCE_ROLES


class UserProfile(models.Model):
    """Extended user info — avatar and display preferences."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    title = models.CharField(max_length=80, blank=True)

    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return ""

    def __str__(self):
        return f"Profile of {self.user.username}"


class PushSubscription(models.Model):
    """Web push subscription for a user (one per browser/device)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="push_subscriptions")
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"push:{self.user.username}:{self.endpoint[-24:]}"


class NotificationPreference(models.Model):
    """Per-user opt-in per notification category for web push."""
    CATEGORIES = [
        ("chat", "Chat messages"),
        ("approvals", "Approvals & requests"),
        ("hr", "HR updates"),
        ("announcements", "Announcements"),
        ("system", "System alerts"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="notification_pref")
    chat = models.BooleanField(default=True)
    approvals = models.BooleanField(default=True)
    hr = models.BooleanField(default=True)
    announcements = models.BooleanField(default=True)
    system = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    def enabled(self, category):
        return bool(getattr(self, category, True))

    def __str__(self):
        return f"prefs:{self.user.username}"
