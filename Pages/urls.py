# pages/urls.py
from django.urls import path

from .views import HomePageView, SharePageView  # new
from . import views
urlpatterns = [
    path('share/', SharePageView.as_view(), name='share'), # new
    path('share/upload/', views.upload, name='upload'), # new
    path('', HomePageView.as_view(), name='home'),
    path('booking/', views.booking, name='booking'),
    path('allbookings/', views.allbookings, name='allbookings'),
]