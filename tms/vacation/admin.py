from django.contrib import admin
from .models import Holiday, HolidayType, OverlayDescription, Overlay,PermissionRequest

class HolidayTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class HolidayAdmin(admin.ModelAdmin):
    list_display = ('user', 'working_holiday', 'custom_holiday_type', 'start_date', 'end_date', 'status', 'delegatee', 'delegatee_approved')
    list_filter = ('status', 'working_holiday', 'custom_holiday_type', 'delegatee')
    search_fields = ('user__username', 'delegatee__username', 'address')
    readonly_fields = ('approved_by', 'rejected_by', 'assigned_by')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            # Set fields to readonly if the status is not 'pending'
            if obj.status in ['approved', 'rejected']:
                return self.readonly_fields + ('user', 'address', 'working_holiday', 'custom_holiday_type', 'start_date', 'end_date', 'my_last_holiday_start', 'my_last_holiday_end', 'current_address', 'delegatee')
        return self.readonly_fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(user=request.user)
        return queryset

class OverlayDescriptionAdmin(admin.ModelAdmin):
    list_display = ('description', 'added_by', 'added_on')
    search_fields = ('description', 'added_by__username')
    readonly_fields = ('added_by', 'added_on')

class OverlayAdmin(admin.ModelAdmin):
    filter_horizontal = ('descriptions',)



class PermissionRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'start_date', 'end_date', 'place', 'description', 'delegatee', 'reporting_date')
    search_fields = ('user__username', 'address', 'place')


# Register the models with the admin site
admin.site.register(HolidayType, HolidayTypeAdmin)
admin.site.register(Holiday, HolidayAdmin)
admin.site.register(OverlayDescription, OverlayDescriptionAdmin)
admin.site.register(Overlay, OverlayAdmin)
admin.site.register(PermissionRequest, PermissionRequestAdmin)