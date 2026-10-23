import io
import re
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import User, DoctorProfile, Department, Medicine, Hospital, Slot


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.ROLES[:-1])
    consent = forms.BooleanField(
        label="I have read the Privacy Policy and Terms and Conditions."
    )

    class Meta:
        model = User
        fields = ["name", "email", "phone", "role", "password1", "password2", "consent"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone(self):
        return clean_phone(self.cleaned_data.get("phone", ""))

    def save(self, commit=True):
        u = super().save(False)
        u.approval = "approved" if u.role == "patient" else "pending"
        if commit:
            u.save()
            if u.role == 'patient':
                from .models import PatientRegistration
                PatientRegistration.objects.get_or_create(patient=u)
        return u


def clean_phone(value):
    if value and not re.fullmatch(r"\+?[0-9 ()-]{7,20}", value):
        raise forms.ValidationError("Enter a valid phone number.")
    return value


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "phone", "date_of_birth"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}

    def clean_date_of_birth(self):
        value = self.cleaned_data.get("date_of_birth")
        if value and value > timezone.localdate():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return value

    def clean_phone(self):
        return clean_phone(self.cleaned_data.get("phone", ""))


class ReceptionPatientForm(RegisterForm):
    duplicate_reviewed = forms.BooleanField(required=False, label='I reviewed any existing patient with this phone number; this is a separate person.')
    role = forms.ChoiceField(choices=[("patient", "Patient")], initial="patient", widget=forms.HiddenInput)


    def clean(self):
        data = super().clean()
        phone = data.get('phone', '')
        if phone and User.objects.filter(role='patient', phone=phone).exists() and not data.get('duplicate_reviewed'):
            raise forms.ValidationError('Possible duplicate phone number. Search existing patients first; confirm separate identity before proceeding. No records were merged.')
        return data


class DoctorForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = [
            "department",
            "qualification",
            "registration_number",
            "experience",
            "bio",
            "fee",
            "daily_limit",
            "location",
        ]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["department"].queryset = Department.objects.filter(active=True)
        self.fields["department"].required = True
        self.fields['daily_limit'].required = False

    def clean_daily_limit(self):
        return self.cleaned_data.get('daily_limit') or 0


class AvailabilityForm(forms.Form):
    duration = forms.IntegerField(min_value=5, max_value=180, required=False, initial=12, label='Consultation minutes')
    buffer = forms.IntegerField(min_value=0, max_value=120, required=False, initial=0, label='Buffer minutes')
    consultation_type = forms.ChoiceField(choices=[("both", "Either"), ("in_person", "In person"), ("video", "Video")], required=False)
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    end = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    def clean(self):
        d = super().clean()
        if d.get("date") and not timezone.localdate() <= d[
            "date"
        ] <= timezone.localdate() + timedelta(days=90):
            raise forms.ValidationError("Choose a date within the next 90 days.")
        if d.get("start") and d.get("end") and d["end"] <= d["start"]:
            raise forms.ValidationError("End time must be after start time.")
        if d.get("start") and d.get("end") and d.get("date"):
            from datetime import datetime
            start = timezone.make_aware(datetime.combine(d["date"], d["start"]))
            end = timezone.make_aware(datetime.combine(d["date"], d["end"]))
            if start <= timezone.now() or end - start < timedelta(minutes=(d.get('duration') or 12)+(d.get('buffer') or 0)):
                raise forms.ValidationError("Choose a future range long enough for consultation plus buffer.")
        return d


class BookingForm(forms.Form):
    mode = forms.ChoiceField(choices=[("in_person", "In person"), ("video", "Video")])
    reason = forms.CharField(
        max_length=400,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Reason for visit",
    )
    consent = forms.BooleanField(
        label="I agree to share this appointment and its reports with my assigned doctor."
    )


class SlotEditForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = ["start", "consultation_type"]
        widgets = {"start": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"})}

    def clean_start(self):
        value = self.cleaned_data["start"]
        if not timezone.now() < value <= timezone.now() + timedelta(days=90):
            raise forms.ValidationError("Choose a future time within 90 days.")
        return value


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ["name", "generic_name", "strength", "dosage_form", "manufacturer", "batch", "expiry", "stock", "price", "purchase_price", "location", "barcode", "reorder_level"]
        widgets = {"expiry": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['purchase_price'].required = False
        self.fields['reorder_level'].required = False

    def clean_purchase_price(self):
        return self.cleaned_data.get('purchase_price') or 0

    def clean_reorder_level(self):
        value = self.cleaned_data.get('reorder_level')
        return 10 if value is None else value

    def clean_expiry(self):
        value = self.cleaned_data["expiry"]
        if value < timezone.localdate():
            raise forms.ValidationError("Cannot add expired medicine.")
        return value


class HospitalForm(forms.ModelForm):
    class Meta:
        model = Hospital
        fields = [
            "name",
            "legal_name",
            "opening_hours",
            "address",
            "phone",
            "ambulance",
            "email",
            "privacy_email",
            "retention_days",
            "cancellation_policy",
            "cancellation_notice_minutes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "cancellation_policy": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_phone(self):
        return clean_phone(self.cleaned_data.get("phone", ""))

    def clean_ambulance(self):
        return clean_phone(self.cleaned_data.get("ambulance", ""))

    def clean_retention_days(self):
        days = self.cleaned_data["retention_days"]
        if not 1 <= days <= 36500:
            raise forms.ValidationError(
                "Choose a retention period between 1 and 36500 days."
            )
        return days


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "description", "active"]


class UploadForm(forms.Form):
    title = forms.CharField(max_length=120)
    file = forms.FileField(
        help_text="JPEG or PNG, up to 5 MB. PDF requires the hospital antivirus scanner."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].help_text = f"JPEG or PNG, up to {settings.REPORT_MAX_BYTES // (1024 * 1024)} MB. PDF requires the hospital antivirus scanner."

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > settings.REPORT_MAX_BYTES:
            raise forms.ValidationError(f"The maximum upload size is {settings.REPORT_MAX_BYTES // (1024 * 1024)} MB.")
        raw = f.read()
        if raw.startswith(b"%PDF-"):
            if not settings.CLAMAV_COMMAND:
                raise forms.ValidationError(
                    "PDF upload is unavailable until antivirus scanning is configured. Upload a PNG or JPEG instead."
                )
            with tempfile.TemporaryDirectory() as folder:
                p = Path(folder) / "upload.pdf"
                p.write_bytes(raw)
                try:
                    result = subprocess.run(
                        [settings.CLAMAV_COMMAND, "--no-summary", str(p)],
                        capture_output=True,
                        timeout=25,
                        check=False,
                    )
                    if result.returncode != 0:
                        raise forms.ValidationError(
                            "The file did not pass the security scan."
                        )
                except (OSError, subprocess.TimeoutExpired):
                    raise forms.ValidationError(
                        "The scanner is unavailable. Please try again later."
                    )
            self.extension = ".pdf"
            return ContentFile(raw, name="report.pdf")
        try:
            with Image.open(io.BytesIO(raw)) as im:
                if im.format not in ("JPEG", "PNG") or im.width * im.height > 20000000:
                    raise ValueError()
                im.load()
                output = io.BytesIO()
                im.convert("RGB").save(output, format="JPEG", quality=92)
                self.extension = ".jpg"
                return ContentFile(output.getvalue(), name="report.jpg")
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
        ):
            raise forms.ValidationError("Upload a valid JPEG or PNG image.")
