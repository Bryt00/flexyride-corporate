from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_future_datetime(value):
    if value and value < timezone.now():
        raise ValidationError("Datetime cannot be in the past.")


def validate_booking_request(instance):
    """
    Model clean() validator for TransportationRequest (US-01, US-02, US-05).
    """
    errors = {}

    if instance.departure_datetime and instance.departure_datetime < timezone.now():
        errors['departure_datetime'] = "Departure datetime must be in the future."

    if instance.journey_type == 'RETURN' and instance.return_datetime:
        if instance.return_datetime <= instance.departure_datetime:
            errors['return_datetime'] = "Return datetime must be after departure datetime."

    if instance.journey_type == 'AIRPORT_TRANSFER':
        if not instance.flight_number and not instance.airport_name:
            errors['flight_number'] = "Airport transfer requests must provide flight number or airport name."

    if instance.child_seats_count > instance.passenger_count:
        errors['child_seats_count'] = "Number of child seats cannot exceed total passenger count."

    if errors:
        raise ValidationError(errors)
