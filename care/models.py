import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


def specialty_key(value):
    return ' '.join(value.casefold().split()).replace('orthopaed','orthoped').replace('paediatr','pediatr').replace('gynaec','gynec').replace('counselling','counseling').replace('anaesthe','anesthe')


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
    must_change_password = models.BooleanField(default=False)
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
    daily_limit = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(500)])
    location = models.CharField(max_length=160, blank=True)
    specialties = models.ManyToManyField('Specialty', blank=True, related_name='doctors')


class Specialty(models.Model):
    name = models.CharField(max_length=120, unique=True)
    normalized_name = models.CharField(max_length=120, unique=True, editable=False)
    departments = models.ManyToManyField(Department, related_name='specialties')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name = ' '.join(self.name.split())
        self.normalized_name = specialty_key(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Slot(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="slots")
    start = models.DateTimeField()
    booked = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    duration = models.PositiveSmallIntegerField(default=12, validators=[MinValueValidator(5), MaxValueValidator(180)])
    buffer = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(120)])
    session = models.ForeignKey('ScheduleSession', null=True, blank=True, on_delete=models.PROTECT)
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
            ("no_show", "No show"),
        ],
    )
    reason = models.CharField(max_length=400)
    cancellation_reason = models.CharField(max_length=300, blank=True)
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
    generic_name = models.CharField(max_length=150, blank=True)
    strength = models.CharField(max_length=80, blank=True)
    dosage_form = models.CharField(max_length=80, blank=True)
    manufacturer = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=120, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    reorder_level = models.PositiveIntegerField(default=10)
    purchase_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    safety_status = models.CharField(max_length=12, default='available', choices=[('available', 'Available'), ('quarantined', 'Quarantined'), ('recalled', 'Recalled'), ('damaged', 'Damaged')])

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
    route = models.CharField(max_length=60, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration_text = models.CharField(max_length=100, blank=True)
    dispensed_quantity = models.PositiveSmallIntegerField(default=0)
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)]
    )

    @property
    def remaining(self):
        return self.quantity - self.dispensed_quantity

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(dispensed_quantity__lte=models.F('quantity')), name='issue_not_above_prescribed')]


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
    status = models.CharField(max_length=20, default='waiting', choices=[('waiting', 'Waiting'), ('called', 'Called'), ('in_consultation', 'In consultation'), ('completed', 'Completed'), ('cancelled', 'Cancelled')])
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


class ScheduleSession(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.PROTECT)
    weekday = models.PositiveSmallIntegerField(choices=list(enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])))
    start = models.TimeField()
    end = models.TimeField()
    duration = models.PositiveSmallIntegerField(default=15, validators=[MinValueValidator(5), MaxValueValidator(180)])
    buffer = models.PositiveSmallIntegerField(default=5, validators=[MaxValueValidator(120)])
    mode = models.CharField(max_length=10, default='both', choices=[('both', 'Either'), ('in_person', 'In person'), ('video', 'Video')])
    visit_type = models.CharField(max_length=12, default='new', choices=[('new', 'New patient'), ('follow_up', 'Follow-up'), ('urgent', 'Reserved urgent')])
    capacity = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1), MaxValueValidator(500)])
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['weekday', 'start']
        constraints = [models.UniqueConstraint(fields=['doctor', 'weekday', 'start'], name='schedule_doctor_day_start'),
            models.CheckConstraint(condition=models.Q(end__gt=models.F('start')), name='schedule_positive_session'),
            models.CheckConstraint(condition=models.Q(duration__gte=5, duration__lte=180, buffer__lte=120, capacity__gte=1, weekday__lte=6), name='schedule_valid_limits')]


class ScheduleBlock(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.PROTECT)
    start = models.DateTimeField()
    end = models.DateTimeField()
    reason = models.CharField(max_length=120, choices=[('break', 'Break'), ('leave', 'Leave / holiday'), ('rounds', 'Ward rounds'), ('procedure', 'Procedure'), ('other', 'Unavailable')])

    class Meta:
        ordering = ['start']
        constraints = [models.CheckConstraint(condition=models.Q(end__gt=models.F('start')), name='schedule_positive_block')]


class PatientRegistration(models.Model):
    patient = models.OneToOneField(User, on_delete=models.PROTECT, related_name='registration')
    mrn = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    emergency_name = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=600, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    guardian = models.CharField(max_length=120, blank=True)
    consent = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    @property
    def display_mrn(self):
        return 'MN-' + self.mrn.hex.upper()


class Bed(models.Model):
    label = models.CharField(max_length=80, unique=True)
    ward = models.CharField(max_length=100)
    room_type = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.ward} / {self.label} ({self.room_type})'


class Admission(models.Model):
    patient = models.ForeignKey(User, on_delete=models.PROTECT, related_name='admissions')
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='admission_requests')
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    bed = models.OneToOneField(Bed, null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, default='requested', choices=[('requested', 'Requested'), ('admitted', 'Admitted'), ('discharge_ready', 'Discharge ready'), ('discharged', 'Discharged'), ('cancelled', 'Cancelled')])
    last_bed = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class DispensingEvent(models.Model):
    key = models.UUIDField(default=uuid.uuid4, unique=True)
    item = models.ForeignKey(PrescriptionItem, on_delete=models.PROTECT, related_name='issues')
    pharmacist = models.ForeignKey(User, on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    created = models.DateTimeField(auto_now_add=True)


class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    contact = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100000)])
    received = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, default='requested', choices=[('requested', 'Requested'), ('approved', 'Approved'), ('received', 'Received'), ('cancelled', 'Cancelled')])
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(received__lte=models.F('quantity'), quantity__gte=1), name='receipt_not_above_order')]

    def __str__(self):
        return f'#{self.pk}: {self.supplier} / {self.medicine} ({self.quantity-self.received} outstanding)'


class GoodsReceipt(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT)
    reference = models.CharField(max_length=120, unique=True)
    quantity = models.PositiveIntegerField()
    received_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)


class ClinicalDraft(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    complaint = models.TextField(max_length=3000)
    examination = models.TextField(max_length=3000, blank=True)
    assessment = models.TextField(max_length=3000, blank=True)
    plan = models.TextField(max_length=3000)
    follow_up = models.TextField(max_length=1500, blank=True)
    revision = models.PositiveIntegerField(default=1)
    updated = models.DateTimeField(auto_now=True)


class Investigation(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT, related_name='investigations')
    ordered_by = models.ForeignKey(User, on_delete=models.PROTECT)
    category = models.CharField(max_length=12, choices=[('lab', 'Laboratory'), ('radiology', 'Radiology'), ('referral', 'Referral')])
    name = models.CharField(max_length=180)
    status = models.CharField(max_length=12, default='ordered', choices=[('ordered', 'Ordered'), ('resulted', 'Resulted'), ('acknowledged', 'Acknowledged')])
    result = models.TextField(max_length=3000, blank=True)
    critical = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)


class HospitalFAQ(models.Model):
    question = models.CharField(max_length=200)
    answer = models.TextField(max_length=2000)
    language = models.CharField(max_length=2, default='en', choices=[('en', 'English'), ('mr', 'Marathi'), ('hi', 'Hindi')])
    approved = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)


class AssistantEscalation(models.Model):
    patient = models.ForeignKey(User, on_delete=models.PROTECT)
    topic = models.CharField(max_length=24, choices=[('appointment', 'Appointments'), ('billing', 'Billing'), ('technical', 'Technical support'), ('clinical', 'Contact clinical team')])
    resolved = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)


class SupportCase(models.Model):
    CATEGORIES = [('appointments', 'Appointments / reception'), ('reports', 'Reports / assigned clinician'),
        ('pharmacy', 'Pharmacy'), ('billing', 'Billing'), ('clinical', 'Clinical team'),
        ('privacy', 'Privacy / administrator'), ('technical', 'Portal technical support')]
    STATUSES = [(v, v.replace('_', ' ').title()) for v in
        ['open', 'assigned', 'in_progress', 'waiting_for_patient', 'escalated', 'resolved', 'closed']]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.PROTECT, related_name='support_cases')
    category = models.CharField(max_length=16, choices=CATEGORIES)
    priority = models.CharField(max_length=8, default='routine', choices=[('routine', 'Routine'), ('priority', 'Priority')])
    status = models.CharField(max_length=20, choices=STATUSES, default='open')
    summary = models.TextField(max_length=2000)
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT, null=True, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='assigned_support_cases')
    consented_at = models.DateTimeField()
    request_key = models.UUIDField(unique=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated']
        indexes = [models.Index(fields=['category', 'status'], name='support_queue_idx')]

    @property
    def reference(self):
        return 'MN-' + str(self.pk).upper()


class SupportMessage(models.Model):
    case = models.ForeignKey(SupportCase, on_delete=models.PROTECT, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    text = models.TextField(max_length=2000)
    internal = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created', 'pk']


class VideoAttendance(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT)
    patient_consented_at = models.DateTimeField(null=True)
    admitted_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)


class AppointmentReview(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='review')
    patient = models.ForeignKey(User, on_delete=models.PROTECT, related_name='submitted_reviews')
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='received_reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=2000, blank=True, default='')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='review_rating_1_to_5')]


class WaitingList(models.Model):
    patient = models.ForeignKey(User, on_delete=models.PROTECT, related_name='waiting_requests')
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    mode = models.CharField(max_length=10, choices=[('in_person', 'In person'), ('video', 'Video')])
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['patient','doctor','mode'], name='waiting_patient_doctor_mode')]
