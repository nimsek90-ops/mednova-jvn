from datetime import timedelta
from django import forms
from django.utils import timezone
from .models import (ScheduleSession, ScheduleBlock, PatientRegistration, Bed,
    Supplier, PurchaseOrder, Medicine, ClinicalDraft, Investigation, HospitalFAQ)
from .forms import clean_phone


class SessionForm(forms.ModelForm):
    class Meta:
        model = ScheduleSession
        fields = ['weekday', 'start', 'end', 'duration', 'buffer', 'mode', 'visit_type', 'capacity']
        labels = {'duration':'Consultation minutes', 'buffer':'Buffer minutes', 'capacity':'Maximum bookings per session'}
        widgets = {'start':forms.TimeInput(attrs={'type':'time'}), 'end':forms.TimeInput(attrs={'type':'time'})}

    def clean(self):
        data = super().clean()
        if data.get('start') and data.get('end') and data['end'] <= data['start']:
            raise forms.ValidationError('A session must end after it starts. Use separate sessions for each day.')
        return data


class BlockForm(forms.ModelForm):
    class Meta:
        model = ScheduleBlock
        fields = ['start', 'end', 'reason']
        widgets = {field: forms.DateTimeInput(attrs={'type':'datetime-local'}) for field in ['start','end']}


class PublishForm(forms.Form):
    first = forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    last = forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = PatientRegistration
        fields = ['emergency_name', 'emergency_phone', 'guardian', 'consent']

    def clean_emergency_phone(self):
        return clean_phone(self.cleaned_data.get('emergency_phone',''))


class BedForm(forms.ModelForm):
    class Meta:
        model = Bed
        fields = ['label', 'ward', 'room_type']


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact']


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'medicine', 'quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.filter(active=True)
        self.fields['medicine'].queryset = Medicine.objects.filter(safety_status='available', expiry__gte=timezone.localdate())


class ReceiptForm(forms.Form):
    order = forms.ModelChoiceField(queryset=PurchaseOrder.objects.none())
    quantity = forms.IntegerField(min_value=1, max_value=100000)
    reference = forms.CharField(max_length=120, label='Unique delivery / GRN reference')
    verified = forms.BooleanField(label='I verified this batch, expiry, quantity and condition against the delivery.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].queryset = PurchaseOrder.objects.filter(status='approved').select_related('medicine','supplier')


class PartialIssueForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=1000)
    key = forms.UUIDField(widget=forms.HiddenInput)
    verified = forms.BooleanField(label='I verified the patient, prescription, selected batch and remaining quantity.')


class DraftForm(forms.ModelForm):
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    class Meta:
        model = ClinicalDraft
        fields = ['complaint','examination','assessment','plan','follow_up']
        widgets = {field: forms.Textarea(attrs={'rows':3}) for field in fields}


class InvestigationForm(forms.ModelForm):
    class Meta:
        model = Investigation
        fields = ['category','name']


class ResultForm(forms.Form):
    result = forms.CharField(max_length=3000, widget=forms.Textarea(attrs={'rows':3}))
    critical = forms.BooleanField(required=False)


class FAQForm(forms.ModelForm):
    class Meta:
        model = HospitalFAQ
        fields = ['question','answer','language','approved']


class AssistantForm(forms.Form):
    question = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'placeholder':'Ask about hospital services or choose an action'}))
    topic = forms.ChoiceField(choices=[('doctors','Find a doctor'),('appointments','My appointments'),('reports','My reports / prescriptions'),('billing','Billing help'),('directions','Hospital directions'),('medicine','Medicine help'),('support','Talk to support')])
