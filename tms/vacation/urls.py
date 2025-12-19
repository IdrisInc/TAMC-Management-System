from django.urls import path
from .import views
app_name = 'vacation'

urlpatterns = [
  path('leave-permission',views.vacation_home, name='vacation'),
    path('create/', views.holiday_create, name='holiday_create'),
     path('view/', views.view_holidays, name='view_holidays'),
     path('edit/<int:id>/',views.edit_holiday,name= 'edit_holiday'),
     path('delete/<int:id>/',views.delete_holiday,name= 'delete_holiday'),
      path('approve/<int:holiday_id>/', views.approve_holiday, name='approve_holiday'),
    path('reject/<int:holiday_id>/', views.reject_holiday, name='reject_holiday'),
     path('approve_delegatee/<int:holiday_id>/', views.approve_delegatee, name='approve_delegatee'),
    path('reject_delegatee/<int:holiday_id>/', views.reject_delegatee, name='reject_delegatee'),
    path('permission_request',views.create_permission, name = 'permission_request'),
    
    path('view_permission_request',views.view_requests, name = 'view_permission_request'),
    # path('vacation/edit_permission_request/<int:request_id>/',views.edit_permission_request, name='edit_permission_request'),
   path('edit_request/<int:request_id>/', views.edit_request, name='edit_request'), 
    path('delete_request/<int:request_id>/',views.delete_request, name='delete_request'),
     path('approve-request/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject-request/<int:request_id>/', views.reject_request, name='reject_request'),
     path('view_permission_request/<int:request_id>/', views.view_permission_request, name='view_permission_request'),
    # 
    
    path('overlay/add/', views.add_overlay_description, name='add_overlay_description'),
    path('overlay/view/', views.overlay_description_view, name='overlay_description_view'),
]
