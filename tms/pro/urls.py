from django.urls import path
from . import views

app_name = 'pro'

urlpatterns = [
    path('programs/', views.program_list, name='program_list'),
    path('programs/create/', views.program_create, name='program_create'),
    path('programs/<int:program_id>/edit/', views.program_edit, name='program_edit'),
]
