from django import forms
from fleet.models import Vehicle, Driver

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'make', 'model', 'year', 'color', 'registration_number',
            'category', 'seating_capacity', 'luggage_capacity',
            'has_accessibility', 'has_child_seat', 'wifi_available', 'water_provided'
        ]
        widgets = {
            'make': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'model': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'year': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'color': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'registration_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'category': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'seating_capacity': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'luggage_capacity': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
        }

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            'full_name', 'phone_number', 'license_number',
            'license_expiry', 'photo', 'languages_spoken'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'license_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'license_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'languages_spoken': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
        }
