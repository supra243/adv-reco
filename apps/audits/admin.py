from django.contrib import admin

from .models import AuditMission


@admin.register(AuditMission)
class AuditMissionAdmin(admin.ModelAdmin):
    list_display = ("mission_name", "source", "audited_entity", "issuance_date")
    list_filter = ("source", "issuance_date")
    search_fields = ("mission_name", "audited_entity", "source")
    date_hierarchy = "issuance_date"
