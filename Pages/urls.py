# pages/urls.py
from django.urls import path

from .views import HomePageView, SharePageView # new

urlpatterns = [
    path('share/', SharePageView.as_view(), name='share'), # new
    path('', HomePageView.as_view(), name='home'),  
]