from django.contrib import admin
from .models import Equipment, AssignmentDetail, TaskAssignment, AssignmentEquipment

import io
from PIL import Image

class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'type_model', 'quantity', 'equipment_image', 'slug','status')
    search_fields = ['name', 'category', 'type_model']  # Add search functionality
    list_filter = ['category', 'type_model']  # Add filtering options

    def save_model(self, request, obj, form, change):
        # Convert uploaded image to JPEG format and resize
        if 'equipment_image' in form.cleaned_data:
            image_field = form.cleaned_data['equipment_image']
            if image_field:
                # Open the uploaded image
                image = Image.open(image_field)
                
                # Resize the image to a specific height and width
                target_height = 300  # Set your desired height
                target_width = 300   # Set your desired width
                image = image.resize((target_width, target_height), Image.LANCZOS) 
                
                # Convert to RGB if not already in that mode
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                # Create a BytesIO object to hold the JPEG image data
                jpeg_io = io.BytesIO()
                
                # Save the image as JPEG to the BytesIO object
                image.save(jpeg_io, format='JPEG', quality=90)
                
                # Move the file pointer to the beginning of the BytesIO object
                jpeg_io.seek(0)
                
                # Set the image field to the JPEG data
                obj.equipment_image.save(image_field.name, jpeg_io, save=False)

        super().save_model(request, obj, form, change)

    def add_category_manually(self, request, queryset):
        # Add a new category manually
        new_category = request.POST.get('new_category')
        if new_category:
            Equipment.CATEGORY_CHOICES.append((new_category, new_category))
            self.message_user(request, f"New category '{new_category}' added successfully.")
        else:
            self.message_user(request, "No category provided.")
    add_category_manually.short_description = "Add Category Manually"

    def add_type_model_manually(self, request, queryset):
        # Add a new type model manually
        new_type_model = request.POST.get('new_type_model')
        if new_type_model:
            Equipment.TYPE_MODEL_CHOICES.append((new_type_model, new_type_model))
            self.message_user(request, f"New type model '{new_type_model}' added successfully.")
        else:
            self.message_user(request, "No type model provided.")
    add_type_model_manually.short_description = "Add Type Model Manually"

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['add_category_manually'] = (
            self.add_category_manually,
            'add_category_manually',
            "Add new category manually"
        )
        actions['add_type_model_manually'] = (
            self.add_type_model_manually,
            'add_type_model_manually',
            "Add new type model manually"
        )
        return actions
class AssignmentDetailAdmin(admin.ModelAdmin):
    list_display = ('detail',)
    
class AssignmentEquipmentAdmin(admin.ModelAdmin):
    list_display = ('task_assignment', 'equipment', 'quantity')

class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'date', 'location', 'category', 'submission_date', 'status', 'requested_by')

admin.site.register(AssignmentDetail,AssignmentDetailAdmin)
admin.site.register(TaskAssignment,TaskAssignmentAdmin)
admin.site.register(AssignmentEquipment,AssignmentEquipmentAdmin)
admin.site.register(Equipment, EquipmentAdmin)
