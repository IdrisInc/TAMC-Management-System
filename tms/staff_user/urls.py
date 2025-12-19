from django.urls import path
from . import views

app_name = 'staff_user'

urlpatterns = [
  path('',views.index,name ='welcome'),
    path('login', views.login_process, name='staff_login_process'),
    path('register/', views.user_registration, name='user_registration'),
    path('registered_users/', views.view_registered_users, name='registered_users'),
    path('dashboard/', views.dashboard, name='staff/dashboard'),
    
    path('my-profile/', views. view_user_profile, name='my_profile'),
      path('profile/update/', views.update_profile, name='update_profile'),  # URL to update the profile
      path('view-user/<int:user_id>/',views.view_user_detail,name='view_user_detail'),
      path('change-password/', views.change_password, name='change_password'),
     path('chat/', views.chat_view, name='chat'),
    path('fetch_messages/', views.fetch_messages, name='fetch_messages'),
    path('message/success/', views.message_success, name='message_success'),
    path('logout/', views.logout_user, name='logout'),
    path('password_reset/', views.password_reset_form, name='password_reset'),
    path('password_reset/done/', views.password_reset_done, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('404/', views.custom_404_page, name='custom_404_page'),  # Include custom 404 page URL
]

handler404 = views.custom_404_page  # Define handler404 after including custom 404 page view
