from pages.models import bookings
import django_filters

class BookingFilter(django_filters.FilterSet):
	booking_id = django_filters.CharFilter(lookup_expr='iexact')

	class Meta:
		model = bookings
		fields = ['booking_id', 'qty']