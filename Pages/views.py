from django.views.generic.base import TemplateView


class HomePageView(TemplateView):

    template_name = "pages/home.html"


class SharePageView(TemplateView):
    template_name = 'pages/share.html'    