from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token
from .views import *
from .views_api import *

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'bookings', BookingsViewSet, basename='bookings')
router.register(r'booking', BookingViewSet, basename='booking')
router.register(r'bookinglines', BookingLinesViewSet, basename='bookinglines')
router.register(r'bookinglinedetails', BookingLineDetailsViewSet, basename='bookinglinedetails')
router.register(r'comm', CommsViewSet, basename='comm')
router.register(r'note', NotesViewSet, basename='note')
router.register(r'packagetype', PackageTypesViewSet, basename='packagetype')
urlpatterns = router.urls

urlpatterns += [
    url(r'^api-token-auth/', obtain_jwt_token),
    url(r'^api-token-verify/', verify_jwt_token),
    url(r'^warehouses/', WarehouseViewSet.as_view({'get': 'list'})),
    url(r'^share/upload/(?P<filename>[^/]+)$', FileUploadView.as_view()),
    url(r'^share/attachments/(?P<filename>[^/]+)$', AttachmentsUploadView.as_view()),
    url(r'^share/upload-status/', upload_status),
    url(r'^download-pdf/', download_pdf),
    url(r'^download-pod/', download_pod),

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

    url(r'^booking_allied/', booking_allied),
    url(r'^booking_st/', booking_st),
    url(r'^get_label_allied/', get_label_allied),
    url(r'^excel/', returnexcel),
    url(r'^get_label_st/', get_label_st),
    url(r'^cancel_booking/', cancel_booking),
    url(r'^st_create_order/', st_create_order),
    url(r'^get_order_summary/', get_order_summary),
    url(r'^pricing_allied/', pricing_allied),

    url(r'^suburb/', getSuburbs),
    url(r'^attachments/', getAttachmentsHistory),

    url(r'^temp_excel/', returntempexcel),


    url(r'^get_booking_history/', get_booking_history),
    url(r'^get_all_statuses/', get_all_statuses),
]
