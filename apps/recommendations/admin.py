from django.contrib import admin

from .models import (
    DueDateChange,
    Recommendation,
    RecommendationComment,
    RecommendationHistory,
    RecommendationResponsible,
)


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class RecommendationResponsibleInline(ReadOnlyInline):
    model = RecommendationResponsible
    fields = ("user", "role", "is_primary", "assigned_at")
    readonly_fields = fields


class DueDateChangeInline(ReadOnlyInline):
    model = DueDateChange
    fields = ("previous_date", "new_date", "reason", "changed_by", "changed_at")
    readonly_fields = fields


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "audit_mission",
        "responsible_department",
        "status",
        "effective_due_date",
    )
    list_filter = ("status", "responsible_department", "risk_type", "classification")
    search_fields = ("reference", "finding", "recommendation", "audit_mission__mission_name")
    readonly_fields = tuple(field.name for field in Recommendation._meta.fields)
    inlines = (RecommendationResponsibleInline, DueDateChangeInline)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RecommendationHistory)
class RecommendationHistoryAdmin(admin.ModelAdmin):
    list_display = ("recommendation", "action", "field", "user", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("recommendation__reference", "user__username", "comment")
    readonly_fields = tuple(field.name for field in RecommendationHistory._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"}

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RecommendationComment)
class RecommendationCommentAdmin(admin.ModelAdmin):
    list_display = ("recommendation", "author", "created_at")
    search_fields = ("recommendation__reference", "author__username", "body")
    readonly_fields = tuple(field.name for field in RecommendationComment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"}

    def has_delete_permission(self, request, obj=None):
        return False
