from django import forms
from quotations.models import ProviderQuote, CustomerQuote

class ProviderQuoteForm(forms.ModelForm):
    class Meta:
        model = ProviderQuote
        fields = ['offered_cost', 'proposed_vehicle', 'valid_until', 'notes']
        widgets = {
            'offered_cost': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'proposed_vehicle': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'notes': forms.Textarea(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'rows': 3}),
        }

class CustomerQuoteForm(forms.ModelForm):
    class Meta:
        model = CustomerQuote
        fields = ['final_customer_price', 'provider_cost']
        widgets = {
            'final_customer_price': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'provider_cost': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white', 'readonly': 'readonly'}),
        }
