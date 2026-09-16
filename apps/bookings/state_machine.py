from django.core.exceptions import ValidationError


class BookingStateMachine:
    """
    State machine enforcing valid status transitions for TransportationRequest (US-01 through US-22).
    """

    ALLOWED_TRANSITIONS = {
        'DRAFT': ['SUBMITTED', 'CANCELLED'],
        'SUBMITTED': ['APPROVED_INTERNAL', 'REJECTED', 'CANCELLED'],
        'APPROVED_INTERNAL': ['QUOTE_REQUESTED', 'CANCELLED'],
        'QUOTE_REQUESTED': ['QUOTE_RECEIVED', 'CANCELLED', 'REJECTED'],
        'QUOTE_RECEIVED': ['QUOTE_SENT', 'CANCELLED'],
        'QUOTE_SENT': ['QUOTE_ACCEPTED', 'REJECTED', 'CANCELLED'],
        'QUOTE_ACCEPTED': ['PAYMENT_PENDING', 'PAID', 'VEHICLE_ASSIGNED', 'CANCELLED'],
        'PAYMENT_PENDING': ['PAID', 'CANCELLED'],
        'PAID': ['VEHICLE_ASSIGNED', 'CANCELLED'],
        'VEHICLE_ASSIGNED': ['DISPATCHED', 'CANCELLED'],
        'DISPATCHED': ['IN_PROGRESS', 'CANCELLED'],
        'IN_PROGRESS': ['COMPLETED', 'CANCELLED'],
        'COMPLETED': [],  # Terminal state
        'CANCELLED': [],  # Terminal state
        'REJECTED': [],   # Terminal state
    }

    @classmethod
    def can_transition(cls, current_status, new_status):
        if current_status == new_status:
            return True
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, [])
        return new_status in allowed

    @classmethod
    def validate_transition(cls, current_status, new_status):
        if not cls.can_transition(current_status, new_status):
            raise ValidationError(
                f"Invalid status transition from '{current_status}' to '{new_status}'. "
                f"Allowed transitions from '{current_status}': {cls.ALLOWED_TRANSITIONS.get(current_status, [])}"
            )
