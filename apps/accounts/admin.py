from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Organisation", {"fields": ("department", "role")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Organisation", {"fields": ("department", "role")}),
    )
    list_display = DjangoUserAdmin.list_display + ("department", "role")
    list_filter = DjangoUserAdmin.list_filter + ("role", "department")
