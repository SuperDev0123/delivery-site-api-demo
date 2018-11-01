from django.views.generic.base import TemplateView


class AccountView(TemplateView):

    template_name = "pages/login.html"