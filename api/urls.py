from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token

from .views import *
from .views_api import *
from .views_external_apis import *
from .fp_apis import st_apis as st_apis

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"bookings", BookingsViewSet, basename="bookings")
router.register(r"booking", BookingViewSet, basename="booking")
router.register(r"bookinglines", BookingLinesViewSet, basename="bookinglines")
router.register(
    r"bookinglinedetails", BookingLineDetailsViewSet, basename="bookinglinedetails"
)
router.register(r"comm", CommsViewSet, basename="comm")
router.register(r"note", NotesViewSet, basename="note")
router.register(r"packagetype", PackageTypesViewSet, basename="packagetype")
router.register(r"bookingstatus", BookingStatusViewSet, basename="bookingstatus")
router.register(r"statushistory", StatusHistoryViewSet, basename="statushistory")
router.register(r"fp", FPViewSet, basename="fp")
router.register(r"status", StatusViewSet, basename="status")
router.register(r"api_bcl", ApiBCLViewSet, basename="api_bcl")
router.register(r"reports", DmeReportsViewSet, basename="reports")
urlpatterns = router.urls

urlpatterns += [
    # Auth
    url(r"^api-token-auth/", obtain_jwt_token),
    url(r"^api-token-verify/", verify_jwt_token),
    url(r"^warehouses/", WarehouseViewSet.as_view({"get": "list"})),
    url(r"^suburb/", getSuburbs),
    url(r"^attachments/", getAttachmentsHistory),
    # Uploads
    url(r"^share/upload/(?P<filename>[^/]+)$", FileUploadView.as_view()),
    url(r"^upload/attachments/", AttachmentsUploadView.as_view()),
    url(r"^upload/label/", LabelUploadView.as_view()),
    url(r"^upload/pod/", PodUploadView.as_view()),
    url(r"^share/upload-status/", upload_status),
    # Downloads
    url(r"^download-pdf/", download_pdf),
    url(r"^download-pod/", download_pod),
    url(r"^download-connote/", download_connote),
    url(r"^download-manifest/", download_manifest),
    # Generates
    url(r"^generate-csv/", generate_csv),
    url(r"^generate-xml/", generate_xml),
    url(r"^generate-pdf/", generate_pdf),
    url(r"^generate-manifest/", generate_manifest),
    # BIOPAK push apis
    url(r"^bok_0_bookingskeys/", bok_0_bookingkeys),
    url(r"^bok_1_headers/", bok_1_headers),
    url(r"^bok_2_lines/", bok_2_lines),
    url(r"^bok_1_to_bookings/", bok_1_to_bookings),
    # ST apis
    url(r"^st_tracking/", st_apis.tracking),
    url(r"^st_book/", st_apis.book),
    url(r"^st_get_label/", st_apis.get_label),
    url(r"^st_edit_book/", st_apis.edit_book),
    url(r"^st_cancel_book/", st_apis.cancel_book),
    (?# url(r"^st_create_order/", st_apis.create_order),)
    url(r"^st_create_order/", st_apis.order_summary),
    # Allied apis
    url(r"^allied_tracking/", allied_tracking),
    url(r"^trigger_allied/", trigger_allied),
    url(r"^trigger_all/", all_trigger),
    url(r"^booking_allied/", booking_allied),
    url(r"^get_label_allied/", get_label_allied),
    url(r"^pricing_allied/", pricing_allied),
    # Hunter apis
    url(r"^hunter_tracking/", hunter_tracking),
    # External apis
    url(r"^get_booking_status_by_consignment/", get_booking_status_by_consignment),
]
