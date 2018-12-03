from django.shortcuts import render
from rest_framework import views, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework import viewsets
from django.http import JsonResponse
from api.serializers import BookingSerializer
from pages.models import bookings

class UserView(APIView):
    def post(self, request, format=None):
        return JsonResponse({'username': request.user.username})

class BookingViewSet(viewsets.ModelViewSet):
    queryset = bookings.objects.all()
    serializer_class = BookingSerializer