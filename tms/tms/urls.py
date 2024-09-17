"""
URL configuration for tms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf.urls import handler404
from staff_user.views import custom_404_page
from django.conf import settings
from django.conf.urls.static import static


handler404 = custom_404_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/',include('django.contrib.auth.urls')),
    path('staff/',include('staff_user.urls',namespace='staff_user')),
    path('ems/',include('equipment.urls', namespace='equipment')),
    path('finance/',include('finance.urls', namespace='finance')),
    path('pro/',include('pro.urls',namespace='PRO')),
    path('vacation/',include ('vacation.urls',namespace= 'vacation')),
    path('404/', custom_404_page), 
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    