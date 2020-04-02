from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token

from .views import *
from .views_api import *
from .views_external_apis import *
from .fp_apis import apis as fp_apis
from .file_operations.uploads import get_upload_status

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
router.register(r"emailtemplates", EmailTemplatesViewSet, basename="emailtemplates")
router.register(r"options", OptionsViewSet, basename="options")
router.register(r"status", StatusViewSet, basename="status")
router.register(r"api_bcl", ApiBCLViewSet, basename="api_bcl")
router.register(r"reports", DmeReportsViewSet, basename="reports")
router.register(r"pricing", ApiBookingQuotesViewSet, basename="pricing")
router.register(r"sqlqueries", SqlQueriesViewSet, basename="sqlqueries")
router.register(r"vehicles", VehiclesViewSet, basename="vehicles")
router.register(r"timings", TimingsViewSet, basename="timing")
router.register(r"availabilities", AvailabilitiesViewSet, basename="availabilities")
router.register(r"costs", CostsViewSet, basename="costs")
router.register(r"pricing_rules", PricingRulesViewSet, basename="pricing_rules")

router.register(
    r"fp-store-booking-log", FPStoreBookingLog, basename="fp-store-booking-log"
)
router.register(r"bok_0_bookingskeys", BOK_0_ViewSet, basename="bok0")
router.register(r"bok_1_headers", BOK_1_ViewSet, basename="bok1")
router.register(r"bok_2_lines", BOK_2_ViewSet, basename="bok2")
router.register(r"bok_3_lines_data", BOK_3_ViewSet, basename="bok3")
router.register(r"files", FilesViewSet, basename="files")
router.register(r"bookingsets", BookingSetsViewSet, basename="bookingsets")

urlpatterns = router.urls

urlpatterns += [
    # Auth
    url(r"^api-token-auth/", obtain_jwt_token),
    url(r"^api-token-verify/", verify_jwt_token),
    url(r"^warehouses/", WarehouseViewSet.as_view({"get": "list"})),
    url(r"^suburb/", getSuburbs),
    url(r"^attachments/", getAttachmentsHistory),
    url(
        r"^password_reset/",
        include("django_rest_passwordreset.urls", namespace="password_reset"),
    ),
    # Uploads
    url(r"^upload/", FileUploadView.as_view()),
    url(r"^upload/status/", get_upload_status),
    # Downloads
    url(r"^download/", download),
    # Delete
    url(r"^delete-file/", delete_file),
    # Generates
    url(r"^generate-csv/", generate_csv),
    url(r"^generate-xml/", generate_xml),
    url(r"^generate-pdf/", generate_pdf),
    url(r"^generate-manifest/", generate_manifest),
    # BOK apis(BIOPAK push apis, Get API - no auth)
    url(r"^boks/", boks),
    # url(r"^bok_1_to_bookings/", bok_1_to_bookings),
    # Freight Provider apis
    url(r"^fp-api/(?P<fp_name>[^/]+)/tracking/", fp_apis.tracking),
    url(r"^fp-api/(?P<fp_name>[^/]+)/reprint/", fp_apis.reprint),
    url(r"^fp-api/(?P<fp_name>[^/]+)/rebook/", fp_apis.rebook),
    url(r"^fp-api/(?P<fp_name>[^/]+)/book/", fp_apis.book),
    url(r"^fp-api/(?P<fp_name>[^/]+)/pod/", fp_apis.pod),
    url(r"^fp-api/(?P<fp_name>[^/]+)/get-label/", fp_apis.get_label),
    url(r"^fp-api/(?P<fp_name>[^/]+)/edit-book/", fp_apis.edit_book),
    url(r"^fp-api/(?P<fp_name>[^/]+)/cancel-book/", fp_apis.cancel_book),
    url(r"^fp-api/(?P<fp_name>[^/]+)/create-order/", fp_apis.create_order),
    url(r"^fp-api/(?P<fp_name>[^/]+)/get-order-summary/", fp_apis.get_order_summary),
    url(r"^fp-api/pricing/", fp_apis.pricing),
    # External apis
    url(r"^get_booking_status_by_consignment/", get_booking_status_by_consignment),
]
