# pages/urls.py
from django.urls import path

from .views import HomePageView, SharePageView  # new
from . import views
urlpatterns = [
    path('share/', SharePageView.as_view(), name='share'), # new
    path('share/upload/', views.upload, name='upload'), # new
    path('', HomePageView.as_view(), name='home'),  
    path('allbookings/', views.allbookings, name='allbookings'),
    path('booking/', views.bookings, name='bookings'),
]