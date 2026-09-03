from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class UserAdmin(DjangoUserAdmin):
    inlines = [UserProfileInline]
    list_display = DjangoUserAdmin.list_display + ("role",)

    def role(self, obj):
        return getattr(obj.profile, "get_role_display", lambda: "-")()


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
