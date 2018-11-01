# pages/urls.py
from django.urls import path

from .views import AccountView # new

urlpatterns = [
    path('login/', AccountView.as_view(), name='login'), # new
      
]