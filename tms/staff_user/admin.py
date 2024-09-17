from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from.models import ChatMessage,UserProfile

admin.site.site_header ='TAMC MANAGEMENT SYSTEM'
# Register your models here.
admin.site.unregister(User)  # Unregister the default User model

class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'groups'),
        }),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    
class MessageAdmin(admin.ModelAdmin):
    list_display =('user','message','timestamp')
    

class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user","phone_number","gender","nida_number")
   
admin.site.register(User, MyUserAdmin)  # Register the User model with the custom admin class
admin.site.register(ChatMessage,MessageAdmin)
admin.site.register(UserProfile,ProfileAdmin)

