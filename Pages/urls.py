# pages/urls.py
from django.urls import path

from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
	path('', views.HomeView.as_view(), name='home'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('share/', views.share, name='share'), # new
    path('share/upload/', views.upload, name='upload'), # new
    path('share/upload/status/', views.upload_status, name='upload_status'), # new
    path('booking/', views.booking, name='booking'),
    path('allbookings/', views.allbookings, name='allbookings'),
]