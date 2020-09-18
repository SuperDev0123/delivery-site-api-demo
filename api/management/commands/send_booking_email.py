from django.core.management.base import BaseCommand

from api.outputs.emails import send_booking_email_using_template


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("booking_id")
        parser.add_argument("email_type")

    def handle(self, *args, **options):
        booking_id = options["booking_id"]
        email_type = options["email_type"]

        if email_type not in [
            "General Booking",
            "Return Booking",
            "POD",
            "Futile Pickup",
            "Unpacked Return Booking",
        ]:
            self.stdout.write(
                self.style.ERROR(("Error: email_type should be one of the following."))
            )
            self.stdout.write(
                self.style.WARNING(
                    '"General Booking", "Return Booking", "POD", "Futile Pickup", "Unpacked Return Booking"'
                )
            )
        else:
            print(
                f"Test sending booking email - Booking ID: {booking_id}, Email Type: {email_type}"
            )
            send_booking_email_using_template(booking_id, email_type, "TESTER")
