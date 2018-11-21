# pages/urls.py
from django.urls import path

from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
	path('', views.HomeView.as_view(), name='home'),
    path('login/', auth_views.LoginView.as_view()),
    path('share/', views.share, name='share'), # new
    path('share/upload/', views.upload, name='upload'), # new
    path('booking/', views.booking, name='booking'),
    path('allbookings/', views.allbookings, name='allbookings'),
]