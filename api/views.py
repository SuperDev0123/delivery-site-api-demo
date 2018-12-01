from django.shortcuts import render
from rest_framework import views, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from django.http import JsonResponse

class UserView(APIView):
    def post(self, request, format=None):
        return JsonResponse({'username': request.user.username})