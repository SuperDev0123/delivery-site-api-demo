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
class HomePageView(TemplateView):

	template_name = "pages/home.html"


class SharePageView(TemplateView):
	template_name = 'pages/share.html'  


def handle_uploaded_file(f,request):
	user_id = request.user.id
	cleintEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
	dme_account_num = cleintEmployeObject[0].fk_id_dme_client.dme_account_num
	with open('/var/www/html/DeliverMe/media/onedrive/' + dme_account_num + '_' + f.name, 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)

def upload(request):
	handle_uploaded_file(request.FILES['file'])
	html = "<html><body>Uploaded File :  %s </body></html>"  % request.FILES['file'].name      
	return HttpResponse(html)


def allbookings(request):
	context = {'latest_question_list': 'latest_question_list'}
	return render(request, 'pages/allbookings.html', context)

def syncbooking(request):
	data = bookings.objects.all()
	booking_data = {
	    "bookings": data
	}
	return render_to_response("pages/sync_booking.html", booking_data)
