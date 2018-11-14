from django.views.generic.base import TemplateView
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.views import generic
from django.utils import timezone



class HomePageView(TemplateView):

    template_name = "pages/home.html"


class SharePageView(TemplateView):
    template_name = 'pages/share.html'   

def handle_uploaded_file(f):
    with open('/var/www/html/DeliverMe/media/onedrive/2222016067_' + f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

def upload(request):
	handle_uploaded_file(request.FILES['file'])
	html = "<html><body>Uploaded File :  %s </body></html>"  % request.FILES['file'].name      
	return HttpResponse(html)

def bookings(request):
	context = {'latest_question_list': 'latest_question_list'}
	return render(request, 'pages/booking.html', context)

def allbookings(request):
	context = {'latest_question_list': 'latest_question_list'}
	return render(request, 'pages/allbookings.html', context)
