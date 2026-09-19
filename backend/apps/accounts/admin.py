from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Address, User


class AddressInline(admin.StackedInline):
    model = Address
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "phone")
    inlines = [AddressInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2"),
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "city", "country", "is_default")
    list_filter = ("country", "is_default")
    search_fields = ("full_name", "user__email", "city", "postal_code")