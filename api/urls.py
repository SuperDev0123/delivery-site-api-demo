from django.conf.urls import url, include
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token
from .views import UserView

urlpatterns = [
    url(r'^auth/user/$', UserView.as_view()),
    url(r'^api-token-auth/', obtain_jwt_token),
    url(r'^api-token-verify/', verify_jwt_token),
]