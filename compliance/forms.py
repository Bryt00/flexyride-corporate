from django import forms
from compliance.models import ComplianceDocument

class ComplianceDocumentForm(forms.ModelForm):
    class Meta:
        model = ComplianceDocument
        fields = [
            'target_type', 'document_type', 'document_file',
            'document_number', 'issue_date', 'expiry_date'
        ]
        widgets = {
            'target_type': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'document_type': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'document_file': forms.FileInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'document_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 bg-[#121829] border border-white/10 rounded-xl text-white'}),
        }
