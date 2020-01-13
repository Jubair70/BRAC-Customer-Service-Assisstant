from django.contrib import admin
from django.db.models import Count
from usermodule.models import UserModuleProfile,UserPasswordHistory,UserFailedLogin


class UserFailedLoginAdmin(admin.ModelAdmin):
    list_display = ['was_username', 'login_attempt_time']
    ordering = ['user_id','login_attempt_time']

admin.site.register(UserFailedLogin,UserFailedLoginAdmin)
