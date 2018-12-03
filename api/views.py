from django.shortcuts import render
from rest_framework import views, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework import viewsets
from django.http import JsonResponse
from django.db.models import Q
from api.serializers import BookingSerializer
from pages.models import bookings

class UserView(APIView):
	def post(self, request, format=None):
		return JsonResponse({'username': request.user.username})

class BookingViewSet(viewsets.ModelViewSet):
	serializer_class = BookingSerializer

	def get_queryset(self):
		searchType = self.request.query_params.get('searchType', None)
		keyword = self.request.query_params.get('keyword', None)

		if searchType is not None:
			if keyword.isdigit():
				queryset = bookings.objects.filter(Q(id__contains=keyword) | Q(b_bookingID_Visual=keyword) | Q(b_dateBookedDate__contains=keyword) | Q(puPickUpAvailFrom_Date__contains=keyword) | Q(b_clientReference_RA_Numbers=keyword) | Q(b_status__contains=keyword) | Q(vx_freight_provider__contains=keyword) | Q(vx_serviceName__contains=keyword) | Q(s_05_LatestPickUpDateTimeFinal__contains=keyword) | Q(s_06_LatestDeliveryDateTimeFinal__contains=keyword) | Q(v_FPBookingNumber__contains=keyword) | Q(puCompany__contains=keyword) | Q(deToCompanyName__contains=keyword))
			else:
				queryset = bookings.objects.filter(Q(id__contains=keyword) | Q(b_dateBookedDate__contains=keyword) | Q(puPickUpAvailFrom_Date__contains=keyword) | Q(b_clientReference_RA_Numbers=keyword) | Q(b_status__contains=keyword) | Q(vx_freight_provider__contains=keyword) | Q(vx_serviceName__contains=keyword) | Q(s_05_LatestPickUpDateTimeFinal__contains=keyword) | Q(s_06_LatestDeliveryDateTimeFinal__contains=keyword) | Q(v_FPBookingNumber__contains=keyword) | Q(puCompany__contains=keyword) | Q(deToCompanyName__contains=keyword))
		else:
			queryset = bookings.objects.all()

		return queryset