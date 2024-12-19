from django.urls import path
from .import views
from staff_user.views import custom_404_page  # Import custom_404_page from staff_user app




app_name ='equipment'

urlpatterns = [
     path('register-equipment/', views.register_equipment, name='register_equipment'),
     path('equipment-list/', views.equipment_list, name='equipment_list'),
     path('<int:pk>/delete_confirmation/', views.delete_confirmation, name='delete_confirmation'),  # Add this line
    path('<int:pk>/edit/', views.edit_equipment, name='edit_equipment'),
    path('<int:pk>/delete/', views.delete_equipment, name='delete_equipment'),

    path('task-assignment/', views.task_assignment, name='task_assignment'),
    path('view-task-assignment/', views.view_assignments, name='view_assignments'),
    path('specific-request/<int:task_id>/', views.specific_request_view, name='specific_request'),

  path('edit-task/<int:task_id>/', views.edit_task_assignment, name='edit_task_assignment'),
    path('delete-task/<int:task_id>/', views.delete_task_assignment, name='delete_task_assignment'),
    path('approve/<int:task_id>/', views.approve_request, name='approve_request'),
    path('reject/<int:task_id>/', views.reject_request, name='reject_request'),
path('approved-requests/', views.view_approved_requests, name='view_approved_requests'),
      path('confirm-return/<int:task_id>/', views.confirm_return, name='confirm_return'),
 
    # Add other paths as needed
] 
handler404 = custom_404_page