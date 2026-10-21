import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(
            role="admin", approval="approved", is_staff=True, is_superuser=True
        )
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    ROLES = [
        ("patient", "Patient"),
        ("doctor", "Doctor"),
        ("receptionist", "Receptionist"),
        ("pharmacist", "Pharmacist"),
        ("admin", "Admin"),
    ]
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default="patient")
    approval = models.CharField(
        max_length=12,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("denied", "Denied"),
        ],
        default="approved",
    )
    review_note = models.CharField(max_length=300, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    def __str__(self):
        return self.name or self.email


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=400, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="doctor_profile"
    )
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True)
    qualification = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    experience = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(70)]
    )
    bio = models.TextField(max_length=1500, blank=True)
    fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )


class Slot(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="slots")
    start = models.DateTimeField()
    booked = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    consultation_type = models.CharField(max_length=10, default="both", choices=[("both", "Either"), ("in_person", "In person"), ("video", "Video")])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start"], name="unique_doctor_slot"
            )
        ]
        ordering = ["start"]


class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="appointments"
    )
    slot = models.ForeignKey(
        Slot, on_delete=models.PROTECT, related_name="appointments"
    )
    mode = models.CharField(
        max_length=10, choices=[("in_person", "In person"), ("video", "Video")]
    )
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
    )
    reason = models.CharField(max_length=400)
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-slot__start"]

    @property
    def short_id(self):
        return str(self.id).split("-")[0].upper()


class Prescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.OneToOneField(
        Appointment, on_delete=models.PROTECT, related_name="prescription"
    )
    instructions = models.TextField(max_length=3000)
    created = models.DateTimeField(auto_now_add=True)
    dispensed = models.BooleanField(default=False)
    dispensed_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name="+"
    )
    dispensed_at = models.DateTimeField(null=True)


class Medicine(models.Model):
    name = models.CharField(max_length=150)
    batch = models.CharField(max_length=60)
    expiry = models.DateField()
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "batch"], name="unique_medicine_batch"
            )
        ]

    def __str__(self):
        return f"{self.name} | {self.batch}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="items"
    )
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    dose = models.CharField(max_length=200)
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)]
    )


def report_path(instance, filename):
    return f"reports/{uuid.uuid4().hex}{instance.extension}"


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        Appointment, on_delete=models.PROTECT, related_name="reports"
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    title = models.CharField(max_length=120)
    extension = models.CharField(max_length=5)
    file = models.FileField(upload_to=report_path)
    created = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.PROTECT, related_name="payment"
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(
        max_length=16,
        default="unpaid",
        choices=[
            ("unpaid", "Unpaid"),
            ("paid", "Paid"),
            ("refund_due", "Refund due"),
            ("refunded", "Refunded"),
        ],
    )
    method = models.CharField(max_length=12, blank=True)
    order_id = models.CharField(max_length=100, blank=True)
    provider_id = models.CharField(max_length=100, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    received_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name="+"
    )
    updated = models.DateTimeField(auto_now=True)


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=120, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]


class RateBucket(models.Model):
    key = models.CharField(max_length=64, unique=True)
    count = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField()


class Signal(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12)
    payload = models.JSONField(default=dict)
    created = models.DateTimeField(default=timezone.now)


class Hospital(models.Model):
    name = models.CharField(max_length=120, default="MedNova")
    address = models.TextField(max_length=600, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    ambulance = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    privacy_email = models.EmailField(blank=True)
    legal_name = models.CharField(max_length=200, blank=True)
    retention_days = models.PositiveIntegerField(default=1095)
    opening_hours = models.CharField(max_length=600, blank=True)
    cancellation_policy = models.TextField(max_length=2000, blank=True)
    cancellation_notice_minutes = models.PositiveIntegerField(default=0)


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT, null=True, blank=True)
    message = models.CharField(max_length=200)
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-pk"]


class WellnessEntry(models.Model):
    patient = models.ForeignKey(User, on_delete=models.PROTECT)
    date = models.DateField()
    sleep = models.DecimalField(max_digits=4, decimal_places=1, validators=[MinValueValidator(0), MaxValueValidator(24)])
    water = models.DecimalField(max_digits=4, decimal_places=1, validators=[MinValueValidator(0), MaxValueValidator(30)])
    exercise_days = models.PositiveSmallIntegerField(validators=[MaxValueValidator(7)])
    stress = models.PositiveSmallIntegerField(validators=[MaxValueValidator(10)])
    score = models.PositiveSmallIntegerField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['patient', 'date'], name='wellness_patient_date')]
        ordering = ['-date']


class WellnessRevision(models.Model):
    entry = models.ForeignKey(WellnessEntry, on_delete=models.PROTECT, related_name='revisions')
    values = models.JSONField()
    created = models.DateTimeField(auto_now_add=True)


class HealthAssessment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    answers = models.JSONField()
    result = models.JSONField()

    class Meta:
        ordering = ['-created']


class ClinicalNote(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    complaint = models.TextField(max_length=3000)
    examination = models.TextField(max_length=3000, blank=True)
    assessment = models.TextField(max_length=3000, blank=True)
    plan = models.TextField(max_length=3000)
    follow_up = models.TextField(max_length=1500, blank=True)
    correction_reason = models.CharField(max_length=300, blank=True)
    version = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['appointment', 'version'], name='clinical_note_version')]
        ordering = ['-version']


class QueueCounter(models.Model):
    date = models.DateField(unique=True)
    number = models.PositiveIntegerField(default=0)


class QueueEntry(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='queue_entry')
    date = models.DateField()
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=12, default='waiting', choices=[('waiting', 'Waiting'), ('called', 'Called'), ('completed', 'Completed'), ('cancelled', 'Cancelled')])
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['date', 'number'], name='queue_daily_token')]
        ordering = ['date', 'number']


class StockMovement(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='movements')
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, null=True)
    quantity = models.IntegerField()
    balance = models.PositiveIntegerField()
    reason = models.CharField(max_length=120)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created', '-pk']


class DeliveryOutbox(models.Model):
    notification = models.OneToOneField(Notification, on_delete=models.PROTECT)
    dedupe_key = models.CharField(max_length=120, unique=True)
    status = models.CharField(max_length=12, default='pending', choices=[('pending', 'Pending'), ('sending', 'Sending'), ('sent', 'Sent'), ('failed', 'Failed'), ('unavailable', 'Unavailable')])
    attempts = models.PositiveSmallIntegerField(default=0)
    lease_until = models.DateTimeField(null=True)
    next_attempt = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=120, blank=True)
