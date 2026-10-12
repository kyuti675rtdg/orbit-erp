from django.contrib import admin

from .models import Company, Membership


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "city", "plan", "is_active", "created_at")
    list_filter = ("plan", "is_active", "country")
    search_fields = ("name", "city", "tin")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active")
    search_fields = ("user__username", "company__name")
