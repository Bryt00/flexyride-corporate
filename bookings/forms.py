from django import forms
from bookings.models import TransportationRequest, PassengerInfo

class TransportationRequestForm(forms.ModelForm):
    class Meta:
        model = TransportationRequest
        fields = [
            'journey_type', 'priority_level', 'customer_reference',
            'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'destination_address', 'destination_latitude', 'destination_longitude',
            'departure_datetime', 'return_datetime', 'duration_hours',
            'flight_number', 'airline', 'flight_datetime', 'airport_name',
            'requested_vehicle_category', 'vehicles_requested_count', 'passenger_count',
            'luggage_requirements', 'accessibility_required', 'child_seats_count',
            'executive_vehicle_required', 'additional_stops_notes'
        ]
        widgets = {
            'departure_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'return_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'flight_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'pickup_address': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'destination_address': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
        }

class PassengerInfoForm(forms.ModelForm):
    class Meta:
        model = PassengerInfo
        fields = ['full_name', 'phone_number', 'email', 'is_primary']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
        }
