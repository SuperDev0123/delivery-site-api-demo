from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token
from .views import UserViewSet, BookingViewSet, BookingLinesView, BookingLineDetailsView, WarehouseViewSet, FileUploadView, upload_status, booking
from .views_api import bok_0_bookingkeys, bok_1_headers, bok_2_lines, st_tracking, allied_tracking, hunter_tracking, \
    trigger_allied, trigger_st, all_trigger, bok_1_to_bookings

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
urlpatterns = router.urls

urlpatterns += [
    url(r'^api-token-auth/', obtain_jwt_token),
    url(r'^api-token-verify/', verify_jwt_token),
    url(r'^bookinglines/', BookingLinesView.as_view()),
    url(r'^bookinglinedetails/', BookingLineDetailsView.as_view()),
    url(r'^booking/$', booking),
    url(r'^bookings/$', BookingViewSet.as_view({'get': 'list'})),
    url(r'^bookings/(?P<pk>\d+)/$', BookingViewSet.as_view({'get': 'list', 'put': 'update', 'post': 'create'})),
    url(r'^warehouses/', WarehouseViewSet.as_view({'get': 'list'})),
    url(r'^share/upload/(?P<filename>[^/]+)$', FileUploadView.as_view()),
    url(r'^share/upload-status/', upload_status),

    url(r'^bok_0_bookingskeys/', bok_0_bookingkeys),
    url(r'^bok_1_headers/', bok_1_headers),
    url(r'^bok_2_lines/', bok_2_lines),
    url(r'^bok_1_to_bookings/', bok_1_to_bookings),

    url(r'^st_tracking/', st_tracking),
    url(r'^allied_tracking/', allied_tracking),
    url(r'^hunter_tracking/', hunter_tracking),

    url(r'^trigger_allied/', trigger_allied),
    url(r'^trigger_st/', trigger_st),
    url(r'^trigger_all/', all_trigger),
]
