from django.urls import path
from .import views

app_name = 'finance'

urlpatterns = [
    path('money-request/', views.money, name='financial_form'), 
    path('request-detail/', views.request_detail_view, name='request_detail'), 
  path('specific-detail/<int:request_id>/', views.specific_detail_view, name='specific_detail'), 
  path('update-request/<int:request_id>/', views.update_request, name='update_request'),
 path('delete_confirmation/<int:request_id>/', views.delete_confirmation, name='delete_confirmation'),
    path('delete_request/<int:request_id>/', views.delete_request, name='delete_request'),
    
  path('approve_request/<int:request_id>/', views.approve_request, name='approve_request'),
path('All-financial-request/',views.financial_requests_view,name='all_financial_request'),
# path('edit_request/<int:request_id>/', views.edit_request_view, name='edit_request'),

]