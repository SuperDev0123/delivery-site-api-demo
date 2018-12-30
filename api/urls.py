from django.conf.urls import url, include
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token
from .views import UserView, BookingViewSet, BookingLinesView, WarehouseViewSet, FileUploadView, upload_status
from .views_api import bok_0_bookingkeys, bok_1_headers, bok_2_lines, st_tracking

urlpatterns = [
    url(r'^auth/user/$', UserView.as_view()),
    url(r'^api-token-auth/', obtain_jwt_token),
    url(r'^api-token-verify/', verify_jwt_token),
    url(r'^bookings/$', BookingViewSet.as_view({'get': 'list'})),
    url(r'^bookinglines/', BookingLinesView.as_view()),
    url(r'^bookings/(?P<pk>\d+)/$', BookingViewSet.as_view({'get': 'list', 'put': 'update'})),
    url(r'^warehouses/', WarehouseViewSet.as_view({'get': 'list'})),
    url(r'^share/upload/(?P<filename>[^/]+)$', FileUploadView.as_view()),
    url(r'^share/upload-status/', upload_status),

    url(r'^bok_0_bookingskeys/', bok_0_bookingkeys),
    url(r'^bok_1_headers/', bok_1_headers),
    url(r'^bok_2_lines/', bok_2_lines),

    url(r'^st_tracking/', st_tracking),
]
