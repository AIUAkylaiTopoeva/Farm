from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, FarmerProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("id", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "role")}),
        ("Permissions", {"fields": (
            "is_active", "is_staff", "is_superuser",
            "groups", "user_permissions"
        )}),
        ("Meta", {"fields": ("last_login", "date_joined", "activation_code")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "password1", "password2",
                "role", "is_active", "is_staff"
            ),
        }),
    )


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "farm_name", "address",
        "lat", "lon", "is_verified"
    )
    list_filter = ("is_verified",)
    search_fields = ("user__email", "farm_name", "address")
    list_editable = ("is_verified",)  # ← можно менять прямо в списке
    actions = ["verify_farmers", "unverify_farmers"]

    def verify_farmers(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, "Фермеры верифицированы!")
    verify_farmers.short_description = "Верифицировать выбранных фермеров"

    def unverify_farmers(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, "Верификация снята!")
    unverify_farmers.short_description = "Снять верификацию"