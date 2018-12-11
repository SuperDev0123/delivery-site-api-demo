from django.conf.urls import url, include
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token
from .views import UserView, BookingViewSet, WarehouseViewSet, FileUploadView, upload_status

urlpatterns = [
    url(r'^auth/user/$', UserView.as_view()),
    url(r'^api-token-auth/', obtain_jwt_token),
    url(r'^api-token-verify/', verify_jwt_token),
    url(r'^bookings/$', BookingViewSet.as_view({'get': 'list'})),
    url(r'^bookings/(?P<pk>\d+)/$', BookingViewSet.as_view({'get': 'list', 'put': 'update'})),
    url(r'^warehouses/', WarehouseViewSet.as_view({'get': 'list'})),
    url(r'^share/upload/(?P<filename>[^/]+)$', FileUploadView.as_view()),
    url(r'^share/upload-status/', upload_status),
]