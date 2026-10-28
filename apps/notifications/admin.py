from django.contrib import admin

from .models import Notification, NotificationDelivery


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "notification_type",
        "recommendation",
        "recipient",
        "status",
        "scheduled_at",
        "sent_at",
        "read_at",
    )
    list_filter = ("notification_type", "status", "scheduled_at")
    search_fields = ("recommendation__reference", "recipient__username", "subject")
    readonly_fields = tuple(field.name for field in Notification._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"}

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("notification", "channel", "status", "retry_count", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("notification__recommendation__reference",)
    readonly_fields = tuple(field.name for field in NotificationDelivery._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"}

    def has_delete_permission(self, request, obj=None):
        return False
