# admin.py
from django.contrib import admin
from .models import Program 

class ProgramAdmin(admin.ModelAdmin):
    list_display = ('time_and_date', 'program_name', 'status', 'is_new')

# Register the Program model with the custom admin class
admin.site.register(Program, ProgramAdmin)
