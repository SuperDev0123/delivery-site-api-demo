from django.views.generic.base import TemplateView
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from pages.models import Client_employees
from pages.models import DME_clients
from pages.models import bookings
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required

def home(TemplateView):
	template_name = "pages/home.html"
	context = {}
	return render_to_response(template_name, context)

@login_required(login_url='/login/')
def share(TemplateView):
	template_name = 'pages/share.html'
	context = {}
	return render_to_response(template_name, context)

@login_required(login_url='/login/')
def handle_uploaded_file(dme_account_num, f):
	with open('/var/www/html/DeliverMe/media/onedrive/' + str(dme_account_num) + '_' + f.name, 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)

@login_required(login_url='/login/')
def upload(request):
	user_id = request.user.id
	cleintEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
	dme_account_num = cleintEmployeObject[0].fk_id_dme_client.dme_account_num
	handle_uploaded_file(dme_account_num, request.FILES['file'])
	html = str(dme_account_num) + '_' + request.FILES['file'].name
	return HttpResponse(html)

@login_required(login_url='/login/')
def booking(request):
	context = {}
	return render(request, 'pages/booking.html', context)

@login_required(login_url='/login/')
def allbookings(request):
	data = bookings.objects.all()
	booking_data = { "bookings": data }
	return render_to_response("pages/allbookings.html", booking_data)
