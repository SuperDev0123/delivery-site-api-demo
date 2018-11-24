from django.views.generic.base import TemplateView
from django.shortcuts import render, get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import redis

# from .filters import BookingFilter
from .utils import clearFileCheckHistory, getFileCheckHistory
from .models import Client_employees, DME_clients, bookings

class HomeView(TemplateView):
    template_name = "pages/home.html"

@login_required(login_url='/login/')
def share(request):
	template_name = 'pages/share.html'
	context = {}
	return render(request, template_name, context)

@login_required(login_url='/login/')
def handle_uploaded_file(requst, dme_account_num, f):
	# live code
	with open('/var/www/html/DeliverMe/media/onedrive/' + str(dme_account_num) + '_' + f.name, 'wb+') as destination:
	# local code
	# with open('/Users/admin/work/goldmine/xlsimport/upload/' + f.name, 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)

	clearFileCheckHistory(str(dme_account_num) + '_' + f.name)

@login_required(login_url='/login/')
def upload(request):
	user_id = request.user.id
	clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
	dme_account_num = clientEmployeObject[0].fk_id_dme_client.dme_account_num
	handle_uploaded_file(request, dme_account_num, request.FILES['file'])
	html = str(dme_account_num) + '_' + request.FILES['file'].name
	return HttpResponse(html)

@login_required(login_url='/login/')
def upload_status(request):
	user_id = request.user.id
	clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
	dme_account_num = clientEmployeObject[0].fk_id_dme_client.dme_account_num
	result = getFileCheckHistory(str(dme_account_num) + '_' + request.GET.get('filename'))

	if result == 0:
		return JsonResponse({'status_code': 0})

	if len(result) == 0:
		return JsonResponse({'status_code': 1})
	else:
		return JsonResponse({'status_code': 2, 'errors': result})


@login_required(login_url='/login/')
def booking(request):
	context = {}
	return render(request, 'pages/booking.html', context)

@login_required(login_url='/login/')
def allbookings(request):
	search = request.GET.get('search')

	if search is not None:
		if search.isdigit():
			booking_search = bookings.objects.filter(Q(booking_id__contains=search) | Q(qty=search) | Q(booked_date__contains=search) | Q(pickup_from_date__contains=search) | Q(ref_number=search) | Q(status__contains=search) | Q(service__contains=search) | Q(pickup_by__contains=search) | Q(latest_delivery__contains=search) | Q(consignment__contains=search) | Q(pick_up_entity__contains=search) | Q(delivery_entity__contains=search))
		else:
			booking_search = bookings.objects.filter(Q(booking_id__contains=search) | Q(booked_date__contains=search) | Q(pickup_from_date__contains=search) | Q(status__contains=search) | Q(service__contains=search) | Q(pickup_by__contains=search) | Q(latest_delivery__contains=search) | Q(consignment__contains=search) | Q(pick_up_entity__contains=search) | Q(delivery_entity__contains=search))
		return render(request, 'pages/allbookings.html', {'bookings': booking_search})

	booking_list = bookings.objects.all()
	booking_data = { "bookings": booking_list }
	return render_to_response("pages/allbookings.html", booking_data)
