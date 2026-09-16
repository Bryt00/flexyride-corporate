from django import forms
from bookings.models import TransportationRequest, PassengerInfo

class TransportationRequestForm(forms.ModelForm):
    priority_level = forms.CharField(required=False, initial='STANDARD')
    vehicles_requested_count = forms.IntegerField(required=False, initial=1)
    child_seats_count = forms.IntegerField(required=False, initial=0)
    flight_number = forms.CharField(required=False)
    airport_name = forms.CharField(required=False)
    airline = forms.CharField(required=False)
    customer_reference = forms.CharField(required=False)
    luggage_requirements = forms.CharField(required=False)
    duration_hours = forms.IntegerField(required=False)
    accessibility_required = forms.BooleanField(required=False)
    executive_vehicle_required = forms.BooleanField(required=False)
    additional_stops_notes = forms.CharField(required=False)

    departure_datetime = forms.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}
        )
    )
    return_datetime = forms.DateTimeField(
        required=False,
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}
        )
    )
    flight_datetime = forms.DateTimeField(
        required=False,
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}
        )
    )

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
            'journey_type': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'pickup_address': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'placeholder': 'e.g. Airport City, Accra or Kotoka Airport Terminal 3'}),
            'destination_address': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'placeholder': 'e.g. MTN House, Ridge, Accra or Tema Port'}),
            'requested_vehicle_category': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'passenger_count': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'min': 1, 'max': 50}),
            'additional_stops_notes': forms.Textarea(attrs={'rows': 2, 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white resize-none', 'placeholder': 'Optional stops, special chauffeur instructions...'}),
            'flight_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'placeholder': 'e.g. BA 078 or KQ 508'}),
            'airport_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'placeholder': 'Kotoka International Airport (ACC)'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('priority_level'):
            cleaned_data['priority_level'] = 'STANDARD'
        if not cleaned_data.get('vehicles_requested_count'):
            cleaned_data['vehicles_requested_count'] = 1
        if cleaned_data.get('child_seats_count') is None:
            cleaned_data['child_seats_count'] = 0
            
        # If journey_type is an airport journey and airport_name/flight_number not given, default to Kotoka International Airport
        if cleaned_data.get('journey_type') in ['AIRPORT_TRANSFER', 'AIRPORT_MEET_GREET']:
            if not cleaned_data.get('flight_number') and not cleaned_data.get('airport_name'):
                cleaned_data['airport_name'] = 'Kotoka International Airport (ACC)'

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.priority_level:
            instance.priority_level = 'STANDARD'
        if not instance.vehicles_requested_count:
            instance.vehicles_requested_count = 1
        if instance.child_seats_count is None:
            instance.child_seats_count = 0
        if instance.journey_type in ['AIRPORT_TRANSFER', 'AIRPORT_MEET_GREET']:
            if not instance.airport_name and not instance.flight_number:
                instance.airport_name = 'Kotoka International Airport (ACC)'
        if commit:
            instance.save()
        return instance


class PassengerInfoForm(forms.ModelForm):
    is_primary = forms.BooleanField(required=False, initial=True)
    email = forms.EmailField(required=False)

    class Meta:
        model = PassengerInfo
        fields = ['full_name', 'phone_number', 'email', 'is_primary']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'placeholder': 'e.g. Kwame Mensah'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'placeholder': '+233 24 000 0000'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'placeholder': 'passenger@company.com'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_primary = True
        if commit:
            instance.save()
        return instance
